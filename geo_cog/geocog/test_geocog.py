import pytest
import io
from .geo_utils import MapBox, Tile, GBIF
from .geo_utils import lat_lon_parse2, get_token

mapbox = MapBox(get_token())
gbif = GBIF()


# @pytest.mark.parametrize(
#     "input, output",
#     [
#         ("+90.0, -127.554334", (90.0, -127.554334)),
#         # ("45, 180", (45.0, 180.0)),
#         # ("-90.000, -180.0", (-90.0, -180.0)),
#         # ("20,80", (20.0, 80.0)),
#         # ("47.1231231, 179.99999999", (47.1231231, 179.99999999)),
#         # ("-90., -180.", (-90.0, -180.0)),
#         # ("045, 180", (45.0, 180.0)),
#         ("45N, 90W", (45.0, -90.0)),
#     ],
# )
# def test_lat_lon_parse(input, output):
#     res = lat_lon_parse2(input)
#     assert res == output


@pytest.mark.parametrize(
    "input_string, output",
    [
        ("Vancouver, Canada", (-123.116838, 49.279862)),
    ],
)
def test_mapbox_geocode(input_string, output):
    res = mapbox.geocode(input_string)
    assert res == output


# @pytest.mark.parametrize(
#     "z, x, y, fmt, style, high_res",
#     [
#         (0, 0, 0, "jpg90", "satellite", False),
#         (6, 40, 44, "jpg90", "satellite", True),
#         (2, 2, 2, "jpg90", "satellite", True),
#     ],
# )
# def test_get_tiles(z, x, y, fmt, style, high_res):
#     res = mapbox.get_tile(z, x, y, fmt, style, high_res)
#     res.save()
#     assert type(res) == Tile


@pytest.mark.parametrize(
    "z, x, y, fmt, style, high_res, taxon_id",
    [
        (0, 0, 0, "jpg90", "satellite", True, 2494988),
        (0, 0, 0, "jpg90", "satellite", True, 9515886),
    ],
)
def test_tile_composite(z, x, y, fmt, style, high_res, taxon_id):
    mb = mapbox.get_tile(z, x, y, fmt, style, high_res)
    gb = gbif.get_hex_map(z, x, y, taxon_id, high_res=False)
    mb.name = f"mb-{taxon_id}"
    gb.name = f"gb-{taxon_id}"
    mb.save()
    gb.save()
    t1 = mb.composite(gb)
    with open("t1b.png", "wb") as f:
        d = io.BytesIO()
        t1.img.save(d, "png")
        f.write(d.getvalue())
    t1.name = f"comp-{taxon_id}"
    t1.save()
    # Do something to make sure the composition worked correctly. Should probably be using saved tiles too.


@pytest.mark.parametrize(
    "species, taxon_id",
    [
        ("Bushtit", ("Psaltriparus minimus", 2494988)),
        ("Barn Swallow", ("Hirundo rustica", 9515886)),
        ("Anna's Hummingbird", ("Calypte anna", 2476674)),
        ("Hirundo rustica", ("Hirundo rustica", 9515886)),
    ],
)
def test_gbif_lookup(species, taxon_id):
    res = gbif.lookup_species(species)
    assert res == taxon_id
