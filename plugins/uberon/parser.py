from collections import defaultdict
import networkx as nx
import obonet
import os
import re

def get_synonyms(data):
    """Format synonyms as a dictionary.
    Exact and related synonyms are the keys, and their values are lists.
    """
    synonyms = defaultdict(list)
    for syn in data.get('synonym', []):
        match = re.findall(r'\"(.+?)\"', syn)
        if 'EXACT' in syn:
            synonyms["exact"].extend(match)
        elif 'RELATED' in syn:
            synonyms["related"].extend(match)
    return dict(synonyms)

def load_ontology_data(data_folder):
    path = os.path.join(data_folder, "uberon.obo")
    graph = obonet.read_obo(path)
    return graph

def process_node(graph, item):
    rec = graph.nodes[item]
    rec["_id"] = item
    rec["uberon"] = item
    if rec.get("is_a"):
        rec["parents"] = [parent for parent in rec.pop("is_a") if parent.startswith("UBERON:")]
    if rec.get("xref"):
        rec["xrefs"] = process_xrefs(rec.pop("xref"))
    rec["children"] = [child for child in graph.predecessors(item) if child.startswith("UBERON:")]
    rec["ancestors"] = [ancestor for ancestor in nx.descendants(graph, item) if ancestor.startswith("UBERON:")]
    rec["descendants"] = [descendant for descendant in nx.ancestors(graph, item) if descendant.startswith("UBERON:")]
    rec["synonym"] = get_synonyms(rec)
    remove_unnecessary_fields(rec)
    process_relationships(rec)
    return rec

def process_xrefs(xref_list):
    xrefs = defaultdict(list)
    for val in xref_list:
        if ":" in val:
            prefix, idx = val.split(':', 1)
            if prefix.lower() in ['umls', 'mesh']:
                xrefs[prefix.lower()].append(idx)
            elif prefix == 'EFO':
                xrefs[prefix.lower()].append(val)
    return dict(xrefs)

def remove_unnecessary_fields(rec):
    fields_to_remove = ["created_by", "creation_date", "property_value", "relationship"]
    for field in fields_to_remove:
        rec.pop(field, None)

def process_relationships(rec):
    if rec.get("relationship"):
        rels = {}
        for rel in rec.get("relationship"):
            predicate, val = rel.split(' ')
            prefix = val.split(':')[0]
            if predicate not in rels:
                rels[predicate] = defaultdict(set)
            if prefix.lower() not in rels[predicate]:
                rels[predicate][prefix.lower()].add(val)
        for m, n in rels.items():
            for p, q in n.items():
                n[p] = list(q)
            rels[m] = dict(n)
        rec.update(rels)
        rec.pop("relationship")

def load_data(data_folder):
    graph = load_ontology_data(data_folder)
    for item in graph.nodes():
        if item.startswith("UBERON:"):
            rec = process_node(graph, item)
            yield rec
