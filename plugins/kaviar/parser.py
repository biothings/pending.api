import os
import csv
from biothings.utils.dataload import unlist
from biothings.utils.dataload import value_convert_to_number
from biothings.utils.dataload import merge_duplicate_rows, dict_sweep
from myvariant.src.utils.hgvs import get_hgvs_from_vcf
from itertools import groupby, chain
import json
import vcf
import tarfile
import gzip, shutil
from csvsort import csvsort 
import config

VALID_COLUMN_NO = 8

'''this parser is for Kaviar version 160204-Public(All variants, annotated with data sources) downloaded from
http://db.systemsbiology.net/kaviar/Kaviar.downloads.html'''

# patch tempfile to force tmp dir to in data_folder
import tempfile
def mytempdir():
    return [os.path.join(config.DATA_ARCHIVE_ROOT,"tmp")]
tempfile._candidate_tempdir_list = mytempdir
from tempfile import mkstemp


# convert one snp to json
# convert one snp to json
def _map_line_to_json(item):
    chrom = item.CHROM
    chromStart = item.POS
    ref = item.REF
    info = item.INFO

    try:
        af = info['AF']
    except:
        af = None
    try:
        ac = info['AC']
    except:
        ac = None
    try:
        an = info['AN']
    except:
        ac = None
    try:
        ds = info['DS']
    except:
        ds = None

    # convert vcf object to string
    item.ALT = [str(alt) for alt in item.ALT]

    # if multiallelic, put all variants as a list in multi-allelic field
    hgvs_list = None
    if len(item.ALT) > 1:
        hgvs_list = []
        for alt in item.ALT:
            try:
                hgvs_list.append(get_hgvs_from_vcf(chrom, chromStart, ref, alt, mutant_type=False))
            except:
                hgvs_list.append(alt)

        assert len(item.ALT) == len(info['AC']), "Expecting length of item.ALT= length of info.AC, but not for %s" % (item)
        assert len(item.ALT) == len(info['AF']), "Expecting length of item.ALT= length of info.AF, but not for %s" % (item)
        if ds:
            if len(item.ALT) != len(info['DS']):
                ds_str = ",".join(info['DS'])
                ds_str = ds_str.replace("NA7022,18", "NA7022_18")
                ds_list = ds_str.split(",")
                info['DS'] = [d.replace("NA7022_18", "NA7022,18") for d in ds_list]
                assert len(item.ALT) ==len(info['DS']), "info.DS mismatch, %s: %s\n## DS: %s" % (item, info['DS'])

    for i, alt in enumerate(item.ALT):
        try:
            (HGVS, var_type) = get_hgvs_from_vcf(chrom, chromStart, ref, alt, mutant_type=True)
        except:
            continue

        if HGVS is None:
            return

        # load as json data
        one_snp_json = {
            "_id": HGVS,
            "kaviar": {
                "multi-allelic": hgvs_list,
                "ref": ref,
                "alt": alt,
                "af": info['AF'][i],
                "ac": info['AC'][i],
                "an": an,
                "ds": info['DS'][i].split("|") if ds else None,
            }
        }

        yield value_convert_to_number(one_snp_json)



# open file, parse, pass to json mapper
def load_data(data_folder):
    tar = tarfile.open(os.path.join(data_folder, "Kaviar-160204-Public-hg19.vcf.tar"))
    member = tar.getmember("Kaviar-160204-Public/vcfs/Kaviar-160204-Public-hg19.vcf.gz")
    member.name = os.path.basename(member.name)
    tar.extract(member, path=data_folder)
    tar.close()

    input_fn = os.path.join(data_folder, "Kaviar-160204-Public-hg19.vcf.gz")
    vcf_reader = vcf.Reader(filename=input_fn, compressed=True, strict_whitespace=True)

    json_rows = map(_map_line_to_json, vcf_reader)
    json_rows = chain.from_iterable(json_rows)

    fd_tmp, tmp_path = mkstemp(dir=data_folder)   

    try:
        with open(tmp_path, "w") as f:
            dbwriter = csv.writer(f)
            for doc in json_rows:
                if doc:
                    dbwriter.writerow([doc['_id'], json.dumps(doc)])

        csvsort(tmp_path, [0,])

        with open(tmp_path) as csvfile:
            json_rows = csv.reader(csvfile)
            json_rows = (json.loads(row[1]) for row in json_rows)
            row_groups = (it for (key, it) in groupby(json_rows, lambda row: row["_id"]))
            json_rows = (merge_duplicate_rows(rg, "kaviar") for rg in row_groups)
        
            import logging
            for row in json_rows:
                logging.debug(row)
                res = unlist(dict_sweep(row, vals=[None, ]))
                yield res

    finally:
        os.remove(tmp_path)
        os.remove(input_fn)


