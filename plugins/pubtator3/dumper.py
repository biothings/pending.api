import pathlib
import re
import urllib
import urllib.request

import bs4

from biothings import config
from biothings.hub.dataload.dumper import FTPDumper


logger = config.logger


class Pubtator3Dumper(FTPDumper):
    SRC_NAME = "pubtator3"
    SRC_ROOT_FOLDER = pathlib.Path(config.DATA_ARCHIVE_ROOT).joinpath(SRC_NAME)
    FTP_HOST = "ftp.ncbi.nlm.nih.gov"
    CWD_DIR = "/pub/lu/PubTator3/"
    ARCHIVE = False
    SCHEDULE = "0 12 * * *"
    FTP_TIMEOUT = 5 * 60.0
    FTP_USER = ""
    FTP_PASSWD = ""
    MAX_PARALLEL_DUMP = 2

    def __init__(self):
        self.SRC_ROOT_FOLDER = pathlib.Path(self.SRC_ROOT_FOLDER).resolve().absolute()
        super().__init__(
            src_name=self.SRC_NAME,
            src_root_folder=self.SRC_ROOT_FOLDER,
            log_folder=config.LOG_FOLDER,
            archive=self.ARCHIVE,
        )
        self.prepare_client()
        self.set_release()

    def set_release(self) -> None:
        """
        Extracts the version date from the FTP site for pubtator3

        Since the FTP site is raw HTML the structure is fairly simplistic:
        <a href="relation2pubtator3.gz">relation2pubtator3.gz</a>    2024-01-23 06:49  245M

        We look for the attribute instance that matches the file pattern we care about and then
        get the next sibling to extract the version date

        We then manipulate the string to strip out the time and data size so we only pull back
        string date
        """

        pubtator_ftp_site = "https://ftp.ncbi.nlm.nih.gov/pub/lu/PubTator3/"
        request_timeout_sec = 15

        # [Bandit security warning note]
        # any usage of the urllib trigger the warning: {B310: Audit url open for permitted schemes}
        # urllib.request.urlopen supports file system access via ftp:// and file://
        #
        # if our usage accepted external input, then this would be a potential security concern, but
        # our use case leverages hard-coded URL's pointing directly at the FDA webpages
        try:
            page_request = urllib.request.Request(url=pubtator_ftp_site, data=None, headers={}, method="GET")
            with urllib.request.urlopen(url=page_request, timeout=request_timeout_sec) as http_response:  # nosec
                raw_html_structure = b"".join(http_response.readlines())
        except Exception as gen_exc:
            logger.exception(gen_exc)
            release_version = "Unknown"
            return release_version

        html_parser = bs4.BeautifulSoup(raw_html_structure, features="html.parser")

        attribute_tag = html_parser.find("a", href=re.compile("relation2pubtator3"))
        metadata_string = attribute_tag.next_sibling
        release_version = metadata_string.strip().split()[0]
        self.release = release_version

    def create_todump_list(self, force: bool = False) -> None:
        """
        Generates the dump list

        We access the ftp server using the parent class FTP client instance
        to acquire the list of files. Then after validating the relation file exists,
        we add the entry to our `to_dump` collection

        We override the parent class instance of `create_todump_list`, but we have no
        usage for the `force` argument
        """
        relation_pubtator_filename = "relation2pubtator3.gz"
        remote_pubtator_files = set(self.client.nlst())
        if relation_pubtator_filename in remote_pubtator_files:
            local_data_path = pathlib.Path(self.current_data_folder).resolve().absolute()
            local_relation_pubtator_filepath = local_data_path.joinpath(relation_pubtator_filename)
            dump_entry = {"remote": relation_pubtator_filename, "local": local_relation_pubtator_filepath}
            logger.debug("dump entry: %s", dump_entry)
            self.to_dump.append(dump_entry)
