import dataclasses
import logging
import os
import time
from typing import Union

import bmt

from biothings.web.handlers import BaseAPIHandler
from biothings.web.services.namespace import BiothingsNamespace
from tornado.web import HTTPError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


BIOLINK_VERSION = os.getenv("BIOLINK_VERSION", "v4.2.2")
BIOLINK_MODEL_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/{BIOLINK_VERSION}/biolink-model.yaml"
toolkit = bmt.Toolkit(BIOLINK_MODEL_URL)


defaultconfig = {
    "demote_labels_longer_than": 15,
}


@dataclasses.dataclass(frozen=True)
class NormalizedNode:
    curie: str
    canonical_identifier: str
    preferred_label: str
    information_content: float
    identifiers: list[str]
    types: list[str]


class NormalizedNodesHandler(BaseAPIHandler):
    """
    Mirror implementation to the renci implementation found at
    https://nodenormalization-sri.renci.org/docs

    We intend to mirror the /get_normalized_nodes endpoint
    """

    name = "normalizednodes"

    async def get(self):
        normalized_curies = self.get_arguments("curie")
        if len(normalized_curies) == 0:
            raise HTTPError(
                detail="Missing curie argument, there must be at least one curie to normalize", status_code=400
            )

        def parse_boolean(argument: Union[str, bool]) -> bool:
            if isinstance(argument, bool):
                return argument
            if isinstance(argument, str):
                return not argument.lower() == "false"
            return False

        conflate = parse_boolean(self.get_argument("conflate", True))
        drug_chemical_conflate = parse_boolean(self.get_argument("drug_chemical_conflate", False))
        description = parse_boolean(self.get_argument("description", False))
        individual_types = parse_boolean(self.get_argument("individual_types", False))

        normalized_nodes = await get_normalized_nodes(
            self.biothings,
            normalized_curies,
            conflate,
            drug_chemical_conflate,
            include_descriptions=description,
            include_individual_types=individual_types,
        )

        # If curie contains at least one entry, then the only way normalized_nodes could be blank
        # would be if an error occurred during processing.
        if not normalized_nodes:
            raise HTTPError(detail="Error occurred during processing.", status_code=500)

        self.finish(normalized_nodes)

    async def post(self):
        """
        Returns the equivalent identifiers and semantic types for the curie(s)

        Example body
        {
          "curie": [
            "MESH:D014867",
            "NCIT:C34373"
          ]
        }

        Example output
        {
          "MESH:D014867": {
            "id": {
              "identifier": "CHEBI:15377",
              "label": "Water"
            },
            "equivalent_identifiers": [
              {
                "identifier": "CHEBI:15377",
                "label": "water"
              },
              ...
            ],
            "type": [
              "biolink:SmallMolecule",
              "biolink:MolecularEntity",
              "biolink:ChemicalEntity",
              "biolink:PhysicalEssence",
              "biolink:ChemicalOrDrugOrTreatment",
              "biolink:ChemicalEntityOrGeneOrGeneProduct",
              "biolink:ChemicalEntityOrProteinOrPolypeptide",
              "biolink:NamedThing",
              "biolink:PhysicalEssenceOrOccurrent"
            ],
            "information_content": 47.7
          },
          "NCIT:C34373": {
            "id": {
              "identifier": "MONDO:0004976",
              "label": "amyotrophic lateral sclerosis"
            },
            "equivalent_identifiers": [
              {
                "identifier": "MONDO:0004976",
                "label": "amyotrophic lateral sclerosis"
              },
              ...
            ],
            "type": [
              "biolink:Disease",
              "biolink:DiseaseOrPhenotypicFeature",
              "biolink:BiologicalEntity",
              "biolink:ThingWithTaxon",
              "biolink:NamedThing"
            ],
            "information_content": 74.9
          }
        }
        """
        normalization_curies = self.args_json.get("curies", [])
        if len(normalization_curies) == 0:
            raise HTTPError(
                detail="Missing curie argument, there must be at least one curie to normalize", status_code=400
            )

        conflate = self.args_json.get("conflate", True)
        drug_chemical_conflate = self.args_json.get("drug_chemical_conflate", False)
        description = self.args_json.get("description", False)
        individual_types = self.args_json.get("individual_types", False)

        normalized_nodes = await get_normalized_nodes(
            self.biothings,
            normalization_curies,
            conflate,
            drug_chemical_conflate,
            include_descriptions=description,
            include_individual_types=individual_types,
        )

        # If curie contains at least one entry, then the only way normalized_nodes could be blank
        # would be if an error occurred during processing.
        if not normalized_nodes:
            raise HTTPError(detail="Error occurred during processing.", status_code=500)

        self.finish(normalized_nodes)


async def get_normalized_nodes(
    biothings_metadata: BiothingsNamespace,
    curies: list[str],
    conflate_gene_protein: bool = False,
    conflate_chemical_drug: bool = False,
    include_descriptions: bool = False,
    include_individual_types: bool = False,
) -> dict:
    start_time = time.perf_counter_ns()

    conflations = {
        "GeneProtein": conflate_gene_protein,
        "DrugChemical": conflate_chemical_drug,
    }

    nodes = await _lookup_curie_metadata(biothings_metadata, curies, conflations)

    normal_nodes = {}
    for aggregate_node in nodes:
        normal_node = await create_normalized_node(
            aggregate_node,
            include_descriptions=include_descriptions,
            include_individual_types=include_individual_types,
            conflations=conflations,
        )
        normal_nodes[aggregate_node.curie] = normal_node

    end_time = time.perf_counter_ns()
    logger.debug(
        (
            f"Normalized {len(curies)} nodes in {(end_time - start_time)/1_000_000:.2f} ms with arguments "
            f"(curies={curies}, conflate_gene_protein={conflate_gene_protein}, conflate_chemical_drug={conflate_chemical_drug}, "
            f"include_descriptions={include_descriptions}, include_individual_types={include_individual_types})"
        )
    )
    return normal_nodes


async def create_normalized_node(
    aggregate_node: NormalizedNode,
    include_descriptions: bool = True,
    include_individual_types: bool = False,
    conflations: dict = None,
) -> dict:
    """
    Construct the output format given the aggregated node data
    from elasticsearch
    """
    normal_node = {}

    # It's possible that we didn't find a canonical_id
    if aggregate_node.canonical_identifier is None:
        return None

    if conflations is None:
        conflations = {}

    # If we have 'None' in the equivalent IDs, skip it so we don't confuse things further down the line.
    if None in aggregate_node.identifiers:
        logging.warning(
            "Filtering none-type values for canonical identifier {%s} among equivalent identifiers [%s]",
            aggregate_node.canonical_identifier,
            aggregate_node.identifiers,
        )
        aggregate_node.identifiers = [eqid for eqid in aggregate_node.identifiers if eqid is not None]
        if not aggregate_node.identifiers:
            logging.warning(
                "Only discovered none-type values for canonical identifier {%s} among filtered equivalent identifiers [%s]",
                aggregate_node.canonical_identifier,
                aggregate_node.identifiers,
            )
            return None

    # If we have 'None' in the canonical types, something went horribly wrong (specifically: we couldn't
    # find the type information for all the eqids for this clique). Return None.
    if None in aggregate_node.types:
        logging.error(
            "No types found for canonical identifier {%s} among types [%s]",
            aggregate_node.canonical_identifier,
            aggregate_node.types,
        )
        return None

    if aggregate_node.preferred_label is not None and aggregate_node.preferred_label != "":
        normal_node = {
            "id": {"identifier": aggregate_node.identifiers[0]["i"], "label": aggregate_node.preferred_label}
        }
    else:
        if aggregate_node.identifiers is not None and len(aggregate_node.identifiers) > 0:
            normal_node = {"id": {"identifier": aggregate_node.identifiers[0]["i"]}}
        else:
            normal_node = {"id": {"identifier": aggregate_node.canonical_identifier}}

    # if descriptions are enabled, look for the first available description and use that
    if include_descriptions:
        descriptions = list(
            map(
                lambda x: x[0],
                filter(lambda x: len(x) > 0, [eid["d"] for eid in aggregate_node.identifiers if "d" in eid]),
            )
        )
        if len(descriptions) > 0:
            normal_node["id"]["description"] = descriptions[0]

    # now need to reformat the identifier keys.  It could be cleaner but we have to worry about if there is a label
    normal_node["equivalent_identifiers"] = []
    for identifier in aggregate_node.identifiers:
        eq_item = {"identifier": identifier["i"]}
        if "l" in identifier:
            eq_item["label"] = identifier["l"]

        # if descriptions is enabled and exist add them to each eq_id entry
        if include_descriptions and "d" in identifier and len(identifier["d"]) > 0:
            eq_item["description"] = identifier["d"][0]

        # if individual types have been requested, add them too.
        if include_individual_types and "t" in identifier:
            eq_item["type"] = identifier["t"][-1]

        normal_node["equivalent_identifiers"].append(eq_item)

    normal_node["type"] = aggregate_node.types

    # add the info content to the node if we got one
    if aggregate_node.information_content is not None:
        normal_node["information_content"] = aggregate_node.information_content

    return normal_node


async def _lookup_curie_metadata(
    biothings_metadata: BiothingsNamespace, curies: list[str], conflations: dict
) -> list[NormalizedNode]:
    """
    Handles the lookup process for the CURIE identifiers within our elasticsearch instance

    Ported from the redis instance, this performs one set of batch lookup calls via a singular
    terms query with the entire set of curies. Given the default maximum amount of terms queries
    specified by index.max_terms_count is 65536 (2**16), we should be well under given our
    usual maximum query size is ~3000 CURIE identifiers

    We most also be careful though as the terms query is simply checking if any document
    contains at least one of the terms. We expect a 1-1 matching for CURIE identifier to
    document, so we can determine which terms were not found via set difference between the
    returned document CURIE identifiers and the user provided set of CURIE identifiers
    """
    identifier_result_lookup, malformed_curies = await _lookup_equivalent_identifiers(biothings_metadata, curies)

    nodes = []
    for input_curie in curies:
        if input_curie in malformed_curies:
            node = NormalizedNode(
                curie=input_curie,
                canonical_identifier=None,
                preferred_label=None,
                information_content=-1.0,
                identifiers=[],
                types=[],
            )
            nodes.append(node)
        else:
            result = identifier_result_lookup[input_curie]
            result_source = result.get("_source", {})
            identifiers = result_source.get("identifiers", [])
            biolink_type = result_source.get("type", None)
            preferred_label = result_source.get("preferred_name", None)

            # Every equivalent identifier here has the same type.
            for eqid in identifiers:
                eqid.update({"t": [biolink_type]})

            try:
                canonical_identifier = identifiers[0].get("i", None)
            except IndexError:
                canonical_identifier = None
            finally:
                if canonical_identifier is None:
                    continue
            try:
                information_content = round(float(result_source.get("ic", None)), 1)
                if information_content == 0.0:
                    information_content = None
            except TypeError:
                information_content = None

            node_types = await _populate_biolink_type_ancestors(biolink_type, canonical_identifier)

            conflation_identifiers = []
            conflation_information = identifiers[0].get("c", {})
            if conflations.get("GeneProtein", False):
                gene_protein_identifiers = conflation_information.get("gp", None)
                if gene_protein_identifiers is not None:
                    conflation_identifiers.extend(gene_protein_identifiers)

            if conflations.get("DrugChemical", False):
                drug_chemical_identifiers = conflation_information.get("dc", None)
                if drug_chemical_identifiers is not None:
                    conflation_identifiers.extend(drug_chemical_identifiers)

            if any(conflations.values()) and len(conflation_identifiers) > 0:
                conflation_result_lookup, malformed_conflation_curies = await _lookup_equivalent_identifiers(
                    biothings_metadata, conflation_identifiers
                )

                replacement_identifiers = []
                replacement_types = []
                conflation_label_discovered = False
                for conflation_curie in conflation_identifiers:
                    conflation_result = conflation_result_lookup.get(conflation_curie, {})
                    conflation_biolink_type = conflation_result.get("_source", {}).get("type", [])
                    conflation_identifier_lookup = conflation_result.get("_source", {}).get("identifiers", [])

                    for conflation_entry in conflation_identifier_lookup:
                        conflation_entry.update({"t": [conflation_biolink_type]})

                    conflation_types = await _populate_biolink_type_ancestors(
                        conflation_biolink_type, conflation_identifier_lookup[0].get("i", None)
                    )

                    replacement_identifiers += conflation_identifier_lookup
                    replacement_types += conflation_types

                    conflation_preferred_label = conflation_result.get("_source", {}).get("preferred_name", None)
                    if conflation_preferred_label is not None and not conflation_label_discovered:
                        preferred_label = conflation_preferred_label
                        conflation_label_discovered = True

                replacement_types = unique_list(replacement_types)

                labels = [identifier.get("l", "") for identifier in replacement_identifiers]

                node = NormalizedNode(
                    curie=input_curie,
                    canonical_identifier=canonical_identifier,
                    preferred_label=preferred_label,
                    information_content=information_content,
                    identifiers=replacement_identifiers,
                    types=replacement_types,
                )
                nodes.append(node)
            else:
                labels = [identifier.get("l", "") for identifier in identifiers]
                node = NormalizedNode(
                    curie=input_curie,
                    canonical_identifier=canonical_identifier,
                    preferred_label=preferred_label,
                    information_content=information_content,
                    identifiers=identifiers,
                    types=node_types,
                )
                nodes.append(node)
    return nodes


async def _populate_biolink_type_ancestors(biolink_type: Union[str, list[str]], canonical_identifier: str) -> list[str]:
    if not isinstance(biolink_type, list):
        biolink_type = [biolink_type]

    biolink_type_tree = []
    for bltype in biolink_type:
        if not bltype:
            fallback_type = "biolink:NamedThing"
            logging.error(
                "No type information found for '%s'. Default type set to -> '%s'",
                canonical_identifier,
                fallback_type,
            )
            biolink_type_tree.append(fallback_type)
        else:
            for anc in toolkit.get_ancestors(bltype):
                biolink_type_tree.append(toolkit.get_element(anc)["class_uri"])

    # We need to remove `biolink:Entity` from the types returned.
    # (See explanation at https://github.com/TranslatorSRI/NodeNormalization/issues/173)
    try:
        biolink_type_tree.remove("biolink:Entity")
    except ValueError:
        pass
    return biolink_type_tree


def unique_list(seq) -> list:
    seen = set()
    seen_add = seen.add
    return [x for x in seq if not (x in seen or seen_add(x))]


async def _lookup_equivalent_identifiers(
    biothings_metadata: BiothingsNamespace, curies: list[str]
) -> tuple[list, list]:
    if len(curies) == 0:
        return [], []

    curie_terms_query = {"bool": {"filter": [{"terms": {"identifiers.i": curies}}]}}
    source_fields = ["identifiers", "type", "ic", "preferred_name"]
    index = biothings_metadata.elasticsearch.metadata.indices["node"]
    term_search_result = await biothings_metadata.elasticsearch.async_client.search(
        query=curie_terms_query, index=index, size=len(curies), source_includes=source_fields
    )

    # Post processing to ensure we can identify invalid curies provided by the query
    identifiers_set = set()
    identifier_result_lookup = {}
    for result in term_search_result.body["hits"]["hits"]:
        identifiers = result.get("_source", {}).get("identifiers", [])
        for identifier in identifiers:
            equivalent_identifier = identifier.get("i", None)
            identifiers_set.add(equivalent_identifier)
            identifier_result_lookup[equivalent_identifier] = result

    malformed_curies = set(curies) - identifiers_set
    return identifier_result_lookup, malformed_curies
