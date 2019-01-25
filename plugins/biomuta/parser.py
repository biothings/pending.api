import os
import csv
from biothings.utils.dataload import unlist
from biothings.utils.dataload import value_convert_to_number
from biothings.utils.dataload import merge_duplicate_rows, dict_sweep
from myvariant.src.utils.hgvs import get_hgvs_from_vcf
from itertools import groupby
from tempfile import mkstemp
import json
from csvsort import csvsort 
import re

VALID_COLUMN_NO = 22

'''this parser is for BioMuta v4.0(BioMuta v4.0 Complete Dataset) downloaded from
https://hive.biochemistry.gwu.edu/prd//biomuta/content/biomuta-master.csv'''


# convert one snp to json
def _map_line_to_json(df):
    # specific variable treatment
    chrom = df["chr_id"]
    pos = df["chr_pos"]
    if chrom == 'M':
        chrom = 'MT'

    ref = df["ref_nt"]
    alt = df["alt_nt"]

    HGVS = get_hgvs_from_vcf(chrom, int(pos), ref, alt, mutant_type=False)
    
    transcript_id = clean_data(df["transcript_id"], ("-",))
    peptide_id = clean_data(df["peptide_id"], ("-",))
    uniprot_ac = clean_data(df["uniprot_ac"], ("-",))
    refseq_ac = clean_data(df["refseq_ac"], ("-",))
    cds_pos = clean_data(df["cds_pos"], ("-",))
    pep_pos = clean_data(df["pep_pos"], ("-",))
    uniprot_pos = clean_data(df["uniprot_pos"], ("-",))
    ref_aa = clean_data(df["ref_aa"], ("-",))
    alt_aa = clean_data(df["alt_aa"], ("-",))
    mut_freq = clean_data(df["mut_freq"], ("-",))
    data_src = clean_data(df["data_src"], ("-",))
    do_id = clean_data(df["do_id"], ("-",))
    do_name_id, do_name = do_name_split(df["do_name"])
    if do_id and do_name_id:
        assert do_id == do_name_id, "do_id mismatch!"

    uberon_id = to_list(df["uberon_id"])
    gene_name = clean_data(df["gene_name"], ("-",))
    pmid_list = to_list(df["pmid_list"])
    site_prd = site_prd_parser(clean_data(df["site_prd"], ("-",)))
    site_ann = site_ann_parser(df["site_ann"])


# load as json data
    one_snp_json = {
        "_id": HGVS,
        "biomuta": {
            'chrom': chrom,
            'pos': pos,
            'ref': ref,
            'alt': alt,
            'transcript_id': transcript_id,
            'peptide_id': peptide_id,
            'uniprot_ac': uniprot_ac,
            'refseq_ac': refseq_ac,
            'cds_pos': cds_pos,
            'pep_pos': pep_pos,
            'uniprot_pos': uniprot_pos,
            'ref_aa': ref_aa,
            'alt_aa': alt_aa,
            'mut_freq': mut_freq,
            'data_src': data_src,
            'do_id': {
                        "do_id" : do_id,
                        "do_name" : do_name
                        },
            'uberon_id': uberon_id,
            'gene_name': gene_name,
            'pmid': pmid_list,
            'site_prd': site_prd,
            'site_ann': site_ann
        }
    }
    one_snp_json = value_convert_to_number(one_snp_json)
    one_snp_json['biomuta']['chrom'] = str(one_snp_json['biomuta']['chrom'])
    one_snp_json['biomuta']['do_id']['do_id'] = str(one_snp_json['biomuta']['do_id']['do_id'])
    return one_snp_json


def clean_index(s):
    return s.lower().replace("/", "_").replace("-", "_").replace("(", "_").replace(")", "").replace("#", "")


def clean_data(d, vals):
    if d in vals:
        return None
    else:
        return d

def to_list(s, sep=";"):
    if s:
        return s.split(sep)
    else:
        return None

def do_name_split(do_name):
    if not do_name:
        return None, None
    do_id, do_name = do_name.split(" / ")
    do_id = do_id.split(":")[1]
    return do_id, do_name

def site_prd_parser(s):
    prds = s.strip()
    if prds:
        prds = prds.split(";")
        return [ prd_parser(prd) for prd in prds]

def prd_parser(prd):
    prd = prd.strip()
    if prd.startswith("polyphen"):
        prd_count = len([match for match in re.finditer(":", prd)])
        assert prd_count == 1, "other site_prd: {}".format(prd)
        matched = re.match("polyphen:(.*) \(probability = ([0-9\.]*)\)", prd)
        assert matched, "polyphen parser error: {}".format(prd)
        return {"prd": "polyphen", "prediction": matched.group(1), "score": matched.group(2)}

    elif prd.startswith("netnglyc"):
        prd_count = len([match for match in re.finditer(":", prd)])
        assert prd_count == 1, "other site_prd: {}".format(prd)
        matched = re.match(r"netnglyc:([^\|]*)\|(.*)", prd)
        assert matched, "netnglyc parser error: {}".format(prd)
        return {"prd": "netnglyc", "prediction": matched.group(2), "score": matched.group(1)}

    else:
        raise ValueError("No matching parser: {}".format(prd))

def ann_parser(ann):
    s = ann.strip().split(":")
    if len(s) == 1:
        return s[0]
    elif len(s) == 2:
        return {s[0] : s[1]}
    else:
        raise ValueError("Not Adequate key:value or value format: {}".format(ann))

def site_ann_parser(s):
    anns = s.strip().split(";")
    return [ ann_parser(ann) for ann in anns]

# open file, parse, pass to json mapper
def load_data(data_folder):
    input_fn = os.path.join(data_folder,"biomuta-master.csv")
    open_file = open(input_fn)
    db_biomuta = csv.reader(open_file)
    index = next(db_biomuta)
    assert len(index) == VALID_COLUMN_NO, "Expecting %s columns, but got %s" % (VALID_COLUMN_NO, len(index))
    index = [clean_index(s) for s in index]
    biomuta = (dict(zip(index, row)) for row in db_biomuta)
    json_rows = map(_map_line_to_json, biomuta)

    fd_tmp, tmp_path = mkstemp(dir=data_folder)
    
    try:
        with open(tmp_path, "w") as f:
            dbwriter = csv.writer(f)
            for i, doc in enumerate(json_rows):
                if doc:
                    dbwriter.writerow([doc['_id'], json.dumps(doc)])  

        csvsort(tmp_path, [0,], has_header=False)
        
        with open(tmp_path) as csvfile:
            json_rows = csv.reader(csvfile)
            json_rows = (json.loads(row[1]) for row in json_rows)
            row_groups = (it for (key, it) in groupby(json_rows, lambda row: row["_id"]))
            json_rows = (merge_duplicate_rows(rg, "biomuta") for rg in row_groups)
            json_rows = (unlist(dict_sweep(row, vals=[None, ])) for row in json_rows)
            for res in json_rows:
                yield res

    finally:
        os.remove(tmp_path)



