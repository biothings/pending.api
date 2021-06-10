import pytest
from web.graph import GraphObject

reference = {  # from text_mining_targeted_association api
    "_id": "CHEBI:100147-PR:000023452-ay-9l3RTMPjsZ_Jwei4NxBVYBjo",
    "_score": 1,
    "association": {
        "edge_label": "negatively_regulates_entity_to_entity",
        "evidence": [{
            "object_spans": "start: 41, end: 45",
            "provided_by": "TMProvider",
            "publications": "PMID:25080814",
            "relation_spans": "",
            "score": "0.99955386",
            "sentence": "The nalidixic acid significantly ...",
            "subject_spans": "start: 4, end: 18"}],
        "evidence_count": "1",
        "relation": "RO:0002212"},
    "object": {
        "PR": "PR:000023452",
        "id": "PR:000023452",
        "type": "GeneOrGeneProduct"},
    "subject": {
        "CHEBI": "CHEBI:100147",
        "id": "CHEBI:100147",
        "type": "ChemicalSubstance"}
}


def test_01_import():
    graph = GraphObject.from_dict(reference)
    assert graph.subject == reference["subject"]
    assert graph.object == reference["object"]
    assert graph.associ == reference["association"]


def test_02_export():
    graph = GraphObject.from_dict(reference)
    output = graph.to_dict()
    correct = dict(reference)
    correct.pop("_id")
    correct.pop("_score")
    assert output == correct


def test_03_reverse():
    graph = GraphObject.from_dict(reference)
    assert graph.reversible()
    graph.reverse()
    assert graph.predicate == "negatively_regulated_by_entity_to_entity"
    assert graph.object == reference["subject"]
    assert graph.subject == reference["object"]


def test_04_reversible():
    bad = dict(reference)
    bad["association"] = dict(bad["association"])
    bad["association"]["edge_label"] = "undocumented"
    graph = GraphObject.from_dict(bad)
    assert not graph.reversible()
    with pytest.raises(TypeError):
        graph.reverse()
