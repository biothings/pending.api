"""
Within the zip file provided by the FDA there are 11 files.

We don't need all of them but for the one's we do we define a file
structure here to help strictly specify the structure in code

The document we want to construct has the following structure:

[0]  Application Number -> [Products.txt, TE.txt, MarketingStatus.txt, Applications.txt]
[1]  Product Number -> [Products.txt, TE.txt, MarketingStatus.txt, Applications.txt]
[2]  Drug Name -> Products.txt
[3]  Active Ingredients -> Products.txt
[4]  Strength -> Products.txt
[5]  Dosage Form/Route  -> Products.txt
[6]  Marketing Status -> [TE.txt, MarketingStatus.txt] + MarketingStatus_Lookup.txt
[7]  Therapeutic Equivalence Code -> TE.txt
[8]  Reference Level Drug -> Products.txt
[9]  Reference Standard -> Products.txt
[10] Company -> Applications.txt 

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

    ApplNo: str
    ProductNo: str
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

    ApplNo: str
    ProductNo: str
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
    ApplNo: str
    ProductNo: str


NULL_MARKETING_STATUS = MarketingStatusEntry(MarketingStatusID=None, ApplNo=None, ProductNo=None)


@dataclasses.dataclass(frozen=True)
class ApplicationsEntry:
    """
    ==> Applications.txt <==
    ApplNo	ApplType	ApplPublicNotes	             SponsorName
    218158	NDA         FORMOSA PHARMACEUTICALS INC
    218181	ANDA                                     GRAVITI PHARMS
    218182	ANDA                                     TARO
    218193	NDA         MYLAN PHARMS INC
    218194	ANDA                                     AUROBINDO PHARMA
    218197	NDA         ASTRAZENECA
    218213	NDA         BRISTOL
    218221	ANDA                                     BIONPHARMA
    """

    ApplNo: str
    ApplTyp: str
    ApplPublicNotes: str
    SponsorName: str


NULL_APPLICATION = ApplicationsEntry(ApplNo=None, ApplTyp=None, ApplPublicNotes=None, SponsorName=None)
