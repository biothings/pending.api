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
    * It's fine to set all column types to str

    Args:
      folder_path: pathlib Path to folder containing csv files
      data_file_pattern: str pattern for csv file pathnames (syntax: pathlib's pattern language)

    Returns:
      pandas dataframe containing data from multiple csv files
    """
    ## using pathlib's Path.glob method, which produces a generator
    ## then turning the generator into a list, so can check if it's empty

    all_file_paths = list(folder_path.glob(data_file_pattern))

    ## read_csv dtype notes:
    ## - Want to read "gene mim" and "disease mim" columns as str. Otherwise, default reading will be float
    ##   for some files (extra steps to handle)
    ## - All IDs in final API docs should be strings (ex: "publications")
    ## - didn't save memory to read some columns as "category"

    ## using generator expression (think list/dict comprehension) within pd.concat to load files 1 at a time
    ## ingesting all columns as str for now
    if all_file_paths:
        return pd.concat((pd.read_csv(f, dtype=str) for f in all_file_paths), ignore_index=True)
    else:
        raise FileNotFoundError(f"Can't find files in `{folder_path}` matching `{data_file_pattern}`")


def duplicates_check(dataframe: pd.DataFrame, column_subset: list[str]):
    """This function checks whether drop_duplicates using all columns will actually remove all duplicates.

    Many column values are delimited strings, and my concern is that these could differ only in list order
    for the same records in different files/panels.

    If the duplicated data with this column subset == duplicated data using all columns: then this column 
    subset does uniquely define records / rows. And drop_duplicates using all columns should work as expected.

    Else: raise AssertionError. The other columns of the data need more investigation (something else is 
    contributing to the uniqueness of each row, and it could be delimited-string list order). And the parser 
    probably needs adjustment.

    Args:
      dataframe: pandas dataframe
      column_subset: array of column names in dataframe that should uniquely define one record/row
    
    Returns:
      None
    """

    n_duplicates_subset = dataframe[dataframe.duplicated(subset=column_subset, keep=False)].shape
    n_duplicates_all = dataframe[dataframe.duplicated(keep=False)].shape

    if n_duplicates_subset != n_duplicates_all:
        raise AssertionError(
            "The data format has changed, and record de-duplication may not work as-expected. "
            "Double-check the data and what columns uniquely define one record"
        )


def nodenorm_genes(dataframe: pd.DataFrame, column_name: str, nodenorm_url: str):
    """Use Translator NodeNorm to add primary/canonical IDs and names for genes to dataframe

    Assumes dataframe's column_name contains 1 gene CURIE (Translator-formatted ID) per row,
    with no NA values.

    Will run NodeNorm on the column_name's gene CURIEs, create mapping dict of those CURIEs to
    NodeNorm's primary IDs and names. Then will add columns gene_nodenorm_id and
    gene_node_norm_name to dataframe, using column_name and the mapping dict. This function will
    change dataframe in its place, so it doesn't need to return anything.

    Args:
      dataframe: pandas dataframe
      column_name: name of column containing gene CURIEs (Translator-formatted IDs)
      nodenorm_url: NodeNorm API endpoint to send requests to

    Returns:
      None
    """
    ## called below dataframe=df, column_name="hgnc_id", nodenorm_url="https://nodenorm.ci.transltr.io/get_normalized_nodes"
    unique_curies = dataframe[column_name].dropna().unique()

    nodenorm_mapping = {}
    ## larger batches are quicker
    for batch in batched(unique_curies, 1000):
        req_body = {
            "curies": list(batch),  ## batch is a tuple, cast into list
            "conflate": True,       ## do gene-protein conflation
        }
        r = requests.post(nodenorm_url, json=req_body)
        response = r.json()
        ## dictionary expression
        ## response's keys are input IDs, values are dictionary that includes primary/canonical info
        temp = {
            k: {"primary_id": v["id"]["identifier"],
                "primary_label": v["id"]["label"]} 
            for k,v in response.items()
        }
        nodenorm_mapping.update(temp)

    dataframe["gene_nodenorm_id"] = [nodenorm_mapping[i]["primary_id"] for i in dataframe[column_name]]
    dataframe["gene_nodenorm_label"] = [nodenorm_mapping[i]["primary_label"] for i in dataframe[column_name]]


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
    ## First check that drop_duplicates using all columns will work as-intended, raise error if concern
    ## Based on exploring the data, this column subset should uniquely define one record/row
    ##   (none have delimited strings).
    duplicates_check(df, ["g2p_id", "gene_symbol", "disease_name", "allelic_requirement", "molecular_mechanism"])
    ## drop duplicates if no error was raised
    df.drop_duplicates(inplace=True, ignore_index=True)

    ## COLUMN-LEVEL TRANSFORMS
    ## 1. adding Translator/biolink prefixes to IDs
    df["gene_mim"] = "OMIM:" + df["gene_mim"]
    df["hgnc_id"] = "HGNC:" + df["hgnc_id"]
    df["disease_mim"] = df["disease_mim"].str.replace("Orphanet", "orphanet")
    ## done to preserve NA, orphanet values in column
    df["disease_mim"] = [i if pd.isna(i)
                         else "OMIM:" + i if i.isnumeric()
                         else i 
                         for i in df["disease_mim"]]
    ## 2. strip whitespace
    df["disease_name"] = df["disease_name"].str.strip()
    df["comments"] = df["comments"].str.strip()
    ## 3. create new columns
    ## UI really wants resource website urls like this. May need to adjust over time as website changes
    df["g2p_record_url"] = "https://www.ebi.ac.uk/gene2phenotype/lgd/" + df["g2p_id"]
    ## 4. replace panel keywords with full human-readable names (based on what's shown on G2P website)
    ## keeping "Hearing loss" as-is, changing all other values
    df["panel"] = df["panel"].str.replace("DD", "Developmental disorders")
    df["panel"] = df["panel"].str.replace("Cancer", "Cancer disorders")
    df["panel"] = df["panel"].str.replace("Cardiac", "Cardiac disorders")
    df["panel"] = df["panel"].str.replace("Eye", "Eye disorders")
    df["panel"] = df["panel"].str.replace("Skeletal", "Skeletal disorders")
    df["panel"] = df["panel"].str.replace("Skin", "Skin disorders")
    ## 5. add columns for NodeNorm primary/canonical IDs and names
    nodenorm_genes(df, "hgnc_id", "https://nodenorm.ci.transltr.io/get_normalized_nodes")

    ## GENERATING DOCS
    ## using itertuples because it's faster, preserves column datatypes
    for row in df.itertuples(index=False):
        ## 1. simple assignments
        document = {
            "_id": row.g2p_id,
            "subject": {
                "hgnc_symbol": row.gene_symbol, 
                "hgnc": row.hgnc_id,
                "nodenorm_id": row.gene_nodenorm_id,
                "nodenorm_label": row.gene_nodenorm_label,
                "type": "Gene"
            },
            "association": {
                "g2p_record_id": row.g2p_id,
                "g2p_record_url": row.g2p_record_url,
                "allelic_requirement": row.allelic_requirement,
                "confidence": row.confidence,
                "molecular_mechanism": row.molecular_mechanism,
                "molecular_mechanism_categorisation": row.molecular_mechanism_categorisation,
                "g2p_panels": [i.strip() for i in row.panel.split(";")],
                ## cast into str for export
                "date_of_last_review": str(row.date_of_last_review),
            },
            "object": {
                "name": row.disease_name, 
                "type": "Disease"
            },
        }

        ## 2. only create field if value is not NA. list comprehension with split won't work if value is NA
        ## 2A. Gene
        if pd.notna(row.gene_mim):
            document["subject"]["omim"] = row.gene_mim
        if pd.notna(row.previous_gene_symbols):
            document["subject"]["previous_gene_symbols"] = [i.strip() for i in row.previous_gene_symbols.split(";")]

        ## 2B. Association
        if pd.notna(row.cross_cutting_modifier):
            document["association"]["cross_cutting_modifiers"] = [
                i.strip() for i in row.cross_cutting_modifier.split(";")
            ]
        if pd.notna(row.variant_consequence):
            document["association"]["variant_consequences"] = [i.strip() for i in row.variant_consequence.split(";")]
        if pd.notna(row.variant_types):
            document["association"]["variant_types"] = [i.strip() for i in row.variant_types.split(";")]
        ## uses diff delimiters, could do more parsing
        if pd.notna(row.molecular_mechanism_evidence):
            document["association"]["molecular_mechanism_evidence"] = [
                i.strip() for i in row.molecular_mechanism_evidence.split("&")
            ]
        if pd.notna(row.phenotypes):
            document["association"]["phenotypes"] = [i.strip() for i in row.phenotypes.split(";")]
        if pd.notna(row.publications):
            document["association"]["pmids"] = [i.strip() for i in row.publications.split(";")]
        if pd.notna(row.comments):
            document["association"]["curator_comments"] = row.comments

        ## 2C. Disease
        ## disease_mim: create field depending on whether OMIM or orphanet
        if pd.notna(row.disease_mim):
            if row.disease_mim.startswith("orphanet"):
                document["object"]["orphanet"] = row.disease_mim
            elif row.disease_mim.startswith("OMIM"):
                document["object"]["omim"] = row.disease_mim
        if pd.notna(row.disease_MONDO):
            document["object"]["mondo"] = row.disease_MONDO

        yield document
