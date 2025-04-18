import pathlib
import pandas as pd
import requests
## from BioThings annotator code: for interoperability between diff Python versions
try:
    from itertools import batched  # new in Python 3.12
except ImportError:
    from itertools import islice

    def batched(iterable, n):
        # batched('ABCDEFG', 3) → ABC DEF G
        if n < 1:
            raise ValueError("n must be at least one")
        iterator = iter(iterable)
        while batch := tuple(islice(iterator, n)):
            yield batch


def _load_multiple_csv_into_one_df(folder_path: pathlib.Path, data_file_pattern: str) -> pd.DataFrame:
    """Load EBI gene2pheno data files into 1 pandas DataFrame.

    Assumptions:
    * All data files are csv (can be compressed) AND have the same header so they can be concatenated easily.
      pandas can infer and automatically do on-the-fly decompression for some file extensions
      (see pandas.read_csv for details)
    * It's fine to load all columns as str type

    Args:
      folder_path: pathlib Path to folder containing csv files
      data_file_pattern: str pattern for csv file pathnames (syntax: pathlib's pattern language)

    Returns:
      pandas dataframe containing data from multiple csv files
    """
    ## using pathlib's Path.glob method, which produces a generator
    ## then turning the generator into a list, so can check if it's empty

    all_file_paths = list(folder_path.glob(data_file_pattern))

    ## read_csv dtype notes: ingesting all columns as str for now
    ## - Want to read "gene mim" and "disease mim" columns as str. Otherwise, default reading will be float
    ##   for some files (extra steps to handle)
    ## - All IDs in final API docs should be strings (ex: "publications")
    ## - didn't save memory to read some columns as "category"

    ## using generator expression (think list/dict comprehension) within pd.concat to load files 1 at a time
    if all_file_paths:
        return pd.concat((pd.read_csv(f, dtype=str) for f in all_file_paths), ignore_index=True)
    else:
        raise FileNotFoundError(f"Can't find files in `{folder_path}` matching `{data_file_pattern}`")


def duplicates_check(dataframe: pd.DataFrame, column_subset: list[str]):
    """Check if assumptions are correct: (1) duplicate records have completely identical rows; (2) column_subset are key column(s) for unique records/rows

    There are duplicates in the dataframe because the same record can show up in multiple panel files
    (disease falls into multiple categories). We want to drop those duplicates.

    However, what if these "duplicates" aren't completely identical rows? Many columns have
    delimited-string values, and my concern is that these could differ in list order between "duplicates".

    To check this scenario, this function compares the n_duplicates found using the key column(s) VS
    using all columns. If the counts are equal, then "duplicates" are completely identical. AND using the
    key column(s) for _id later is fine.

    If not, then there's a problem with at least 1 assumption, and the data needs to be re-explored.
    The parser also likely needs adjustments. So this function raises an AssertionError.

    Args:
      dataframe: pandas dataframe
      column_subset: array, names of `dataframe`'s key column(s) for unique records/rows

    Returns:
      None
    """

    n_duplicates_subset = dataframe[dataframe.duplicated(subset=column_subset, keep=False)].shape
    n_duplicates_all = dataframe[dataframe.duplicated(keep=False)].shape

    if n_duplicates_subset != n_duplicates_all:
        raise AssertionError(
            "The data format has changed, and the assumptions about duplicates/key columns may "
            "no longer hold. Re-explore the data and adjust the parser.\n"
        )


def nodenorm(dataframe: pd.DataFrame, input_col_name: str, expected_category: str, nodenorm_url: str,
             output_col_names: list[str]):
    """Run Translator NodeNorm on IDs for 1 bioentity category, then add the NodeNorm primary IDs and names to `dataframe`

    This function will create a dict mapping the CURIEs from `input_col_name` to NodeNorm's primary
    IDs and names. The function will then create columns in `dataframe` containing the mapping information;
    because the function makes these changes in-place, it returns None.

    It prints basic stats of NodeNorm mapping failures.

    Args:
      dataframe: pandas dataframe
      input_col_name: name of column in `dataframe`. Should contain single CURIEs (Translator-formatted ID) or NA for each row
      expected_category: the expected biolink-model category for all input IDs (should be Translator format with prefix). Will be compared to the main category in NodeNorm for the entity. If there's a mismatch, the mapping will be treated as failed.
      nodenorm_url: NodeNorm API endpoint to send requests to
      output_col_names: names of output columns with NodeNorm mapping info - first element should be primary ID, second should be primary name.

    Returns:
      None
    """

    ## get unique ID set from dataframe's input_col_name
    unique_curies = dataframe[input_col_name].dropna().unique()

    ## set up mapping dict
    nodenorm_mapping = {}

    ## set up variables to catch mapping failures
    mapping_failures = {"unexpected_error": {}, "nodenorm_returned_none": [], "wrong_category": {}, "no_label": []}

    ## larger batches are quicker
    for batch in batched(unique_curies, 1000):
        req_body = {
            "curies": list(batch),  ## batch is a tuple, cast into list
            "conflate": True,       ## do gene-protein conflation
        }
        r = requests.post(nodenorm_url, json=req_body)
        response = r.json()

        ## response's keys are input IDs, values are dictionary that includes primary/canonical info
        ## not doing dict comprehension. allows for easier review, logic writing
        for k, v in response.items():
            ## catch unexpected errors
            try:
                ## if NodeNorm didn't have info on this ID, v will be None
                if v is not None:
                    ## don't keep mapping if category is not the expected one
                    if v["type"][0] == expected_category:
                        ## also throw out mapping if no primary label found
                        if v["id"].get("label"):
                            temp = {
                                k: {"primary_id": v["id"]["identifier"],
                                    "primary_label": v["id"]["label"]}
                            }
                            nodenorm_mapping.update(temp)
                        else:
                            mapping_failures["no_label"].append(k)
                    else:
                        mapping_failures["wrong_category"].update({k: v["type"][0]})
                else:
                    mapping_failures["nodenorm_returned_none"].append(k)
            except:
                mapping_failures["unexpected_error"].update({k: v})

    ## create output columns for NodeNorm data
    dataframe[output_col_names[0]] = [nodenorm_mapping[i]["primary_id"] if nodenorm_mapping.get(i) 
                                        else pd.NA 
                                        for i in dataframe[input_col_name]]
    dataframe[output_col_names[1]] = [nodenorm_mapping[i]["primary_label"] if nodenorm_mapping.get(i) 
                                        else pd.NA 
                                        for i in dataframe[input_col_name]]

    ## calculate stats: number of rows affected by each type of mapping failure
    n_rows_no_data = dataframe[dataframe[input_col_name].isin(mapping_failures["nodenorm_returned_none"])].shape[0]
    n_rows_wrong_category = dataframe[
                                dataframe[input_col_name].isin(mapping_failures["wrong_category"].keys())
                            ].shape[0]
    n_rows_no_label = dataframe[dataframe[input_col_name].isin(mapping_failures["no_label"])].shape[0]

    ## print stats on mapping failures
    print(f"{input_col_name} NodeNorm mapping failures:")
    print(f'{n_rows_no_data} row(s) for {len(mapping_failures["nodenorm_returned_none"])} IDs with no data in NodeNorm')
    print(f'{n_rows_wrong_category} row(s) for {len(mapping_failures["wrong_category"])} IDs '
          f'with the wrong NodeNormed category (not {expected_category})')
    print(f'{n_rows_no_label} row(s) for {len(mapping_failures["no_label"])} IDs with no label in NodeNorm\n')


## main function can have any name.
## Put into manifest's uploader.parser field: "parser:{funct name}"
## DON'T NEED A MAIN EXECUTION BLOCK `if __name__ == "__main__"`
def upload_documents(data_folder: str):
    """main execution: yield documents from 1 row of data at a time

    Args:
      data_folder: Biothings will provide the data_folder (path) when running this function
    """

    ## LOAD DATA
    ## doing resolve() just in case
    base_file_path = pathlib.Path(data_folder).resolve()
    ## using "*.csv.gz": data files from FTP site have this extension. And want all data files/panels
    df = _load_multiple_csv_into_one_df(folder_path=base_file_path, data_file_pattern="*.csv.gz")
    ## make column names snake-case to make them usable with itertuples later
    df.columns = df.columns.str.replace(" ", "_")
    ## change "date_of_last_review" dtype to datetime, which should save a little memory
    df["date_of_last_review"] = pd.to_datetime(df["date_of_last_review"])

    ## DROP DUPLICATES
    ## Will raise error if data format has changed and assumptions are now incorrect
    duplicates_check(df, ["g2p_id"])
    ## drop duplicates if no error was raised
    df.drop_duplicates(inplace=True, ignore_index=True)

    ## DROP RECORDS/ROWS with confidence == "refuted" or "disputed" (strong evidence of no association, negated)
    ## print n_rows before dropping, with those confidence values
    n_rows_original = df.shape[0]
    n_rows_refuted = df[df["confidence"] == "refuted"].shape[0]
    n_rows_disputed = df[df["confidence"] == "disputed"].shape[0]
    print(f"{n_rows_original} unique rows/records in original dataset\n")
    print(f"Removing rows based on confidence:")
    print(f"{n_rows_refuted}: 'refuted'")
    print(f"{n_rows_disputed}: 'disputed'\n")
    ## drop rows, calculate n_rows after
    df = df[~df["confidence"].isin(["refuted", "disputed"])].reset_index(drop=True)
    n_rows_after_confidence = df.shape[0]
    print(f"{n_rows_after_confidence} rows afterwards\n")

    ## COLUMN-LEVEL TRANSFORMS
    ## UI really wants resource website urls like this. May need to adjust over time as website changes
    df["g2p_record_url"] = "https://www.ebi.ac.uk/gene2phenotype/lgd/" + df["g2p_id"]
    ## adding Translator/biolink prefixes to IDs used for NODENORM
    df["hgnc_id"] = "HGNC:" + df["hgnc_id"]
    df["disease_mim"] = df["disease_mim"].str.replace("Orphanet", "orphanet")
    ## done to preserve NA, orphanet values in column
    df["disease_mim"] = [i if pd.isna(i)
                         else "OMIM:" + i if i.isnumeric()
                         else i 
                         for i in df["disease_mim"]]

    ## NODENORM, DROP RECORDS/ROWS that aren't completely normalized
    nodenorm(df, "hgnc_id", "biolink:Gene", "https://nodenorm.ci.transltr.io/get_normalized_nodes",
             ["gene_nodenorm_id", "gene_nodenorm_label"])
    nodenorm(df, "disease_mim", "biolink:Disease", "https://nodenorm.ci.transltr.io/get_normalized_nodes",
             ["disease_nodenorm_id", "disease_nodenorm_label"])    
    ## DROP rows that have empty values in nodenorm columns
    df.dropna(subset=["gene_nodenorm_id", "gene_nodenorm_label", "disease_nodenorm_id", "disease_nodenorm_label"],
              inplace=True)
    ## print number of rows dropped and left
    n_rows_after_nodenorm = df.shape[0]
    print(f"{n_rows_after_confidence - n_rows_after_nodenorm} rows removed during NodeNorming process. Reasons: "
          "NA values in hgnc_id or disease_mim columns, NodeNorm mapping failures")
    print(f"{n_rows_after_nodenorm} rows after NodeNorming ({n_rows_after_nodenorm/n_rows_after_confidence:.1%})\n")

    ## GENERATING DOCS
    ## format: list of TRAPI edges, except _id is kept for BioThings just in case
    ## using itertuples because it's faster, preserves column datatypes
    for row in df.itertuples(index=False):
        ## simple assignments: no NA or "if"
        document = {
            "_id": row.g2p_id,
            "subject": row.gene_nodenorm_id,
            "qualifiers": [  ## needs data-modeling/TRAPI validation review
                {
                    "qualifier_type_id": "biolink:subject_form_or_variant_qualifier",
                    "qualifier_value": "genetic_variant_form",
                }
            ],
            "object": row.disease_nodenorm_id,
            "sources": [
                {
                    "resource_id": "infores:ebi-gene2phenotype",
                    "resource_role": "primary_knowledge_source",
                    "source_record_urls": [row.g2p_record_url],
                }
            ],
            "attributes": [
                {"attribute_type_id": "biolink:knowledge_level", "value": "knowledge_assertion"},
                {"attribute_type_id": "biolink:agent_type", "value": "manual_agent"},
                {
                    "attribute_type_id": "biolink:original_subject",
                    "original_attribute_name": "hgnc id",  ## original column name
                    "value": row.hgnc_id,
                },
                {  ## currently, after NodeNorming, no NAs in OMIM/orphanet column
                    "attribute_type_id": "biolink:original_object",
                    "original_attribute_name": "disease mim",  ## original column name
                    "value": row.disease_mim,
                },
                {  ## needs data-modeling/TRAPI validation review
                    ## EBI gene2pheno website calls this "Last Updated"/"Last Updated On"
                    "attribute_type_id": "biolink:update_date",
                    "original_attribute_name": "date of last review",  ## original column name
                    "value": str(row.date_of_last_review),
                },
            ],
        }

        ## more complex assignments ("if", handling NA). When value is NA, list comprehension with split won't work
        ## predicate
        if row.confidence == "limited":
            document["predicate"] = "biolink:related_to"
        elif row.confidence in ["moderate", "strong", "definitive"]:
            document["predicate"] = "biolink:causes"
        else:
            raise ValueError(f"Unexpected confidence value during predicate mapping: {row.confidence}. Adjust parser.")
        ## publications
        if pd.notna(row.publications):
            document["attributes"].append(
                {
                    "attribute_type_id": "biolink:publications",
                    "value": ["PMID:" + i.strip() for i in row.publications.split(";")]
                }
            )

        yield document
