"""
Static defintions for urls and file locations
"""

CONFLATION_LOOKUP_DATABASE = "conflation.sqlite3"
IDENTIFIER_LOOKUP_DATABASE = "identifier.sqlite3"
PRIOR_URL = [
    "https://stars.renci.org/var/babel_outputs/2025mar31/",
    "https://stars.renci.org/var/babel_outputs/2025jan23",
]
BASE_URL = "https://stars.renci.org/var/babel_outputs/2025sep1/"


NODENORM_FILE_COLLECTION = [
    "AnatomicalEntity.txt",
    "BiologicalProcess.txt",
    "Cell.txt",
    "CellularComponent.txt",
    "ChemicalEntity.txt",
    "ChemicalMixture.txt",
    "ComplexMolecularMixture.txt",
    "Disease.txt",
    "Drug.txt",
    "GeneFamily.txt",
    "GrossAnatomicalStructure.txt",
    "MacromolecularComplex.txt",
    "MolecularActivity.txt",
    "OrganismTaxon.txt",
    "Pathway.txt",
    "PhenotypicFeature.txt",
    "Polypeptide.txt",
    "umls.txt",
]

NODENORM_CONFLATION_COLLECTION = ["DrugChemical.txt", "GeneProtein.txt"]


NODENORM_BIG_FILE_COLLECTION = {
    "MolecularMixture.txt": 50,
    "Gene.txt": 75,
    "Publication.txt": 100,
    "SmallMolecule.txt": 150,
    "Protein.txt": 200,
}

DRUG_CHEMICAL_IDENTIFIER_FILES = [
    "Drug.txt",
    "ChemicalEntity.txt",
    "SmallMolecule.txt",
    "ComplexMolecularMixture.txt",
    "MolecularMixture.txt",
    "Protein.txt",
]


GENE_PROTEIN_IDENTIFER_FILES = ["Protein.txt", "Gene.txt"]


NODENORM_UPLOAD_CHUNKS = {
    "AnatomicalEntity.txt": 1,
    "BiologicalProcess.txt": 1,
    "Cell.txt": 1,
    "CellularComponent.txt": 1,
    "ChemicalEntity.txt": 10,
    "ChemicalMixture.txt": 1,
    "ComplexMolecularMixture.txt": 1,
    "Disease.txt": 10,
    "Drug.txt": 10,
    "Gene.txt": 30,
    "GeneFamily.txt": 1,
    "GrossAnatomicalStructure.txt": 1,
    "MacromolecularComplex.txt": 1,
    "MolecularActivity.txt": 10,
    "MolecularMixture.txt": 30,
    "OrganismTaxon.txt": 10,
    "Pathway.txt": 1,
    "PhenotypicFeature.txt": 10,
    "Polypeptide.txt": 1,
    "Protein.txt": 50,
    "Publication.txt": 30,
    "SmallMolecule.txt": 40,
    "umls.txt": 10,
}
