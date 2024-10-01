import os
import re
from collections import defaultdict

import networkx as nx
import obonet


class OntologyHelper:
    """
    A helper class for parsing and extracting information from OBO ontology files.

    Attributes:
        prefix (str or None): The prefix to filter ontology terms. If None, all terms are included.
    """

    IS_A_EDGE_TYPE = "is_a"
    SYNONYM_PATTERN = re.compile(r"\"(.+?)\"")
    XREF_INVALID_PREFIXES = {"https", "http"}
    XREF_ALWAYS_PREFIXED = {"DOID", "HP", "MP", "OBI", "EFO"}

    def __init__(self, prefix=None):
        """
        Initialize the OntologyHelper.

        Args:
            prefix (str, optional): The prefix to filter ontology terms. Defaults to None.
        """
        self.prefix = prefix

    def load_obo_network(self, filepath: str) -> nx.MultiDiGraph:
        """
        Load the OBO file into a NetworkX MultiDiGraph.

        Args:
            filepath (str): The path to the OBO file.

        Returns:
            nx.MultiDiGraph: A graph representing the ontology with 'is_a' relationships.
        """
        graph = obonet.read_obo(filepath, ignore_obsolete=False)
        edges_to_remove = [
            (u, v, key)
            for (u, v, key) in graph.edges(keys=True)
            if key != self.IS_A_EDGE_TYPE
        ]
        graph.remove_edges_from(edges_to_remove)
        return graph

    def parse_synonyms(self, node_obj: dict) -> dict:
        """
        Parse synonyms from a node object.

        Args:
            node_obj (dict): The node attributes from the ontology graph.

        Returns:
            dict: A dictionary containing exact and related synonyms.
        """
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
        """
        Parse cross-references from a node object.

        Args:
            node_obj (dict): The node attributes from the ontology graph.

        Returns:
            dict: A dictionary of cross-references grouped by prefix.
        """
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
        """
        Parse relationships from a node object.

        Args:
            node_obj (dict): The node attributes from the ontology graph.

        Returns:
            dict: A dictionary of relationships grouped by prefix.
        """
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
        """
        Check if a node is marked as obsolete.

        Args:
            node_obj (dict): The node attributes from the ontology graph.

        Returns:
            bool: True if the node is obsolete, False otherwise.
        """
        return node_obj.get("is_obsolete", "false") == "true"

    def is_target_prefix(self, node_id: str) -> bool:
        """
        Determine if a node ID matches the target prefix.

        Args:
            node_id (str): The ID of the node.

        Returns:
            bool: True if the node ID starts with the target prefix or if prefix is None.
        """
        if self.prefix is None:
            return True
        return node_id.startswith(self.prefix)

    def get_ontological_predecessors(self, graph: nx.MultiDiGraph, node_id: str):
        """
        Get immediate parent nodes in the ontology hierarchy.

        Args:
            graph (nx.MultiDiGraph): The ontology graph.
            node_id (str): The ID of the node.

        Returns:
            list: A list of parent node IDs.
        """
        return list(graph.successors(node_id))

    def get_ontological_successors(self, graph: nx.MultiDiGraph, node_id: str):
        """
        Get immediate child nodes in the ontology hierarchy.

        Args:
            graph (nx.MultiDiGraph): The ontology graph.
            node_id (str): The ID of the node.

        Returns:
            list: A list of child node IDs.
        """
        return list(graph.predecessors(node_id))

    def get_ontological_ancestors(self, graph: nx.MultiDiGraph, node_id: str):
        """
        Get all ancestor nodes in the ontology hierarchy.

        Args:
            graph (nx.MultiDiGraph): The ontology graph.
            node_id (str): The ID of the node.

        Returns:
            list: A list of ancestor node IDs.
        """
        return list(nx.descendants(graph, node_id))

    def get_ontological_descendants(self, graph: nx.MultiDiGraph, node_id: str):
        """
        Get all descendant nodes in the ontology hierarchy.

        Args:
            graph (nx.MultiDiGraph): The ontology graph.
            node_id (str): The ID of the node.

        Returns:
            list: A list of descendant node IDs.
        """
        return list(nx.ancestors(graph, node_id))


def load_obo(data_folder, obofile, prefix=None):
    """
    Load an OBO ontology file and yield processed node documents.

    This function reads an OBO-formatted ontology file and processes its contents
    to extract relevant information for each node (term) in the ontology. It filters
    nodes based on an optional prefix and yields a dictionary for each node containing
    various ontological details such as synonyms, cross-references, relationships,
    and hierarchical information like parents and children.

    Args:
        data_folder (str): The directory containing the OBO file.
        obofile (str): The name of the OBO file to load.
        prefix (str, optional): A prefix string to filter ontology terms. Only terms
            whose IDs start with this prefix will be processed. If None, all terms
            in the ontology are processed. Defaults to None.

    Yields:
        dict: A dictionary representing a node (ontology term) with processed
        ontology information. The dictionary includes:

            - "_id" (str): The unique identifier of the node.
            - "label" (str): The name of the node.
            - "definition" (str): The textual definition of the node.
            - "synonym" (dict): A dictionary of synonyms categorized as "exact" or "related".
            - "xrefs" (dict): Cross-references to other databases or ontologies.
            - "relationships" (dict): Relationships to other ontology terms.
            - "parents" (list): Immediate parent node IDs in the ontology hierarchy.
            - "children" (list): Immediate child node IDs in the ontology hierarchy.
            - "ancestors" (list): All ancestor node IDs (transitive closure).
            - "descendants" (list): All descendant node IDs (transitive closure).
            - "is_obsolete" (bool): Indicates if the node is obsolete.
            - "replaced_by" (str): The node ID that replaces this obsolete node.
            - "consider" (list): A list of node IDs to consider instead of the obsolete node.

    Notes:
        - The function uses the `OntologyHelper` class to parse and extract information.
        - Only 'is_a' relationships are considered in the ontology graph.
        - Obsolete terms are included and marked with the "is_obsolete" flag.
        - The function skips nodes that do not match the provided prefix, if any.

    """
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
        node_doc["relationships"] = helper.parse_relationship(node_obj)

        node_doc["definition"] = node_obj.get("def", "").replace('"', '')
        node_doc["label"] = node_obj.get("name")

        node_doc = {k: v for k, v in node_doc.items() if v not in [None, [], ""]}

        yield node_doc
