import os
import re
from collections import defaultdict

import networkx as nx
import obonet


class OntologyHelper:
    IS_A_EDGE_TYPE = "is_a"
    SYNONYM_PATTERN = re.compile(r"\"(.+?)\"")
    XREF_INVALID_PREFIXES = {"https", "http"}
    XREF_ALWAYS_PREFIXED = {"DOID", "HP", "MP", "OBI", "EFO"}

    def __init__(self, prefix):
        self.prefix = prefix

    def load_obo_network(self, filepath: str) -> nx.MultiDiGraph:
        graph = obonet.read_obo(filepath, ignore_obsolete=False)
        edges_to_remove = [(u, v, key) for (u, v, key) in graph.edges(keys=True) if key != self.IS_A_EDGE_TYPE]
        graph.remove_edges_from(edges_to_remove)
        return graph

    def parse_synonyms(self, node_obj: dict) -> dict:
        if "synonym" not in node_obj:
            return {}
        exact_synonyms = []
        related_synonyms = []
        for synonym_description in node_obj["synonym"]:
            if "EXACT" in synonym_description:
                exact_synonyms += self.SYNONYM_PATTERN.findall(synonym_description)
            elif "RELATED" in synonym_description:
                related_synonyms += self.SYNONYM_PATTERN.findall(synonym_description)
        synonyms = {}
        if exact_synonyms:
            synonyms["exact"] = exact_synonyms
        if related_synonyms:
            synonyms["related"] = related_synonyms
        return synonyms

    def parse_xref(self, node_obj: dict) -> dict:
        if "xref" not in node_obj:
            return {}
        xrefs = defaultdict(set)
        for curie in node_obj.get("xref"):
            curie_prefix, curie_id = curie.split(":", 1)
            if curie_prefix in self.XREF_INVALID_PREFIXES:
                continue
            if curie_prefix in self.XREF_ALWAYS_PREFIXED:
                xrefs[curie_prefix.lower()].add(curie)
            else:
                xrefs[curie_prefix.lower()].add(curie_id)
        for curie_prefix in xrefs:
            xrefs[curie_prefix] = list(xrefs[curie_prefix])
        return xrefs

    def parse_relationship(self, node_obj: dict) -> dict:
        if "relationship" not in node_obj:
            return {}
        rels = defaultdict(set)
        for relationship_description in node_obj.get("relationship"):
            predicate, curie = relationship_description.split(" ")
            curie_prefix = curie.split(":")[0].lower()

            rels[curie_prefix].add(curie)

        for curie_prefix in rels:
            rels[curie_prefix] = list(rels[curie_prefix])

        return dict(rels)

    def is_obsolete(self, node_obj: dict) -> bool:
        return node_obj.get("is_obsolete", "false") == "true"

    def is_target_prefix(self, node_id: str) -> bool:
        return node_id.startswith(self.prefix)

    def get_ontological_predecessors(self, graph: nx.MultiDiGraph, node_id: str):
        return list(graph.successors(node_id))

    def get_ontological_successors(self, graph: nx.MultiDiGraph, node_id: str):
        return list(graph.predecessors(node_id))

    def get_ontological_ancestors(self, graph: nx.MultiDiGraph, node_id: str):
        return list(nx.descendants(graph, node_id))

    def get_ontological_descendants(self, graph: nx.MultiDiGraph, node_id: str):
        return list(nx.ancestors(graph, node_id))

def load_obo(data_folder, obofile, prefix):
    path = os.path.join(data_folder, obofile)
    helper = OntologyHelper(prefix)
    graph = helper.load_obo_network(path)

    for node_id in graph.nodes(data=False):
        if not helper.is_target_prefix(node_id):
            continue

        node_doc = {"_id": node_id}
        node_obj = graph.nodes[node_id]

        node_doc["parents"] = helper.get_ontological_predecessors(graph, node_id)
        node_doc["children"] = helper.get_ontological_successors(graph, node_id)
        node_doc["ancestors"] = helper.get_ontological_ancestors(graph, node_id)
        node_doc["descendants"] = helper.get_ontological_descendants(graph, node_id)

        if helper.is_obsolete(node_obj):
            node_doc["is_obsolete"] = True
            replaced_by = node_obj.get("replaced_by", None)
            if replaced_by:
                node_doc["replaced_by"] = replaced_by[0]
            node_doc["consider"] = node_obj.get("consider", None)

        node_doc["synonym"] = helper.parse_synonyms(node_obj)
        node_doc["xrefs"] = helper.parse_xref(node_obj)
        node_doc.update(helper.parse_relationship(node_obj))

        node_doc["definition"] = node_obj.get("def", "").replace('"', '')
        node_doc["label"] = node_obj.get("name")

        node_doc = {k: v for k, v in node_doc.items() if v not in [None, [], ""]}

        yield node_doc
