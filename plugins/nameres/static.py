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


NAMERES_UPLOAD_CHUNKS = {
    "AnatomicalEntity.txt": 10,
    "BiologicalProcess.txt": 5,
    "Cell.txt": 1,
    "CellLine.txt": 1,
    "CellularComponent.txt": 1,
    "Disease.txt": 10,
    "DrugChemicalConflated.txt": 75,
    "GeneFamily.txt": 1,
    "GeneProteinConflated.txt": 100,
    "GrossAnatomicalStructure.txt": 1,
    "MacromolecularComplex.txt": 1,
    "MolecularActivity.txt": 10,
    "OrganismTaxon.txt": 10,
    "Pathway.txt": 5,
    "PhenotypicFeature.txt": 10,
    "Publication.txt": 1,
    "umls.txt": 10,
}
