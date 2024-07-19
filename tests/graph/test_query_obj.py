import pytest
from web.graph import GraphQuery


def test_01_import():
    """Typical JSON input"""
    query = GraphQuery.from_dict(
        {"subject": {"_id": "cat"}, "object": {"_id": "mouse"}, "association": {"edge_label": "eats"}}
    )
    assert query.subject["_id"] == "cat"
    assert query.object["_id"] == "mouse"
    assert query.predicate == "eats"


def test_02_import():
    """Partial fields"""
    GraphQuery.from_dict(
        {
            "subject": {"_id": "cat"},
        }
    )


def test_03_import():
    """Dotfield notation"""
    query = GraphQuery.from_dict(
        {"subject.id.a": "x", "subject.id.b.c": "x", "object.id": "x", "object.id.d": "x", "association": {}}
    )
    assert tuple(query.to_dict().keys()) == ("subject", "object", "association")


def test_04_import():
    """Invalid top level type"""
    with pytest.raises(TypeError):
        GraphQuery.from_dict([{"subject": {}, "object": {}, "association": {}}])


def test_05_import():
    """Invalid root values"""
    with pytest.raises(TypeError):
        GraphQuery.from_dict({"subject": 1, "object": 2, "association": 3})


def test_06_import():
    """Invalid root values"""
    with pytest.raises(TypeError):
        GraphQuery.from_dict(
            {
                "object": [1, 2, 3],
            }
        )


def test_07_import():
    """Invalid inner structs"""
    with pytest.raises(TypeError):
        GraphQuery.from_dict(
            {
                "object": {"list": [{}, [], None]},
            }
        )


def test_08_import():
    """Dotfield key collision"""  # TODO
    query = GraphQuery.from_dict(
        {
            "subject": {"_id": "cat"},
            "subject._id": "fakecat",
        }
    )
    assert query.subject["_id"] == "fakecat"


def test1():
    q1 = GraphQuery.from_dict(
        {
            "subject": {"id": "NCBIGene:1017", "type": "Gene", "taxid": "9606"},
            "object": {"id": "MONDO:000123", "type": "Disease"},
            "association": {"predicate": "negatively_regulated_by", "publications": ["PMID:123", "PMID:124"]},
        }
    )
    q2 = GraphQuery.from_dict(
        {
            "subject.id": "NCBIGene:1017",
            "subject.type": "Gene",
            "subject.taxid": "9606",
            "object.id": "MONDO:000123",
            "object.type": "Disease",
            "association.predicate": "negatively_regulated_by",
            "association.publications": ["PMID:123", "PMID:124"],
        }
    )
    assert str(q1.to_dict()) == str(q2.to_dict())


def test2():

    q = GraphQuery.from_dict(
        {"subject.id.a": "x", "subject.id.b.c": "x", "object.id": "x", "object.id.d": "x", "association": {}}
    ).to_dict()
    assert "subject" in q
    assert "object" in q
    assert "association" in q
