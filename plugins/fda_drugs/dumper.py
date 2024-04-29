"""
Methods for pulling down the FDA Drugs data
"""

import json
from pathlib import Path
from typing import List, Union
import urllib.request
import zipfile

import bs4

import biothings.hub
from biothings import config

from .file_definitions import (
    ApplicationsEntry,
    MarketingStatusEntry,
    NULL_APPLICATION,
    NULL_MARKETING_STATUS,
    NULL_PRODUCT,
    NULL_TE,
    ProductsFileEntry,
    TEFileEntry,
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
        self.grouped_file = "FDA_DRUGS_GROUPING.json"

        super().__init__()

    def post_dump(self, *args, **kwargs):
        """
        Takes the FDA drug data files pulled down from the source and groups them to form
        one joined file that contains the structure we wish to upload to our index

        The final structure of our file is a collection of row-based entries with these headers:

        {
            unique_id,
            application_number,
            product_number,
            drug_name,
            active_ingredients,
            strength,
            dosage_form
            marketing_status,
            te_code,
            reference_drug,
            reference_standard
        )

        """

        # Force creation of the to_dump collection
        self.create_todump_list(force=True)
        local_zip_file = self.to_dump[0]["local"]
        data_directory = Path(local_zip_file).parent

        with zipfile.ZipFile(local_zip_file, "r") as zip_object:
            zip_object.extractall(data_directory)

        unique_entries = set()
        products_content = self._process_product_file(data_directory=data_directory, unique_entries=unique_entries)
        marketing_status_content = self._process_marketing_status_file(
            data_directory=data_directory, unique_entries=unique_entries
        )
        te_content = self._process_te_file(data_directory=data_directory, unique_entries=unique_entries)
        applications_content = self._process_applications_file(data_directory=data_directory)

        marketing_status_lookup_file = Path(data_directory).joinpath("MarketingStatus_Lookup.txt")
        marketing_status_lookup_table = self._build_marketing_status_lookup_table(marketing_status_lookup_file)

        group_file_path = Path(data_directory).joinpath(self.grouped_file)
        join_mapping = []
        for lookup_key in unique_entries:
            product = products_content.get(lookup_key, NULL_PRODUCT)
            marketing_status = marketing_status_content.get(lookup_key, NULL_MARKETING_STATUS)
            te = te_content.get(lookup_key, NULL_TE)

            marketing_status_value = marketing_status_lookup_table.get(marketing_status.MarketingStatusID, None)

            application_numbers = [product.ApplNo, marketing_status.ApplNo, te.ApplNo]
            application_number = [appl for appl in application_numbers if appl is not None][0]

            product_numbers = set([product.ProductNo, marketing_status.ProductNo, te.ProductNo])
            product_number = [prod for prod in product_numbers if prod is not None][0]

            application = applications_content.get(application_number, NULL_APPLICATION)
            application_company = None
            breakpoint()
            if application.ApplPublicNotes is not None:
                application_company = application.ApplPublicNotes
            elif application.SponsorName is not None:
                application_company = application.SponsorName

            unique_id = f"{application_number}-{product_number}"

            grouped_entry = {
                "unique_id": unique_id,
                "application_number": application_number,
                "product_number": product_number,
                "drug_name": product.DrugName,
                "active_ingredient": product.ActiveIngredient,
                "strength": product.Strength,
                "dosage_form": product.Form,
                "marketing_status": marketing_status_value,
                "te_code": te.TECode,
                "reference_drug": product.ReferenceDrug,
                "reference_standard": product.ReferenceStandard,
                "company": application_company,
            }
            logger.debug(json.dumps(grouped_entry, indent=4))

            join_mapping.append(grouped_entry)

        with open(group_file_path, "w", encoding="utf-8") as group_handle:
            json.dump(join_mapping, group_handle, indent=4)

    def _process_product_file(self, data_directory: Path, unique_entries: set) -> dict:
        """
        Processes the Product.txt file into a collection of the following structure:

        ApplNo: str
        ProductNo: str
        Form: list[str]
        Strength: list[str]
        ReferenceDrug: bool
        DrugName: str
        ActiveIngredient: str
        ReferenceStandard: bool

        """
        products_file = Path(data_directory).joinpath("Products.txt")
        products_content = {}
        column_delimiter = "\t"

        with open(products_file, "r", encoding="utf-8") as product_handle:
            for raw_entry in product_handle.readlines()[1:]:
                entry_row = raw_entry.split(column_delimiter)
                entry_row = [entry.strip() for entry in entry_row]

                application_number = entry_row[0]
                product_number = entry_row[1]

                dosage_delimiter = ";"
                dosage_forms = entry_row[2].split(dosage_delimiter)
                dosage_forms = [str(dosage_entry).strip().lower() for dosage_entry in dosage_forms]

                strength_delimiter = ";"
                strength = entry_row[3].split(strength_delimiter)
                strength = [str(strength_entry).strip().lower() for strength_entry in strength]

                try:
                    reference_drug_index = int(entry_row[4])
                except ValueError:
                    reference_drug_index = 0
                finally:
                    reference_drug = bool(reference_drug_index)

                drug_name = str(entry_row[5])
                active_ingredients = str(entry_row[6]).lower()

                try:
                    reference_standard_index = int(entry_row[7])
                except ValueError:
                    reference_standard_index = 0
                finally:
                    reference_standard = bool(reference_standard_index)

                product_structure = ProductsFileEntry(
                    ApplNo=application_number,
                    ProductNo=product_number,
                    Form=dosage_forms,
                    Strength=strength,
                    ReferenceDrug=reference_drug,
                    DrugName=drug_name,
                    ActiveIngredient=active_ingredients,
                    ReferenceStandard=reference_standard,
                )
                hash_key = hash(application_number) + hash(product_number)
                products_content[hash_key] = product_structure
                unique_entries.add(hash_key)
        return products_content

    def _process_marketing_status_file(self, data_directory: Path, unique_entries: set) -> dict:
        """
        Processes the MarketingStatus.txt file into a collection of the following structure:

        MarketingStatusID: int
        ApplNo: str
        ProductNo: str

        """
        marketing_status_file = Path(data_directory).joinpath("MarketingStatus.txt")
        marketing_status_content = {}
        column_delimiter = "\t"

        with open(marketing_status_file, "r", encoding="utf-8") as marketing_handle:
            for raw_entry in marketing_handle.readlines()[1:]:
                entry_row = raw_entry.split(column_delimiter)
                entry_row = [entry.strip() for entry in entry_row]

                marketing_status_index = int(entry_row[0])
                application_number = entry_row[1]
                product_number = entry_row[2]
                marketing_status_structure = MarketingStatusEntry(
                    MarketingStatusID=marketing_status_index, ApplNo=application_number, ProductNo=product_number
                )
                hash_key = hash(application_number) + hash(product_number)
                marketing_status_content[hash_key] = marketing_status_structure
                unique_entries.add(hash_key)
        return marketing_status_content

    def _process_te_file(self, data_directory: Path, unique_entries: set) -> dict:
        """
        Processes the TE.txt file into a collection of the following structure:

        ApplNo: str
        ProductNo: str
        MarketingStatusID: int
        TECode: str

        """
        te_file = Path(data_directory).joinpath("TE.txt")
        te_content = {}
        column_delimiter = "\t"

        with open(te_file, "r", encoding="utf-8") as te_handle:
            for raw_entry in te_handle.readlines()[1:]:
                entry_row = raw_entry.split(column_delimiter)
                entry_row = [entry.strip() for entry in entry_row]

                application_number = entry_row[0]
                product_number = entry_row[1]
                marketing_status_index = int(entry_row[2])
                te_code = str(entry_row[3])

                te_structure = TEFileEntry(
                    ApplNo=application_number,
                    ProductNo=product_number,
                    MarketingStatusID=marketing_status_index,
                    TECode=te_code,
                )
                hash_key = hash(application_number) + hash(product_number)
                te_content[hash_key] = te_structure
                unique_entries.add(hash_key)
        return te_content

    def _process_applications_file(self, data_directory: Path) -> dict:
        """
        Processes the Applications.txt file into a collection of the following structure:

        ApplNo: str
        ApplTyp: str
        ApplPublicNotes: str
        SponsorName: str

        """
        applications_file = Path(data_directory).joinpath("Applications.txt")
        applications_content = {}
        column_delimiter = "\t"

        with open(applications_file, "r", encoding="utf-8") as te_handle:
            for raw_entry in te_handle.readlines()[1:]:
                entry_row = raw_entry.split(column_delimiter)
                entry_row = [entry.strip() for entry in entry_row]

                application_number = entry_row[0]
                application_type = entry_row[1]

                application_publication_notes = str(entry_row[2]).lower()
                if application_publication_notes == "":
                    application_publication_notes = None

                sponsor_name = str(entry_row[3]).lower()
                if sponsor_name == "":
                    sponsor_name = None

                application_structure = ApplicationsEntry(
                    ApplNo=application_number,
                    ApplTyp=application_type,
                    ApplPublicNotes=application_publication_notes,
                    SponsorName=sponsor_name,
                )
                applications_content[application_number] = application_structure
        return applications_content

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
                marketing_status_index = int(lookup_contents[0])
                marketing_status_value = str(lookup_contents[1]).strip().lower()

                marketing_status_mapping[marketing_status_index] = marketing_status_value
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

        # [Bandit security warning note]
        # any usage of the urllib trigger the warning: {B310: Audit url open for permitted schemes}
        # urllib.request.urlopen supports file system access via ftp:// and file://
        #
        # if our usage accepted external input, then this would be a potential security concern, but
        # our use case leverages hard-coded URL's pointing directly at the FDA webpages
        try:
            page_request = urllib.request.Request(url=fda_drug_data_page, data=None, headers={}, method="GET")
            with urllib.request.urlopen(url=page_request, timeout=request_timeout_sec) as http_response:  # nosec
                raw_html_structure = b"".join(http_response.readlines())
        except Exception as gen_exc:
            raise gen_exc

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

        # [Bandit security warning note]
        # any usage of the urllib trigger the warning: {B310: Audit url open for permitted schemes}
        # urllib.request.urlopen supports file system access via ftp:// and file://
        #
        # if our usage accepted external input, then this would be a potential security concern, but
        # our use case leverages hard-coded URL's pointing directly at the FDA webpages
        try:
            page_request = urllib.request.Request(url=fda_drug_data_page, data=None, headers={}, method="GET")
            with urllib.request.urlopen(url=page_request, timeout=request_timeout_sec) as http_response:  # nosec
                raw_html_structure = b"".join(http_response.readlines())
        except Exception as gen_exc:
            raise gen_exc

        html_parser = bs4.BeautifulSoup(raw_html_structure, features="html.parser")

        data_entity_attributes = {"data-entity-substitution": True, "data-entity-type": True, "data-entity-uuid": True}
        data_tag = html_parser.find("a", attrs=data_entity_attributes)
        version_tag = data_tag.next_sibling
        return version_tag.text.strip()
