"""
Within the zip file provided by the FDA there are 11 files.

We don't need all of them but for the one's we do we define a file
structure here to help strictly specify the structure in code

The document we want to construct has the following structure:
Drug Name	Active Ingredients	Strength	Dosage Form/Route	Marketing Status	TE Code	RLD	RS

[0] Drug Name -> Products.txt
[1] Active Ingredients -> Products.txt
[2] Strength -> Products.txt
[3] Dosage Form/Route  -> Products.txt
[4] Marketing Status -> [TE.txt, MarketingStatusi.txt] + MarketingStatus_Lookup.txt
[5] TE Code -> TE.txt
[6] RLD -> Products.txt
[7] RS -> Products.txt

Naming References:
https://www.fda.gov/drugs/drug-approvals-and-databases/orange-book-data-files
"""

import dataclasses


@dataclasses.dataclass(frozen=True)
class ProductsFileEntry:
    """
    ==> Products.txt <==
    ApplNo  ProductNo Form                      Strength ReferenceDrug DrugName  ActiveIngredient                  ReferenceStandard
    000004  004       SOLUTION/DROPS;OPHTHALMIC 1%       0             PAREDRINE [HYDROXYAMPHETAMINE HYDROBROMIDE] 0
    """

    ApplNo: int
    ProductNo: int
    Form: list[str]
    Strength: list[str]
    ReferenceDrug: bool
    DrugName: str
    ActiveIngredient: str
    ReferenceStandard: bool


NULL_PRODUCT = ProductsFileEntry(
    ApplNo=None,
    ProductNo=None,
    Form=None,
    Strength=None,
    ReferenceDrug=None,
    DrugName=None,
    ActiveIngredient=None,
    ReferenceStandard=None,
)


@dataclasses.dataclass(frozen=True)
class TEFileEntry:
    """
    ==> TE.txt <==
    ApplNo  ProductNo MarketingStatusID TECode
    003444  001       1                 AA
    """

    ApplNo: int
    ProductNo: int
    MarketingStatusID: int
    TECode: str


NULL_TE = TEFileEntry(ApplNo=None, ProductNo=None, MarketingStatusID=None, TECode=None)


@dataclasses.dataclass(frozen=True)
class MarketingStatusEntry:
    """
    ==> TE.txt <==
    MarketingStatusID ApplNo  ProductNo
    3                 000004  004
    """

    MarketingStatusID: int
    ApplNo: int
    ProductNo: str


NULL_MARKETING_STATUS = MarketingStatusEntry(MarketingStatusID=None, ApplNo=None, ProductNo=None)
