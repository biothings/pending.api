"""
Static defintions for urls and file locations
"""

CONFLATION_LOOKUP_DATABASE = "conflation.sqlite3"
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
