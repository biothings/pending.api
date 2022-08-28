from enum import Flag, auto
from biothings.web.handlers.query import BaseAPIHandler

from web.utils import NGDUndefinedException, UNDEFINED_STR
from web.service.umls_service import UMLSResourceManager
from web.service.ngd_service import NGDService, DocStatsService, NGDCache, DocStatsCache, Term, TermPair


class ExpansionMode(Flag):
    """
    When a pair of terms is passed in as arguments, this Enum class can be used to indicate which term should be expanded.
    """
    NIL = 0              # none of the paired terms should expand
    LEFT = auto()        # (LEFT == 1) only the left (i.e. 1st) term of the pair should expand
    RIGHT = auto()       # (RIGHT == 2) only the right (i.e. 2nd) term of the pair should expand
    BOTH = LEFT | RIGHT  # (BOTH == 3) both terms should expand

    @classmethod
    def mode_of(cls, name: str):
        if (name is None) or (not name):
            return cls.NIL

        # E.g. when member_name == "NIL", member is ExpansionMode.NIL
        for member_name, member in cls.__members__.items():
            if member_name == name.upper():
                return member
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{name}'")


class ErrorReason:
    @classmethod
    def wrong_terms_quantity(cls, terms: list):
        return f"Exact 2 UMLS terms are required. Got {terms}, {len(terms)} term(s)."

    @classmethod
    def unknown_expansion_mode(cls, arg_expand: str):
        return f"Parameter 'expand' accepts empty string, 'nil, 'left', 'right', and 'both', case-insensitive. Got '{arg_expand}'."

    @classmethod
    def zero_document_freq(cls, term: str):
        return f"the document frequency of term '{term}' is 0 in SemMedDB API."

    @classmethod
    def terms_not_a_list(cls, terms):
        return f"A list of 2 UMLS terms are required. Got {terms}, a {type(terms).__name__}."


class SemmedNGDHandler(BaseAPIHandler):
    name = "ngd"

    kwargs = {
        **BaseAPIHandler.kwargs,

        'GET': {
            'umls': {
                'type': list,
                # 'max': 2,  # exactly 2 umls are required. Will check the cardinality in get()
                'required': True
            },
            'expand': {
                'type': str,
                'required': False
            }
        },
        'POST': {
            'umls': {
                'type': list,
                'max': 1000,
                'required': True
            },
            'expand': {
                'type': str,
                'required': False
            }
        }
    }

    doc_stats_cache = DocStatsCache(unary_capacity=10240, bipartite_capacity=10240)
    ngd_cache = NGDCache(capacity=10240)

    def initialize(self, subject_field_name: str, object_field_name: str, umls_resouce_manager: UMLSResourceManager):
        super().initialize()

        # The following 3 arguments are injected from the URLSpec in config_web/<plugin_name>.py

        # Note that only {"type": "keyword"} fields are supported for NGD calculation
        # (since we are going to use ES "terms" filter)
        self.subject_field_name = subject_field_name
        self.object_field_name = object_field_name

        self.umls_resouce_manager = umls_resouce_manager

    def prepare(self):
        super().prepare()

        """
        Here `self.biothings.metadata` is a `biothings.web.services.metadata.BiothingsESMetadata` instance, which would include 3 attributes:

        - `biothing_mappings`, enriched ES mappings for this API
        - `biothing_licenses`, transformed license info for this API
        - `biothing_metadata`, transformed from "_meta" field stored in ES mapping

        E.g. for pending-semmeddb, the `self.biothings.metadata.biothing_metadata[self.biothings.config.ES_DOC_TYPE]` content covers
        <mapping_json>["pending-semmeddb"]["mappings"]["_meta"]
        """
        self.doc_total = self.biothings.metadata.biothing_metadata[self.biothings.config.ES_DOC_TYPE]["stats"]["total"]

        self.doc_stats_service = DocStatsService(
            es_async_client=self.biothings.elasticsearch.async_client,  # injected by handler's application instace (created by APILauncher)
            es_index_name=self.biothings.config.ES_INDEX,  # injected by handler's application instace (created by APILauncher)
            subject_field_name=self.subject_field_name,
            object_field_name=self.object_field_name,
            doc_total=self.doc_total
        )

        self.ngd_service = NGDService(
            doc_stats_service=self.doc_stats_service,
            doc_stats_cache=self.doc_stats_cache,
            ngd_cache=self.ngd_cache
        )

    def expand_term(self, term: Term):
        prefix = "UMLS:"
        prefix_len = len(prefix)

        root_term = term.root
        if not root_term.startswith(prefix):
            root_term = "UMLS:" + root_term

        # "narrower_relationships" is a name defined in config_web/semmeddb.py
        nr_client = self.umls_resouce_manager.get_resource_client("narrower_relationships")
        leaf_terms = nr_client.query(root_term)
        if leaf_terms:
            leaf_terms = [term[prefix_len:] if term.startswith(prefix) else term for term in leaf_terms]

        term.expand(leaf_terms)
        return term

    def pair_two_terms(self, term_x_root: str, term_y_root: str, expansion_mode: ExpansionMode) -> TermPair:
        term_x = Term(root=term_x_root)
        term_y = Term(root=term_y_root)
        if expansion_mode & ExpansionMode.LEFT:  # expansion_mode is LEFT or BOTH
            term_x = self.expand_term(term_x)
        if expansion_mode & ExpansionMode.RIGHT:  # expansion_mode is RIGHT or BOTH
            term_y = self.expand_term(term_y)
        term_pair = TermPair(term_x=term_x, term_y=term_y)
        return term_pair

    async def get(self, *args, **kwargs):
        arg_umls = self.args['umls']
        if len(arg_umls) != 2:
            self.write_error(status_code=400, reason=ErrorReason.wrong_terms_quantity(arg_umls))
            return

        arg_expand = self.args.get('expand')
        try:
            expansion_mode = ExpansionMode.mode_of(arg_expand)
        except ValueError:
            self.write_error(status_code=400, reason=ErrorReason.unknown_expansion_mode(arg_expand))
            return

        term_pair = self.pair_two_terms(term_x_root=arg_umls[0], term_y_root=arg_umls[1], expansion_mode=expansion_mode)
        try:
            ngd = await self.ngd_service.calculate_ngd(term_pair)
            result = {
                "ngd": ngd
            }
        except NGDUndefinedException as ue:
            # Here we assume that `ue.cause` is an NGDZeroCountException, which is the only possibility so far.
            # If in the future there are other types of `ue.cause`, should check `type(ne.cause)` first in this clause.
            causative_term = ue.cause.term
            reason = ErrorReason.zero_document_freq(causative_term.root)
            result = {
                "ngd": UNDEFINED_STR,
                "reason": reason
            }
        finally:
            result["umls"] = [term.root for term in term_pair]
            result["expand"] = expansion_mode.name.lower()
            if expansion_mode is not ExpansionMode.NIL:
                result["leaf_umls"] = {term.root: term.leaves for term in term_pair if term.has_expanded}

            self.finish(result)
            return

    async def post(self, *args, **kwargs):
        # Step 1: Accept two arguments
        arg_umls = self.args['umls']  # should be a list of 2-termed sublists, e.g. [['a', 'b'], ['c', 'd']]
        arg_expand = self.args.get('expand')

        # Step 2: verify argument `expand`, raise an error simultaneously if found
        try:
            expansion_mode = ExpansionMode.mode_of(arg_expand)
        except ValueError:
            self.write_error(status_code=400, reason=ErrorReason.unknown_expansion_mode(arg_expand))
            return

        # Step 3: verify argument `umls` and calculate NGDs.
        # If any pair of terms failed the verification, do not raise an error simultaneously but wrap the error in the response.
        async def yield_results(arg_umls: list):
            for terms in arg_umls:
                if not isinstance(terms, list):
                    yield {
                        "umls": terms,
                        "ngd": UNDEFINED_STR,
                        "reason": ErrorReason.terms_not_a_list(terms)
                    }
                    continue

                if len(terms) != 2:
                    yield {
                        "umls": terms,
                        "ngd": UNDEFINED_STR,
                        "reason": ErrorReason.wrong_terms_quantity(terms)
                    }
                    continue

                term_pair = self.pair_two_terms(term_x_root=terms[0], term_y_root=terms[1], expansion_mode=expansion_mode)
                try:
                    ngd = await self.ngd_service.calculate_ngd(term_pair)
                    result = {
                        "ngd": ngd
                    }
                except NGDUndefinedException as ue:
                    # Here we assume that `ue.cause` is an NGDZeroCountException, which is the only possibility so far.
                    # If in the future there are other types of `ue.cause`, should check `type(ne.cause)` first in this clause.
                    causative_term = ue.cause.term
                    reason = ErrorReason.zero_document_freq(causative_term.root)
                    result = {
                        "ngd": UNDEFINED_STR,
                        "reason": reason
                    }
                finally:
                    result["umls"] = [term.root for term in term_pair]
                    result["expand"] = expansion_mode.name.lower()
                    if expansion_mode is not ExpansionMode.NIL:
                        result["leaf_umls"] = [{term.root: term.leaves} for term in term_pair if term.has_expanded]

                    yield result

        results = [res async for res in yield_results(arg_umls)]
        self.finish(results)
        return
