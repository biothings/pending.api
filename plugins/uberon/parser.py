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
        syn_dict = {}
        exact = []
        related = []
        for syn in data['synonym']:
            if 'EXACT' in syn: 
                match = re.findall(r'\"(.+?)\"', syn)
                exact = exact + match
            elif 'RELATED' in syn: 
                match = re.findall(r'\"(.+?)\"', syn)
                related = related + match
        synonyms = {}
        if len(exact) > 0:
            synonyms["exact"] = exact
        if len(related) > 0:
            synonyms["related"] = related
        return synonyms
    else:
        return {}

def load_data(data_folder):
    path = os.path.join(data_folder, "uberon.obo")
    graph = obonet.read_obo(path)
    for item in graph.nodes():
        if item.startswith("UBERON:"):
            rec = graph.nodes[item]
            rec["_id"] = item
            rec["uberon"] = item
            if rec.get("is_a"):
                rec["parents"] = [parent for parent in rec.pop("is_a") if parent.startswith("UBERON:")]
            if rec.get("xref"):
                xrefs = defaultdict(set)
                for val in rec.get("xref"):
                    if ":" in val:
                        prefix, id = val.split(':', 1)
                        if prefix in ['UMLS', 'MESH']:
                            xrefs[prefix.lower()].add(id)
                        elif prefix == 'EFO':
                            xrefs[prefix.lower()].add(val)
                        else:
                            continue
                for k, v in xrefs.items():
                    xrefs[k] = list(v)
                rec.pop("xref")
                rec["xrefs"] = dict(xrefs)
            rec["children"] = [child for child in graph.predecessors(item) if child.startswith("UBERON:")]
            rec["ancestors"] = [ancestor for ancestor in nx.descendants(graph, item) if ancestor.startswith("UBERON:")]
            rec["descendants"] = [descendant for descendant in nx.ancestors(graph,item) if descendant.startswith("UBERON:")]
            rec['synonym'] = get_synonyms(rec)
            if rec.get("created_by"):
                rec.pop("created_by")
            if rec.get("creation_date"):
                rec.pop("creation_date")
            if rec.get("property_value"):
                rec.pop("property_value")
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
            yield rec
