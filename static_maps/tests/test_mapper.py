import io
from dataclasses import dataclass
from pprint import pprint

from typing import Any

import mercantile
import pytest


from static_maps.geo import LatLonBBox
from static_maps.mapper import BaseMap, MapBox, GBIF, get_token
from static_maps.tiles import Tile, TileID, TileArray

mapbox = MapBox(token=get_token())
gbif = GBIF()

class TestMapBox:
    mapbox: MapBox = MapBox(token=get_token())
    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "input_string, output",
        [
            ("Vancouver, Canada", (-123.116838, 49.279862)),
            ("Vondelpark", (4.877867, 52.362441)),
        ],
    )
    def test_geocode(self, input_string, output):
        res = self.mapbox.get_geocode(input_string)
        assert res == output

    def test_no_token(self):
        mp = MapBox()
        with pytest.raises(BaseMap.AuthMissingError):
            _ = mp.get_geocode("The Moon")

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "tid, fmt, style, high_res",
        [
            (TileID(0, 0, 0), "jpg90", "satellite", False),
            (TileID(6, 40, 44), "jpg90", "satellite", True),
            (TileID(2, 2, 2), "jpg90", "satellite", True),
        ],
    )
    def test_get_tiles(self, tid, fmt, style, high_res):
        res = self.mapbox.get_tile(tid, fmt=fmt, style=style, high_res=high_res)

        assert res.resolution == int(high_res) + 1
        print("res:", res)
        res.save()
        assert type(res) == Tile

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "tile_array",
        [
            (
                TileID(15, 16826, 10770),
                TileID(15, 16826, 10771),
                TileID(15, 16827, 10770),
                TileID(15, 16827, 10771)
            ),
        ],
    )
    def test_get_tilearray(self, tile_array):
        res_tiles = self.mapbox.get_tiles(tile_array)
        assert type(res_tiles) == TileArray
        for t in res_tiles.values():
            t.save()

class TestGBIF:
    gbif: Any = GBIF()

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
    def test_gbif_lookup(self, species, taxon_id):
        res = self.gbif.lookup_species(species)
        assert res == taxon_id

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "taxon_id, lat_lon_bbox",
        [
            (2494988, LatLonBBox(14, 55, -127, 15)),
            (5232445, LatLonBBox(10, 54, -161, 19)),
            (5228134, LatLonBBox(0, -38, -13, -38)),
        ],
    )
    def test_get_bbox(self, taxon_id, lat_lon_bbox):
        res = self.gbif.get_bbox(taxon_id)
        assert res == lat_lon_bbox


    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "map_type",
        [
            "hex", "square",
        ],
    )
    @pytest.mark.parametrize(
        "taxon_id, tile_size",
        [
            (9515886, None),
            (9515886, 256),
            (2494988, 512),
        ],
    )
    def test_get_map_tile(self, taxon_id, tile_size, map_type):
        if map_type == "hex":
            gb = self.gbif.get_hex_tile(tile_id=TileID(0, 0, 0), taxonKey=taxon_id, tile_size=tile_size)
        elif map_type == "square":
            gb = self.gbif.get_square_tile(tile_id=TileID(0, 0, 0), taxonKey=taxon_id, tile_size=tile_size)
        # else:
        #     gb = self.gbif.get_tile(tile_id=TileID(0, 0, 0), taxonKey=taxon_id, tile_size=tile_size)
        print("gb", gb)
        gb.name = f"test_{taxon_id}-{map_type}-s{tile_size // 512 if tile_size is not None else 1}"
        assert gb

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "map_type",
        [
            "hex", "square",
        ],
    )
    @pytest.mark.parametrize(
        "taxon_id, tile_ids_expected_image",
        [
            (2482552,
                {
                    TileID(7, 121, 26): True,
                    TileID(7, 121, 27): True,
                    TileID(7, 120, 27): True,
                    TileID(7, 120, 26): False,
                },
            ),
        ],
    )
    def test_get_tilearray(self, taxon_id, tile_ids_expected_image, map_type):
        ta = TileArray()
        tile_ids = tile_ids_expected_image.keys()
        ta.from_dict({x: Tile(x) for x in tile_ids})
        ta = self.gbif.get_tiles(taxon_id, ta, mode=map_type)
        print(ta)
        for k, t in ta.items():
            t.save()
            print("IE", k, tile_ids_expected_image[k])
            print("timg", t.img)
            # assert t.img.getbbox() is not None
        assert False


class TestGBIFOther:
    gbif: GBIF = GBIF()
    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "species, taxon_id",
        [
            ("Bushtit", ("Psaltriparus minimus", 2494988)),
            ("Barn Swallow", ("Hirundo rustica", 9515886)),
            ("Anna's Hummingbird", ("Calypte anna", 2476674)),
            ("Hirundo rustica", ("Hirundo rustica", 9515886)),
            ("Red-billed Chough", ("Pyrrhocorax pyrrhocorax", 2482552)),
            ("Chiffchaff", ("Phylloscopus collybita", 2493091)),
        ],
    )
    def test_gbif_lookup(self, species, taxon_id):
        res = self.gbif.lookup_species(species)
        assert res == taxon_id

class TestCombinedGBIF:
    gbif: GBIF = GBIF()
    mapbox: MapBox = MapBox(token=get_token())

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "taxon_id, tile_ids",
        [
            (
                2493091,
                (
                    (
                    TileID(15, 16826, 10770),
                    TileID(15, 16826, 10771),
                    TileID(15, 16827, 10770),
                    TileID(15, 16827, 10771)
                    )
                ),
            ),
        ],
    )
    def test_gbif_mapbox_comp(self, taxon_id, tile_ids):
        mpta = TileArray()
        mpta.from_dict({x: Tile(x) for x in tile_ids})
        gbta = TileArray()
        gbta.from_dict({x: Tile(x) for x in tile_ids})

        mapbox_tiles = self.mapbox.get_tiles(mpta)
        gbif_tiles = self.gbif.get_tiles(taxon_id, gbta)
        for tile in gbif_tiles.values():
            tile.save()
        c_tiles = mapbox_tiles._composite_layer(gbif_tiles)
        c_tiles.name = "gbif+mapbox"
        for t in c_tiles.values():
            assert t.img

        print(c_tiles)
        for t in c_tiles.values():
            t.name = "gbif+mapbox"
            t.save()

        final_image = c_tiles._composite_all()
        final_image.save(f"gbif+mapbox-{taxon_id}-final.png")

class TestFullMapGBIF:
    gbif: GBIF = GBIF()
    mapbox: MapBox = MapBox(token=get_token())


    # @pytest.mark.vcr("new")
    # @pytest.mark.parametrize(
    #     "taxon_id",#, expected_bbox",
    #     [
    #         (
    #             2493091,

    #             # (
    #             #     (
    #             #     TileID(15, 16826, 10770),
    #             #     TileID(15, 16826, 10771),
    #             #     TileID(15, 16827, 10770),
    #             #     TileID(15, 16827, 10771)
    #             #     )
    #             # ),
    #         ),
    #     ],
    # )
    # def test_get_bbox(self, taxon_id, expected_bbox):
    #     pass
    # out4 = _pygbif.maps.map(z=10, x=512, y=512)
    # out5 = _pygbif.maps.map(z=10, x=10, y=10)
    # assert out5.response.status_code == 200

    # @pytest.mark.vcr("new")
    # @pytest.mark.parametrize(
    #     "z, x, y, fmt, style, high_res, taxon_id",
    #     [
    #         (0, 0, 0, "jpg90", "satellite", True, 2494988),
    #         (0, 0, 0, "jpg90", "satellite", True, 9515886),
    #         (0, 0, 0, "jpg90", "satellite", True, 2480528),
    #         (0, 0, 0, "jpg90", "satellite", True, 5228134),
    #     ],
    # )
    # def test_tile_composite(z, x, y, fmt, style, high_res, taxon_id):
    #     gb = gbif.get_hex_map(z, x, y, taxon_id, high_res=False)[0]
    #     az, ax, ay = gb.tid
    #     mb = mapbox.get_tile(z=az, x=ax, y=ay, fmt=fmt, style=style, high_res=high_res)
    #     mb.name = f"mb-{taxon_id}"
    #     gb.name = f"gb-{taxon_id}"
    #     # mb.save()
    #     # gb.save()
    #     t1 = mb.composite(gb)
    #     # with open("t1b.png", "wb") as f:
    #     #     d = io.BytesIO()
    #     #     t1.img.save(d, "png")
    #     #     f.write(d.getvalue())
    #     t1.name = f"test_tile_comp-{taxon_id}"
    #     t1.save()
    #     # Do something to make sure the composition worked correctly. Should probably be using saved tiles too.

# @pytest.mark.vcr("new")
# @pytest.mark.parametrize(
#     "z, x, y, fmt, style, high_res, taxon_id",
#     [
#         (0, 0, 0, "jpg90", "satellite", True, 2494988),
#         (0, 0, 0, "jpg90", "satellite", True, 9515886),
#         (0, 0, 0, "jpg90", "satellite", True, 2480528),
#         (0, 0, 0, "jpg90", "satellite", True, 5228134),
#     ],
# )
# def test_tile_composite(z, x, y, fmt, style, high_res, taxon_id):
#     gb = gbif.get_hex_map(z, x, y, taxon_id, high_res=False)[0]
#     az, ax, ay = gb.tid
#     mb = mapbox.get_tile(z=az, x=ax, y=ay, fmt=fmt, style=style, high_res=high_res)
#     mb.name = f"mb-{taxon_id}"
#     gb.name = f"gb-{taxon_id}"
#     # mb.save()
#     # gb.save()
#     t1 = mb.composite(gb)
#     # with open("t1b.png", "wb") as f:
#     #     d = io.BytesIO()
#     #     t1.img.save(d, "png")
#     #     f.write(d.getvalue())
#     t1.name = f"test_tile_comp-{taxon_id}"
#     t1.save()
#     # Do something to make sure the composition worked correctly. Should probably be using saved tiles too.
