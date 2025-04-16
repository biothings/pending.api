from datetime import datetime
import pathlib
import re
import re
import urllib
import urllib.request

import bs4

from biothings import config
from biothings.hub.dataload.dumper import FTPDumper


logger = config.logger


class EBIGene2PhenotypeDumper(FTPDumper):
    SRC_NAME = "ebi_gene2phenotype"
    SRC_ROOT_FOLDER = pathlib.Path(config.DATA_ARCHIVE_ROOT).joinpath(SRC_NAME)
    FTP_HOST = "ftp.ebi.ac.uk"
    CWD_DIR = "/pub/databases/gene2phenotype/G2P_data_downloads/"
    ARCHIVE = False

    # Release schedule on the ftp site appears to be on the 28th of each month. So we
    # give a brief buffer and pull on the first day of each month for scheduled update
    SCHEDULE = "0 2 1 * *"
    FTP_TIMEOUT = 5 * 60.0
    FTP_USER = ""
    FTP_PASSWD = ""
    MAX_PARALLEL_DUMP = 2
    UNCOMPRESS = False

    def __init__(self):
        self.SRC_ROOT_FOLDER = pathlib.Path(self.SRC_ROOT_FOLDER).resolve().absolute()
        super().__init__(
            src_name=self.SRC_NAME,
            src_root_folder=self.SRC_ROOT_FOLDER,
            log_folder=config.LOG_FOLDER,
            archive=self.ARCHIVE,
        )
        self.folder_metadata = self._extract_latest_version_folder()
        self.prepare_client()
        self.set_release()

    def _extract_latest_version_folder(self) -> dict:
        ebi_ftp_site = "https://ftp.ebi.ac.uk/pub/databases/gene2phenotype/G2P_data_downloads/"
        request_timeout_sec = 15

        # [Bandit security warning note]
        # any usage of the urllib trigger the warning: {B310: Audit url open for permitted schemes}
        # urllib.request.urlopen supports file system access via ftp:// and file://
        #
        # if our usage accepted external input, then this would be a potential security concern, but
        # our use case leverages hard-coded URL's pointing directly at the FDA webpages
        try:
            page_request = urllib.request.Request(url=ebi_ftp_site, data=None, headers={}, method="GET")
            with urllib.request.urlopen(url=page_request, timeout=request_timeout_sec) as http_response:  # nosec
                raw_html_structure = b"".join(http_response.readlines())
        except Exception as gen_exc:
            logger.exception(gen_exc)
            release_version = "Unknown"
            return release_version

        html_parser = bs4.BeautifulSoup(raw_html_structure, features="html.parser")

        date_folders = {}
        datetimes = []

        search_tags = html_parser.find_all("tr")
        for tag in search_tags:
            img_section = tag.find("img")
            if img_section is not None:
                alt_value = img_section.get("alt", None)
                if alt_value is not None and alt_value == "[DIR]":
                    folder_date_name = tag.find("a")["href"][:-1]
                    split_date_values = folder_date_name.split("_")

                    extracted_datetime = datetime(
                        int(split_date_values[0]),
                        int(split_date_values[1]),
                        int(split_date_values[2]),
                    )
                    datetimes.append(extracted_datetime)
                    date_folders[extracted_datetime] = folder_date_name

        latest_datetime = sorted(datetimes, reverse=True)[0]
        latest_date = {"folder": date_folders[latest_datetime], "datetime": latest_datetime}
        return latest_date

    def set_release(self) -> datetime:
        return self.folder_metadata["datetime"].isoformat()

    def create_todump_list(self, force: bool = False) -> None:
        """
        Generates the dump list

        We access the ftp server using the parent class FTP client instance
        to acquire the list of files. Then after validating the relation file exists,
        we add the entry to our `to_dump` collection

        We override the parent class instance of `create_todump_list`, but we have no
        usage for the `force` argument
        """
        remote_ebi_files = set(self.client.nlst(self.folder_metadata["folder"]))
        local_data_path = pathlib.Path(self.current_data_folder).resolve().absolute()

        for remote_file in remote_ebi_files:
            dump_entry = {"remote": remote_file, "local": str(local_data_path.joinpath(remote_file.split("/")[-1]))}
            logger.debug("dump entry: %s", dump_entry)
            self.to_dump.append(dump_entry)
