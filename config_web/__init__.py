# import os

from . import agr
from . import biggim  # use plugin "biggim_kp"
from . import biggim_drugresponse_kp  # use plugin "BigGIM_Parser"
from . import bindingdb  # use plugin "BindingDB"
from . import biomuta
from . import bioplanet_pathway_disease
from . import bioplanet_pathway_gene
from . import ccle
from . import cell_ontology
from . import chebi
from . import clinicaltrials_gov
# from . import cord_anatomy
# from . import cord_bp
# from . import cord_cc
# from . import cord_chemical
# from . import cord_cell
# from . import cord_disease
# from . import cord_gene
# from . import cord_genomic_entity
# from . import cord_ma
# from . import cord_protein
from . import ddinter
from . import denovodb
from . import dgidb  # use plugin "DGIdb"
from . import diseases
from . import doid
from . import ebigene2phenotype  # use plugin "ebi_gene2phenotype"
# from . import fire
from . import foodb  # use plugin "foodb_json"
from . import fooddata  # use plugin "FoodData_parser"
from . import geneset  # use plugin "geneset1"
from . import go
from . import go_bp
from . import go_cc
from . import go_mf
from . import gtrx
from . import gwascatalog
from . import hmdb  # use plugin "prot_meta_assc_hmdb"
from . import hpo
from . import idisk
from . import innatedb
from . import kaviar
from . import mgigene2phenotype  # use plugin "mgi_gene2phenotype"
from . import mondo
from . import mrcoc  # use plugin "bte_filter"
from . import multiomics_clinicaltrials_kp
from . import multiomics_ehr_risk_kp  # use plugin "clinical_risk_kp"
from . import multiomics_wellness
from . import ncit
from . import node_expansion  # an integration of 'pending-go', 'pending-doid', 'pending-mondo', 'pending-chebi'
from . import pfocr
from . import phewas
from . import pseudocap_go
from . import rare_source
from . import repodb
from . import rhea
# from . import semmed
# from . import semmed_anatomy  # use plugin "semmedana"
# from . import semmedbp
# from . import semmedchemical
from . import semmeddb
# from . import semmedgene
# from . import semmedphenotype  # use plugin "semmedphen"
from . import suppkg
from . import tcga_mut_freq_kp
# from . import text_mining_co_occurrence_kp
from . import text_mining_targeted_association
from . import tissues
from . import ttd  # use plugin "BioThings_TTD_Dataplugin"
from . import uberon
from . import umlschem
from . import upheno_ontology

# Default Opentelemetry Settings
OPENTELEMETRY_ENABLED = False
OPENTELEMETRY_SERVICE_NAME = "Service Provider"
OPENTELEMETRY_JAEGER_HOST = "localhost"
OPENTELEMETRY_JAEGER_PORT = 6831
