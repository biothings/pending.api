import collections
import itertools
import json
import multiprocessing
import pathlib
import sqlite3

from typing import Union

DRUG_CHEMICAL_IDENTIFIER_FILES = [
    "Drug.txt",
    "ChemicalEntity.txt",
    "SmallMolecule.txt",
    "ComplexMolecularMixture.txt",
    "MolecularMixture.txt",
    "Protein.txt",
]


GENE_PROTEIN_IDENTIFER_FILES = ["Protein.txt", "Gene.txt"]


def load_data_file(input_file: str, conflation_database: Union[str, pathlib.Path]):
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


def load_conflation_specific_data(input_file: str, conflation_database: Union[str, pathlib.Path]):
    connection = sqlite3.connect(str(conflation_database))

    def query_conflation_database(compendia_lines: dict, connection: sqlite3.Connection) -> list[dict]:
        identifier_results = connection.executemany(
            "SELECT conflation FROM conflations WHERE conflation = VALUES(:identifier)",
            [{"identifier": i} for i in compendia_lines.keys()],
        )
        query_buffer = []
        for lookup_result in identifier_results.fetchall():
            query_buffer.append(compendia_lines[lookup_result[0]])
        return query_buffer

    with multiprocessing.Pool() as file_pool:
        result_buffer = collections.deque()
        return_buffer = []
        with open(input_file, "r", encoding="utf-8") as data_handle:
            while file_slice := [json.loads(line) for line in itertools.islice(data_handle, 10000)]:
                slice_mapping = {doc["identifiers"][0]["i"]: doc for doc in file_slice}
                query_result = file_pool.apply_async(query_conflation_database, [slice_mapping, connection])
                result_buffer.append(query_result)

                if len(result_buffer) >= 10000:
                    result_buffer[0].wait()

                while len(result_buffer) > 0 and result_buffer[0].ready():
                    result = result_buffer.popleft()
                    return_buffer.extend(result.get())

                if len(return_buffer) >= 10000:
                    yield from return_buffer
                    return_buffer = []

        for result in result_buffer:
            result.wait()
            return_buffer.extend(result.get())

        yield from return_buffer
