import pandas as pd
import os

def load_annotations(data_folder):
	"""Load annotations function
	
	Use tsv file to format hp ids, label, mp ids, labels, and scores
	Information on tsv columns can be found at: 
	https://github.com/obophenotype/upheno/blob/master/mappings/README.md
	"""
	url = os.path.join(data_folder,"hp-to-mp-bestmatches.tsv")
	ontology_df = pd.read_csv(url, sep="\t", header = None)
	for row in ontology_df.itertuples():
		current_item = {
			"_id": row[1], # HP Class ID
			"hp_class_label": row[2], # HP Class Label
			"mp_class_id": row[3], # Other ontology class ID
			"mp_ontology_class_label": row[4], # Other ontology class Label 
			"fuzzy_equivalence_score": row[5], # Fuzzy equivalence score
			"fuzzy_subclass_score": row[6] # Fuzzy SubClass score	
		}
		yield(current_item)