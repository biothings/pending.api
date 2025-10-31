import concurrent.futures
import hashlib
import itertools
import json
import os
from pathlib import Path
from typing import Union


from biothings import config
from biothings.hub.dataload.uploader import BaseSourceUploader
from biothings.utils.manager import JobManager

from .static import (
    BASE_URL,
    CONFLATION_LOOKUP_DATABASE,
    DRUG_CHEMICAL_IDENTIFIER_FILES,
    GENE_PROTEIN_IDENTIFER_FILES,
    NODENORM_BIG_FILE_COLLECTION,
    NODENORM_FILE_COLLECTION,
    NODENORM_UPLOAD_CHUNKS,
)
from .worker import subset_upload_worker, create_identifiers_table


logger = config.logger


class NodeNormUploader(BaseSourceUploader):
    name = "nodenorm"
    __metadata__ = {"src_meta": {"url": BASE_URL}}

    def _generate_data_filepaths(self) -> list[Union[str, Path]]:
        """
        Generates the files for processing in parallel
        """
        file_names = [*NODENORM_FILE_COLLECTION, *NODENORM_BIG_FILE_COLLECTION.keys()]
        files = [Path(self.data_folder).joinpath(file) for file in file_names]
        return files

    async def update_data(self, batch_size: int, job_manager: JobManager = None):
        """
        Primary mover for uploading the data to our backend
        """
        self.unprepare()

        create_identifiers_table(self.data_folder)

        with concurrent.futures.ProcessPoolExecutor(max_workers=1 * os.cpu_count()) as executor:
            process_futures = []
            for task in self._build_offset_tasks():
                future = executor.submit(subset_upload_worker, **task)
                process_futures.append(future)

            concurrent.futures.wait(process_futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED)

        total_document_count = 0
        for future in process_futures:
            total_document_count += future.result()
        logger.info("total uploaded documents %s across %s tasks", total_document_count, len(process_futures))

        self.switch_collection()
        self.clean_archived_collections()

    async def load(
        self,
        steps=("data", "post", "master", "clean"),
        force=False,
        batch_size=10000,
        job_manager=None,
        **kwargs,
    ):
        # force new arguments
        steps = ("data", "master", "clean")
        batch_size = 5000
        await super().load(steps, force, batch_size, job_manager, **kwargs)

    @classmethod
    def get_mapping(cls) -> dict:
        mapping = {
            "type": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
            "ic": {"type": "float"},
            "identifiers": {
                "properties": {
                    "i": {
                        "type": "keyword",
                        "normalizer": "keyword_lowercase_normalizer",
                        "copy_to": "all",  # default field
                    },
                    "l": {
                        "type": "text",
                        "fields": {"raw": {"type": "keyword", "ignore_above": 512}},
                        "copy_to": "all",  # default field
                    },
                    "d": {"type": "text"},
                    "t": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
                    "c": {"properties": {"gp": {"type": "keyword"}, "cd": {"type": "keyword"}}},
                }
            },
            "preferred_name": {"type": "text"},
            "taxa": {"normalizer": "keyword_lowercase_normalizer", "type": "keyword"},
            "all": {"type": "text"},
        }
        return mapping

    def _build_offset_tasks(self):
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

            offsets = NodeNormUploader.generate_file_offsets(input_file, num_partitions)

            argument_collection = []
            for offset_range in NodeNormUploader.window(offsets, 2):
                offset_start = offset_range[0]
                offset_end = offset_range[1]

                arguments = {
                    "input_file": input_file,
                    "buffer_size": 5000,
                    "offset_start": offset_start,
                    "offset_end": offset_end,
                    "collection_name": self.temp_collection_name,
                    "conflation_database": conflation_database,
                }
                argument_collection.append(arguments)
            return argument_collection

        thread_futures = []
        with concurrent.futures.ThreadPoolExecutor() as executor:
            for filename, num_partitions in NODENORM_UPLOAD_CHUNKS.items():
                filepath = Path(self.data_folder).joinpath(filename).resolve().absolute()
                arguments = {"input_file": filepath, "num_partitions": num_partitions}
                _populate_upload_arguments(**arguments)
                future = executor.submit(_populate_upload_arguments, **arguments)
                thread_futures.append(future)

        concurrent.futures.wait(thread_futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED)

        yield from itertools.chain.from_iterable([future.result() for future in thread_futures])

    @classmethod
    def generate_file_offsets(cls, file: Union[str, Path], num_partitions: int = None):
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
        file_hash = cls.sha256sum(file)

        if file_index.exists():
            with open(file_index, "r", encoding="utf-8") as index_handle:
                previous_index = json.load(index_handle)

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
            index_handle.write(json.dumps({"index": partitions, "hash": file_hash}))
        return partitions

    @classmethod
    def sha256sum(cls, file: Union[str, Path], buffer_size: int = None):
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

    @classmethod
    def window(cls, seq, n=2):
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
