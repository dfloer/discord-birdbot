import pytest
import io
from .geo_utils import MapBox, Tile, GBIF, eBirdMap, TileID
from .geo_utils import composite_mxn, get_token, composite_quad, comp, find_crop_bounds, find_line_sibling_tiles

# from PIL.Image import Image as Img
import PIL.Image as Img
import mercantile

mapbox = MapBox(get_token())
gbif = GBIF()
ebird = eBirdMap()


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


@pytest.mark.vcr("new")
@pytest.mark.parametrize(
    "z, x, y, fmt, style, high_res, taxon_id",
    [
        (0, 0, 0, "jpg90", "satellite", True, 2494988),
        (0, 0, 0, "jpg90", "satellite", True, 9515886),
        (0, 0, 0, "jpg90", "satellite", True, 2480528),
        (0, 0, 0, "jpg90", "satellite", True, 5228134),
    ],
)
def test_tile_composite(z, x, y, fmt, style, high_res, taxon_id):
    gb = gbif.get_hex_map(z, x, y, taxon_id, high_res=False)[0]
    az, ax, ay = gb.tid
    mb = mapbox.get_tile(z=az, x=ax, y=ay, fmt=fmt, style=style, high_res=high_res)
    mb.name = f"mb-{taxon_id}"
    gb.name = f"gb-{taxon_id}"
    # mb.save()
    # gb.save()
    t1 = mb.composite(gb)
    # with open("t1b.png", "wb") as f:
    #     d = io.BytesIO()
    #     t1.img.save(d, "png")
    #     f.write(d.getvalue())
    t1.name = f"test_tile_comp-{taxon_id}"
    t1.save()
    # Do something to make sure the composition worked correctly. Should probably be using saved tiles too.


@pytest.mark.vcr("new")
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


# Yeah, this shouldn't be here, but it'll get fixed.
mbt = [
    mapbox.get_tile(z=3, x=a, y=b, high_res=False)
    for a, b in [(1, 2), (1, 3), (2, 2), (2, 3)]
]
print("MBT")


@pytest.mark.vcr()
@pytest.mark.parametrize(
    "species_code, zoom, transparancy",
    [
        ("bushti", 3, 200),
        ("bushti", 3, 255),
        ("bushti", 3, 0),
        ("bushti", 3, 64),
        ("bushti", 3, 128),
    ],
)
def test_map_transparency(species_code, zoom, transparancy):
    res = ebird.get_tiles(species_code, zoom)

    ebd_img = composite_quad(res)
    mbt_img = composite_quad(mbt)

    out = comp(mbt_img, ebd_img, transparancy)
    print("n", out)
    with open(f"map_transparency-{species_code}_z{zoom}_{transparancy}.png", "wb") as f:
        out.save(f, "png")


@pytest.mark.vcr()
@pytest.mark.parametrize(
    "species_code, zoom",
    [
        ("bushti", 3),
        ("pilwoo", 3),
        ("inirai1", 0),
        ("bkpwar", 2),
        ("baleag", 1),
        ("grycat", 0),
    ],
)
def test_ebird_map(species_code, zoom):
    out = ebird.get_range_map(species_code, zoom)
    with open(f"ebird_map-{species_code}_{zoom}.png", "wb") as f:
        out.save(f, "png")


@pytest.mark.vcr("new")
@pytest.mark.parametrize(
    "species_code, region, expected_ids",
    [
        ("bushti", "", [(3, 1, 2), (3, 1, 3), (3, 2, 2), (3, 2, 3)]),
        (
            "pilwoo",
            "",
            [(3, 0, 2), (3, 0, 3), (3, 1, 2), (3, 1, 3), (3, 2, 2), (3, 2, 3)],
        ),
        ("inirai1", "", [(8, 118, 155), (8, 118, 156), (8, 119, 155), (8, 119, 156)]),
    ],
)
def test_map_tile_ids(species_code, region, expected_ids):
    tile_ids = ebird.get_bbox(species_code)
    assert [(a.z, a.x, a.y) for a in tile_ids] == expected_ids


@pytest.mark.vcr("new")
@pytest.mark.parametrize(
    "species_code, region, expected_ids",
    [
        ("bushti", "", [(3, 1, 2), (3, 1, 3), (3, 2, 2), (3, 2, 3)]),
        (
            "pilwoo",
            "",
            [(3, 0, 2), (3, 0, 3), (3, 1, 2), (3, 1, 3), (3, 2, 2), (3, 2, 3)],
        ),
        ("inirai1", "", [(8, 118, 155), (8, 118, 156), (8, 119, 155), (8, 119, 156)]),
    ],
)
def test_map_tiles_find(species_code, region, expected_ids):
    res = ebird.get_tiles(species_code, 0)
    big_img = composite_mxn(res)
    with open(f"comp-ebird-{species_code}.png", "wb") as f:
        big_img.save(f)
    for t in res:
        t.save()


@pytest.mark.parametrize(
    "tile_id, result_id",
    [
        ((0, 0, 0), (0, 0, 0)),
        ((1, 1, 1), (1, 1, 1)),
        ((8, 118, 155), (8, 118, 155)),
        ((118, 155, 8), (8, 118, 155)),
    ],
)
def test_tile_id(tile_id, result_id):
    tid = tile_id
    test_tile = Tile(tid, img=Img.new("RGB", (256, 256)))
    assert tuple(test_tile.tid) == result_id


@pytest.mark.parametrize(
    "tile_id, center",
    [
        (TileID(0, 0, 0), (0.0, 0.0)),
        (TileID(1, 1, 1), (90.0, -42.5255645)),
        (TileID(8, 118, 155), (-13.359375, -36.029279)),
    ],
)
def test_tile_math(tile_id, center):
    test_tile = Tile(tile_id, img=Img.new("RGB", (256, 256)))
    assert test_tile.center == pytest.approx(center)


@pytest.mark.parametrize(
    "bbox, scale, result_ids",
    [
        ((-180, 19, -160, 23), 1, [TileID(z=3, x=0, y=3)]),
        ((-180, 19, -160, 23), 0, [TileID(z=3, x=0, y=3)]),
        ((-180, 19, -160, 23), -2, [TileID(z=1, x=0, y=0)]),
        ((-180, 19, -160, 23), -16, [TileID(z=0, x=0, y=0)]),
        (
            (-180, 19, -160, 23),
            2,
            [
                TileID(x=0, y=12, z=5),
                TileID(x=1, y=12, z=5),
                TileID(x=1, y=13, z=5),
                TileID(x=0, y=13, z=5),
                TileID(x=2, y=12, z=5),
                TileID(x=3, y=12, z=5),
                TileID(x=3, y=13, z=5),
                TileID(x=2, y=13, z=5),
                TileID(x=2, y=14, z=5),
                TileID(x=3, y=14, z=5),
                TileID(x=3, y=15, z=5),
                TileID(x=2, y=15, z=5),
                TileID(x=0, y=14, z=5),
                TileID(x=1, y=14, z=5),
                TileID(x=1, y=15, z=5),
                TileID(x=0, y=15, z=5),
            ],
        ),
        ((-154.94, 19.40, -154.87, 19.46), 16, [TileID(z=12, x=285, y=1822)]),
        ((-178.20, -34.06, 8.65, 71.91), 1, [TileID(z=0, x=0, y=0)]),
    ],
)
def test_gbif_tile_id_from_bbox(bbox, scale, result_ids):
    assert gbif.max_zoom == 12

    tile_ids = gbif.tileid_from_bbox(bbox, scale)
    print(tile_ids)
    assert all(
        [(a.z, a.x, a.y) == (b.z, b.x, b.y) for a, b in zip(tile_ids, result_ids)]
    )

@pytest.mark.parametrize(
    "tile_ids, expected_sibling_ids",
    [
        ([TileID(x=0, y=1, z=2), TileID(x=1, y=1, z=2), TileID(x=2, y=1, z=2)], [TileID(x=2, y=0, z=2), TileID(x=1, y=1, z=2), TileID(x=2, y=1, z=2), TileID(x=0, y=0, z=2), TileID(x=0, y=1, z=2), TileID(x=1, y=0, z=2)]),
        ([TileID(x=0, y=1, z=2), TileID(x=0, y=2, z=2), TileID(x=0, y=3, z=2)], [TileID(x=1, y=3, z=2), TileID(x=1, y=1, z=2), TileID(x=1, y=2, z=2), TileID(x=0, y=1, z=2), TileID(x=0, y=2, z=2), TileID(x=0, y=3, z=2)]),
        ([TileID(x=0, y=0, z=3), TileID(x=0, y=1, z=3)], [TileID(x=1, y=1, z=3), TileID(x=0, y=1, z=3), TileID(x=1, y=0, z=3), TileID(x=0, y=0, z=3)]),
        ([TileID(x=0, y=0, z=4), TileID(x=1, y=0, z=4)], [TileID(x=0, y=0, z=4), TileID(x=1, y=1, z=4), TileID(x=0, y=1, z=4), TileID(x=1, y=0, z=4)]),
        ([TileID(x=3, y=0, z=5), TileID(x=4, y=0, z=5)], [TileID(x=4, y=1, z=5), TileID(x=3, y=0, z=5), TileID(x=3, y=1, z=5), TileID(x=4, y=0, z=5)]),
        ([TileID(x=3, y=3, z=6), TileID(x=3, y=4, z=6)], [TileID(x=3, y=4, z=6), TileID(x=2, y=3, z=6), TileID(x=3, y=3, z=6), TileID(x=2, y=4, z=6)]),
        ([TileID(x=-4, y=160, z=8), TileID(x=-3, y=160, z=8)], [TileID(x=-4, y=160, z=8), TileID(x=-3, y=160, z=8), TileID(x=-4, y=161, z=8), TileID(x=-3, y=161, z=8)]),
    ],
)
def test_find_filtered_siblings(tile_ids, expected_sibling_ids):
    res = find_line_sibling_tiles([mercantile.Tile(t.x, t.y, t.z) for t in tile_ids])
    print(res)
    assert res == [mercantile.Tile(t.x, t.y, t.z) for t in expected_sibling_ids]
