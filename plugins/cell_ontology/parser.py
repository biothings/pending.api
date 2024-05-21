from collections import defaultdict
import networkx as nx
import obonet
import os
import re


def get_synonyms(data):
    """Format synonyms as dicionary
    exact and related synonyms are the keys, and their values are in lists
    """
    if 'synonym' in data:
        exact = []
        related = []
        broad = []
        for syn in data['synonym']:
            if 'EXACT' in syn:
                match = re.findall(r'\"(.+?)\"', syn)
                exact = exact + match
            elif 'RELATED' in syn:
                match = re.findall(r'\"(.+?)\"', syn)
                related = related + match
            elif 'BROAD' in syn:
                match = re.findall(r'\"(.+?)\"', syn)
                broad = broad + match
        synonyms = {}
        if len(exact) > 0:
            synonyms["exact"] = exact
        if len(related) > 0:
            synonyms["related"] = related
        if len(broad) > 0:
            synonyms["broad"] = broad
        return synonyms
    else:
        return {}


def load_data(data_folder):
    path = os.path.join(data_folder, "cl.obo")
    graph = obonet.read_obo(path)
    for item in graph.nodes():
        if item.startswith("CL:"):
            rec = process_node(graph, item)
            yield rec

def process_node(graph, item):
    rec = graph.nodes[item]
    rec["_id"] = item
    rec["cl"] = item
    process_is_a(rec)
    process_xrefs(rec)
    rec["children"] = [child for child in graph.predecessors(item) if child.startswith("CL:")]
    rec["ancestors"] = [ancestor for ancestor in nx.descendants(graph, item) if ancestor.startswith("CL:")]
    rec["descendants"] = [descendant for descendant in nx.ancestors(graph, item) if descendant.startswith("CL:")]
    rec["synonym"] = get_synonyms(rec)
    remove_unnecessary_fields(rec)
    process_relationships(rec)
    return rec

def process_is_a(rec):
    if rec.get("is_a"):
        rec["parents"] = [parent for parent in rec.pop("is_a") if parent.startswith("CL:")]

def process_xrefs(rec):
    if rec.get("xref"):
        xrefs = defaultdict(set)
        for val in rec.get("xref"):
            if ":" in val:
                prefix, idx = val.split(':', 1)
                if prefix not in ["http", "https"]:
                    if prefix in ['UMLS', 'MESH']:
                        xrefs[prefix.lower()].add(idx)
                    else:
                        xrefs[prefix.lower()].add(val)
        for k, v in xrefs.items():
            xrefs[k] = list(v)
        rec.pop("xref")
        rec["xrefs"] = dict(xrefs)

def remove_unnecessary_fields(rec):
    for field in ["created_by", "creation_date", "property_value"]:
        if rec.get(field):
            rec.pop(field)

def process_relationships(rec):
    if rec.get("relationship"):
        rels = defaultdict(lambda: defaultdict(set))
        for rel in rec.get("relationship"):
            predicate, val = rel.split(' ')
            prefix = val.split(':')[0]
            rels[predicate][prefix.lower()].add(val)
        for predicate, values in rels.items():
            for prefix, val_set in values.items():
                values[prefix] = list(val_set)
            rec[predicate] = dict(values)
        rec.pop("relationship")
