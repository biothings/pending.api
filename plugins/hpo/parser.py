import networkx as nx
import obonet
from collections import defaultdict
import re
import os


def get_synonyms(data):
    """Format synonyms as a dictionary.
    Exact, related, and broad synonyms are the keys, and their values are lists.
    """
    if 'synonym' in data:
        synonyms = defaultdict(list)
        for syn in data['synonym']:
            match = re.findall(r'\"(.+?)\"', syn)
            if 'EXACT' in syn:
                synonyms["exact"].extend(match)
            elif 'RELATED' in syn:
                synonyms["related"].extend(match)
            elif 'BROAD' in syn:
                synonyms["broad"].extend(match)
        return dict(synonyms)
    return {}

def load_annotations(data_folder):
    annotations = defaultdict(list)
    infile = os.path.join(data_folder, 'phenotype_to_genes.txt')
    if not os.path.exists(infile):
        raise FileNotFoundError(f"File not found: {infile}")
    with open(infile) as f:
        f.readline()  # Skip header
        for line in f:
            hpoID, _, ncbiGeneID, geneSymbol, diseaseID = line.strip().split('\t')
            obj = {
                'gene': {'id': ncbiGeneID, 'symbol': geneSymbol},
                'disease_id': diseaseID
            }
            annotations[hpoID].append(obj)
    return annotations

def load_ontology(url):
    graph = obonet.read_obo(url)
    return graph

def process_node(graph, item, annotations):
    rec = graph.nodes[item]
    rec["_id"] = item
    rec["hp"] = item
    if rec.get("def"):
        rec["def"] = rec.get("def").replace('"', '')
    if rec.get("is_a"):
        rec["parents"] = [parent for parent in rec.pop("is_a") if parent.startswith("HP:")]
    if rec.get("xref"):
        rec["xrefs"] = process_xrefs(rec.pop("xref"))
    rec["children"] = [child for child in graph.predecessors(item) if child.startswith("HP:")]
    rec["ancestors"] = [ancestor for ancestor in nx.descendants(graph, item) if ancestor.startswith("HP:")]
    rec["descendants"] = [descendant for descendant in nx.ancestors(graph, item) if descendant.startswith("HP:")]
    rec["synonym"] = get_synonyms(rec)
    remove_unnecessary_fields(rec)
    process_relationships(rec)
    rec["annotations"] = annotations[item]
    return rec

def process_xrefs(xref_list):
    xrefs = defaultdict(list)
    for val in xref_list:
        if ":" in val:
            prefix, idx = val.split(':', 1)
            if prefix.lower() in ["http", "https"]:
                continue
            elif prefix.lower() in ['umls', 'snomedct_us', 'snomed_ct', 'cohd', 'ncit']:
                xrefs[prefix.lower()].append(idx)
            elif prefix == 'MSH':
                xrefs['mesh'].append(idx)
            else:
                xrefs[prefix.lower()].append(val)
    return dict(xrefs)

def remove_unnecessary_fields(rec):
    for field in ["created_by", "creation_date", "relationship"]:
        rec.pop(field, None)

def process_relationships(rec):
    if rec.get("relationship"):
        for rel in rec.get("relationship"):
            predicate, val = rel.split(' ')
            prefix = val.split(':')[0]
            rec[predicate] = {prefix.lower(): val}
        rec.pop("relationship")

def load_data(data_folder):
    annotations = load_annotations(data_folder)
    url = "https://raw.githubusercontent.com/obophenotype/human-phenotype-ontology/master/hp.obo"
    graph = load_ontology(url)
    for item in graph.nodes():
        if item.startswith("HP:"):
            rec = process_node(graph, item, annotations)
            yield rec
