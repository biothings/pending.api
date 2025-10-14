"""
Static defintions for urls and file locations
"""

CONFLATION_LOOKUP_DATABASE = "conflation.sqlite3"
PRIOR_URL = []
BASE_URL = "https://stars.renci.org/var/babel_outputs/2025sep1/"


SYNONYM_FILE_COLLECTION = [
    "AnatomicalEntity.txt",
    "BiologicalProcess.txt",
    "Cell.txt",
    "CellLine.txt",
    "CellularComponent.txt",
    "Disease.txt",
    "GeneFamily.txt",
    "GrossAnatomicalStructure.txt",
    "MacromolecularComplex.txt",
    "MolecularActivity.txt",
    "OrganismTaxon.txt",
    "Pathway.txt",
    "PhenotypicFeature.txt",
    "Publication.txt",
    "umls.txt",
]

SYNONYM_BIG_FILE_COLLECTION = {
    "DrugChemicalConflated.txt": 50,
    "GeneProteinConflated.txt": 50,
}
