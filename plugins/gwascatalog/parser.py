import os
import logging
from collections import defaultdict
from biothings_client import get_client
# create symbolic link of myvariant.info repo first
from myvariant.src.utils.hgvs import get_hgvs_from_vcf
from csv import DictReader
from biothings.utils.dataload import dict_sweep, open_anyfile, unlist, value_convert_to_number


CHROM_LIST = [str(i) for i in range(1, 23)] + ['x', 'y']


def batch_query_hgvs_from_rsid(rsid_list):
    hgvs_rsid_dict = {}
    rsid_list = list(set(rsid_list))
    variant_client = get_client('variant')
    for i in range(0, len(rsid_list), 1000):
        if i + 1000 <= len(rsid_list):
            batch = rsid_list[i: i + 1000]
        else:
            batch = rsid_list[i:]
        params = ','.join(batch)
        res = variant_client.getvariants(params, fields="_id")
        for _doc in res:
            if '_id' not in _doc:
                logging.warning('can not convert', _doc)
            hgvs_rsid_dict[_doc['query']] = _doc['_id'] if '_id' in _doc else _doc["query"]
    return hgvs_rsid_dict


def str2float(item):
    """Convert string type to float type
    """
    if item == 'NR':
        return None
    elif item:
        try:
            return float(item)
        except ValueError:
            return None
    else:
        return None


def reorganize_field(field_value, seperator, num_snps):
    if 'non_coding_transcript_exon' in field_value:
        field_value = field_value.replace('exon', 'eXon')
    new_value = [_item.strip().replace('eXon', 'exon') for _item in field_value.split(seperator)]
    if num_snps == 1:
        return new_value
    else:

        if len(new_value) == num_snps:
            return new_value
        elif field_value == '':
            return [None] * num_snps
            # TODO: REST OF THE VALUES SHOULD BE SET TO none
        elif len(new_value) == 1:
            return new_value * num_snps
        elif len(new_value) < num_snps:
            new_value += [None] * (num_snps - len(new_value))
            return new_value
        else:
            logging.info('new value', new_value, num_snps)


def parse_separator_and_snps(row):
    seperator = None
    snps = None
    if row["SNPS"].startswith("rs"):
        if "x" in row["SNPS"]:
            snps = [_item.strip() for _item in row["SNPS"].split('x')]
            seperator = "x"
        elif ";" in row["SNPS"]:
            snps = [_item.strip() for _item in row["SNPS"].split(';')]
            seperator = ";"
        elif "," in row["SNPS"]:
            snps = [_item.strip() for _item in row["SNPS"].split(',')]
            seperator = ","
        elif row["SNPS"]:
            snps = [row["SNPS"]]
    else:
        row["SNPS"] = row["SNPS"].replace('_', ":").replace('-', ':').split(':')
        if len(row["SNPS"]) == 4:
            HGVS = True
            chrom, pos, ref, alt = row["SNPS"]
            chrom = str(chrom).replace('chr', '')
            try:
                snps = [get_hgvs_from_vcf(chrom, pos, ref, alt)]
            except ValueError:
                logging.warning(row["SNPS"])
        else:
            logging.warning(row["SNPS"])
    return (snps, seperator)


def load_data(data_folder):
    input_file = os.path.join(data_folder, "alternative")
    assert os.path.exists(input_file), "Can't find input file '%s'" % input_file
    with open_anyfile(input_file) as in_f:

        # Remove duplicated lines if any
        header = next(in_f).strip().split('\t')
        lines = set(list(in_f))
        reader = DictReader(lines, fieldnames=header, delimiter='\t')
        results = defaultdict(list)
        rsid_list = []
        for row in reader:
            rsids, _ = parse_separator_and_snps(row)
            if rsids:
                rsid_list += rsids
        hgvs_rsid_dict = batch_query_hgvs_from_rsid(rsid_list)
        reader = DictReader(lines, fieldnames=header, delimiter='\t')
        for row in reader:
            variant = {}
            HGVS = False
            snps, seperator = parse_separator_and_snps(row)
            if not snps:
                continue
            region = reorganize_field(row["REGION"], seperator, len(snps))
            chrom = reorganize_field(row["CHR_ID"], seperator, len(snps))
            genes = reorganize_field(row["REPORTED GENE(S)"],
                                     seperator,
                                     len(snps))
            position = reorganize_field(row["CHR_POS"],
                                        seperator,
                                        len(snps))
            context = reorganize_field(row["CONTEXT"],
                                       seperator,
                                       len(snps))
            for i, _snp in enumerate(snps):
                variant = {}
                if _snp in hgvs_rsid_dict:
                    variant["_id"] = hgvs_rsid_dict[_snp]
                else:
                    continue
                variant['gwascatalog'] = {"associations": {'efo': {}, 'study': {}}}
                if not HGVS:
                    variant["gwascatalog"]["rsid"] = _snp
                variant['gwascatalog']['associations']['snps'] = snps
                variant['gwascatalog']['associations']['pubmed'] = int(row['PUBMEDID'])
                variant['gwascatalog']['associations']['date_added'] = row['DATE ADDED TO CATALOG']
                variant['gwascatalog']['associations']['study']['name'] = row['STUDY']
                variant['gwascatalog']['associations']['trait'] = row['DISEASE/TRAIT']
                variant['gwascatalog']['region'] = region[i] if region else None
                if not chrom:
                    chrom = [''] * 10
                elif str(chrom[i]).lower() not in CHROM_LIST:
                    chrom[i] = ''
                variant['gwascatalog']['chrom'] = chrom[i] if chrom else None
                variant['gwascatalog']['pos'] = position[i] if position else None
                variant['gwascatalog']['gene'] = genes[i].split(',') if (genes and genes[i]) else None
                variant['gwascatalog']['context'] = context[i] if context else None
                variant['gwascatalog']['associations']['raf'] = str2float(row['RISK ALLELE FREQUENCY'])
                variant['gwascatalog']['associations']['pval'] = str2float(row['P-VALUE'])
                # variant['gwascatalog']['p_val_mlog'] = str2float(row['PVALUE_MLOG'])
                variant['gwascatalog']['associations']['study']['platform'] = row['PLATFORM [SNPS PASSING QC]']
                variant['gwascatalog']['associations']['study']['accession'] = row['STUDY ACCESSION']
                variant['gwascatalog']['associations']['efo']['name'] = row['MAPPED_TRAIT'].split(',')
                variant['gwascatalog']['associations']['efo']['id'] = [_item.split('/')[-1].replace('_', ':') for _item in row['MAPPED_TRAIT_URI'].split(',')]
                variant = dict_sweep(unlist(value_convert_to_number(variant, skipped_keys=['chrom'])), vals=[[], {}, None, '', 'NR'])
                results[variant["_id"]].append(variant)
        for v in results.values():
            if len(v) == 1:
                yield v[0]
            else:
                doc = {'_id': v[0]['_id'],
                       'gwascatalog': {'associations': []}}
                for _item in ['gene', 'region', 'pos', 'context', 'rsid']:
                    if _item in v[0]['gwascatalog']:
                        doc['gwascatalog'][_item] = v[0]['gwascatalog'][_item]
                doc['gwascatalog']['associations'] = [i['gwascatalog']['associations'] for i in v]
                yield doc
