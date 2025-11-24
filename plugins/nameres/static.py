"""
Static defintions for urls and file locations
"""

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


NAMERES_UPLOAD_CHUNKS = {
    "GeneProteinConflated.txt": 100,
    "DrugChemicalConflated.txt": 75,
    "AnatomicalEntity.txt": 10,
    "Disease.txt": 10,
    "umls.txt": 10,
    "PhenotypicFeature.txt": 10,
    "MolecularActivity.txt": 10,
    "OrganismTaxon.txt": 10,
    "Pathway.txt": 5,
    "BiologicalProcess.txt": 5,
    "Cell.txt": 1,
    "CellLine.txt": 1,
    "CellularComponent.txt": 1,
    "GeneFamily.txt": 1,
    "GrossAnatomicalStructure.txt": 1,
    "MacromolecularComplex.txt": 1,
    "Publication.txt": 1,
}
