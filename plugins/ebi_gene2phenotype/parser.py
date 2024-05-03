import csv
import io
import json
import glob
import sys
import os.path
from datetime import datetime


def load_data(data_folder):
    # Find files matching the first pattern
    files = glob.glob(os.path.join(data_folder, "CancerG2P_*_*_*.csv"))
    if files:
        dt1 = list(csv.reader(open(files[0])))
    else:
        raise FileNotFoundError("Can't find input file matching pattern CancerG2P_*_*_*.csv")

    # Find files matching the second pattern
    files = glob.glob(os.path.join(data_folder, "DDG2P_*_*_*.csv"))
    if files:
        dt2 = list(csv.reader(open(files[0])))
    else:
        raise FileNotFoundError("Can't find input file matching pattern DDG2P_*_*_*.csv")

    # clean data
    props_names = dt1[0]

    for i, name in enumerate(props_names):
        props_names[i] = name.replace(' ', '_')

    dt1_header_removed = dt1[1:]
    dt2_header_removed = dt2[1:]

    def cleanCSV(ls):
        for row in ls:
            if (row[1] == 'No gene mim'):
                row[1] = ''
            if (row[3] == 'No disease mim'):
                row[3] = ''

    cleanCSV(dt1_header_removed)
    cleanCSV(dt2_header_removed)

    dt = dt1_header_removed + dt2_header_removed

    # parse and ignore empty data

    result_dict = {}  # intermediate dict construct, with unique ids

    for x in range(len(dt)):  # of all observations
        dict_gene = {}  # each observation's storage to attach to the 'gene2phenotype' of its unique id in main dict

        for y in range(len(dt[0])):  # of all properties
            if dt[x][y] != '':  # of not empty properties
                if (y == 2 or y == 3):
                    # additional processsing for disease name and mim
                    if 'disease' not in dict_gene:
                        dict_gene['disease'] = {}
                    dict_gene['disease'][props_names[y]] = dt[x][y]
                elif (y == 7 or y == 8 or y == 11): 
                    # additional processing for rgan specificity list , pre symbols, phenotypes
                    dict_gene[props_names[y]] = dt[x][y].split(';')
                elif (y == 9):
                    # additional processing for pmids (list of integers)
                    dict_gene[props_names[y]] = [int(x) for x in dt[x][y].split(';')]
                elif (y == 12):
                    continue
                elif (y == 13):
                    if dt[x][y] != 'No date':
                        dict_gene[props_names[y]] = datetime.strptime(dt[x][y], '%Y-%m-%d %H:%M:%S').isoformat()
                else:
                    dict_gene[props_names[y]] = dt[x][y]

        if int(dt[x][12]) in result_dict:
            list_gene = result_dict[int(dt[x][12])]['gene2phenotype']
            list_gene.append(dict_gene)
            result_dict[int(dt[x][12])]['gene2phenotype'] = list_gene
        else:
            dict_item = {
                "_id": dt[x][12],
                "gene2phenotype": [dict_gene]
            }
            result_dict[int(dt[x][12])] = dict_item

    for v in result_dict.values():
        yield v


if __name__ == "__main__":

    if (len(sys.argv) != 2):
        print('python parser.py <output_file>')
        exit(1)

    result_list = []
    for r in load_data(os.getcwd()):
        result_list.append(r)

    # save to a file
    file = io.open(sys.argv[1], "w", encoding='utf8')
    file.write(json.dumps(result_list, indent=4, sort_keys=True, default=str))
    file.close()
