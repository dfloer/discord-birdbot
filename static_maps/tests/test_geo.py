import pytest
from pprint import pprint
import PIL.Image as Img

# import sys
# import os

# sys.path.append(os.getcwd())

from static_maps.geo import BBoxBase, DynamicBBox, BBoxAlias, LatLonBBox, Point, LatLon
import static_maps.geo as geo
from static_maps.imager import Pixel


class TestBboxAlias:
    @pytest.mark.parametrize(
        "in_bbox",
        [
            {
                "left": ["kestrel"],
                "right": ["merlin"],
                "top": ["hobby"],
                "bottom": ["gyrfalcon"],
            },
            {"left": ["kestrel", "merlin"], "right": ["peregrine"], "top": []},
            ({}),
        ],
    )
    def test_creation(self, in_bbox):
        aliases = BBoxAlias()
        aliases.add(in_bbox)
        rm = aliases.reverse_map
        for k, v in in_bbox.items():
            assert all([a in rm[k] for a in v])

    @pytest.mark.parametrize(
        "in_bbox, exc",
        [
            ({"not a basename": ["pansy", "viola", "wittrockiana"]}, AttributeError),
        ],
    )
    def test_creation_fail(self, in_bbox, exc):
        aliases = BBoxAlias()
        with pytest.raises(exc):
            aliases.add(in_bbox)


class TestBboxBase:
    @pytest.mark.parametrize(
        "in_bbox",
        [
            (
                1,
                2,
                3,
                4,
            ),
        ],
    )
    def test_creation(self, in_bbox):
        res_bbox = BBoxBase(*in_bbox)
        assert res_bbox == in_bbox

    @pytest.mark.parametrize(
        "in_bbox",
        [
            (
                1,
                2,
                3,
                4,
                5,
            ),
        ],
    )
    def test_creation_fail(self, in_bbox):
        with pytest.raises(TypeError):
            res_bbox = BBoxBase(*in_bbox)
            assert res_bbox == in_bbox

    @pytest.mark.parametrize(
        "in_bbox, comp",
        [
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                (1, 2, 3, 4),
            ),
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                [1, 2, 3, 4],
            ),
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                BBoxBase(1, 2, 3, 4),
            ),
        ],
    )
    def test_equal(self, in_bbox, comp):
        print(BBoxBase(*in_bbox))
        assert BBoxBase(*in_bbox) == comp

    @pytest.mark.parametrize(
        "in_bbox, comp",
        [
            (
                (
                    1,
                    2,
                    3,
                    0,
                ),
                (1, 2, 3, 4),
            ),
            (
                (
                    1,
                    2,
                    3,
                    0,
                ),
                [1, 2, 3, 4],
            ),
            (
                (
                    1,
                    2,
                    3,
                    0,
                ),
                BBoxBase(1, 2, 3, 4),
            ),
        ],
    )
    def test_not_equal(self, in_bbox, comp):
        print(BBoxBase(*in_bbox))
        assert BBoxBase(*in_bbox) != comp

    @pytest.mark.parametrize(
        "in_bbox, prop, res",
        [
            (BBoxBase(1, 2, 3, 4), "area", 4),
            (BBoxBase(0, 0, 7, 7), "center", Point(3.5, 3.5)),
            (BBoxBase(1, 2, 3, 4), "tl", Point(1, 2)),
            (BBoxBase(1, 2, 3, 4), "br", Point(3, 4)),
            (BBoxBase(1, 2, 3, 4), "x_dim", 2),
            (BBoxBase(1, 2, 3, 4), "y_dim", 2),
            (BBoxBase(1, 2, 3, 4), "xy_dims", (2, 2)),
            (
                BBoxBase(
                    0,
                    0,
                    0,
                    0,
                ),
                "center",
                Point(0, 0),
            ),
            (
                BBoxBase(
                    0,
                    0,
                    128,
                    128,
                ),
                "center",
                Point(64, 64),
            ),
            (BBoxBase(12, 45, 39, 124), "xy_dims", (27, 79)),
            (BBoxBase(12, 45, 39, 124), "center", Point(25.5, 84.5)),
            (BBoxBase(12, 45, 39, 124), "area", 2133),
        ],
    )
    def test_properties(self, in_bbox, prop, res):
        a = object.__getattribute__(in_bbox, prop)
        assert a == res
        assert type(a) == type(res)

    def test_area(self):
        assert BBoxBase(1, 2, 3, 4).area == 4


class TestDynamicBbox:
    @pytest.mark.parametrize(
        "in_bbox",
        [
            {"left": 1, "top": 2, "right": 3, "bottom": 4},
            {"minx": 1, "maxy": 2, "maxx": 3, "miny": 4},
        ],
    )
    def test_creation_kwargs(self, in_bbox):
        res_bbox = DynamicBBox(**in_bbox)
        assert tuple(res_bbox) == tuple(in_bbox.values())

    @pytest.mark.parametrize(
        "in_bbox",
        [
            {"left": 1, "top": 2, "right": 3, "bottom": 4},
            {"minx": 1, "maxy": 2, "maxx": 3, "miny": 4},
        ],
    )
    def test_get_set(self, in_bbox):
        res_bbox = DynamicBBox(**in_bbox)
        assert res_bbox.left == in_bbox[list(in_bbox.keys())[0]]
        assert res_bbox.minx == in_bbox[list(in_bbox.keys())[0]]

    @pytest.mark.parametrize(
        "in_bbox",
        [
            (1, 2, 3, 4),
        ],
    )
    def test_get_set_alt(self, in_bbox):
        res_bbox = DynamicBBox(*in_bbox)
        res_bbox.left = 7
        assert res_bbox.left == 7
        assert res_bbox.minx == 7

        res_bbox.minx = 3
        assert res_bbox.left == 3
        assert res_bbox.minx == 3

    @pytest.mark.parametrize(
        "in_bbox",
        [
            (1, 2, 3, 4),
        ],
    )
    def test_get_set_fail(self, in_bbox):
        res_bbox = DynamicBBox(*in_bbox)
        with pytest.raises(AttributeError):
            res_bbox.potato = 7

        with pytest.raises(AttributeError):
            _ = res_bbox.potato

    @pytest.mark.parametrize(
        "in_bbox, area",
        [
            ((1, 2, 3, 4), 4),
        ],
    )
    # Make sure that we can still access parent attrs.
    def test_parent_attrs(self, in_bbox, area):
        res_bbox = DynamicBBox(*in_bbox)
        assert res_bbox.area == area

    @pytest.mark.parametrize(
        "in_bbox, prop, res",
        [
            (DynamicBBox(1, 2, 3, 4), "area", 4),
            (DynamicBBox(0, 0, 7, 7), "center", Point(3.5, 3.5)),
            (DynamicBBox(1, 2, 3, 4), "tl", Point(1, 2)),
            (DynamicBBox(1, 2, 3, 4), "br", Point(3, 4)),
            (DynamicBBox(1, 2, 3, 4), "x_dim", 2),
            (DynamicBBox(1, 2, 3, 4), "y_dim", 2),
            (DynamicBBox(1, 2, 3, 4), "xy_dims", (2, 2)),
            (
                DynamicBBox(
                    0,
                    0,
                    0,
                    0,
                ),
                "center",
                Point(0, 0),
            ),
            (
                DynamicBBox(
                    0,
                    0,
                    128,
                    128,
                ),
                "center",
                Point(64, 64),
            ),
            (DynamicBBox(12, 45, 39, 124), "xy_dims", (27, 79)),
            (DynamicBBox(12, 45, 39, 124), "center", Point(25.5, 84.5)),
            (DynamicBBox(12, 45, 39, 124), "area", 2133),
        ],
    )
    def test_properties(self, in_bbox, prop, res):
        a = object.__getattribute__(in_bbox, prop)
        assert a == res
        assert type(a) == type(res)

    def test_area(self):
        assert DynamicBBox(1, 2, 3, 4).area == 4


class TestLatLonBbox:
    @pytest.mark.parametrize(
        "in_bbox",
        [
            (-54.75, -68.25, -54.85, -68.35),
        ],
    )
    def test_creation(self, in_bbox):
        res_bbox = LatLonBBox(*in_bbox)
        assert res_bbox == in_bbox

    @pytest.mark.parametrize(
        "not_eq",
        [
            True,
            False,
        ],
    )
    @pytest.mark.parametrize(
        "in_bbox, comp",
        [
            (
                (
                    -90.0,
                    -45.0,
                    90.0,
                    45.0,
                ),
                (-90.0, -45.0, 90.0, 45.0),
            ),
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                [1, 2, 3, 4],
            ),
            (
                (
                    1,
                    2,
                    3,
                    4,
                ),
                LatLonBBox(1, 2, 3, 4),
            ),
        ],
    )
    def test_comparison(self, in_bbox, comp, not_eq):
        res_bbox = LatLonBBox(*in_bbox)
        if not_eq:
            assert res_bbox != tuple(reversed(in_bbox))
        else:
            assert res_bbox == comp

    @pytest.mark.parametrize(
        "in_bbox, srs",
        [
            ((-54.75, -68.25, -54.85, -68.35), "EPSG:4326"),
        ],
    )
    def test_comparison_srs(self, in_bbox, srs):
        assert LatLonBBox(*in_bbox) != LatLonBBox(*in_bbox, srs=srs)

    @pytest.mark.parametrize(
        "in_bbox",
        [
            (1, 2, 3, 4),
        ],
    )
    def test_get_set_alt(self, in_bbox):
        res_bbox = LatLonBBox(*in_bbox)
        assert res_bbox.maxlat == in_bbox[1]
        res_bbox.left = 7
        assert res_bbox.left == 7
        assert res_bbox.west == 7

        res_bbox.minx = 3
        assert res_bbox.left == 3
        assert res_bbox.west == 3

    def test_property_aliases(self):
        bbx = LatLonBBox(-110.39, 24.06, -110.25, 24.17)
        assert bbx.xy_dims == bbx.range

    def test_property_direct(self):
        a = LatLonBBox(20.0, 40.0, 40.0, -40.0).center
        assert a == LatLon(30.0, 0.0)
        assert type(a) == LatLon

    @pytest.mark.parametrize(
        "in_bbox, prop, res",
        [
            (LatLonBBox(-54.75, -68.25, -54.85, -68.35), "tl", LatLon(-54.75, -68.25)),
            (LatLonBBox(-54.75, -68.25, -54.85, -68.35), "br", LatLon(-54.85, -68.35)),
            (LatLonBBox(-54.75, -68.25, -54.85, -68.35), "xy_dims", (0.1, 0.1)),
            (LatLonBBox(20.0, 40.0, 40.0, -40.0), "xy_dims", (20.0, 80.0)),
            (LatLonBBox(1.0, 2.0, 1.0, 4.0), "xy_dims", (0.0, 2.0)),
            (
                LatLonBBox(-54.75, -68.25, -54.85, -68.35),
                "center",
                LatLon(-54.80, -68.30),
            ),
        ],
    )
    def test_properties(self, in_bbox, prop, res):
        a = object.__getattribute__(in_bbox, prop)
        assert pytest.approx(a) == res
        assert type(a) == type(res)

    def test_area_ni(self):
        with pytest.raises(NotImplementedError):
            _ = LatLonBBox(12, 45, 39, 124).area


class TestLatLon:
    @pytest.mark.parametrize(
        "latlon_in, latlon_out, zoom",
        [
            ((28.304380682962783, -15.468750000000012), (28.3, -15.5), 0),
            ((28.304380682962783, -15.468750000000012), (28.30, -15.47), 5),
            ((28.304380682962783, -15.468750000000012), (28.3044, -15.4688), 12),
            ((0.0, 0.0), (0.0, 0.0), 42),
            ((-89.86367491884421, 75.43308649874739), (-89.8637, 75.4331), 12),
        ],
    )
    def test_truncate_precision(self, latlon_in, latlon_out, zoom):
        latlon_in = LatLon(*latlon_in)
        res = geo.truncate_latlon_precision(latlon_in, zoom)
        assert res == latlon_out

    @pytest.mark.parametrize(
        "roundtrip",
        [False, True],
    )
    @pytest.mark.parametrize(
        "pixels, latlon, zoom, tile_size",
        [
            ((245, 153), (33.1, 164.5), 0, 256),
            ((256, 173), (53.3, 180.0), 0, 256),
            ((1, 149), (28.3, -178.6), 0, 256),
            ((4, 164), (45.1, -174.4), 0, 256),
            ((0, 0), (-85.1, -180.0), 0, 256),
            ((128, 128), (0.0, 0.0), 0, 256),
            ((256, 256), (85.1, 180.0), 0, 256),
            ((987, 808), (71.5, 167.0), 0, 1024),
        ],
    )
    def test_pixels_to_lat_lon(self, pixels, latlon, zoom, tile_size, roundtrip):
        pixels = Pixel(*pixels)
        latlon = LatLon(*latlon)
        print(pixels, latlon, zoom, tile_size, roundtrip)
        result_lat_lon = geo.pixels_to_lat_lon(pixels, zoom, tile_size)
        result_pixels = geo.lat_lon_to_pixels(result_lat_lon, zoom, tile_size)
        assert result_lat_lon == latlon
        if not roundtrip:
            assert result_pixels == pixels

    # @pytest.mark.parametrize(
    #     "pixels_bbox, zoom, tile_size, truncate, expected",
    #     [
    #         ((0, 0, 255, 255), 0, 256, True, ()),
    #     ],
    # )
    # def test_pixel_bbox_to_latlon_bbox(self, pixels_bbox, zoom, tile_size, truncate, expected):
    #     pbb = PixBbox(*pixels_bbox)
    #     ex = LatLonBBox(*expected)
    #     res = geo_utils.bounding_pixels_to_lat_lon(pbb, zoom, tile_size, truncate)
    #     assert res == ex


class TestFindTiles:
    @pytest.mark.parametrize(
        "bbox, start_zoom, end_zoom, name, test_image_fn",
        [
            (
                LatLonBBox(
                    east=175.781248, south=-42.032974, west=173.671878, north=-40.979897
                ),
                0,
                9,
                "Wellington Test - general area test.",
                None,
            ),
            (
                LatLonBBox(
                    west=-179.99999999291,
                    south=16.9397716157348,
                    east=179.326113654898,
                    north=71.9081724700314,
                ),
                0,
                2,
                "Bald Eagle - AM wrap with zoom.",
                None,
            ),
            (
                LatLonBBox(
                    west=-172.813477719954,
                    south=-82.1269032464488,
                    east=179.326113654898,
                    north=-39.6895335169534,
                ),
                0,
                1,
                "Emperor Pengiun - Antartica.",
                None,
            ),
            (
                LatLonBBox(
                    west=-163.830324878759,
                    south=47.02752144317,
                    east=163.156438540747,
                    north=71.9081724700314,
                ),
                0,
                1,
                "Gray-headed Chickadee- No AM wrap.",
                None,
            ),
            (
                LatLonBBox(
                    west=-91.965102149197,
                    south=-1.38713438223174,
                    east=-89.2701562968385,
                    north=0.421740150964651,
                ),
                0,
                8,
                "Galapagos Pengiun - small area",
                None,
            ),
            (
                LatLonBBox(
                    west=-178.203369424671,
                    south=-52.691212723642,
                    east=179.326113654898,
                    north=-28.7802470429875,
                ),
                0,
                4,
                "Tui - AM wrap with more zoom.",
                "tui_0-0-0.png",
            ),
            (
                LatLonBBox(
                    west=-151.253910901085,
                    south=4.9495734055138,
                    east=5.05294853571131,
                    north=63.6299576758096,
                ),
                0,
                2,
                "Gray Catbird - 3x1 line",
                None,
            ),
            (
                LatLonBBox(
                    west=63.4434420034802,
                    south=6.76762999637114,
                    east=109.257521493576,
                    north=35.0816917166643,
                ),
                0,
                3,
                "Rufous Treepie",
                None,
            ),
        ],
    )
    def test_bbox_to_tiles(self, bbox, start_zoom, end_zoom, name, test_image_fn):
        res = geo.bounding_box_to_tiles(bbox)
        pprint(res)
