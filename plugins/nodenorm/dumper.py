import asyncio
import concurrent.futures
import json
import multiprocessing
import os
import sqlite3
from pathlib import Path
from functools import partial
from typing import override, Union
from urllib.parse import urlparse

from biothings import config
from biothings.hub.dataload.dumper import DumperException, LastModifiedHTTPDumper
from biothings.utils.manager import JobManager

from .parse import DRUG_CHEMICAL_IDENTIFIER_FILES, GENE_PROTEIN_IDENTIFER_FILES


logger = config.logger

PRIOR_URL = ["https://stars.renci.org/var/babel_outputs/2025jan23"]
BASE_URL = "https://stars.renci.org/var/babel_outputs/2025mar31/"


NODENORM_FILE_COLLECTION = [
    "AnatomicalEntity.txt",
    "BiologicalProcess.txt",
    "Cell.txt",
    "CellularComponent.txt",
    "ChemicalEntity.txt",
    "ChemicalMixture.txt",
    "ComplexMolecularMixture.txt",
    "Disease.txt",
    "Drug.txt",
    "GeneFamily.txt",
    "GrossAnatomicalStructure.txt",
    "MacromolecularComplex.txt",
    "MolecularActivity.txt",
    "OrganismTaxon.txt",
    "Pathway.txt",
    "PhenotypicFeature.txt",
    "Polypeptide.txt",
    "umls.txt",
]

NODENORM_CONFLATION_COLLECTION = ["DrugChemical.txt", "GeneProtein.txt"]


NODENORM_BIG_FILE_COLLECTION = {
    "MolecularMixture.txt": 50,
    "Gene.txt": 75,
    "Publication.txt": 100,
    "SmallMolecule.txt": 150,
    "Protein.txt": 200,
}


file_collections = {
    "compendia": NODENORM_FILE_COLLECTION,
    "compendia-large": NODENORM_BIG_FILE_COLLECTION,
    "conflation": NODENORM_CONFLATION_COLLECTION,
}

CONFLATION_LOOKUP_DATABASE = "conflation.sqlite3"


class NodeNormDumper(LastModifiedHTTPDumper):
    SRC_NAME = "nodenorm"
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

        for nodenorm_file in file_collections["compendia"]:
            self.to_dump.append(
                {
                    "remote": f"{BASE_URL}/compendia/{nodenorm_file}",
                    "local": str(local_datafolder.joinpath(nodenorm_file)),
                }
            )

        for nodenorm_file in file_collections["conflation"]:
            self.to_dump.append(
                {
                    "remote": f"{BASE_URL}/conflation/{nodenorm_file}",
                    "local": str(local_datafolder.joinpath(nodenorm_file)),
                }
            )

        for nodenorm_file, file_partitions in file_collections["compendia-large"].items():
            self.to_dump_large.append(
                {
                    "remoteurl": f"{BASE_URL}/compendia/{nodenorm_file}",
                    "localfile": str(local_datafolder.joinpath(nodenorm_file)),
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
        logger.info(f"Downloading (large) file %s -> %s | Partitions %s", remoteurl, localfile, num_partitions)
        self.prepare_local_folders(localfile)

        thread_futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=4) as executor:
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
        logger.info(f"Downloading (normal) file %s -> %s | Partitions %s", remoteurl, localfile, 10)
        self.prepare_local_folders(localfile)

        thread_futures = []
        with concurrent.futures.ThreadPoolExecutor(max_workers=16) as executor:
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
        # Force creation of the to_dump collection
        self.create_todump_list(force=True)
        local_zip_file = self.to_dump[0]["local"]
        data_directory = Path(local_zip_file).parent
        self._generate_conflation_database(data_directory)

    def _generate_conflation_database(self, data_directory: Union[str, Path]) -> Union[str, Path]:
        """
        Takes the generated conflation files and creates a sqlite3 database used for looking
        up the conflation identifiers for the supported types of nodes

        Finds the identifiers and then flattens so each identifier found within the conflation list
        points back to the same list of identifiers, so every CURIE within the list points to the
        same list

        Example:
        conflation  | identifiers
        identifier0 | identifer0,identifer1,identifer2,identifer3,identifer4
        identifier1 | identifer0,identifer1,identifer2,identifer3,identifer4
        identifier2 | identifer0,identifer1,identifer2,identifer3,identifer4
        identifier3 | identifer0,identifer1,identifer2,identifer3,identifer4
        identifier4 | identifer0,identifer1,identifer2,identifer3,identifer4
        """
        conflation_database_path = data_directory.joinpath(CONFLATION_LOOKUP_DATABASE).resolve().absolute()
        conflation_database = sqlite3.connect(conflation_database_path)
        cursor = conflation_database.cursor()

        enable_foreign_keys = "PRAGMA foreign_keys = ON;"
        cursor.execute(enable_foreign_keys)
        conflation_existance_check = "DROP TABLE IF EXISTS conflations"
        cursor.execute(conflation_existance_check)

        conflations_table = (
            "CREATE TABLE conflations "
            "("
            "conflation text PRIMARY KEY NOT NULL, "
            "identifiers text NOT NULL, "
            "type text NOT NULL"
            ");"
        )
        cursor.execute(conflations_table)

        conflation_files = [
            data_directory.joinpath("GeneProtein.txt").resolve().absolute(),
            data_directory.joinpath("DrugChemical.txt").resolve().absolute(),
        ]
        for conflation_file in conflation_files:
            if not conflation_file.exists():
                raise OSError(f"Unable to locate conflation file {conflation_file}")

            with open(conflation_file, "r", encoding="utf-8") as handle:
                batch = []
                for line in handle.readlines():
                    identifiers = json.loads(line)
                    identifiers_repr = ",".join(identifiers)

                    for identifier in identifiers:
                        batch.append(
                            {"conflation": identifier, "identifiers": identifiers_repr, "type": conflation_file.stem}
                        )

                    if len(batch) >= 10000:
                        cursor.executemany("INSERT INTO conflations VALUES (:conflation, :identifiers, :type)", batch)
                        batch = []

        if len(batch) > 0:
            cursor.executemany("INSERT INTO conflations VALUES (:conflation, :identifiers, :type)", batch)
            batch = []
        conflation_database.commit()
        conflation_database.close()
