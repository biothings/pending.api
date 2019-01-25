import os
import csv
from biothings.utils.dataload import unlist
from biothings.utils.dataload import value_convert_to_number
from biothings.utils.dataload import merge_duplicate_rows, dict_sweep
from myvariant.src.utils.hgvs import get_hgvs_from_vcf
from itertools import groupby

VALID_COLUMN_NO = 31

'''this parser is for denovo-db v1.6.1 downloaded from
http://denovo-db.gs.washington.edu/denovo-db/Download.jsp'''


# convert one snp to json
def _map_line_to_json(df):
    # specific variable treatment
    chrom = df["Chr"]
    if chrom == 'M':
        chrom = 'MT'

    position = int(df["Position"])
    ref, alt = df["Variant"].upper().split(">")

    HGVS = get_hgvs_from_vcf(chrom, position, ref, alt, mutant_type=False)

    sampleid = df["SampleID"]
    studyname = df["StudyName"]
    pubmedid = df["PubmedID"]
    numprobands = df["NumProbands"]
    numcontrols = df["NumControls"]
    sequencetype = df["SequenceType"]
    primaryphenotype = df["PrimaryPhenotype"]
    validation = df["Validation"]
    chrom = df["Chr"]
    position = df["Position"]
    variant = df["Variant"]
    rsid = clean_rsid(df["rsID"], ("0", ))
    dbsnpbuild = clean_data(df["DbsnpBuild"], ("0", ))
    ancestralallele = df["AncestralAllele"]
    kgenomecount = df["1000GenomeCount"]
    exacfreq = df["ExacFreq"]
    espaafreq = df["EspAaFreq"]
    espeafreq = df["EspEaFreq"]
    transcript = clean_data(df["Transcript"], ("none", ""))
    codingdnasize = clean_data(df["codingDnaSize"], ("-1", ))
    gene = clean_data(df["Gene"], ("NA", ""))
    functionclass = clean_data(df["FunctionClass"], ("none", ""))
    cdnavariant = clean_data(df["cDnaVariant"], ("NA", ""))
    proteinvariant = clean_data(df["ProteinVariant"], ("NA", ""))
    exon_intron = clean_data(df["Exon_Intron"], ("NA",))
    polyphen_hdiv = clean_data(df["PolyPhen_HDiv"], ("-1",))
    polyphen_hvar = clean_data(df["PolyPhen_HVar"], ("-1",))
    siftscore = clean_data(df["SiftScore"], ("-1",))
    caddscore = clean_data(df["CaddScore"], ("-1",))
    lofscore = clean_data(df["LofScore"], ("-1",))
    lrtscore = clean_data(df["LrtScore"], ("-1",))


# load as json data
    one_snp_json = {
        "_id": HGVS,
        "denovodb": {
            "chrom": convert_or_none(chrom, str),
            "pos" : convert_or_none(position, int),
            "ref": convert_or_none(ref, str),
            "alt": convert_or_none(alt, str),
            "sampleid": convert_or_none(sampleid, str),
            "studyname": convert_or_none(studyname, str),
            "pmid": convert_or_none(pubmedid, int),
            "numprobands": convert_or_none(numprobands, int),
            "numcontrols":  convert_or_none(numcontrols, int),
            "sequencetype":  convert_or_none(sequencetype,str),
            "primaryphenotype": convert_or_none(primaryphenotype,str),
            "validation": convert_or_none(validation, str),
            "variant": convert_or_none(variant, str),
            "rsid": convert_or_none(rsid, str),
            "dbsnpbuild": convert_or_none(dbsnpbuild, int),
            "ancestralallele": convert_or_none(ancestralallele, str),
            "1000genomecount":  convert_or_none(kgenomecount, int),
            "exacfreq":  convert_or_none(exacfreq, float),
            "espaafreq":   convert_or_none(espaafreq, float),
            "espeafreq":   convert_or_none(espeafreq, float),
            "transcript":  convert_or_none(transcript, str),
            "codingdnasize":  convert_or_none(codingdnasize, int),
            "gene":    convert_or_none(gene, str),
            "functionclass":  convert_or_none(functionclass,str),
            "cdnavariant": convert_or_none(cdnavariant,str),
            "proteinvariant":  convert_or_none(proteinvariant,str),
            "exon_intron":   convert_or_none(exon_intron,str),
            "polyphen_hdiv": convert_or_none(polyphen_hdiv,float),
            "polyphen_hvar": convert_or_none(polyphen_hvar,float),
            "siftscore":   convert_or_none(siftscore,float),
            "caddscore": convert_or_none(caddscore,float),
            "lofscore":  convert_or_none(lofscore,float),
            "lrtscore":  convert_or_none(lrtscore,float),
        }
    }

    return one_snp_json

def convert_or_none(v, to_f, none_vals=[]):
    if (not v) or (v in none_vals):
        return None
    return to_f(v)   

def clean_index(s):
    return s.replace("/", "_").replace("-", "_").replace("(", "_").replace(")", "").replace("#", "")


def clean_data(d, vals):
    if d in vals:
        return None
    else:
        return d

def clean_rsid(d, vals):
    if d in vals:
        return None
    else:
        return "rs{}".format(d)


# open file, parse, pass to json mapper
def load_data(data_folder):
    input_fn = os.path.join(data_folder,"denovo-db.non-ssc-samples.variants.tsv")
    open_file = open(input_fn)
    db_denovodb = csv.reader(open_file, delimiter="\t")
    index = next(db_denovodb)
    while index[0].startswith("##"):
        index = next(db_denovodb)
    assert len(index) == VALID_COLUMN_NO, "Expecting %s columns, but got %s" % (VALID_COLUMN_NO, len(index))
    index = [clean_index(s) for s in index]
    denovodb = (dict(zip(index, row)) for row in db_denovodb)
    denovodb = filter(lambda row: row["Chr"] != "", denovodb)
    json_rows = map(_map_line_to_json, denovodb)
    json_rows = (row for row in json_rows if row)
    json_rows = sorted(json_rows, key=lambda row: row["_id"])
    row_groups = (it for (key, it) in groupby(json_rows, lambda row: row["_id"]))
    json_rows = (merge_duplicate_rows(rg, "denovodb") for rg in row_groups)
    return (unlist(dict_sweep(row, vals=[None, ])) for row in json_rows)
