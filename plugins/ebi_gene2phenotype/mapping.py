def ebi_gene2pheno_mapping(cls):
    """
    Provide ElasticSearch mapping for documents

    No normalizer when probably should only allow exact matches

    Maybe don't need to be keywords:
    subject.label
    subject.original_data.hgnc_symbol
    subject.type (always the same)
    """
    elasticsearch_mapping = {
        "subject": {
            "properties": {
                "id": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                "label": {"type": "keyword"},
                "original_subject": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                "original_data": {
                    "properties": {
                        "hgnc": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                        "omim": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                        "hgnc_symbol": {"type": "keyword"},
                        "previous_gene_symbols": {"type": "text"},
                    }
                },
                "type": {"type": "constant_keyword"},
            }
        },
        "association": {
            "properties": {
                "g2p_record_id": {"type": "keyword"},
                "g2p_record_url": {"type": "text"},
                "allelic_requirement": {"type": "keyword"},
                "cross_cutting_modifier": {"type": "keyword"},
                "confidence": {"type": "keyword"},
                "variant_consequences": {"type": "keyword"},
                "variant_types": {"type": "keyword"},
                "molecular_mechanism": {"type": "keyword"},
                "molecular_mechanism_categorisation": {"type": "keyword"},
                "molecular_mechanism_evidence": {"type": "text"},
                "phenotypes": {"type": "keyword"},
                "pmids": {"type": "keyword"},
                "g2p_panels": {"type": "keyword"},
                "curator_comments": {"type": "text"},
                "date_of_last_review": {"type": "date", "format": "yyyy-MM-dd HH:mm:ssz"},
            }
        },
        "object": {
            "properties": {
                "id": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                "label": {"type": "keyword"},
                "original_object": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                "original_data": {
                    "properties": {
                        "omim": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                        "orphanet": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                        "mondo": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                        "name": {"type": "keyword"},
                    }
                },
                "type": {"type": "constant_keyword"},
            }
        },
    }

    return elasticsearch_mapping
