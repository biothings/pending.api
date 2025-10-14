"""
Static defintions for urls and file locations
"""

CONFLATION_LOOKUP_DATABASE = "conflation.sqlite3"
PRIOR_URL = []
BASE_URL = "https://stars.renci.org/var/babel_outputs/2025sep1/"


SYNONYM_FILE_COLLECTION = [
    "AnatomicalEntity.txt.gz",
    "BiologicalProcess.txt.gz",
    "Cell.txt.gz",
    "CellLine.txt.gz",
    "CellularComponent.txt.gz",
    "Disease.txt.gz",
    "GeneFamily.txt.gz",
    "GrossAnatomicalStructure.txt.gz",
    "MacromolecularComplex.txt.gz",
    "MolecularActivity.txt.gz",
    "OrganismTaxon.txt.gz",
    "Pathway.txt.gz",
    "PhenotypicFeature.txt.gz",
    "Publication.txt.gz",
    "umls.txt.gz",
]

SYNONYM_BIG_FILE_COLLECTION = {
    "DrugChemicalConflated.txt.gz": 50,
    "GeneProteinConflated.txt.gz": 50,
}
