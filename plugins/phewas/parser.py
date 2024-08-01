import os
from collections import defaultdict
from biothings_client import get_client
import re

from csv import DictReader
from biothings.utils.dataload import dict_sweep, open_anyfile, unlist, value_convert_to_number


def batch_query_hgvs_from_rsid(rsid_list):
    hgvs_rsid_dict = {}
    print('total rsids: {}'.format(len(rsid_list)))
    rsid_list = list(set(rsid_list))
    variant_client = get_client('variant')
    for i in range(0, len(rsid_list), 1000):
        if i + 1000 <= len(rsid_list):
            batch = rsid_list[i: i+1000]
        else:
            batch = rsid_list[i:]
        params = ','.join(batch)
        res = variant_client.getvariants(params, fields="_id")
        print("currently processing {}th variant".format(i))
        for _doc in res:
            if '_id' not in _doc:
                print('can not convert', _doc)
            hgvs_rsid_dict[_doc['query']] = _doc['_id'] if '_id' in _doc else _doc["query"]
    return hgvs_rsid_dict


def load_data(data_folder):

    input_file = os.path.join(data_folder, "phewas-catalog.csv")
    assert os.path.exists(input_file), "Can't find input file '%s'" % input_file
    with open_anyfile(input_file) as in_f:

        # Remove duplicated lines if any
        header = next(in_f).strip().split(',')
        header = [_item[1:-1] for _item in header]
        lines = set(list(in_f))
        reader = DictReader(lines, fieldnames=header, delimiter=',')

        results = defaultdict(list)
        for row in reader:
            variant = {"associations": {"phenotype": {}}, "variant": {}}
            assert re.match("^rs\d+$", row["snp"]) != None
            variant["variant"]["rsid"] = row["snp"]
            variant["associations"]["phenotype"]["name"] = row["phewas phenotype"]
            variant["associations"]["cases"] = row["cases"]

            variant["associations"]["pval"] = float(row["p-value"])
            variant["associations"]["odds-ratio"] = row["odds-ratio"]
            variant["associations"]["phenotype"]["phewas_code"] = row["phewas code"]
            variant["variant"]["gene"] = row["gene_name"]
            variant["variant"]["gwas_associations"] = row["gwas-associations"].split(',')
            pos_info = row["chromosome"].split(' ')
            if len(pos_info) == 2:
                variant["variant"]["chrom"], variant["variant"]["pos"] = pos_info
            else:
                variant["variant"]["chrom"] = pos_info[0]
            results[variant["variant"]["rsid"]].append(variant)
        # Merge duplications
        rsid_list = [_item for _item in results.keys()]
        hgvs_rsid_dict = batch_query_hgvs_from_rsid(rsid_list)
        for k, v in results.items():
            if k in hgvs_rsid_dict and hgvs_rsid_dict[k]:
                if len(v) == 1:
                    doc = {'_id': hgvs_rsid_dict[k],
                           'phewas': v[0]["variant"]}
                    doc["phewas"]["associations"] = v[0]["associations"]
                    yield dict_sweep(unlist(value_convert_to_number(doc, skipped_keys=['chrom'])), vals=[[], {}, None, '', 'NULL'])
                else:
                    doc = {'_id': hgvs_rsid_dict[k],
                           'phewas': v[0]["variant"]}
                    doc["phewas"]["associations"] = []
                    for _item in v:
                        doc["phewas"]["associations"].append(_item["associations"])
                    yield dict_sweep(unlist(value_convert_to_number(doc, skipped_keys=['chrom'])), vals=[[], {}, None, '', 'NULL'])
