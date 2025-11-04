import concurrent.futures
import copy
import hashlib
import itertools
import json
import os
import sqlite3
import time
from collections import defaultdict
from pathlib import Path
from typing import Union

import pymongo
from pymongo.errors import BulkWriteError

from biothings import config
from biothings.utils.dataload import merge_struct
from biothings.utils.serializer import json_loads
from biothings.utils.hub_db import get_src_db
from biothings.utils.common import iter_n

from .static import (
    CONFLATION_LOOKUP_DATABASE,
    DRUG_CHEMICAL_IDENTIFIER_FILES,
    GENE_PROTEIN_IDENTIFER_FILES,
    IDENTIFIER_LOOKUP_DATABASE,
    NODENORM_UPLOAD_CHUNKS,
)


logger = config.logger


def upload_process(data_folder: Union[str, Path], collection_name: str) -> int:
    create_identifiers_table(data_folder)

    with concurrent.futures.ProcessPoolExecutor(max_workers=1 * os.cpu_count()) as executor:
        process_futures = []
        for index, task in enumerate(_build_offset_tasks(data_folder, collection_name)):
            future = executor.submit(subset_upload_worker, **task)
            process_futures.append(future)

        total_document_count = 0
        for index, future in enumerate(concurrent.futures.as_completed(process_futures)):
            try:
                identifiers = future.result()
            except Exception as gen_exc:
                logger.exception(gen_exc)
                raise gen_exc
            else:
                update_identifier_collection(data_folder, identifiers)
                total_document_count += len(identifiers)
                logger.debug(
                    "Task %s completed | Update %s identifiers | Total identifiers %s",
                    index,
                    len(identifiers),
                    total_document_count,
                )
                del identifiers

    create_mongo_identifiers_index(collection_name)
    create_identifiers_index(data_folder)
    cleanup_curie_duplication(data_folder, collection_name)
    return int(total_document_count)


def _build_offset_tasks(data_folder: Union[str, Path], collection_name: str):
    """
    Reads every file and builds an index file compiling the offset ranges
    we want to read as a subset of the file processing.

    These are all generated in a queue that we continually feed to multiprocessing queue
    that is continually uploading to the backend database
    """

    def _populate_upload_arguments(input_file: Union[Path, str], num_partitions: int) -> list:
        logger.info("Analyzing offsets for %s | number of partitions %s", input_file, num_partitions)
        conflation_database = None
        if input_file.name in DRUG_CHEMICAL_IDENTIFIER_FILES or input_file.name in GENE_PROTEIN_IDENTIFER_FILES:
            data_folder = Path(input_file).absolute().resolve().parent
            conflation_database = data_folder.joinpath(CONFLATION_LOOKUP_DATABASE)

        offsets = generate_file_offsets(input_file, num_partitions)

        argument_collection = []
        for offset_range in window(offsets, 2):
            offset_start = offset_range[0]
            offset_end = offset_range[1]

            arguments = {
                "input_file": input_file,
                "buffer_size": 5000,
                "offset_start": offset_start,
                "offset_end": offset_end,
                "collection_name": collection_name,
                "conflation_database": conflation_database,
            }
            argument_collection.append(arguments)
        return argument_collection

    thread_futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for filename, num_partitions in NODENORM_UPLOAD_CHUNKS.items():
            filepath = Path(data_folder).joinpath(filename).resolve().absolute()
            arguments = {"input_file": filepath, "num_partitions": num_partitions}
            _populate_upload_arguments(**arguments)
            future = executor.submit(_populate_upload_arguments, **arguments)
            thread_futures.append(future)

    concurrent.futures.wait(thread_futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED)

    yield from itertools.chain.from_iterable([future.result() for future in thread_futures])


def generate_file_offsets(file: Union[str, Path], num_partitions: int = None):
    """
    Generates an in-memory index for a file. Rather than storing the offset

    We're primarily interested in parallel processsing a file in batches for uploading
    to a database, so we don't need to store every offset as that would be a waste of memory.
    Rather, based off the number of partitions we store the file size as we iterate over the file
    so we can track the approximate percentage we've completed so we can store inteval markers while
    chunking the file
    """
    if num_partitions is None:
        num_partitions = 10

    file = Path(file).absolute().resolve()
    file_size_bytes = file.stat().st_size
    file_index = file.with_suffix(".index")

    logger.debug("Calculating SHA256 hashsum for file: %s", file)
    file_hash = sha256sum(file)

    if file_index.exists():
        with open(file_index, "r", encoding="utf-8") as index_handle:
            previous_index = json.load(index_handle)

        if previous_index["hash"] == file_hash:
            return previous_index["index"]

        logger.debug(
            "Different hash found for file %s [%s, %s] [previous, current]. " "Updating file offsets with the new file",
            file,
            previous_index["hash"],
            file_hash,
        )

    partitions = [0]
    marker = file_size_bytes / num_partitions
    progress_bytes = 0
    with open(file, "rb") as handle:
        while line := handle.readline():
            if progress_bytes >= marker:
                partitions.append(handle.tell())
                progress_bytes = 0
            else:
                progress_bytes += len(line)
        partitions.append(handle.tell())
    with open(file_index, "w", encoding="utf-8") as index_handle:
        index_handle.write(json.dumps({"index": partitions, "hash": file_hash}))
    return partitions


def sha256sum(file: Union[str, Path], buffer_size: int = None):
    """
    Generates a sha256 hashsum for a file to determine if the previously generated
    index requires updating
    """
    if buffer_size is None:
        buffer_size = 1024 * 128

    filehash = hashlib.sha256()
    buffer = bytearray(buffer_size)
    file_view = memoryview(buffer)

    with open(file, "rb", buffering=0) as file_handle:
        while n := file_handle.readinto(file_view):
            filehash.update(file_view[:n])
    return filehash.hexdigest()


def window(seq: tuple, n: int = 2):
    """
    Returns a sliding window (of width n) over data from the iterable.
    s -> (s0,s1,...s[n-1]), (s1,s2,...,sn), ...
    """
    it = iter(seq)
    result = tuple(itertools.islice(it, n))
    if len(result) == n:
        yield result
    for elem in it:
        result = result[1:] + (elem,)
        yield result


def subset_upload_worker(
    input_file: Union[str, Path],
    buffer_size: int,
    offset_start: int,
    offset_end: int,
    collection_name: str,
    conflation_database: str = None,
) -> list[str]:
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
                if conflation_connection is not None:
                    buffer = _update_buffer_with_conflations(buffer, canonical_identifiers, conflation_connection)
                _upload_buffer(collection, buffer, input_file, file_handle.tell() / offset_end)
                buffer = []
                canonical_identifiers = []

        if len(buffer) > 0:
            if conflation_connection is not None:
                buffer = _update_buffer_with_conflations(buffer, canonical_identifiers, conflation_connection)
            _upload_buffer(collection, buffer, input_file, file_handle.tell() / offset_end)
    return identifiers


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


def create_identifiers_table(data_folder: Union[str, Path]) -> None:
    logger.debug("Creating sqlite3 identifiers database")
    identifier_database = Path(data_folder).resolve().absolute().joinpath(IDENTIFIER_LOOKUP_DATABASE)
    identifier_connection = sqlite3.connect(str(identifier_database))
    cursor = identifier_connection.cursor()
    identifier_existence_check = "DROP TABLE IF EXISTS identifiers"
    cursor.execute(identifier_existence_check)

    identifier_table = (
        "CREATE TABLE IF NOT EXISTS identifiers(identifier text PRIMARY KEY NOT NULL, count INT DEFAULT 1);"
    )
    cursor.execute(identifier_table)
    identifier_connection.commit()
    identifier_connection.close()


def create_identifiers_index(data_folder: Union[str, Path]) -> None:
    logger.debug("Creating sqlite3 identifiers database index")
    identifier_database = Path(data_folder).resolve().absolute().joinpath(IDENTIFIER_LOOKUP_DATABASE)
    identifier_connection = sqlite3.connect(str(identifier_database))
    cursor = identifier_connection.cursor()

    identifier_index = "CREATE INDEX IF NOT EXISTS idx_identifiers ON identifiers (identifier, count);"
    cursor.execute(identifier_index)
    identifier_connection.commit()
    identifier_connection.close()


def create_mongo_identifiers_index(collection_name: str) -> None:
    logger.debug("Creating mongodb identifiers.i database index")
    upload_database = get_src_db()
    collection = pymongo.collection.Collection(database=upload_database, name=collection_name)
    collection.create_index("identifiers.i")


def update_identifier_collection(data_folder: Union[str, Path], identifiers: list[str]):
    """
    Temporarily stopgap to identify our CURIE duplication issue

    Stores all identifiers in a sqlite3 database for post-update fixing
    """
    identifier_database = Path(data_folder).joinpath(IDENTIFIER_LOOKUP_DATABASE)
    identifier_connection = sqlite3.connect(str(identifier_database))
    cursor = identifier_connection.cursor()

    upsert_statement = (
        "INSERT INTO identifiers(identifier) "
        "VALUES(:identifier) "
        "ON CONFLICT(identifier) "
        "DO UPDATE SET count=count+1;"
    )
    identifier_information = [{"identifier": identifier} for identifier in identifiers]

    cursor.executemany(upsert_statement, identifier_information)
    identifier_connection.commit()
    identifier_connection.close()


def cleanup_curie_duplication(data_folder: Union[str, Path], collection_name: str):
    """
    Handle the CURIE duplication directly in the mongodb database
    """
    logger.info("Handling CURIE duplication issue")

    identifier_database = Path(data_folder).resolve().absolute().joinpath(IDENTIFIER_LOOKUP_DATABASE)
    identifier_connection = sqlite3.connect(str(identifier_database))
    cursor = identifier_connection.cursor()

    identifier_table = "SELECT identifier FROM identifiers WHERE count > 1;"
    results = cursor.execute(identifier_table)
    duplicate_curies = tuple(results.fetchall())
    identifier_connection.close()

    with concurrent.futures.ThreadPoolExecutor(max_workers=1 * os.cpu_count()) as executor:
        process_futures = []
        for index, curie_batch in enumerate(iter_n(duplicate_curies, 1000)):
            arguments = {"task_id": index, "curies": curie_batch, "collection_name": collection_name}
            future = executor.submit(_curie_duplication_batch_handler, **arguments)
            process_futures.append(future)

        total_correction_count = 0
        for future in concurrent.futures.as_completed(process_futures):
            try:
                task_id, num_corrections = future.result()
            except Exception as gen_exc:
                logger.exception(gen_exc)
            else:
                total_correction_count += num_corrections
                logger.debug(
                    "Task %s completed | Corrected %s documents | Total corrections %s",
                    task_id,
                    num_corrections,
                    total_correction_count,
                )


def _curie_duplication_batch_handler(task_id: int, curies: list[str], collection_name: str):

    num_retry = 10
    counter = 0
    collection = None

    # Due to potential thread starvation from the job-manager heartbeat (which blocks for reasons
    # I'm not quite sure of) we need a potential retry mechanism in case we happen to get starved
    # of resources before we can legitmately connect
    upload_database = get_src_db()
    while collection is None:
        try:
            collection = pymongo.collection.Collection(database=upload_database, name=collection_name)
        except pymongo.errors.ServerSelectionTimeoutError as mongo_timeout_error:
            counter += 1
            logger.exception(mongo_timeout_error)

            if counter >= num_retry:
                raise mongo_timeout_error

            logger.info(
                "Unable to connect to [%s]@<%s>. Re-attempting connection. %d attempts left",
                upload_database,
                collection_name,
                num_retry - counter,
            )

    buffer = []
    for result in curies:
        identifier = result[0]

        cursor = collection.find({"identifiers.i": identifier})
        documents = list(cursor)

        # Handle case where the identifier.i is duplicated within the same document
        if len(documents) == 1:

            # We need to generate every comparison within the same document. itertools.combinations
            # produces every combination, but we need to store it on a per identifier level so we
            # can determine if any of the identifiers match any of the others. This is the goal
            # behind the comparison matrix we build to make every inner comparison possible
            identifier_combinations = tuple(itertools.combinations(documents[0]["identifiers"], 2))

            comparison_matrix = defaultdict(list)
            for index, identifier in enumerate(documents[0]["identifiers"]):
                comparison_filter = [identifier in entry for entry in identifier_combinations]
                comparison_matrix[index] = tuple(itertools.compress(identifier_combinations, comparison_filter))

            removal_index = []
            for index, comparisons in comparison_matrix.items():
                removal_index.append(
                    not all(identifier_group[0] == identifier_group[1] for identifier_group in comparisons)
                )

            # Skipping document as we likely already merged this earlier with duplicate _id merging
            if all(removal_index) or (not any(removal_index) and len(removal_index) == 1):
                logger.debug(
                    "[Task %d] Ignore 1 document due to initial upload BulkWriteError caught duplicate _id. Likely identical documents merged on the type field: %s",
                    task_id,
                    documents[0],
                )
            elif not any(removal_index) and len(removal_index) > 1:
                original_document = copy.deepcopy(documents[0])
                documents[0]["identifiers"] = [documents[0]["identifiers"][0]]

                buffer.append(pymongo.ReplaceOne(original_document, documents[0]))
                logger.debug(
                    "[Task %d] Replace 1 document to trim all identifiers except the first due to them all being identical: %s",
                    task_id,
                    documents[0],
                )
            else:
                original_document = copy.deepcopy(documents[0])
                documents[0]["identifiers"] = list(itertools.compress(documents[0]["identifiers"], removal_index))
                buffer.append(pymongo.ReplaceOne(original_document, documents[0]))
                logger.debug(
                    "[Task %d] Replace 1 document to trim some duplicate identifiers: %s", task_id, documents[0]
                )

        # Handle case where the identifier.i is spread across 2 documents
        elif len(documents) == 2:

            def _evaluate_document_subset(more_identifiers_doc: dict, less_identifiers_doc: dict) -> pymongo.DeleteOne:
                """
                If it passes the subset check, then we can safely delete the document while keeping
                the other document. It must be a complete subset, otherwise we have to perform
                additional analysis to determine where the interesection exists between the two
                documents
                """
                subset_check = []
                for subset_identifier in less_identifiers_doc["identifiers"]:
                    subset_check.append(subset_identifier in more_identifiers_doc["identifiers"])

                operation = None
                if all(subset_check):
                    operation = pymongo.DeleteOne(less_identifiers_doc)
                    logger.debug("[Task %d] Delete 1 document: %s", task_id, less_identifiers_doc)
                return operation

            def _evaluate_document_intersection(more_identifiers_doc: dict, less_identifiers_doc: dict):
                """
                One crucial assumption here is that at least one of these documents is has a type of
                biolink:Protein.

                If the type biolink:Protein isn't found then we cannot make any assumptions about
                how to handle the intersection between the two documents
                """
                operation = None
                if (
                    more_identifiers_doc["type"] == "biolink:Protein"
                    or less_identifiers_doc["type"] == "biolink:Protein"
                ):
                    if more_identifiers_doc["type"] == "biolink:Protein":
                        main_document = more_identifiers_doc
                        side_document = less_identifiers_doc
                    else:
                        main_document = less_identifiers_doc
                        side_document = more_identifiers_doc

                    subset_mask = []
                    for subset_identifier in side_document["identifiers"]:
                        subset_mask.append(subset_identifier not in main_document["identifiers"])

                    if any(subset_mask):
                        original_document = copy.deepcopy(side_document)
                        side_document["identifiers"] = list(
                            itertools.compress(side_document["identifiers"], subset_mask)
                        )
                        operation = pymongo.ReplaceOne(original_document, side_document)
                        logger.debug(
                            "[Task %d] Replace 1 document to trim the intersection of identifiers with another document: %s",
                            task_id,
                            side_document,
                        )
                return operation

            operation = None
            more_identifiers_doc = None
            less_identifiers_doc = None
            if len(documents[0]["identifiers"]) > len(documents[1]["identifiers"]):
                more_identifiers_doc = documents[0]
                less_identifiers_doc = documents[1]
            else:
                more_identifiers_doc = documents[1]
                less_identifiers_doc = documents[0]

            operation = _evaluate_document_subset(more_identifiers_doc, less_identifiers_doc)
            if operation is None:
                operation = _evaluate_document_subset(more_identifiers_doc, less_identifiers_doc)

            if operation is None:
                logger.critical(
                    "[Task %d] Unable to evaluate identifer %s subset or intersection between documents",
                    task_id,
                    identifier,
                )
            buffer.append(operation)

    if buffer is not None and len(buffer) > 0:
        logger.debug("[Task %d] Bulk writing %s changes to collection", task_id, len(buffer))
        collection.bulk_write(buffer)
        return task_id, len(buffer)
    else:
        logger.debug("[Task %d] Bulk writing found no changes to collection to apply", task_id)
        return task_id, 0
