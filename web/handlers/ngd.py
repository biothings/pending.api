from enum import Flag, auto
from biothings.web.handlers.query import BaseAPIHandler

from web.utils import NGDZeroDocFreqException, UNDEFINED_STR
from web.service.ngd_service import NGDService, DocStatsService, NGDCache, DocStatsCache, Term, TermPair, TermExpansionService


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
    def zero_document_freq(cls, term: str, expanded: bool):
        status = " (expanded)" if expanded else ""
        return f"The document frequency of term '{term}'{status} is 0 in SemMedDB API."

    @classmethod
    def terms_not_a_list(cls, terms):
        return f"A list of 2 UMLS terms is required. Got {terms}, a {type(terms).__name__}."


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
            },
            'show-leaves': {
                'type': bool,
                'default': False
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
            },
            'show-leaves': {
                'type': bool,
                'default': False
            }
        }
    }

    # Suppose each term ID is an 8-char string and each doc freq is an integer. An OrderedDict of size 102400 takes ~10MB in RAM
    doc_stats_cache = DocStatsCache(unary_capacity=102400, bipartite_capacity=102400)
    ngd_cache = NGDCache(capacity=102400)

    def initialize(self, subject_field_name: str, object_field_name: str, doc_freq_agg_name: str, term_expansion_service: TermExpansionService):
        super().initialize()

        # The following 5 arguments are injected from the URLSpec in config_web/<plugin_name>.py
        self.subject_field_name = subject_field_name
        self.object_field_name = object_field_name
        self.doc_freq_agg_name = doc_freq_agg_name
        self.term_expansion_service = term_expansion_service

    def prepare(self):
        super().prepare()

        self.doc_stats_service = DocStatsService(
            es_async_client=self.biothings.elasticsearch.async_client,  # injected by handler's application instance (created by APILauncher)
            es_index_name=self.biothings.config.ES_INDEX,  # injected by handler's application instance (created by APILauncher)
            subject_field_name=self.subject_field_name,
            object_field_name=self.object_field_name,
            doc_freq_agg_name=self.doc_freq_agg_name
        )

        self.ngd_service = NGDService(
            doc_stats_service=self.doc_stats_service,
            term_expansion_service=self.term_expansion_service,
            doc_stats_cache=self.doc_stats_cache,
            ngd_cache=self.ngd_cache
        )

    @classmethod
    def pair_two_terms(cls, term_x_root: str, term_y_root: str, expansion_mode: ExpansionMode) -> TermPair:
        # "expansion_mode & ExpansionMode.LEFT" is true when expansion_mode is LEFT or BOTH
        # "expansion_mode & ExpansionMode.RIGHT" is true when expansion_mode is RIGHT or BOTH
        term_x = Term(root=term_x_root, expandable=bool(expansion_mode & ExpansionMode.LEFT))
        term_y = Term(root=term_y_root, expandable=bool(expansion_mode & ExpansionMode.RIGHT))
        term_pair = TermPair(term_x=term_x, term_y=term_y)
        return term_pair

    async def make_response(self, term_pair: TermPair, expansion_mode: ExpansionMode, show_leaves: bool):
        response = {}

        try:
            ngd = await self.ngd_service.calculate_ngd(term_pair)
        except NGDZeroDocFreqException as e:
            ngd = UNDEFINED_STR

            # We assume that "e.term" is an instance of Term class
            # Note that we don't use "e.term.expanded" here because it's not necessarily True at this moment
            # even if we have indicated to expand it. (due to lazy-expansion)
            reason = ErrorReason.zero_document_freq(e.term.root, e.term.expandable)
            response["reason"] = reason

        response["ngd"] = ngd
        response["umls"] = [term.root for term in term_pair]

        if expansion_mode is not ExpansionMode.NIL:
            # only write "expand" field in response when expansion mode is not 'nil'
            response["expand"] = expansion_mode.name.lower()

            # arg "show-leaves" only works when expansion mode is not 'nil'
            if show_leaves:
                # The last lazy-expansion step.
                # Suppose the term pair is (x, y). When calling self.ngd_service.calculate_ngd(), if (x, y) hits the distance cache (i.e. ngd_cache[(x, y)]),
                # or if it hits all three doc freq caches (i.e. unary_doc_freq[x], unary_doc_freq[y], and bipartite_doc_freq[(x, y)]), the terms are NOT
                # expanded. So here we must check and expand these two terms if necessary before writing the "leaf_umls" field in the response.
                self.ngd_service.expand_term_pair(term_pair)
                response["leaf_umls"] = {term.root: (term.leaves or None) for term in term_pair if term.expanded}

        return response

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

        arg_show_leaves = self.args['show-leaves']
        term_pair = self.pair_two_terms(term_x_root=arg_umls[0], term_y_root=arg_umls[1], expansion_mode=expansion_mode)
        response = await self.make_response(term_pair=term_pair, expansion_mode=expansion_mode, show_leaves=arg_show_leaves)
        await self.finish(response)
        return

    async def post(self, *args, **kwargs):
        # Step 1: Accept two arguments
        arg_umls = self.args['umls']  # should be a list of 2-termed sublists, e.g. [['a', 'b'], ['c', 'd'], ...]
        arg_expand = self.args.get('expand')
        arg_show_leaves = self.args['show-leaves']

        # Step 2: verify argument `expand`, raise an error simultaneously if invalid
        try:
            expansion_mode = ExpansionMode.mode_of(arg_expand)
        except ValueError:
            self.write_error(status_code=400, reason=ErrorReason.unknown_expansion_mode(arg_expand))
            return

        # Step 3: verify argument `umls` and calculate NGDs.
        # If any pair of terms failed the verification, do not raise an error simultaneously but wrap the error in the response.
        async def yield_responses(terms_list: list):
            for terms in terms_list:
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
                response = await self.make_response(term_pair=term_pair, expansion_mode=expansion_mode, show_leaves=arg_show_leaves)
                yield response

        response_list = [res async for res in yield_responses(arg_umls)]
        await self.finish(response_list)
        return
