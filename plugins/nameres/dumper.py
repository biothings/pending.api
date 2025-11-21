import asyncio
import concurrent.futures
import gzip
import os
import shutil
from functools import partial
from pathlib import Path
from typing import override, Union
from urllib.parse import urlparse

from biothings import config
from biothings.hub.dataload.dumper import DumperException, LastModifiedHTTPDumper
from biothings.utils.manager import JobManager


from .static import (
    BASE_URL,
    SYNONYM_BIG_FILE_COLLECTION,
    SYNONYM_FILE_COLLECTION,
)


logger = config.logger


file_collections = {
    "synonym": SYNONYM_FILE_COLLECTION,
    "synonym-large": SYNONYM_BIG_FILE_COLLECTION,
}


class NameResDumper(LastModifiedHTTPDumper):
    SRC_NAME = "nameres"
    SRC_ROOT_FOLDER = Path(config.DATA_ARCHIVE_ROOT) / SRC_NAME
    SCHEDULE = "0 2 1 * *"  # Monthly updates on the 1st of every month
    AUTO_UPLOAD = True
    SUFFIX_ATTR = "release"

    ARCHIVE = False
    SCHEDULE = None

    def __init__(self, src_name: str = None, src_root_folder: str = None, log_folder: str = None, archive: bool = None):
        super().__init__(src_name, src_root_folder, log_folder, archive)
        self.to_dump_large = []

    def create_todump_list(self, force: bool = False) -> None:
        self.set_release()
        local_datafolder = Path(self.current_data_folder)

        for synonym_file in file_collections["synonym"]:
            self.to_dump.append(
                {
                    "remote": f"{BASE_URL}/synonyms/{synonym_file}",
                    "local": str(local_datafolder.joinpath(synonym_file)),
                }
            )

        for synonym_file, file_partitions in file_collections["synonym-large"].items():
            self.to_dump_large.append(
                {
                    "remoteurl": f"{BASE_URL}/synonyms/{synonym_file}",
                    "localfile": str(local_datafolder.joinpath(synonym_file)),
                    "num_partitions": file_partitions,
                }
            )

    @override
    async def do_dump(self, job_manager: JobManager = None):
        await self._handle_normal_size_files(job_manager)
        await self._handle_large_size_files(job_manager)
        self.logger.info("%s successfully downloaded", self.SRC_NAME)

    async def _handle_normal_size_files(self, job_manager: JobManager):
        self.logger.info("%d file(s) to download (normal size)", len(self.to_dump))
        jobs = []
        self.unprepare()
        for file_mapping in self.to_dump:
            remote = file_mapping["remote"]
            local = file_mapping["local"]

            pinfo = self.get_pinfo()
            pinfo["step"] = "dump"
            pinfo["description"] = remote

            job = await job_manager.defer_to_process(pinfo, partial(self.download, remote, local))
            jobs.append(job)

        await asyncio.gather(*jobs)
        self.to_dump = []

    async def _handle_large_size_files(self, job_manager: JobManager):
        self.logger.info("%d file(s) to download (large size)", len(self.to_dump_large))
        jobs = []
        self.unprepare()
        for file_mapping in self.to_dump_large:
            pinfo = self.get_pinfo()
            pinfo["step"] = "dump"
            pinfo["description"] = file_mapping["remoteurl"]

            job = await job_manager.defer_to_process(pinfo, partial(self.large_download, **file_mapping))
            jobs.append(job)
        await asyncio.gather(*jobs)
        self.to_dump_large = []

    def large_download(self, remoteurl: str, localfile: [str, Path], num_partitions: int = 100) -> None:
        """
        Handles downloading of particularly large files. It breaks it into further smaller
        chunks
        """
        logger.info("Downloading (large) file %s -> %s | Partitions %s", remoteurl, localfile, num_partitions)
        self.prepare_local_folders(localfile)

        thread_futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            chunks, chunk_size = self.get_range_chunks(remoteurl, num_partitions)

            for index, chunk_start in enumerate(chunks):
                chunk_end = chunk_start + (chunk_size - 1)
                output_chunk = f"{localfile}.part{index}"

                arguments = {"url": remoteurl, "start": chunk_start, "end": chunk_end, "output": output_chunk}
                future = executor.submit(self.download_range, **arguments)
                thread_futures.append(future)

            concurrent.futures.wait(thread_futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED)
            with open(localfile, "wb") as combined_output:
                for index in range(len(chunks)):
                    chunk_path = f"{localfile}.part{index}"

                    with open(chunk_path, "rb") as partial_input:
                        combined_output.write(partial_input.read())
                    os.remove(chunk_path)
                logger.info(f"Combined all chunks -> {localfile}")

    def download(self, remoteurl: str, localfile: Union[str, Path], headers: dict = {}) -> None:
        """
        Handles downloading of remote files over HTTP to the local file system

        Leverages multiple threads to download the remote file in multiple chunks
        concurrently and then combines them at the end
        """
        logger.info("Downloading (normal) file %s -> %s | Partitions %s", remoteurl, localfile, 10)
        self.prepare_local_folders(localfile)

        thread_futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            chunks, chunk_size = self.get_range_chunks(remoteurl, 10)

            for index, chunk_start in enumerate(chunks):
                chunk_end = chunk_start + (chunk_size - 1)
                output_chunk = f"{localfile}.part{index}"

                arguments = {"url": remoteurl, "start": chunk_start, "end": chunk_end, "output": output_chunk}
                future = executor.submit(self.download_range, **arguments)
                thread_futures.append(future)

            concurrent.futures.wait(thread_futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED)
            with open(localfile, "wb") as combined_output:
                for index in range(len(chunks)):
                    chunk_path = f"{localfile}.part{index}"

                    with open(chunk_path, "rb") as partial_input:
                        combined_output.write(partial_input.read())
                    os.remove(chunk_path)
                logger.info(f"Combined all chunks -> {localfile}")

    def get_file_size(self, url: str) -> int:
        """
        Sends a HEAD request to the specified URL and extracts
        the `Content-Length` header to determine the file size

        Used for determining how to chunk the file download
        """
        response = self.client.head(url)
        size = int(response.headers["Content-Length"])
        return size

    def get_range_chunks(self, url: int, num_partitions: int = 10) -> tuple[range, int]:
        """
        Partitions a file into distinct chunks for consuming each chunk within
        a thread concurrently
        """
        file_size = self.get_file_size(url)
        chunk_size = int(file_size / num_partitions)
        chunks = range(0, file_size, chunk_size)
        return chunks, chunk_size

    def download_range(self, url: str, start: int, end: int, output: str) -> None:
        self.logger.debug("Downloading Filepart '%s' as '%s'", url, output)
        headers = {"Range": f"bytes={start}-{end}"}
        response = self.client.get(url, headers=headers)

        if not response.status_code == 206:
            raise DumperException(
                "Error while downloading '%s' (status: %s, reason: %s)",
                url,
                response.status_code,
                response.reason,
            )

        with open(output, "wb") as file_handle:
            for response_part in response.iter_content(512 * 1024):
                file_handle.write(response_part)
        logger.info(f"Chunk Completed | {output} | Byte Range [{start}, {end}]")

    def set_release(self) -> None:
        """
        Parses the BASE_URL to extract the data from the url pathing
        """
        parse_result = urlparse(BASE_URL)
        self.release = parse_result.path.split("/")[-1]

    def post_dump(self, *args, **kwargs):
        """
        Post dump processing:
        - unzip all gzipped file
        """
        # Force creation of the to_dump collection
        self.create_todump_list(force=True)

        def decompress_file(archive_file: Union[str, Path]) -> None:
            decompressed_file = archive_file.with_name(archive_file.stem)
            with gzip.open(archive_file, "rb") as input_handle, open(decompressed_file, "wb") as output_handle:
                logger.info("Decompressing %s -> %s", archive_file.name, decompressed_file.name)
                shutil.copyfileobj(input_handle, output_handle)
            logger.debug("Deleting archive file %s", archive_file.name)
            archive_file.unlink()

        thread_futures = []
        data_directory = Path(self.current_data_folder).resolve().absolute()
        with concurrent.futures.ThreadPoolExecutor(max_workers=os.cpu_count()) as executor:
            for archive_file in data_directory.glob("**/*.gz"):
                arguments = {"archive_file": archive_file}
                future = executor.submit(decompress_file, **arguments)
                thread_futures.append(future)
            concurrent.futures.wait(thread_futures, timeout=None, return_when=concurrent.futures.ALL_COMPLETED)
