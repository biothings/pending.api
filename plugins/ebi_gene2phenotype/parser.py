import csv
import io
import json
import glob
import sys
import os.path
from datetime import datetime


def load_data(data_folder):
    dt1 = load_csv(data_folder, "CancerG2P_*_*_*.csv")
    dt2 = load_csv(data_folder, "DDG2P_*_*_*.csv")

    props_names = clean_headers(dt1[0])
    dt1_cleaned = clean_csv_data(dt1[1:])
    dt2_cleaned = clean_csv_data(dt2[1:])

    dt = dt1_cleaned + dt2_cleaned
    result_dict = parse_data(dt, props_names)

    for v in result_dict.values():
        yield v

def load_csv(data_folder, pattern):
    files = glob.glob(os.path.join(data_folder, pattern))
    if files:
        with open(files[0], 'r') as f:
            return list(csv.reader(f))
    else:
        raise FileNotFoundError(f"Can't find input file matching pattern {pattern}")

def clean_headers(headers):
    return [name.replace(' ', '_') for name in headers]

def clean_csv_data(rows):
    for row in rows:
        if row[1] == 'No gene mim':
            row[1] = ''
        if row[3] == 'No disease mim':
            row[3] = ''
    return rows

def parse_data(data, headers):
    result_dict = {}
    for row in data:
        dict_gene = parse_row(row, headers)
        id_key = int(row[12])
        if id_key in result_dict:
            result_dict[id_key]['gene2phenotype'].append(dict_gene)
        else:
            result_dict[id_key] = {
                "_id": row[12],
                "gene2phenotype": [dict_gene]
            }
    return result_dict

def parse_row(row, headers):
    dict_gene = {}
    for y, cell in enumerate(row):
        if cell != '':
            if y in {2, 3}:
                if 'disease' not in dict_gene:
                    dict_gene['disease'] = {}
                dict_gene['disease'][headers[y]] = cell
            elif y in {7, 8, 11}:
                dict_gene[headers[y]] = cell.split(';')
            elif y == 9:
                dict_gene[headers[y]] = [int(x) for x in cell.split(';')]
            elif y == 13:
                if cell != 'No date':
                    dict_gene[headers[y]] = datetime.strptime(cell, '%Y-%m-%d %H:%M:%S').isoformat()
            elif y != 12:
                dict_gene[headers[y]] = cell
    return dict_gene


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
