import pytest

import ebird_taxonomy_parse as etp

fn = "eBird_Taxonomy_v2018_14Aug2018.csv"
common_name_mappings = etp.parse_raw_ebird_to_4lc(fn)


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
    assert set(codes).issubset(common_name_mappings[name])
