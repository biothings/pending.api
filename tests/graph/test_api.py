"""
TODO
TESTING THIS FEATURE IS DATA DEPENDENT
SHALL SETUP DATA FIXTURES TO PERFORM TESTING

The following test cases are designed around document
"_id": "CHEBI:28821-PR:000023452-CPYs48qe6Tu5aq9mphml7Ed_DT4"

API: text_mining_targeted_association

#1

The following query CAN find the document:
{
    "association.edge_label": "positively_regulates_entity_to_entity",
    "object.id": "PR:000023452"
}

#2

The follwing query CANNOT find the document:
{
    "association.edge_label": "positively_regulated_by_entity_to_entity",
    "subject.id": "PR:000023452"
}

#3

The following query CAN find the document in reversed presentation:
http://localhost:8000/text_mining_targeted_association/query/graph?fields=association.edge_label,object.id,subject.id&dotfield&reverse
{
    "association.edge_label": "positively_regulated_by_entity_to_entity",
    "subject.id": "PR:000023452"
}

And the result is:
{
    "took": 1,
    "total": 1,
    "max_score": 8.541612,
    "hits": [
        {
            "_id": "CHEBI:28821-PR:000023452-CPYs48qe6Tu5aq9mphml7Ed_DT4",
            "_score": 8.541612,
            "association.edge_label": "positively_regulated_by_entity_to_entity",
            "object.id": "CHEBI:28821",
            "subject.id": "PR:000023452"
        }
    ]
}

#4

The following query CAN find the document in its original presentation:
http://localhost:8000/text_mining_targeted_association/query/graph?fields=association.edge_label,object.id,subject.id&dotfield&reverse&reversed=false
{
    "took": 1,
    "total": 1,
    "max_score": 8.541612,
    "hits": [
        {
            "_id": "CHEBI:28821-PR:000023452-CPYs48qe6Tu5aq9mphml7Ed_DT4",
            "_score": 8.541612,
            "association.edge_label": "positively_regulates_entity_to_entity",
            "object.id": "PR:000023452",
            "subject.id": "CHEBI:28821"
        }
    ]
}

"""
