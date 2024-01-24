import os
# from collections import ChainMap
import pandas as pd


"""
This script parses entries of the repoDB csv file (named `full.csv`) and outputs documents as SmartAPI requires.

Each document represents a unique pair of drug and indication, using DrugBank ID (_id) and indication ID (ind_id) as the composed primary key.
One drug may have multiple indications, and it will have one document per drug + indication pair.
One pair of drug and indication may have multiple trials, which will be grouped into one document.
Each trial is composed of NCT, status, phase, and DetailedStatus.

and these indications will be grouped into one document.

NCT | status   | phase | DetailedStatus
"id": "NCT00057447",
"detailed_status": "administrative reasons",
"phase": "Phase 1/Phase 2",
"status": "terminated"

See https://github.com/SmartAPI/smartAPI/issues/85 for more details.

Example: Suppose we have the following entries in the repoDB csv.

| drug_name     | drugbank_id | ind_name                                           | ind_id   | NCT | status   | phase | DetailedStatus |
|---------------|-------------|----------------------------------------------------|----------|-----|----------|-------|----------------|
| enalapril     | DB00584     | Asymptomatic left ventricular systolic dysfunction | C3698411 | NA  | Approved | NA    | NA             |
| enalapril     | DB00584     | Hypertensive disease                               | C0020538 | NA  | Approved | NA    | NA             |

The expected output is:

```
# Document 1
{
    "_id": "DB00584_C3698411",
    "drug": {
        "drugbank": "DB00584",
        "name": "Enalapril"
    },
    "indication": {
        "name": "Asymptomatic left ventricular systolic dysfunction",
        "umls": "C3698411"
    },
    "trials": [
        {
            "status": "approved"
        }
    ]
}

# Document 2
{
    "_id": "DB00584_C0020538",
    "drug": {
        "drugbank": "DB00584",
        "name": "Enalapril"
    },
    "indication": {
        "name": "Hypertensive disease",
        "umls": "C0020538"
    },
    "trials": [
        {
            "status": "approved"
        }
    ]
}
```
"""

############################################
# Part 1 - Client to read DrugBank CSV     #
############################################

def process_drugbank_csv(data_folder):
  """
  Reads open source DrugBank CSV to get names for DrugBank IDs

  Args:
      data_folder (str): the path where data files are stored

  Returns:
      id_name_map (dict[str, str]): a mapping of DrugBank ids to names
  """
  with open(os.path.join(data_folder, 'drugbank vocabulary.csv'), encoding='utf-8') as f:
    data = [line.strip().split(',') for line in f.readlines()][1:] # exclude first line (headings)

  id_name_map = {}
  for entry in data:
    ids = [entry[0], *entry[1].split(' | ')]
    for i in ids:
      id_name_map[i] = entry[2]

  return id_name_map


##########################################
# Part 2 - Util to revise the repoDB csv #
##########################################


def revise_drugbank_name(repodb_df, id_name_map):
    """
    Revise the drugbank name of the original repoDB csv.

    Args:
        repodb_df (pandas.DataFrame): the original dataframe from the repoDB csv

    Returns:
        repodb_df (pandas.DataFrame): the revised dataframe
    """

    """
    Addendum (2020-11-05): we found a possible glitch in the original repoDB csv file that one drugbank ID
    may correspond to multiple drug names. E.g. drugbank ID "DB00002" is found in the following entries:

    | drug_name               | drugbank_id | ind_name                           | ind_id   | NCT         | status     | phase           | DetailedStatus      |
    |-------------------------|-------------|------------------------------------|----------|-------------|------------|-----------------|---------------------|
    | cetuximab               | DB00002     | Squamous cell carcinoma of mouth   | C0585362 | NA          | Approved   | NA              | NA                  |
    | cetuximab               | DB00002     | Squamous cell carcinoma of nose    | C3163899 | NA          | Approved   | NA              | NA                  |
    | cetuximab               | DB00002     | Squamous cell carcinoma of pharynx | C1319317 | NA          | Approved   | NA              | NA                  |
    | cetuximab               | DB00002     | Laryngeal Squamous Cell Carcinoma  | C0280324 | NA          | Approved   | NA              | NA                  |
    | cetuximab               | DB00002     | Malignant tumor of colon           | C0007102 | NA          | Approved   | NA              | NA                  |
    | NA                      | DB00002     | Non-Small Cell Lung Carcinoma      | C0007131 | NCT00203931 | Terminated | Phase 2         | Slow accrual and ...|
    | dexamethasone phosphate | DB00002     | Multiple Myeloma                   | C0026764 | NCT00368121 | Terminated | Phase 2         | Lack of ...         |
    | cetuximab               | DB00002     | Non-Small Cell Lung Carcinoma      | C0007131 | NCT00694603 | Terminated | Phase 2         | Slow accrual ...    |
    | cetuximab               | DB00002     | Squamous cell carcinoma            | C0007137 | NCT01794845 | Terminated | Phase 2         | Early termination...|
    | NA                      | DB00002     | Squamous cell carcinoma            | C0007137 | NCT02298595 | Withdrawn  | Phase 1/Phase 2 | NA                  |

    It's not clear how NA was produced in the 1st column but for the 7th entry (dexamethasone phosphate) 
    Kevin found it's actually a combo drug with cetuximab.

    To maintain the one-to-one relationship between `drug_name` and `drugbank_id`, here we apply the following policy:

    - Discard the original `drug_name` column in the repoDB csv file
    - Use mychem.info API to find a correct drug name for each drugbank ID
    """

    """
    Addendum (2020-11-06): we found that some drug bank IDs are not found in mychem.info (e.g. "DB12430")

    To maintain the one-to-one relationship between `drug_name` and `drugbank_id`, here we apply the following policy:

    - Temporarily discard the original `drug_name` column in the repoDB csv file
    - Use mychem.info API to find a drug name for each drugbank ID
        - If not found, use the original `drug_name`
            - If the original `drug_name` is NA or not unique, manipulate manually
    """

    for _, row in repodb_df.iterrows():
        # If `row.drugbank_id` is not a key in `id_name_map`, `new_drug_name` is set None;
        # otherwise `new_drug_name` is the mapped drug name (which could be None)
        new_drug_name = id_name_map.get(row.drugbank_id, None)
        if new_drug_name is not None:
            row.drug_name = new_drug_name

    assert is_injective(repodb_df, "drugbank_id", "drug_name"), "drugbank_id has multiple drug_names after manipulation"

    return repodb_df

def is_injective(df, col1, col2):
    """
    Check if two columns are injective in a dataframe.

    A injective relation between two columns is like (same with the injective in functions):

    | col1 | col2      |
    |------|-----------|
    | a    | apple     |
    | b    | banana    |
    | c    | cranberry |
    | r    | cranberry |

    Args:
        df (pandas.DataFrame): a pandas dataframe
        col1 (str): name of the 1st column
        col2 (str): name of the 2nd column
    Returns:
        result (boolean): True if injective otherwise False
    """
    df = df.drop_duplicates(subset=[col1, col2])
    is_injective = (df.groupby(col1)[col2].count().max() == 1)

    return is_injective

def is_one_to_one(df, col1, col2):
    """
    Check if two columns are one-to-one in a dataframe.

    A one-to-one relation between two columns is like (same with the bijection in functions):

    | col1 | col2      |
    |------|-----------|
    | a    | apple     |
    | b    | banana    |
    | c    | cranberry |

    Args:
        df (pandas.DataFrame): a pandas dataframe
        col1 (str): name of the 1st column
        col2 (str): name of the 2nd column
    Returns:
        result (boolean): True if one-to-one otherwise False
    """
    df = df.drop_duplicates(subset=[col1, col2])
    is_injective = (df.groupby(col1)[col2].count().max() == 1)
    is_surjective = (df.groupby(col2)[col1].count().max() == 1)

    return is_injective and is_surjective


#####################################
# Part 3 - Parser of the repoDB csv #
#####################################


class IndicationEntry:
    def __init__(self, series):
        self._id = f"{series['drugbank_id'].iat[0]}_{series['ind_id'].iat[0]}"
        self.drug = {
            "drugbank": series["drugbank_id"].iat[0],
            "name": series["drug_name"].iat[0]
        }
        self.indication = {
            "name": series["ind_name"].iat[0],
            "umls": series["ind_id"].iat[0]
        }

        # Remove fields that contain `NA` value.
        self.__dict__ = {key: value for key, value in self.__dict__.items() if value != "NA"}

        # Construct the trials field using vectorized operations
        trials = []
        for _, trial_info in series.iterrows():
            trial_entry = {
                "id": trial_info["NCT"],
                "detailed_status": trial_info["DetailedStatus"],
                "phase": trial_info["phase"],
                "status": trial_info["status"].lower()
            }
            # Remove fields that contain `NA` value.
            trial_entry = {key: value for key, value in trial_entry.items() if value != "NA"}
            trials.append(trial_entry)

        if any(trials):
            self.trials = trials

    def to_dict(self):
        entry_dict = {
            "_id": self._id,
            "drug": self.drug,
            "indication": self.indication,
            "trials": self.trials if self.trials else None
            # Add more attributes as needed
        }

        # Remove fields that contain `None` or `NA` values.
        entry_dict = {key: value for key, value in entry_dict.items() if value is not None and value != "NA"}

        return entry_dict


def load_data(data_folder):
    id_name_map = process_drugbank_csv(data_folder)
    repodb_file = os.path.join(data_folder, "full.csv")

    # "NA" strings in the csv will be preserved instead of being converted to `np.nan`
    repodb_df = pd.read_csv(repodb_file, na_filter=False)

    # Revise the drugbank name of the original repoDB csv.
    repodb_df = revise_drugbank_name(repodb_df, id_name_map)

    for _, indication_dataframe in repodb_df.groupby(["drugbank_id", "drug_name"], as_index=False):
        indication_entries = [IndicationEntry(series) for _, series in indication_dataframe.groupby(["drug_name", "drugbank_id", "ind_id", "ind_name"], as_index=False)]
        yield from (item.to_dict() for item in indication_entries)
