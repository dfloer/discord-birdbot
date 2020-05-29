import pytest

import ebird_taxonomy_parse as etp
import banding_code_parse as bcp

fn = "eBird_Taxonomy_v2019.csv"
common, scientific, code, short = etp.taxonomy_parse(fn)
common_name_mappings = {k: v.short_codes for k, v in common.items()}
scientific_name_mappings = {k: v.short_codes for k, v in scientific.items()}

csv_filename = "list19p.csv"
banding_mapping = bcp.common_name_to_banding(csv_filename)
banding_mapping_all = bcp.common_name_to_banding(csv_filename, True)


@pytest.mark.parametrize("name, codes",
    [
        # Single word names
        ("Gadwall", ["GADW"]),
        ("Willet", ["WILL"]),
        # Two word names
        ("Spotted Redshank", ["SPRE"]),
        ("House Sparrow", ["HOSP"]),
        ("Common Tern", ["COTE"]),
        # Three word names
        ("Red-winged Blackbird", ["RWBL"]),
        ("South Polar Skua", ["SPSK"]),
        ("Long-tailed Jaeger", ["LTJA"]),
        # Alternate hyphenation rules.
        ("Eurasian Collared-Dove", ["ECDO", "EUCD"]),
        # Four worded names.
        ("Black-throated Magpie-Jay", ["BTMJ"]),
        ("Black-bellied Storm-Petrel", ["BBSP"]),
        ("Black-throated Green Warbler", ["BTGW"]),
        ("White-winged Black-Tyrant", ["WWBT"]),
        ("Von der Decken's Hornbill", ["VDDH"]),
        # >4 word names and their alternate forms.
        ("Black-and-white-casqued Hornbill", ["BAWC", "BWCH"]),
        ("King-of-Saxony Bird-of-Paradise", ["KOSB", "KSBP"]),
        # These include the binomial/scientific name tests.
        ("American Robin", ["AMRO", "TUMI"]),
        ("Rough-legged Hawk", ["BULA", "RLHA"]),
        ("Lesser Rhea", ["LERH", "RHPE"]),
        ("Graylag Goose", ["GRGO", "ANAN"]),
        ("Townsend's Warbler", ["TOWA", "SETO"]),
        ("Hermit Warbler", ["HEWA", "SEOC"]),
        # Special yellow-rumped warbler code.
        ("Yellow-rumped Warbler (Myrtle)", ["YRWA", "MYWA"]),
        ("Yellow-rumped Warbler (Audubon's)", ["YRWA", "AUWA"]),
    ],
)
def test_ebird(name, codes):
    assert set(codes) == set(common_name_mappings[name])


@pytest.mark.parametrize("name, code",
    [
        ("Barn Owl", "BANO"),
        ("Barred Owl", "BADO"),
        ("Bank Swallow", "BANS"),
        ("Barn Swallow", "BARS"),
        ("Eurasian Collared-Dove", "EUCD"),
    ],
)
def test_banding_included(name, code):
    assert banding_mapping[name] == code


@pytest.mark.parametrize("name",
    [
        ("Western X Mountain Bluebird Hybrid"),
        ("Slate-colored Junco"),
        ("Unidentified Swallow"),
        ("Cackling/Canada Goose"),
        ("Unidentified Bird"),
    ],
)
def test_banding_excluded(name):
    assert name not in banding_mapping.keys()

@pytest.mark.parametrize("name",
    [
        ("Western X Mountain Bluebird Hybrid"),
        ("Slate-colored Junco"),
        ("Unidentified Swallow"),
        ("Cackling/Canada Goose"),
        ("Unidentified Bird"),
    ],
)
def test_banding_all(name):
    assert name in banding_mapping_all.keys()

# And now the same test for scientific names.
@pytest.mark.parametrize("scientific_name, all_codes",
    [
        ("Setophaga coronata", ["YRWA", "MYWA", "AUWA", "SECO"]),
        ("Mareca strepera", ["GADW", "MAST"]),
        ("Tringa semipalmata", ["WILL", "TRSE"]),
        ("Tringa erythropus", ["SPRE", "TRER"]),
        ("Passer domesticus", ["HOSP", "PADO"]),
        ("Sterna hirundo", ["COTE", "STHI"]),
        ("Agelaius phoeniceus", ["RWBL", "AGPH"]),
        ("Stercorarius maccormicki", ["SPSK", "STMA"]),
        ("Stercorarius longicaudus", ["LTJA", "STLO"]),
        ("Streptopelia decaocto", ["ECDO", "EUCD", "STDE"]),
        ("Calocitta colliei", ["BTMJ", "BLMJ", "CACO"]),
        ("Fregetta tropica", ["BBSP", "BLSP", "FRTR"]),
        ("Setophaga virens", ["BTGW", "SEVI"]),
        ("Knipolegus aterrimus", ["WWBT", "WHBT", "KNAT"]),
        ("Tockus deckeni", ["VDDH", "TODE"]),
        ("Bycanistes subcylindricus", ["BAWC", "BWCH", "BYSU"]),
        ("Pteridophora alberti", ["KOSB", "KSBP", "PTAL"]),
    ],
)
def test_ebird(scientific_name, all_codes):
    assert set(all_codes) == set(scientific_name_mappings[scientific_name])
