from typing import Any

from pathlib import Path

import pytest
from static_maps.geo import LatLonBBox
from static_maps.mapper import (
    GBIF,
    BaseMap,
    MapBox,
    get_token,
    generate_gbif_mapbox_range,
    eBirdMap,
)
from static_maps.tiles import Tile, TileArray, TileID
from static_maps.imager import Image

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

        assert res.resolution == 256 if not high_res else 512
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
                TileID(15, 16827, 10771),
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
            (2494988, LatLonBBox(right=14, top=55, left=-127, bottom=15)),
            (5232445, LatLonBBox(right=10, top=54, left=-161, bottom=19)),
            (5228134, LatLonBBox(right=0, top=-38, left=-13, bottom=-38)),
        ],
    )
    def test_get_bbox(self, taxon_id, lat_lon_bbox):
        res = self.gbif.get_bbox(taxon_id)
        assert res == lat_lon_bbox

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "map_type",
        [
            "hex",
            "square",
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
            gb = self.gbif.get_hex_tile(
                tile_id=TileID(0, 0, 0), taxonKey=taxon_id, tile_size=tile_size
            )
        elif map_type == "square":
            gb = self.gbif.get_square_tile(
                tile_id=TileID(0, 0, 0), taxonKey=taxon_id, tile_size=tile_size
            )
        # else:
        #     gb = self.gbif.get_tile(tile_id=TileID(0, 0, 0), taxonKey=taxon_id, tile_size=tile_size)
        gb.name = f"test_{taxon_id}-{map_type}-s{tile_size // 512 if tile_size is not None else 1}"
        exp = tile_size if tile_size is not None else 512
        assert gb.resolution == exp

    def test_high_res_override(self):
        assert mapbox.high_res is True
        res = mapbox.get_tiles([TileID(0, 0, 0)], high_res=False)
        assert res[TileID(0, 0, 0)].resolution == 256
        res2 = mapbox.get_tiles([TileID(0, 0, 0)])
        assert res2[TileID(0, 0, 0)].resolution == 512

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "map_type",
        [
            "hex",
            "square",
        ],
    )
    @pytest.mark.parametrize(
        "taxon_id, tile_ids_expected_image",
        [
            (
                2482552,
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
        tile_ids = tile_ids_expected_image.keys()
        ta = TileArray.from_dict({x: Tile(x) for x in tile_ids})
        ta = self.gbif.get_tiles(taxon_id, ta, mode=map_type)
        print(ta)
        for k, t in ta.items():
            t.save()
            print("IE", k, tile_ids_expected_image[k])
            print("timg", t.img)
            # assert t.img.getbbox() is not None
        # assert False


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
                        TileID(15, 16827, 10771),
                    )
                ),
            ),
        ],
    )
    def test_gbif_mapbox_comp(self, taxon_id, tile_ids):
        mpta = TileArray.from_dict({x: Tile(x) for x in tile_ids})
        gbta = TileArray.from_dict({x: Tile(x) for x in tile_ids})

        mapbox_tiles = self.mapbox.get_tiles(mpta)
        gbif_tiles = self.gbif.get_tiles(taxon_id, gbta)
        c_tiles = mapbox_tiles._composite_layer(gbif_tiles)
        c_tiles.name = "gbif+mapbox"
        final_image = c_tiles._composite_all()
        final_image.save(f"gbif+mapbox-{taxon_id}-final.png")


class TestFullMapGBIF:
    gbif: GBIF = GBIF()
    mapbox: MapBox = MapBox(token=get_token())

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "taxon_id",  # , expected_bbox",
        [
            (
                2493091,
                # (
                #     (
                #     TileID(15, 16826, 10770),
                #     TileID(15, 16826, 10771),
                #     TileID(15, 16827, 10770),
                #     TileID(15, 16827, 10771)
                #     )
                # ),
            ),
            (5228134,),
        ],
    )
    def test_get_bbox_latlon(self, taxon_id):
        bbox = self.gbif.get_bbox(taxon_id)
        print(bbox)

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "input_species, map_size",
        [
            ("Bushtit", 512),
            ("Bushtit", 1024),
            ("Inaccessible Island Rail", 512),
            ("Inaccessible Island Rail", 1024),
            ("Carolina Chickadee", 512),
        ],
    )
    def test_final_range_map_normal(self, input_species, map_size):
        species, taxon_key = self.gbif.lookup_species(input_species)
        range_map = generate_gbif_mapbox_range(
            taxon_key, self.gbif, self.mapbox, map_size
        )
        assert range_map.size == (map_size, map_size)
        range_map.save(f"test_final_range_map-{map_size}-{taxon_key}.png")

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "input_species, map_size",
        [
            ("Tui", 512),
            ("Hawaiian Hawk", 512),
            ("Bald Eagle", 1024),
            ("Aptenodytes forsteri", 1024),
            ("Eudyptula minor", 512),
        ],
    )
    def test_final_range_map_antimeridian(self, input_species, map_size):
        species, taxon_key = self.gbif.lookup_species(input_species)
        print("taxon_key", taxon_key)
        range_map = generate_gbif_mapbox_range(
            taxon_key, self.gbif, self.mapbox, map_size
        )
        assert range_map.size == (map_size, map_size)
        range_map.save(f"test_final_range_map-{map_size}-{taxon_key}.png")


class TestBaseMap:
    test_img_path = Path("./static_maps/tests/images")
    base_map = BaseMap("")

    @pytest.mark.parametrize(
        "test_img_fn, zoom, tile_size, bbox, bbox_parts",
        [
            (
                "test_bbox_am.png",
                0,
                256,
                None,
                (
                    LatLonBBox(bottom=-53.3, left=164.5, top=-28.3, right=180.0),
                    LatLonBBox(bottom=-53.3, left=-178.6, top=-28.3, right=-174.4),
                    LatLonBBox(bottom=-53.3, left=164.5, top=-28.3, right=-174.4),
                ),
            ),
            (
                "test_bbox_normal.png",
                0,
                256,
                None,
                (
                    None,
                    None,
                    LatLonBBox(bottom=13.9, left=-129.4, top=52.5, right=-88.6),
                ),
            ),
        ],
    )
    def test_bbox_from_img(self, test_img_fn, zoom, tile_size, bbox, bbox_parts):
        with open(self.test_img_path / Path(test_img_fn), "rb") as f:
            test_img = Image.open(f).copy()
        res = self.base_map.find_image_bbox(test_img, zoom)
        if len(res) == 1:
            assert False  # This should never happen!
        else:
            assert res[0] == bbox_parts[0]
            assert res[1] == bbox_parts[1]
            assert res[2] == bbox_parts[2]


class TestEbird:
    ebird: eBirdMap = eBirdMap()
    mapbox: MapBox = MapBox(token=get_token(), high_res=False)

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "species_code, expected_bbox",
        [
            (
                "bushti",
                LatLonBBox(
                    -128.796028798097,
                    51.8596628170432,
                    -89.2701562968385,
                    14.126239979566,
                ),
            ),
            (
                "tui1",
                LatLonBBox(
                    -178.203369424671,
                    -28.7802470429875,
                    179.326113654898,
                    -52.691212723642,
                ),
            ),
            (
                "",
                None,
            ),
            (
                "redcro9",
                LatLonBBox(
                    -115.321299536305,
                    43.2077783892461,
                    -113.524668968066,
                    41.9867319031071,
                ),
            ),
        ],
    )
    def test_get_bbox(self, species_code, expected_bbox):
        res = self.ebird.get_bbox(species_code)
        assert res == expected_bbox

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "species_code",
        [
            "bushti",
        ],
    )
    def test_get_rsid(self, species_code):
        res = self.ebird.get_rsid(species_code)
        assert res

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "tile_id, rsid",
        [
            (
                TileID(0, 0, 0),
                "RS108970032",
            ),
        ],
    )
    def test_get_tile(self, tile_id, rsid):
        res = self.ebird.download_tile(tile_id, rsid)
        assert res.img

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "species_code, expected_ids",
        [
            (
                "tui1",
                [(4, 15, 9), (4, 15, 10), (4, 0, 9), (4, 0, 10)],
            )
        ],
    )
    def test_get_tiles(self, species_code, expected_ids):
        res = self.ebird.get_tiles(species_code)
        print("res:\n", res)
        for x in res:
            for t in x.values():
                t.save()

        for e in res:
            for x in e:
                assert tuple(x) in expected_ids

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "species_code, size, no_data",
        [
            ("tui1", 512, False),
            ("bushti", 512, False),
            ("pilwoo", 512, False),
            ("inirai1", 512, False),
            ("bkpwar", 512, False),
            ("baleag", 512, False),
            ("grycat", 512, False),
            ("kinpen1", 512, False),
            ("carchi", 512, False),
            ("arcter", 512, False),
            ("dodo1", 512, True),
            ("pifgoo", 512, False),
        ],
    )
    def test_map_final(self, species_code, size, no_data):
        res, res_no_data = self.ebird.make_map(species_code, self.mapbox, size)
        assert res_no_data == no_data
        res.save(f"final-ebird-{species_code}_{size}.png")
