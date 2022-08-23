from enum import Flag, auto
from biothings.web.handlers.query import BaseAPIHandler

from .utils import NGDUndefinedException, UNDEFINED_STR
from .service.umls_service import UMLSResourceManager
from .service.ngd_service import NGDService, DocStatsService, NGDCache, DocStatsCache, Term, TermPair


class StarMode(Flag):
    """
    When a pair of terms is passed in as arguments, this Enum class can be used to indicate which term should be treated as a star graph of terms.
    """
    NIL = 0              # none of the paired terms should expand into a star
    LEFT = auto()        # (LEFT == 1) only the left (i.e. 1st) term of the pair should expand into a star
    RIGHT = auto()       # (RIGHT == 2) only the right (i.e. 2nd) term of the pair should expand into a star
    BOTH = LEFT | RIGHT  # (BOTH == 3) both terms should expand

    @classmethod
    def value_of(cls, value: str):
        if (value is None) or (not value):
            return cls.NIL

        # E.g. when member_name == "NIL", member is StarMode.NIL
        for member_name, member in cls.__members__.items():
            if member_name == value.upper():
                return member
        else:
            raise ValueError(f"'{cls.__name__}' enum not found for '{value}'")


class ErrorReason:
    @classmethod
    def wrong_terms_quantity(cls, terms: list):
        return f"Exact 2 UMLS terms are required. Got {terms}, {len(terms)} term(s)."

    @classmethod
    def unknown_star_mode(cls, arg_star_mode: str):
        return f"star-mode accepts empty string, 'nil, 'left', 'right', and 'both', case-insensitive. Got '{arg_star_mode}'."

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
            'star-mode': {
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
            'star-mode': {
                'type': str,
                'required': False
            }
        }
    }

    doc_stats_cache = DocStatsCache(unary_capacity=10240, bipartite_capacity=10240)
    ngd_cache = NGDCache(capacity=10240)

    def initialize(self, umls_resouce_manager: UMLSResourceManager):
        super().initialize()

        # This umls_resouce_manager argument is injected from the URLSpec in config_web/semmeddb.py
        self.umls_resouce_manager = umls_resouce_manager

    def prepare(self):
        super().prepare()

        # TODO inject from URLSpec?
        self.subject_field_name = "subject.umls"
        self.object_field_name = "object.umls"

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

    def make_star_graph(self, term: Term):
        prefix = "UMLS:"

        root_term = term.root
        if not root_term.startswith(prefix):
            root_term = "UMLS:" + root_term

        # "narrower_relationships" is a name defined in config_web/semmeddb.py
        nr_client = self.umls_resouce_manager.get_resource_client("narrower_relationships")
        leaf_terms = nr_client.query(root_term)
        if leaf_terms:
            leaf_terms = [term[5:] if term.startswith(prefix) else term for term in leaf_terms]

        term.make_star_graph(leaf_terms)
        return term

    async def get(self, *args, **kwargs):
        arg_umls = self.args['umls']
        if len(arg_umls) != 2:
            self.write_error(status_code=400, reason=ErrorReason.wrong_terms_quantity(arg_umls))
            return

        arg_star_mode = self.args.get('star-mode')
        try:
            star_mode = StarMode.value_of(arg_star_mode)
        except ValueError:
            self.write_error(status_code=400, reason=ErrorReason.unknown_star_mode(arg_star_mode))
            return

        term_x = Term(root=arg_umls[0])
        term_y = Term(root=arg_umls[1])
        if star_mode & StarMode.LEFT:  # star_mode is LEFT or BOTH
            term_x = self.make_star_graph(term_x)
        if star_mode & StarMode.RIGHT:  # star_mode is RIGHT or BOTH
            term_y = self.make_star_graph(term_y)
        term_pair = TermPair(term_x=term_x, term_y=term_y)

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
            result["star_mode"] = star_mode.name.lower()
            if star_mode is not StarMode.NIL:
                result["leaf_umls"] = [{term.root: term.leaves} for term in term_pair if term.star_graph_mark]

            self.finish(result)
            return

    async def post(self, *args, **kwargs):
        # Step 1: Accept two arguments
        arg_umls = self.args['umls']  # should be a list of 2-termed sublists, e.g. [['a', 'b'], ['c', 'd']]
        arg_star_mode = self.args.get('star-mode')

        # Step 2: verify argument `star-mode`, raise an error simultaneously if found
        try:
            star_mode = StarMode.value_of(arg_star_mode)
        except ValueError:
            self.write_error(status_code=400, reason=ErrorReason.unknown_star_mode(arg_star_mode))
            return

        # Step 3: verify argument `umls` and calculate NGDs. If any pair of terms failed the verification, do not raise an error simultaneously but wrap the error in the response.
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

                term_x = Term(root=terms[0])
                term_y = Term(root=terms[1])
                if star_mode & StarMode.LEFT:  # star_mode is LEFT or BOTH
                    term_x = self.make_star_graph(term_x)
                if star_mode & StarMode.RIGHT:  # star_mode is RIGHT or BOTH
                    term_y = self.make_star_graph(term_y)
                term_pair = TermPair(term_x=term_x, term_y=term_y)

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
                    result["star_mode"] = star_mode.name.lower()
                    if star_mode is not StarMode.NIL:
                        result["leaf_umls"] = [{term.root: term.leaves} for term in term_pair if term.star_graph_mark]

                    yield result

        results = [res async for res in yield_results(arg_umls)]
        self.finish(results)
