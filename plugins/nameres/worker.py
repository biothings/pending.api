import concurrent.futures
import hashlib
import itertools
import os
import time
from pathlib import Path
from typing import Union

import pymongo
from pymongo.errors import BulkWriteError

from biothings import config
from biothings.utils.dataload import merge_struct
from biothings.utils.serializer import json_loads, json_dumps
from biothings.utils.hub_db import get_src_db

from .static import NAMERES_UPLOAD_CHUNKS


logger = config.logger


def upload_process(data_folder: Union[str, Path], collection_name: str) -> int:
    with concurrent.futures.ProcessPoolExecutor(max_workers=1 * os.cpu_count()) as executor:
        process_futures = []
        for index, task in enumerate(_build_offset_tasks(data_folder, collection_name)):
            future = executor.submit(subset_upload_worker, **task)
            process_futures.append(future)

        total_document_count = 0
        for index, future in enumerate(concurrent.futures.as_completed(process_futures)):
            try:
                buffer_upload = future.result()
            except Exception as gen_exc:
                logger.exception(gen_exc)
                raise gen_exc
            else:
                total_document_count += buffer_upload
                logger.debug(
                    "Task %s completed | Total upload size %s",
                    index,
                    total_document_count,
                )
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
        offsets = generate_file_offsets(input_file, num_partitions)

        if offsets is not None:
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
                }
                argument_collection.append(arguments)
            return argument_collection

        logger.debug("File %s is empty. No partitions to generate", input_file)
        return []

    thread_futures = []
    with concurrent.futures.ThreadPoolExecutor() as executor:
        for filename, num_partitions in NAMERES_UPLOAD_CHUNKS.items():
            filepath = Path(data_folder).joinpath(filename).resolve().absolute()
            arguments = {"input_file": filepath, "num_partitions": num_partitions}
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

    if file_size_bytes > 0:
        logger.debug("Calculating SHA256 hashsum for file: %s", file)
        file_hash = sha256sum(file)

        if file_index.exists():
            with open(file_index, "r", encoding="utf-8") as index_handle:
                previous_index = json_loads(index_handle.read())

            if previous_index["hash"] == file_hash:
                return previous_index["index"]

            logger.debug(
                "Different hash found for file %s [%s, %s] [previous, current]. "
                "Updating file offsets with the new file",
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
            index_handle.write(json_dumps({"index": partitions, "hash": file_hash}))
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
) -> list[str]:
    """
    Internal function for handling the multipart uploading of the file in partitions

    Accepts the file path, along with the chunk start and chunk end in bytes to determine
    what offset to start and stop at in the file

    The conflation_connection is a static singular sqlite3 file located in the same directory as the
    data files as it's generated post-dump. We can just derived it at run-time from the provided
    data filepath

    Afterwards the data processing is straight forward, we effectively don't transform the state of
    the nameres files
    """
    logger.info("Starting bulk upload to backend %s [%s|%s]", input_file, offset_start, offset_end)

    upload_database = get_src_db()
    collection = pymongo.collection.Collection(database=upload_database, name=collection_name)

    total_upload = 0
    with open(input_file, encoding="utf-8") as file_handle:
        buffer = []
        line = file_handle.readline()
        while line:
            doc = json_loads(line)
            doc["_id"] = doc["curie"]
            try:
                doc["shortest_name_length"] = int(doc["shortest_name_length"])
            except (TypeError, ValueError):
                doc["shortest_name_length"] = 0

            try:
                doc["clique_identifier_count"] = int(doc["clique_identifier_count"])
            except (TypeError, ValueError):
                doc["clique_identifier_count"] = 0

            buffer.append(doc)

            if len(buffer) >= buffer_size:
                total_upload += len(buffer)
                _upload_buffer(collection, buffer, input_file, file_handle.tell() / offset_end)
                buffer = []

            line = file_handle.readline()

        if len(buffer) > 0:
            total_upload += len(buffer)
            _upload_buffer(collection, buffer, input_file, file_handle.tell() / offset_end)
            buffer = []

    return total_upload


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
