import dataclasses
import logging
import os
import time
from typing import Union

import bmt as bmt

from biothings.web.handlers import BaseAPIHandler
from tornado.web import HTTPError


logger = logging.getLogger(__name__)
logger.setLevel(logging.DEBUG)


BIOLINK_VERSION = os.getenv("BIOLINK_VERSION", "v4.2.2")
BIOLINK_MODEL_URL = f"https://raw.githubusercontent.com/biolink/biolink-model/{BIOLINK_VERSION}/biolink-model.yaml"
toolkit = bmt.Toolkit(BIOLINK_MODEL_URL)


defaultconfig = {
    "preferred_name_boost_prefixes": {
        "biolink:ChemicalEntity": [
            "DRUGBANK",
            "DrugCentral",
            "CHEBI",
            "MESH",
            "CHEMBL.COMPOUND",
            "GTOPDB",
            "HMDB",
            "RXCUI",
            "PUBCHEM.COMPOUND",
        ]
    },
    "demote_labels_longer_than": 15,
}


@dataclasses.dataclass(frozen=True)
class NormalizedNode:
    curie: str
    canonical_identifier: str
    information_content: float
    identifiers: list[str]
    labels: list[str]
    types: list[str]


class NormalizedNodesHandler(BaseAPIHandler):
    """
    Mirror implementation to the renci implementation found at
    https://nodenormalization-sri.renci.org/docs

    We intend to mirror the /get_normalized_nodes endpoint
    """

    name = "normalizednodes"

    async def get(self, *args, **kwargs):
        normalized_curies = self.get_arguments("curie")
        if len(normalized_curies) == 0:
            raise HTTPError(
                detail="Missing curie argument, there must be at least one curie to normalize", status_code=400
            )

        conflate = self.get_argument("conflate", True)
        drug_chemical_conflate = self.get_argument("drug_chemical_conflate", False)
        description = self.get_arguments("description", False)
        individual_types = self.get_arguments("individual_types", False)

        normalized_nodes = await self.get_normalized_nodes(
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
        normalization_curies = self.args_json.get("curie", [])
        if len(normalization_curies) == 0:
            raise HTTPError(
                detail="Missing curie argument, there must be at least one curie to normalize", status_code=400
            )

        conflate = self.args_json.get("conflate", True)
        drug_chemical_conflate = self.args_json.get("drug_chemical_conflate", False)
        description = self.args_json.get("description", False)
        individual_types = self.args_json.get("individual_types", False)

        normalized_nodes = await self.get_normalized_nodes(
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
        self,
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

        nodes = await self._lookup_curie_metadata(curies, conflations)

        # As per https://github.com/TranslatorSRI/Babel/issues/158, we select the first label from any
        # identifier _except_ where one of the types is in preferred_name_boost_prefixes, in which case
        # we prefer the prefixes listed there.
        #
        # This should perfectly replicate NameRes labels for non-conflated cliques, but it WON'T perfectly
        # match conflated cliques. To do that, we need to run the preferred label algorithm on ONLY the labels
        # for the FIRST clique of the conflated cliques with labels.
        node_identifier_label_mapping = await self._lookup_identifiers_with_labels(nodes)

        normal_nodes = {}
        for aggregate_node in nodes:
            identifiers_with_labels = node_identifier_label_mapping[aggregate_node.curie]
            normal_node = await self.create_normalized_node(
                aggregate_node,
                identifiers_with_labels,
                include_descriptions=include_descriptions,
                include_individual_types=include_individual_types,
                conflations=conflations,
            )
            normal_nodes[aggregate_node.curie] = normal_node

        end_time = time.perf_counter_ns()
        logger.info(
            (
                f"Normalized {len(curies)} nodes in {(end_time - start_time)/1_000_000:.2f} ms with arguments "
                f"(curies={curies}, conflate_gene_protein={conflate_gene_protein}, conflate_chemical_drug={conflate_chemical_drug}, "
                f"include_descriptions={include_descriptions}, include_individual_types={include_individual_types})"
            )
        )
        return normal_nodes

    async def create_normalized_node(
        self,
        aggregate_node: NormalizedNode,
        identifiers_with_labels: list[str],
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

        # OK, now we should have id's in the format [ {"i": "MONDO:12312", "l": "Scrofula"}, {},...]

        # We might get here without any labels, which is fine. At least we tried.

        # At this point:
        #   - eids will be the full list of all identifiers and labels in this clique.
        #   - identifiers_with_labels is the list of identifiers and labels for the first subclique that has at least
        #     one label.

        # Note that types[canonical_id] goes from most specific to least specific, so we
        # need to reverse it in order to apply preferred_name_boost_prefixes for the most
        # specific type.
        possible_labels = []
        for bltype in aggregate_node.types[::-1]:
            if bltype in defaultconfig["preferred_name_boost_prefixes"]:
                # This is the most specific matching type, so we use this and then break.
                possible_labels = list(
                    map(
                        lambda ident: ident.get("l", ""),
                        self._sort_identifiers_with_boosted_prefixes(
                            identifiers_with_labels, defaultconfig["preferred_name_boost_prefixes"][bltype]
                        ),
                    )
                )

                # Add in all the other labels -- we'd still like to consider them, but at a lower priority.
                for eid in identifiers_with_labels:
                    label = eid.get("l", "")
                    if label not in possible_labels:
                        possible_labels.append(label)

                # Since this is the most specific matching type, we shouldn't do other (presumably higher-level)
                # categories: so let's break here.
                break

        # Step 1.2. If we didn't have a preferred_name_boost_prefixes, just use the identifiers in their
        # Biolink prefix order.
        if not possible_labels:
            possible_labels = map(lambda eid: eid.get("l", ""), identifiers_with_labels)

        # Step 2. Filter out any suspicious labels.
        filtered_possible_labels = [
            l
            for l in possible_labels
            if l
            and not l.startswith(
                "CHEMBL"
            )  # Ignore blank or empty names.  # Some CHEMBL names are just the identifier again.
        ]

        # Step 3. Filter out labels longer than defaultconfig['demote_labels_longer_than'], but only if there is at
        # least one label shorter than this limit.
        labels_shorter_than_limit = [
            l for l in filtered_possible_labels if l and len(l) <= defaultconfig["demote_labels_longer_than"]
        ]
        if labels_shorter_than_limit:
            filtered_possible_labels = labels_shorter_than_limit

        # Note that the id will be from the equivalent ids, not the canonical_id.  This is to handle conflation
        if len(filtered_possible_labels) > 0:
            normal_node = {
                "id": {"identifier": aggregate_node.identifiers[0]["i"], "label": filtered_possible_labels[0]}
            }
        else:
            # Sometimes, nothing has a label :(
            if aggregate_node.identifiers is not None and len(aggregate_node.identifiers) > 0:
                normal_node = {"id": {"identifier": aggregate_node.identifiers[0]["i"]}}
            else:
                normal_node = {"id": {"identifier": aggregate_node.canonical_identifier}}

        # Now that we've determined a label for this clique, we should never use identifiers_with_labels, possible_labels,
        # or filtered_possible_labels after this point.

        # if descriptions are enabled look for the first available description and use that
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
        for eqid in aggregate_node.identifiers:
            eq_item = {"identifier": eqid["i"]}
            if "l" in eqid:
                eq_item["label"] = eqid["l"]

            # if descriptions is enabled and exist add them to each eq_id entry
            if include_descriptions and "d" in eqid and len(eqid["d"]):
                eq_item["description"] = eqid["d"][0]

            # if individual types have been requested, add them too.
            if include_individual_types and "t" in eqid:
                eq_item["type"] = eqid["t"][-1]

            normal_node["equivalent_identifiers"].append(eq_item)

        normal_node["type"] = aggregate_node.types

        # add the info content to the node if we got one
        if aggregate_node.information_content is not None:
            normal_node["information_content"] = aggregate_node.information_content

        return normal_node

    async def _lookup_curie_metadata(self, curies: list[str], conflations: dict) -> list[NormalizedNode]:
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
        curie_order = {curie: index for index, curie in enumerate(curies)}
        curies, malformed_curies, identifier_result_lookup = await self._lookup_equivalent_identifiers(
            curies, curie_order
        )

        nodes = []
        for input_curie in curies:
            result = identifier_result_lookup[input_curie]
            result_source = result.get("_source", {})
            identifiers = result_source.get("identifiers", [])
            biolink_type = result_source.get("type", None)

            # Every equivalent identifier here has the same type.
            for eqid in identifiers:
                eqid.update({"t": biolink_type})

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

            node_types = await self._populate_biolink_type_ancestors(biolink_type, canonical_identifier)

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
                conflation_order = {curie: index for index, curie in enumerate(conflation_identifiers)}
                conflation_curies, _, conflation_result_lookup = await self._lookup_equivalent_identifiers(
                    conflation_identifiers, conflation_order
                )

                replacement_identifiers = []
                replacement_types = []
                for conflation_curie in conflation_curies:
                    conflation_result = conflation_result_lookup.get(conflation_curie, {})
                    conflation_biolink_type = conflation_result.get("_source", {}).get("type", [])
                    conflation_identifier_lookup = conflation_result.get("_source", {}).get("identifiers", [])

                    for conflation_entry in conflation_identifier_lookup:
                        conflation_entry.update({"t": conflation_biolink_type})

                    conflation_types = await self._populate_biolink_type_ancestors(
                        conflation_biolink_type, conflation_identifier_lookup[0].get("i", None)
                    )

                    replacement_identifiers += conflation_identifier_lookup
                    replacement_types += conflation_types

                replacement_types = self.unique_list(replacement_types)

                labels = [identifier.get("l", "") for identifier in replacement_identifiers]

                node = NormalizedNode(
                    curie=input_curie,
                    canonical_identifier=canonical_identifier,
                    information_content=information_content,
                    identifiers=replacement_identifiers,
                    labels=labels,
                    types=replacement_types,
                )
                nodes.append(node)
            else:
                labels = [identifier.get("l", "") for identifier in identifiers]
                node = NormalizedNode(
                    curie=input_curie,
                    canonical_identifier=canonical_identifier,
                    information_content=information_content,
                    identifiers=identifiers,
                    labels=labels,
                    types=node_types,
                )
                nodes.append(node)

        for curie in malformed_curies:
            node = NormalizedNode(
                curie=curie,
                canonical_identifier=None,
                information_content=-1.0,
                identifiers=[],
                labels=[],
                types=[],
            )
            nodes.insert(curie_order[curie], node)
        return nodes

    async def _populate_biolink_type_ancestors(
        self, biolink_type: Union[str, list[str]], canonical_identifier: str
    ) -> list[str]:
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

    def _sort_identifiers_with_boosted_prefixes(self, identifiers: list[str], prefixes: list[str]):
        """
        Given a list of identifiers (with `identifier` and `label` keys), sort them using
        the following rules:
        - Any identifier that has a prefix in prefixes is sorted based on its order in prefixes.
        - Any identifier that does not have a prefix in prefixes is left in place.

        Copied from https://github.com/TranslatorSRI/Babel/blob/0c3f3aed1bb1647f1ca101ba905dc241797fdfc9/src/babel_utils.py#L315-L333

        :param identifiers: A list of identifiers to sort. This is a list of dictionaries
            containing `identifier` and `label` keys, and possible others that we ignore.
        :param prefixes: A list of prefixes, in the order in which they should be boosted.
            We assume that CURIEs match these prefixes if they are in the form `{prefix}:...`.
        :return: The list of identifiers sorted as described above.
        """

        # Thanks to JetBrains AI.
        return sorted(
            identifiers,
            key=lambda identifier: (
                prefixes.index(identifier["i"].split(":", 1)[0])
                if identifier["i"].split(":", 1)[0] in prefixes
                else len(prefixes)
            ),
        )

    def unique_list(self, seq) -> list:
        seen = set()
        seen_add = seen.add
        return [x for x in seq if not (x in seen or seen_add(x))]

    async def _lookup_equivalent_identifiers(self, curies: list[str], curie_order: dict) -> tuple[list, list, list]:
        if len(curies) == 0:
            return [], [], []

        curie_terms_query = {"bool": {"filter": [{"terms": {"identifiers.i": curies}}]}}
        source_fields = ["identifiers", "type", "ic"]
        index = self.biothings.elasticsearch.metadata.indices["node"]
        term_search_result = await self.biothings.elasticsearch.async_client.search(
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
        if malformed_curies:
            curies = [c for c in curies if c not in malformed_curies]

        return curies, malformed_curies, identifier_result_lookup

    async def _lookup_identifiers_with_labels(self, nodes: list[NormalizedNode]) -> dict:
        """
        Used specifically for handling conflations.

        Replicates Babel's behavior

        Runs on the first set of identifiers and greedily returns the first set with labels found
        """
        curies = []
        for node in nodes:
            curies.extend((identifier["i"] for identifier in node.identifiers))

        curie_order = {curie: index for index, curie in enumerate(curies)}
        _, _, curie_label_lookup = await self._lookup_equivalent_identifiers(curies, curie_order)

        curies_already_checked = set()
        node_identifier_label_mapping = {}
        for aggregate_node in nodes:
            for identifier in aggregate_node.identifiers:
                curie = identifier.get("i", "")
                if curie in curies_already_checked:
                    continue

                identifiers_with_labels = curie_label_lookup[curie].get("_source", {}).get("identifiers", [])

                labels = map(lambda ident: ident.get("l", ""), identifiers_with_labels)
                if any(map(lambda l: l != "", labels)):
                    break

                # Since we didn't get any matches here, add it to the list of CURIEs already checked so
                # we don't make redundant queries to the database.
                curies_already_checked.update(set(map(lambda x: x.get("i", ""), identifiers_with_labels)))

            node_identifier_label_mapping[aggregate_node.curie] = identifiers_with_labels
        return node_identifier_label_mapping
