"""
DRESIS dataplugin parser
"""

from types import GeneratorType
import csv
import itertools
import pathlib


def build_file_mapping(data_folder: str) -> dict:
    """
    Builds the file mapping for the downloaded data files
    Location: https://dresis.idrblab.net/download

    These files appear to have been hosted on a windows machine
    due to their file structure, naming, and encoding so we all
    of the processing specifically here for a reason to avoid issues
    when we run things in a unix/posix flavor

    Lookup Reference Table:
    1-11 -> HIV-DRUG-RESISTANCE-FILE
    1-1  -> GENERAL-DRUG-RESISTANCE-FILE
    2-1  -> DRUG-RESISTANCE-MAPPING-FILE
    3-1  -> DISEASE-RESISTANCE-MAPPING-FILE
    4-1  -> MOLECULAR-RESISTANCE-MAPPING-FILE
    """
    file_mapping = {}

    data_folder = pathlib.Path(data_folder).resolve().absolute()
    data_files = data_folder.glob("*.txt")
    for data_file in data_files:
        if data_file.name.startswith("1-11"):
            file_mapping["HIV_DRUG_RESISTANCE"] = data_file
        elif data_file.name.startswith("1-1"):
            file_mapping["GENERAL_DRUG_RESISTANCE"] = data_file
        elif data_file.name.startswith("2-1"):
            file_mapping["DRUG_RESISTANCE_LOOKUP"] = data_file
        elif data_file.name.startswith("3-1"):
            file_mapping["DISEASE_RESISTANCE_LOOKUP"] = data_file
        elif data_file.name.startswith("4-1"):
            file_mapping["MOLECULAR__RESISTANCE_LOOKUP"] = data_file
    return file_mapping


def load_drug_info(drug_file: pathlib.Path) -> dict:
    """
    Loads the file:
    >>> '2-1. The general information of drugs associated with resistance.txt'

    Returns a mapping of the csv file via drug id to the drug contents
    DRUG_ID -> {DRUGBANK_ID, DRUG_NAME}
    """
    drug_map = {}
    with open(drug_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for entry in reader:
            drugbank_id = entry.get("DrugBank_ID", None)
            if drugbank_id is not None and len(drugbank_id) > 2:
                drug_id = f"DRUGBANK:{drugbank_id}"
                drug_name = entry["Drug_Name"]
                drug_map[entry["Drug_ID"]] = {"drug_id": drug_id, "drug_name": drug_name}
    return drug_map


def load_disease_info(disease_file: pathlib.Path) -> dict:
    """
    Loads the file:
    >>> '3-1. The general information of disease related with resistance.txt'

    Returns a mapping of the csv file via disease id to the disease contents
    DISEASE_ID -> {DISEASE_ICD, DISEASE_NAME}
    """
    disease_map = {}
    with open(disease_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for entry in reader:
            disease_icd = entry.get("Disease_ICD", None)
            if disease_icd is not None and len(disease_icd) > 2:
                disease_id_key = entry["Disease_ID"]
                last_disease_icd = disease_icd.split(":")[-1].replace(" ", "")
                disease_id_value = f"ICD11:{last_disease_icd}"
                disease_name = entry["Disease_name"]
                disease_map[disease_id_key] = {"disease_id": disease_id_value, "disease_name": disease_name}
    return disease_map


def load_molecular_info(molecular_file: pathlib.Path) -> dict:
    """
    Loads the file:
    >>> '4-1. The general information of molecular associated with resistance.txt'

    Returns a mapping of the csv file via hgnc id to the molecular contents
    MOLECULE_ID -> {HGNC_ID, MOLECULE_NAME, MOLECULE_TYPE, MOLECULE_SPECIES}
    """
    molecular_map = {}
    with open(molecular_file, "r", encoding="utf-8") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for entry in reader:
            hgnc_id = entry.get("HGNC_ID", None)
            if hgnc_id is not None and len(hgnc_id) > 2:
                molecule_id_key = entry["Molecule_ID"]
                molecule_name = entry["Molecule_name"]
                molecule_type = entry["Molecule_type"]
                molecule_species = entry["Molecule_species"]
                molecular_map[molecule_id_key] = {
                    "molecule_id": hgnc_id,
                    "molecule_name": molecule_name,
                    "molecule_type": molecule_type,
                    "species": molecule_species,
                }
    return molecular_map


def generate_general_resistances(
    resistance_file: pathlib.Path, drug_map: dict, disease_map: dict, molecular_map: dict
) -> GeneratorType:
    """
    Loads the file:
    >>> '1-1. The pair information of drug-disease (Besides HIV)-molecular based resistance.txt'
    """
    with open(resistance_file, "r", encoding="utf-8", errors="strict") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for entry in reader:
            molecular_id = entry.get("Molecule_ID", None)
            drug_id = entry.get("Drug_ID", None)
            disease_id = entry.get("Disease_ID", None)

            molecular_subject = molecular_map.get(molecular_id, None)
            drug_object = drug_map.get(drug_id, None)
            disease_association = disease_map.get(disease_id, None)
            if molecular_subject and drug_object and disease_association:
                predicate_identifier = (
                    f"{molecular_subject['molecule_id']}-{disease_association['disease_id']}-{drug_object['drug_id']}"
                )
                predicate = {
                    "_id": predicate_identifier,
                    "subject": molecular_subject,
                    "object": drug_object,
                    "association": disease_association,
                }
                predicate["association"]["sensitivity"] = entry["Drug_sensitivity"]
                yield predicate


def generate_hiv_resistances(
    resistance_file: pathlib.Path, drug_map: dict, disease_map: dict, molecular_map: dict
) -> GeneratorType:
    """
    Loads the file:
    >>> '1-11. The pair information of HIV-drug-molecular based resistance.txt'

    This specific file also appears to be encoding slightly differently than utf-8. It appears
    to use utf-16-le. Keep this in mind when processing data from it
    """
    with open(resistance_file, "r", encoding="utf-16-le", errors="strict") as csvfile:
        reader = csv.DictReader(csvfile, delimiter="\t")
        for entry in reader:
            molecular_id = entry.get("Molecule_ID", None)
            drug_id = entry.get("Drug_ID", None)

            molecular_subject = molecular_map.get(molecular_id, None)
            drug_object = drug_map.get(drug_id, None)
            if molecular_subject and drug_object:
                predicate_identifier = f"{molecular_subject['molecule_id']}-{drug_object['drug_id']}"
                predicate = {
                    "_id": predicate_identifier,
                    "subject": molecular_subject,
                    "object": drug_object,
                    "association": {"disease_name": "HIV", "sensitivity": entry["Drug_sensitivity"]},
                }
                yield predicate


def load_data(data_folder: str):
    file_mapping = build_file_mapping(data_folder)

    drug_map = load_drug_info(file_mapping["DRUG_RESISTANCE_LOOKUP"])
    disease_map = load_disease_info(file_mapping["DISEASE_RESISTANCE_LOOKUP"])
    molecular_map = load_molecular_info(file_mapping["MOLECULAR__RESISTANCE_LOOKUP"])

    general_resistances = generate_general_resistances(
        file_mapping["GENERAL_DRUG_RESISTANCE"], drug_map, disease_map, molecular_map
    )
    hiv_resistances = generate_hiv_resistances(
        file_mapping["HIV_DRUG_RESISTANCE"], drug_map, disease_map, molecular_map
    )
    yield from itertools.chain(general_resistances, hiv_resistances)
