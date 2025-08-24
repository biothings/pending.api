import json
import pathlib
import sqlite3

from typing import Union

drug_chemical_identifier_files = [
    "Drug.txt",
    "ChemicalEntity.txt",
    "SmallMolecule.txt",
    "ComplexMolecularMixture.txt",
    "MolecularMixture.txt",
    "Protein.txt",
]


gene_protein_identifier_files = ["Protein.txt", "Gene.txt"]


def load_data_file(input_file: str, conflation_database: Union[str, pathlib.Path]):
    connection = sqlite3.connect(str(conflation_database))
    if input_file.name in drug_chemical_identifier_files or input_file.name in gene_protein_identifier_files:
        _load_data_file_with_conflations(input_file, connection)
    else:
        _load_data_file(input_file)


def _load_data_file(input_file: Union[str, pathlib.Path]):
    with open(input_file, encoding="utf-8") as file_handle:
        buffer = []
        line = file_handle.readline()
        while line:
            doc = json.loads(line)
            doc["_id"] = doc["identifiers"][0]["i"]
            try:
                doc["ic"] = float(doc["ic"])
            except (TypeError, ValueError):
                doc["ic"] = 0.0
            buffer.append(doc)
            doc["identifiers"]["c"] = {"gp": None, "cd": None}

            if len(buffer) >= 1024:
                yield from buffer
                buffer = []
            line = file_handle.readline()

        if len(buffer) > 0:
            yield from buffer
            buffer = []


def _load_data_file_with_conflations(input_file: Union[str, pathlib.Path], conflation_database: sqlite3.Connection):
    with open(input_file, encoding="utf-8") as file_handle:
        buffer = []
        canonical_identifiers = []
        line = file_handle.readline()
        while line:
            doc = json.loads(line)
            canonical_identifier = doc["identifiers"][0]["i"]
            canonical_identifiers.append(canonical_identifier)
            doc["_id"] = canonical_identifier
            try:
                doc["ic"] = float(doc["ic"])
            except (TypeError, ValueError):
                doc["ic"] = 0.0
            buffer.append(doc)
            doc["identifiers"]["c"] = {"gp": None, "cd": None}

            if len(buffer) >= 1024:
                buffer = _update_buffer_with_conflations(buffer, canonical_identifiers, conflation_database)
                yield from buffer
                buffer = []
                canonical_identifiers = []

            line = file_handle.readline()

        if len(buffer) > 0:
            buffer = _update_buffer_with_conflations(buffer, canonical_identifiers, conflation_database)
            yield from buffer


def _update_buffer_with_conflations(
    buffer: list[dict], canonical_identifiers: list[str], conflation_database: sqlite3.Connection
) -> list[str]:
    """
    Batch updates the buffer documents with the conflation identifiers found
    """
    identifiers = [{"canonical_identifier": identifier for identifier in canonical_identifiers}]
    identifier_results = conflation_database.executemany(
        "SELECT identifiers, type FROM conflations WHERE conflation = VALUES(:canonical_identifier)", identifiers
    )

    for document, conflation_results in zip(buffer, identifier_results.fetchall()):
        if conflation_results is not None:
            identifiers = conflation_results[0].split(",").strip()
            conflation_type = conflation_results[1]

            if conflation_type == "GeneProtein":
                document["identifiers"]["c"]["gp"] = identifiers
            elif conflation_type == "DrugChemical":
                document["identifiers"]["c"]["dc"] = identifiers
    return buffer
