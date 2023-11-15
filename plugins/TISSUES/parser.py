"""
TISSUES Data Parser 
For biothings.pending.api 
Original Version Written by: Nichollette A.
"""

# import our packages
import biothings.utils.dataload as dl   
import glob
import os
from itertools import groupby
from operator import itemgetter
#import json # import when testing

def load_tm_data(datafiles):
    """
    Load text mining data -- note we only add human data
    input:
        - filepath: input tsv file
    returns:
        - json_docs: list of records generated from input file
    """

    json_docs = []
    for file in datafiles:
        datalist=dl.tab2list(file, (0,1,2,3,4,5,6)) # load into biothings
        for row in datalist:
            row_dict={}
            row_dict['ensembl']=row[0]
            row_dict['symbol']=row[1]
            row_dict['tissue_identifier']=row[2]
            row_dict['tissue_name']=row[3]
            row_dict['zscore'] = row[4]
            row_dict['confidence'] = row[5]
            row_dict['category'] = 'textmining'
            json_docs.append(row_dict)
    return json_docs


def load_ep_kn_data(datafiles, category):
    """ 
    Load data from the experiments or knowledge file
    Note - the experiments file and the knowledge file share the same column names
    input:
        - datafiles: data 
        - category: the category of the file, should be either experiments or knowledge
    """

    json_docs = []

    for file in datafiles:
        datalist=dl.tab2list(file, (0,1,2,3,4,5,6)) # load into biothings

        for row in datalist:
            row_dict={
                "ensembl":row[0],
                "symbol": row[1],
                "tissue_identifier": row[2],
                "tissue_name": row[3],
                "source": row[4], 
                "expression": row[5],
                "confidence": row[6],
                "category": category
            }
            json_docs.append(row_dict)
    return json_docs

def load_data(data_folder):
    """
    Main data load function
    input:
        - data_folder: folder storing downloaded files
    """

    print("\n[INFO] Loading TISSUE data ....")

    kn_files=glob.glob(os.path.join(data_folder, "*human*_tissue_knowledge_full.tsv"))
    #print("[INFO] %s knowledge files found."%(len(kn_files)))#, kn_files))
    tm_files=glob.glob(os.path.join(data_folder, "*human*_tissue_textmining_full.tsv"))
    #print("[INFO] %s text mining files found."%(len(tm_files)))#, tm_files))
    ex_files=glob.glob(os.path.join(data_folder, "*human*_tissue_experiments_full.tsv"))
    #print("[INFO] %s experiments files found."%(len(ex_files)))#, ex_files))

    json_docs=load_tm_data(tm_files) + load_ep_kn_data(ex_files,  "experiments")+load_ep_kn_data(kn_files, "knowledge")
    sorted_doc=sorted(json_docs, key=itemgetter('tissue_identifier'))
    docs=sorted_doc
    iterator=groupby(docs, key=itemgetter("tissue_identifier"))

    for key, group in iterator:
        i=0
        for _record in list(group):
            i+=1
            # initialize record
            res = {
                "_id": None,
                "subject": {},
                "association":{},
                "object":{}            
            }

            merged_doc = []

            orig_key=key
            mod_key=orig_key+f"_{i:08d}" # modify key

            res["_id"] = mod_key
            res["subject"]['id'] = orig_key               

            _record.pop("tissue_identifier")
            res["subject"]["name"] = _record["tissue_name"]
            merged_doc.append(_record)
            for mod_key in merged_doc[0].keys():
                if mod_key == "ensembl" or mod_key == "symbol":
                    res['object'][mod_key]=merged_doc[0][mod_key]
                else:
                    res["association"][mod_key]= merged_doc[0][mod_key]
            yield res
