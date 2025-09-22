import json
import pathlib
import sqlite3

from typing import Union

# Duplication of definiton from dumper to avoid circular reference
CONFLATION_LOOKUP_DATABASE = "conflation.sqlite3"

DRUG_CHEMICAL_IDENTIFIER_FILES = [
    "Drug.txt",
    "ChemicalEntity.txt",
    "SmallMolecule.txt",
    "ComplexMolecularMixture.txt",
    "MolecularMixture.txt",
    "Protein.txt",
]


GENE_PROTEIN_IDENTIFER_FILES = ["Protein.txt", "Gene.txt"]


def load_data_file(input_file: str):
    """
    Originally attempted to pass the conflation_database as a second argument, but ran into issues
    with the parallelized uploader worker handling multiple arguments

    The conflation_database is a static singular sqlite3 file located in the same directory as the
    data files as it's generated post-dump. We can just derived it at run-time from the provided
    data filepath

    Afterwards the data processing is straight forward, we effectively don't transform the state of
    the nodenorm files
    """
    data_folder = pathlib.Path(input_file).absolute().resolve().parent
    conflation_database = data_folder.joinpath(CONFLATION_LOOKUP_DATABASE)
    connection = sqlite3.connect(str(conflation_database))

    if input_file.name in DRUG_CHEMICAL_IDENTIFIER_FILES or input_file.name in GENE_PROTEIN_IDENTIFER_FILES:
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
