import pytest
from ebird_lookup import (
    TypeSenseSearch,
    MeilisearchSearch,
    PopulateTaxonomyError,
)
from ebird_stuff.ebird.datamodel import eBirdTaxonomy
import json
from pathlib import Path

data_path = Path("input_parsing")

with open(data_path / "all_common.json", "r") as f:
    ebird_data = json.load(f)

with open(data_path / "banding.json", "r") as f:
    banding_data = json.load(f)

test = eBirdTaxonomy(ebird_data, banding_data)
typesense = TypeSenseSearch(api_key="changeMe!", taxonomy=test)
typesense.connect()
fresh = False

if fresh:
    typesense.client.collections["taxonomy"].delete()
try:
    typesense.populate_taxonomy()
except Exception:
    print("Taxonomy already existing, skipping.")
    pass

meili = MeilisearchSearch(api_key="changeMe!", taxonomy=test)
meili.connect()
meili.populate_taxonomy()


@pytest.mark.parametrize(
    "backend",
    [test, typesense, meili],
)
# Note that these tests assume correct data from the input files, and are only testing correct operation.
@pytest.mark.parametrize(
    "name, short_codes, species_code, sci_name, mode",
    [
        ("Red-winged Blackbird", ["RWBL"], "rewbla", "Agelaius phoeniceus", "single"),
        ("Red-winged Blackbird", ["RWBL"], "rewbla", "Agelaius phoeniceus", "all"),
        (
            "Eurasian Collared-Dove",
            ["EUCD", "ECDO"],
            "eucdov",
            "Streptopelia decaocto",
            "all",
        ),
        (
            "Eurasian Collared-Dove",
            ["EUCD"],
            "eucdov",
            "Streptopelia decaocto",
            "banding",
        ),
        (
            "Eurasian Collared-Dove",
            ["EUCD"],
            "eucdov",
            "Streptopelia decaocto",
            "single",
        ),
        ("potatoebird", [], None, None, "single"),
    ],
)
def test_name_to_codes(name, short_codes, species_code, sci_name, mode, backend):
    res = backend.name_to_codes(name, mode)
    assert res["name"] == name
    assert res["short_codes"] == short_codes
    assert res["species_code"] == species_code
    assert res["scientific_name"] == sci_name


@pytest.mark.parametrize("name", ["Bushtit"])
def test_typesense(name):
    res = typesense.search_name(name)
    print(res)


@pytest.mark.parametrize(
    "backend",
    [typesense, meili],
)
@pytest.mark.parametrize(
    "name, codes",
    [
        ("Bushtit", ["BUSH"]),
        ("Eurasian Collared-Dove", ["EUCD"]),
        # ("stonks", ["WTST"]),  # White-tailed Stonechat.
        ("qwerty", []),
        ("Emu", ["EMU"]),
        ("Smew", ["SMEW"]),
        ("smew", ["SMEW"]),
        # Make sure short code has been normalized.
        ("Rüppell's Bustard", ["RUBU"]),
    ],
)
def test_name_lookup(name, codes, backend):
    res = backend.name_to_codes(name)
    print(res)
    assert res["short_codes"] == codes


@pytest.mark.parametrize(
    "backend",
    [typesense, meili],
)
@pytest.mark.parametrize(
    "code, names",
    [
        ("BUSH", ["Bushtit", "Burmese Shrike", "Buller's Shearwater"]),
        ("EUCD", ["Eurasian Collared-Dove"]),
        ("ECDO", ["Enggano Cuckoo-Dove", "Eurasian Collared-Dove"]),
        ("TEST", ["Temminck's Stint"]),
        ("WETA", ["Western Tanager", "White-eared Tailorbird"]),
        ("XXXX", []),
        ("QWERTY", []),
        ("EMU", ["Emu"]),
        ("Smew", ["Smew"]),
        ("smew", ["Smew"]),
        ("potato", []),
    ],
)
def test_code_lookup(code, names, backend):
    res = backend.code_to_names(code)
    print(res)
    assert set(res["names"]) == set(names)


@pytest.mark.parametrize(
    "backend",
    [typesense, meili],
)
@pytest.mark.parametrize(
    "name, common_name",
    [
        # For the Verreaux's test, any of the possibilities are valid.
        ("Red-winged Blackbird", "Red-winged Blackbird"),
        ("Red winged Blackbird", "Red-winged Blackbird"),
        # ("Redwinged Blackbird", "Red-winged Blackbird"),  # is this reasonable?
        # ("Red-wing Blackbird", "Red-winged Blackbird"),
        (
            "Verreaux's",
            [
                "Verreaux's Batis",
                "Verreaux's Eagle-Owl",
                "Verreaux's Coua",
                "Verreaux's Eagle",
            ],
        ),
        (
            "Verreauxs",
            [
                "Verreaux's Batis",
                "Verreaux's Eagle-Owl",
                "Verreaux's Coua",
                "Verreaux's Eagle",
            ],
        ),
        ("St. Helena Rail", "St. Helena Rail"),
        ("St Helena Rail", "St. Helena Rail"),
        ("Grey Partridge", "Gray Partridge"),
        # Make sure we can search without the non-ascii characters.
        ("Ruppell's Bustard", "Rüppell's Bustard"),
        ("Sjostedt's Owlet", "Sjöstedt's Owlet"),
        ("Maranon Crescentchest", "Marañon Crescentchest"),
        ("Oberlander's Ground-Thrush", "Oberländer's Ground-Thrush"),
        # What if there are a few errors?
        # ("oberlander ground thrush", "Oberländer's Ground-Thrush"),
        # ("oberlanders thrush", "Oberländer's Ground-Thrush"),
    ],
)
def test_typesense_punct(name, common_name, backend):
    res = backend.name_to_codes(name)
    print(res)
    assert res["name"] in common_name


def test_short_names():
    assert test.short_names == ["Emu", "Kea", "Tui", "Mao", "Ou"]


@pytest.mark.parametrize(
    "backend",
    [TypeSenseSearch, MeilisearchSearch],
)
def test_populate_exception(backend):
    t = backend(api_key="doesn't matter for this test")
    with pytest.raises(PopulateTaxonomyError):
        t.populate_taxonomy()
