import pytest

import ebird_taxonomy_parse as etp
import banding_code_parse as bcp
from pathlib import Path

test_path = Path("input_parsing")

fn = test_path / Path("eBird_Taxonomy_v2021.csv")
csv_common, csv_scientific, csv_code, csv_short, csv_band = etp.taxonomy_parse(fn)
api_common, api_scientific, api_code, api_short, api_band = etp.taxonomy_parse("")

csv_common_name_mappings = {k: v.short_codes for k, v in csv_common.items()}
csv_scientific_name_mappings = {k: v.scientific_code for k, v in csv_scientific.items()}

api_common_name_mappings = {k: v.short_codes for k, v in api_common.items()}
api_scientific_name_mappings = {k: v.scientific_code for k, v in api_scientific.items()}

csv_filename = test_path / Path("IBP-AOS-LIST21.csv")
banding_mapping = bcp.common_name_to_banding(csv_filename)
downloader_banding_mapping = bcp.common_name_to_banding("")
banding_mapping_all = bcp.common_name_to_banding(csv_filename, True)
api_banding_mapping = {v.common_name: k for k, v in api_band.items()}


@pytest.mark.parametrize(
    "input_data", [csv_common_name_mappings, api_common_name_mappings]
)
@pytest.mark.parametrize(
    "name, codes",
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
        # Special yellow-rumped warbler code.
        ("Yellow-rumped Warbler", ["YRWA", "MYWA", "AUWA"]),
        # Test non-ascii normalization
        ("Rüppell's Bustard", ["RUBU"]),
        ("Sjöstedt's Owlet", ["SJOW"]),
    ],
)
def test_ebird(name, codes, input_data):
    assert set(codes) == set(input_data[name])


@pytest.mark.parametrize(
    "input_data", [banding_mapping, api_banding_mapping, downloader_banding_mapping]
)
@pytest.mark.parametrize(
    "name, code",
    [
        ("Barn Owl", "BANO"),
        ("Barred Owl", "BADO"),
        ("Bank Swallow", "BANS"),
        ("Barn Swallow", "BARS"),
        ("Eurasian Collared-Dove", "EUCD"),
    ],
)
def test_banding_included(name, code, input_data):
    assert input_data[name] == code


@pytest.mark.parametrize(
    "input_data", [banding_mapping, api_banding_mapping, downloader_banding_mapping]
)
@pytest.mark.parametrize(
    "name",
    [
        ("Western X Mountain Bluebird Hybrid"),
        ("Slate-colored Junco"),
        ("Unidentified Swallow"),
        ("Cackling/Canada Goose"),
        ("Unidentified Bird"),
    ],
)
def test_banding_excluded(name, input_data):
    assert name not in input_data.keys()


@pytest.mark.parametrize(
    "name",
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
@pytest.mark.parametrize(
    "input_data", [csv_scientific_name_mappings, api_scientific_name_mappings]
)
@pytest.mark.parametrize(
    "scientific_name, all_codes",
    [
        ("Setophaga coronata", ["SECO"]),
        ("Mareca strepera", ["MAST"]),
        ("Tringa semipalmata", ["TRSE"]),
        ("Tringa erythropus", ["TRER"]),
        ("Passer domesticus", ["PADO"]),
        ("Sterna hirundo", ["STHI"]),
        ("Agelaius phoeniceus", ["AGPH"]),
        ("Stercorarius maccormicki", ["STMA"]),
        ("Stercorarius longicaudus", ["STLO"]),
        ("Streptopelia decaocto", ["STDE"]),
        ("Calocitta colliei", ["CACO"]),
        ("Fregetta tropica", ["FRTR"]),
        ("Setophaga virens", ["SEVI"]),
        ("Knipolegus aterrimus", ["KNAT"]),
        ("Tockus deckeni", ["TODE"]),
        ("Bycanistes subcylindricus", ["BYSU"]),
        ("Pteridophora alberti", ["PTAL"]),
    ],
)
def test_ebird_scientific(scientific_name, all_codes, input_data):
    assert set(all_codes) == set(input_data[scientific_name])
