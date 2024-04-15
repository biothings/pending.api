"""
Methods for pulling down the FDA Drugs data

"""

from pathlib import Path
from typing import List, Union
import urllib.request
import uuid
import zipfile

import bs4

import biothings.hub
from biothings import config

from .file_definitions import (
    ProductsFileEntry,
    NULL_PRODUCT,
    TEFileEntry,
    NULL_TE,
    MarketingStatusEntry,
    NULL_MARKETING_STATUS,
)


logger = config.logger


class FDA_DrugDumper(biothings.hub.dataload.dumper.LastModifiedHTTPDumper):
    FDA_URL = "https://www.fda.gov"

    SRC_NAME = "fda_drugs"
    SRC_ROOT_FOLDER = Path(config.DATA_ARCHIVE_ROOT) / SRC_NAME
    SCHEDULE = None
    UNCOMPRESS = True
    SRC_URLS = []

    def __init__(self):
        self.SRC_URLS = FDA_DrugDumper.extract_fda_drug_data()
        self.__class__.SRC_URLS = self.SRC_URLS
        self.grouped_file = "FDA_DRUGS_GROUPING.txt"

        super().__init__()

    def post_dump(self, *args, **kwargs):
        """
        Takes the FDA drug data files pulled down from the source and groups them to form
        one joined file that contains the structure we wish to upload to our index
        """

        # Force creation of the to_dump collection
        self.create_todump_list(force=True)
        local_zip_file = self.to_dump[0]["local"]
        data_directory = Path(local_zip_file).parent

        with zipfile.ZipFile(local_zip_file, "r") as zip_object:
            zip_object.extractall(data_directory)

        marketing_status_lookup_file = Path(data_directory).joinpath("MarketingStatus_Lookup.txt")
        marketing_status_lookup_table = self._build_marketing_status_lookup_table(marketing_status_lookup_file)

        products_file = Path(data_directory).joinpath("Products.txt")
        marketing_status_file = Path(data_directory).joinpath("MarketingStatus.txt")
        te_file = Path(data_directory).joinpath("TE.txt")

        unique_entries = set()

        products_content = {}
        with open(products_file, "r", encoding="utf-8") as product_handle:
            for raw_entry in product_handle.readlines()[1:]:
                entry_row = raw_entry.strip().split("\t")

                application_number = entry_row[0]
                product_number = entry_row[1]

                if len(entry_row) < 8:
                    reference_standard = None
                else:
                    reference_standard = bool(entry_row[7])

                product_structure = ProductsFileEntry(
                    ApplNo=application_number,
                    ProductNo=product_number,
                    Form=entry_row[2],
                    Strength=entry_row[3],
                    ReferenceDrug=bool(entry_row[4]),
                    DrugName=entry_row[5],
                    ActiveIngredient=entry_row[6],
                    ReferenceStandard=reference_standard,
                )
                hash_key = hash(application_number) + hash(product_number)
                products_content[hash_key] = product_structure
                unique_entries.add(hash_key)

        marketing_status_content = {}
        with open(marketing_status_file, "r", encoding="utf-8") as marketing_handle:
            for raw_entry in marketing_handle.readlines()[1:]:
                entry_row = raw_entry.strip().split("\t")

                application_number = entry_row[1]
                product_number = entry_row[2]
                marketing_status_structure = MarketingStatusEntry(
                    MarketingStatusID=int(entry_row[0]), ApplNo=application_number, ProductNo=product_number
                )
                hash_key = hash(application_number) + hash(product_number)
                marketing_status_content[hash_key] = marketing_status_structure
                unique_entries.add(hash_key)

        te_content = {}
        with open(te_file, "r", encoding="utf-8") as te_handle:
            for raw_entry in te_handle.readlines()[1:]:
                entry_row = raw_entry.strip().split("\t")

                application_number = entry_row[0]
                product_number = entry_row[1]

                if len(entry_row) < 4:
                    te_code = None
                else:
                    te_code = entry_row[3]

                te_status_structure = TEFileEntry(
                    ApplNo=application_number,
                    ProductNo=product_number,
                    MarketingStatusID=int(entry_row[2]),
                    TECode=te_code,
                )
                hash_key = hash(application_number) + hash(product_number)
                te_content[hash_key] = te_status_structure
                unique_entries.add(hash_key)

        group_file_path = Path(data_directory).joinpath(self.grouped_file)
        with open(group_file_path, "w", encoding="utf-8") as group_handle:
            for lookup_key in unique_entries:

                product = products_content.get(lookup_key, NULL_PRODUCT)
                marketing_status = marketing_status_content.get(lookup_key, NULL_MARKETING_STATUS)
                te = te_content.get(lookup_key, NULL_TE)

                marketing_status_value = marketing_status_lookup_table.get(marketing_status.MarketingStatusID, None)
                unique_id = f"ApplNo-{product.ApplNo}-ProductNo-{product.ProductNo}-{uuid.uuid4().hex}"

                grouped_entry = (
                    f"{unique_id}\t"
                    f"{product.DrugName}\t"
                    f"{product.ActiveIngredient}\t"
                    f"{product.Strength}\t "
                    f"{product.Form}\t"
                    f"{marketing_status_value}\t"
                    f"{te.TECode}\t"
                    f"{product.ReferenceDrug}\t"
                    f"{product.ReferenceStandard}\n"
                )
                group_handle.write(grouped_entry)

    @classmethod
    def _build_marketing_status_lookup_table(cls, marketing_status_lookup_file: Union[str, Path]) -> dict:
        """
        Takes the marketing status lookup file and builds a mapping from the file contents
        MarketingStatusID	MarketingStatusDescription
        1	Prescription
        2	Over-the-counter
        3	Discontinued
        4	None (Tentative Approval)
        5	For Further Manufacturing Use
        """
        marketing_status_mapping = {}
        with open(marketing_status_lookup_file, "r", encoding="utf-8") as file_handle:
            file_contents = file_handle.readlines()[1:]
            for entry in file_contents:
                lookup_contents = entry.split("\t")
                marketing_status_mapping[int(lookup_contents[0])] = str(lookup_contents[1]).strip()
        return marketing_status_mapping

    @classmethod
    def extract_fda_drug_data(cls) -> List[str]:
        """
        Parses the FDA Drugs data page provided by the following link:
        https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files

        Expected HTML structure

        <h2>Download File</h2>
        <ul>
            <li>
                <a data-entity-substitution="media_download" \
                   data-entity-type="media" \
                   data-entity-uuid="168c371d-fecf-4ec6-8341-dd275cf9cb77" \
                   href="/media/89850/download?attachment" \
                   title="Drugs@FDA Data File">Drugs@FDA Download File (ZIP - 3.78 MB)
                </a>
                ...
            </li>
        <ul>

        We leverage beautifulsoup to extract the tag and then return the relevant information
        parsed from the HTML page

        Returns the href found from the data as a list of strings
        """
        fda_drug_data_path = "/drugs/drug-approvals-and-databases/drugsfda-data-files"
        fda_drug_data_page = f"{cls.FDA_URL}{fda_drug_data_path}"
        request_timeout_sec = 15
        try:
            http_response = urllib.request.urlopen(url=fda_drug_data_page, data=None, timeout=request_timeout_sec)
        except Exception as gen_exc:
            raise gen_exc

        raw_html_structure = b"".join(http_response.readlines())
        html_parser = bs4.BeautifulSoup(raw_html_structure, features="html.parser")

        data_entity_attributes = {"data-entity-substitution": True, "data-entity-type": True, "data-entity-uuid": True}
        data_tag = html_parser.find("a", attrs=data_entity_attributes)
        logger.debug(f"Extracted data tag: {data_tag}")

        data_url = ""
        data_tag_reference = data_tag.get("href", None)
        if data_tag_reference is not None:
            data_url = f"{cls.FDA_URL}{data_tag_reference}"
        else:
            raise RuntimeError(f"Unable to parse the expected data tag from {fda_drug_data_page}")
        return [data_url]

    @classmethod
    def extract_fda_drug_version(cls) -> str:
        """
        Parses the FDA Drugs data page provided by the following link:
        https://www.fda.gov/drugs/drug-approvals-and-databases/drugsfda-data-files

        Expected HTML structure

        <h2>Download File</h2>
        <ul>
            <li>
                ...
                <br>
                    Data Last Updated: March 12, 2024
                </br>
            </li>
        <ul>

        Returns a dataclass structure holding the two bs4.element.Tags
        mapping to the two HTML elements we care about in the following
        structure:
        class FDA_DrugsTagData:
        {
            file_tag: <class 'bs4.element.Tag'>
            version_tag: <class 'bs4.element.Tag'>
        }
        """
        fda_drug_data_path = "/drugs/drug-approvals-and-databases/drugsfda-data-files"
        fda_drug_data_page = f"{cls.FDA_URL}{fda_drug_data_path}"
        request_timeout_sec = 15
        try:
            http_response = urllib.request.urlopen(url=fda_drug_data_page, data=None, timeout=request_timeout_sec)
        except Exception as gen_exc:
            raise gen_exc

        raw_html_structure = b"".join(http_response.readlines())
        html_parser = bs4.BeautifulSoup(raw_html_structure, features="html.parser")

        data_entity_attributes = {"data-entity-substitution": True, "data-entity-type": True, "data-entity-uuid": True}
        data_tag = html_parser.find("a", attrs=data_entity_attributes)
        version_tag = data_tag.next_sibling
        return version_tag.text.strip()
