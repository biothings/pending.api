import sqlite3
import time
from pathlib import Path
from typing import Union

import pymongo
from pymongo.errors import BulkWriteError

from biothings import config
from biothings.utils.dataload import merge_struct
from biothings.utils.serializer import json_loads, json_dumps
from biothings.utils.hub_db import get_src_db

from .static import IDENTIFIER_LOOKUP_DATABASE


logger = config.logger


def subset_upload_worker(
    input_file: Union[str, Path],
    buffer_size: int,
    offset_start: int,
    offset_end: int,
    collection_name: str,
    conflation_database: str = None,
) -> int:
    """
    Internal function for handling the multipart uploading of the file in partitions

    Accepts the file path, along with the chunk start and chunk end in bytes to determine
    what offset to start and stop at in the file

    The conflation_connection is a static singular sqlite3 file located in the same directory as the
    data files as it's generated post-dump. We can just derived it at run-time from the provided
    data filepath

    Afterwards the data processing is straight forward, we effectively don't transform the state of
    the nodenorm files
    """
    logger.info("Starting bulk upload to backend %s [%s|%s]", input_file, offset_start, offset_end)
    conflation_connection = None
    if conflation_database is not None:
        conflation_connection = sqlite3.connect(str(conflation_database))

    upload_database = get_src_db()
    collection = pymongo.collection.Collection(database=upload_database, name=collection_name)

    document_count = 0
    with open(input_file, encoding="utf-8") as file_handle:
        buffer = []
        identifiers = []
        canonical_identifiers = []
        file_handle.seek(offset_start)
        while file_handle.tell() < offset_end:
            line = file_handle.readline()
            doc = json_loads(line)

            canonical_identifier = doc["identifiers"][0]["i"]
            canonical_identifiers.append(canonical_identifier)
            doc["_id"] = canonical_identifier
            try:
                doc["ic"] = float(doc["ic"])
            except (TypeError, ValueError):
                doc["ic"] = 0.0

            buffer.append(doc)

            for identifier in doc["identifiers"]:
                identifiers.append(identifier["i"])
                identifier["c"] = {"gp": None, "dc": None}

            if len(buffer) >= buffer_size:
                document_count += len(buffer)
                if conflation_connection is not None:
                    buffer = _update_buffer_with_conflations(buffer, canonical_identifiers, conflation_connection)
                _upload_buffer(collection, buffer, input_file, file_handle.tell() / offset_end)
                _update_identifier_collection(input_file, identifiers)
                buffer = []
                canonical_identifiers = []

        if len(buffer) > 0:
            document_count += len(buffer)
            if conflation_connection is not None:
                buffer = _update_buffer_with_conflations(buffer, canonical_identifiers, conflation_connection)
            _upload_buffer(collection, buffer, input_file, file_handle.tell() / offset_end)
            _update_identifier_collection(input_file, identifiers)
    return document_count


def _update_buffer_with_conflations(
    buffer: list[dict], canonical_identifiers: list[str], conflation_database: sqlite3.Connection
) -> list[str]:
    """
    Batch updates the buffer documents with the conflation identifiers found

    Performs a lookup against the conflation database to find all conflation identifiers
    We then create an index table so we can quickly lookup up the buffer index based off the
    canonical identifier

    We iterate over the discovered conflation identifier results and update the buffer with the
    conflation information before returning the newly updated buffer
    """
    identifiers_repr = ", ".join("?" for _ in canonical_identifiers)
    search_statement = f"SELECT identifiers, type FROM conflations WHERE conflation in ({identifiers_repr})"
    identifier_results = conflation_database.execute(search_statement, canonical_identifiers)

    lookup_buffer_index = {document["identifiers"][0]["i"]: index for index, document in enumerate(buffer)}

    for conflation_result in identifier_results.fetchall():
        if conflation_result is not None:
            identifiers = conflation_result[0].strip().split(",")
            conflation_type = conflation_result[1]

            for identifier in identifiers:
                buffer_index = lookup_buffer_index.get(identifier, None)
                if buffer_index is not None:
                    for identifier in buffer[buffer_index]["identifiers"]:
                        if conflation_type == "GeneProtein":
                            identifier["c"]["gp"] = identifiers
                        elif conflation_type == "DrugChemical":
                            identifier["c"]["dc"] = identifiers
    return buffer


def _upload_buffer(
    collection: pymongo.collection.Collection, buffer: list[dict], input_file: Union[str, Path], progress: float
):
    try:
        t0 = time.perf_counter()
        document_group = [pymongo.InsertOne(d) for d in buffer]
        collection.bulk_write(document_group, ordered=False)
        logger.debug(
            "bulk write #[%d] in [%3.4f]s | file %s subset progress: %1.3f%%",
            len(document_group),
            time.perf_counter() - t0,
            input_file.name,
            progress * 100,
        )
    except BulkWriteError as bulk_write_error:
        _handle_bulk_write_error(bulk_write_error, collection, input_file)


def _handle_bulk_write_error(
    bulk_write_error: BulkWriteError, collection: pymongo.collection.Collection, input_file: Union[str, Path]
):
    logger.debug("Fixing %d records ", len(bulk_write_error.details["writeErrors"]))
    ids = [d["op"]["_id"] for d in bulk_write_error.details["writeErrors"]]

    # build hash of existing docs
    docs = collection.find({"_id": {"$in": ids}})

    hdocs = {}
    for doc in docs:
        hdocs[doc["_id"]] = doc

    bulk = []
    for err in bulk_write_error.details["writeErrors"]:
        errdoc = err["op"]
        existing = hdocs[errdoc["_id"]]
        if errdoc is existing:
            continue
        assert "_id" in existing
        _id = errdoc.pop("_id")
        merged = merge_struct(errdoc, existing)

        # update previously fetched doc. if several errors are about the same doc id,
        # we would't merged things properly without an updated document
        assert "_id" in merged
        bulk.append(pymongo.UpdateOne({"_id": _id}, {"$set": merged}))
        hdocs[_id] = merged

    collection.bulk_write(bulk, ordered=False)


def create_identifiers_table(data_directory: Union[str, Path]) -> None:
    identifier_database = Path(data_directory).resolve().absolute().joinpath(IDENTIFIER_LOOKUP_DATABASE)
    identifier_connection = sqlite3.connect(str(identifier_database))
    cursor = identifier_connection.cursor()
    identifier_existence_check = "DROP TABLE IF EXISTS identifiers"
    cursor.execute(identifier_existence_check)

    identifier_table = (
        "CREATE TABLE IF NOT EXISTS identifiers"
        "("
        "identifier text PRIMARY KEY NOT NULL, "
        "count INT DEFAULT 1,"
        "origin_file text NOT NULL"
        ");"
    )
    cursor.execute(identifier_table)
    identifier_connection.commit()
    identifier_connection.close()


def _update_identifier_collection(input_file: Union[str, Path], identifiers: list[str]):
    """
    Temporarily stopgap to identify our CURIE duplication issue

    Stores all identifiers in a sqlite3 database for post-update fixing
    """
    data_directory = Path(input_file).parent
    identifier_database = data_directory.joinpath(IDENTIFIER_LOOKUP_DATABASE)
    identifier_connection = sqlite3.connect(str(identifier_database))
    cursor = identifier_connection.cursor()

    upsert_statement = (
        "INSERT INTO identifiers(identifier, origin_file) "
        "VALUES(:identifier, :origin_file) "
        "ON CONFLICT(identifier) "
        "DO UPDATE SET count=count+1;"
    )
    identifier_information = [{"identifier": identifier, "origin_file": input_file.name} for identifier in identifiers]

    cursor.executemany(upsert_statement, identifier_information)
    identifier_connection.commit()
    identifier_connection.close()
