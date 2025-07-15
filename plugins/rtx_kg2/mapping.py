def edge_mapping(cls) -> dict:
    mapping = {
        "mappings": {
            "properties": {
                "agent_type": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "domain_range_exclusion": {"type": "boolean"},
                "id": {"type": "long"},
                "kg2_ids": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "knowledge_level": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "object": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "predicate": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "primary_knowledge_source": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "publications": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "publications_info": {
                    "properties": {
                        "object_score": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                        },
                        "pmid": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                        "publication_date": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                        },
                        "sentence": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                        },
                        "subject_score": {
                            "type": "text",
                            "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                        },
                    }
                },
                "qualified_object_aspect": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "qualified_object_direction": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "qualified_predicate": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "subject": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            }
        }
    }
    return mapping


def node_mapping(cls) -> dict:
    mapping = {
        "mappings": {
            "properties": {
                "all_categories": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "all_names": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "category": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "description": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "equivalent_curies": {
                    "type": "text",
                    "fields": {"keyword": {"type": "keyword", "ignore_above": 256}},
                },
                "id": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "iri": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "name": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
                "publications": {"type": "text", "fields": {"keyword": {"type": "keyword", "ignore_above": 256}}},
            }
        }
    }
    return mapping
