import pytest
from pprint import pprint
import PIL.Image as Img

# import sys
# import os

# sys.path.append(os.getcwd())

from static_maps.geo import (
    BBoxBase,
    DynamicBBox,
    BBoxAlias,
    LatLonBBox,
    Point,
    LatLon,
    lat_lon_to_pixels,
)
import static_maps.geo as geo
from static_maps.imager import Pixel, PixBbox
import static_maps.constants as constants


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
    def test_base_properties(self, in_bbox, prop, res):
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
        "in_dict, result, exc",
        [
            (
                {"left": 1, "top": 2, "right": 3, "bottom": 4},
                DynamicBBox(left=1, top=2, right=3, bottom=4),
                None,
            ),
            (
                {"minx": 1, "maxy": 2, "maxx": 3, "miny": 4},
                DynamicBBox(left=1, top=2, right=3, bottom=4),
                None,
            ),
            (
                {"minx": 1},
                None,
                ValueError,
            ),
            (
                {"a": 1, "b": 2, "c": 3, "d": 4},
                None,
                AttributeError,
            ),
        ],
    )
    def test_from_dict(self, in_dict, result, exc):
        if exc is None:
            assert DynamicBBox.from_dict(in_dict) == result
        else:
            with pytest.raises(exc):
                assert DynamicBBox.from_dict(in_dict) == result

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
            (DynamicBBox(left=1, top=2, right=3, bottom=4), "tl", Point(1, 2)),
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
    def test_dynamic_properties(self, in_bbox, prop, res):
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
            (LatLonBBox(-180.0, 90.0, 180.0, -90.0), "tl", LatLon(90.0, -180.0)),
            (LatLonBBox(-180.0, 90.0, 180.0, -90.0), "br", LatLon(-90.0, 180)),
            (LatLonBBox(-54.75, -68.25, -54.85, -68.35), "tl", LatLon(-68.25, -54.75)),
            (LatLonBBox(-54.75, -68.25, -54.85, -68.35), "br", LatLon(-68.35, -54.85)),
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

    @pytest.mark.parametrize(
        "latlon, zoom, pixels",
        [
            (
                LatLonBBox(west=-180.0, north=85.0, east=180.0, south=-85.0),
                0,
                PixBbox(left=0, top=0, right=256, bottom=256),
            ),
            (
                LatLonBBox(-54.75, -68.25, -54.85, -68.35),
                4,
                PixBbox(1425, 3123, 1424, 3126),
            ),
            (
                LatLonBBox(-54.75, 68.25, 54.85, -68.35),
                5,
                PixBbox(2850, 1945, 5344, 6253),
            ),
            (
                LatLonBBox(20.0, 40.0, 40.0, -40.0),
                0,
                PixBbox(142, 97, 156, 159),
            ),
            (
                LatLonBBox(-54.75, -68.25, -54.85, -68.35),
                15,
                PixBbox(2918537, 6396732, 2916206, 6403034),
            ),
        ],
    )
    def test_latlon_to_pixels(self, latlon, zoom, pixels):
        res = geo.bounding_lat_lon_to_pixels(latlon, zoom)
        print("res", res)
        assert [a for a in res] == [a for a in pixels]
        # coordinate origin is lower left corner.
        # make sure the results are in this order.
        assert res.left >= res.left
        assert res.top <= res.bottom

    @pytest.mark.parametrize(
        "latlon, result",
        [
            (
                LatLonBBox(north=45.0, south=-45.0, west=-90.0, east=90.0),
                None,
            ),
            (
                LatLonBBox(north=45.0, south=-45.0, west=90.0, east=-90.0),
                (
                    LatLonBBox(north=45.0, south=-45.0, west=90.0, east=180.0),
                    LatLonBBox(north=45.0, south=-45.0, west=-180.0, east=-90.0),
                ),
            ),
            (
                LatLonBBox(left=165, top=-29, right=185, bottom=-53),
                (
                    LatLonBBox(left=165, top=-29, right=180.0, bottom=-53),
                    LatLonBBox(left=-180.0, top=-29, right=-175, bottom=-53),
                ),
            ),
            (
                LatLonBBox(left=-185, top=-29, right=-165, bottom=-53),
                (
                    LatLonBBox(left=175.0, top=-29, right=180, bottom=-53),
                    LatLonBBox(left=-180, top=-29, right=-165, bottom=-53),
                ),
            ),
            (
                LatLonBBox(left=99, top=72, right=379, bottom=9),
                (
                    LatLonBBox(left=99, top=72, right=180, bottom=9),
                    LatLonBBox(left=-180, top=72, right=19, bottom=9),
                ),
            ),
        ],
    )
    def test_antimeridian_split(self, latlon, result):
        res = latlon.am_split()
        if res is None:
            assert res == result
        else:
            assert res[0] == result[0]
            assert res[1] == result[1]


class TestLatLon:
    @pytest.mark.parametrize(
        "latlon_in",
        [
            (49, -123),
        ],
    )
    def test_creation(self, latlon_in):
        res = LatLon(*latlon_in)
        assert res.lat == latlon_in[0]
        assert res.lon == latlon_in[1]
        # Make sure it's iterable.
        lat, lon = res
        assert (lat, lon) == latlon_in

    @pytest.mark.parametrize(
        "latlon_in, radius_km, bbox",
        [
            (
                (49, -123),
                20,
                LatLonBBox(
                    left=-123.2728,
                    top=49.1797,
                    right=-122.7251,
                    bottom=48.8203,
                ),
            ),
            (
                # These results look screwy because they are. This close to the poles, things get weird.
                (90, 180),
                20,
                LatLonBBox(
                    left=177.9923,
                    top=constants.max_latitude,
                    right=182.1585,
                    bottom=84.8715,
                ),
            ),
        ],
    )
    def test_radius(self, latlon_in, radius_km, bbox):
        res = LatLon(*latlon_in)
        radius_bbox = res.get_radius(radius_km)
        for a, b in zip(radius_bbox, bbox):
            assert pytest.approx(a) == b


class TestLatLonBbox:
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
            ((245, 153), (-33.1, 164.5), 0, 256),
            ((256, 173), (-53.3, 180.0), 0, 256),
            ((1, 149), (-28.3, -178.6), 0, 256),
            ((4, 164), (-45.1, -174.4), 0, 256),
            ((0, 0), (85.1, -180.0), 0, 256),
            ((128, 128), (0.0, 0.0), 0, 256),
            ((256, 256), (-85.1, 180.0), 0, 256),
            ((987, 808), (-71.5, 167.0), 0, 1024),
            ((525, 761), (41.9, -87.7), 3, 256),
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

    @pytest.mark.parametrize(
        "latlon, pixels, zoom",
        [
            (LatLon(lat=6.7, lon=109.2), Pixel(206, 123), 0),
        ],
    )
    def test_lat_lon_to_pixels(self, latlon, zoom, pixels):
        res = geo.lat_lon_to_pixels(latlon, zoom)
        assert res == pixels
        # res2 = geo.pixels_to_lat_lon(pixels, zoom)
        # assert res2 == latlon

    @pytest.mark.parametrize(
        "bbox, other_bbox, result",
        [
            (
                LatLonBBox(left=-180.0, right=180.0, top=90.0, bottom=-90.0),
                LatLonBBox(left=-180.0, right=180.0, top=90.0, bottom=-90.0),
                True,
            ),
            (
                LatLonBBox(left=-90.0, right=90.0, top=45.0, bottom=-45.0),
                LatLonBBox(left=-180.0, right=180.0, top=90.0, bottom=-90.0),
                False,
            ),
            (
                LatLonBBox(left=-90.0, right=90.0, top=45.0, bottom=-45.0),
                LatLonBBox(left=-90.0, right=90.0, top=44.99, bottom=-45.0),
                True,
            ),
        ],
    )
    def test_contains(self, bbox, other_bbox, result):
        assert bbox.contains(other_bbox) == result

    @pytest.mark.parametrize(
        "pixels_bbox, zoom, tile_size, truncate, expected",
        [
            (
                PixBbox(0, 0, 255, 255),
                0,
                256,
                True,
                LatLonBBox(bottom=-84.9, left=-180.0, top=85.1, right=178.6),
            ),
            # (PixBbox(1, 149, 256, 173), 0, 256, True, LatLonBBox(0, 0, 0, 0)),
        ],
    )
    def test_pixel_bbox_to_latlon_bbox(
        self, pixels_bbox, zoom, tile_size, truncate, expected
    ):
        res = geo.bounding_pixels_to_lat_lon(pixels_bbox, zoom, tile_size, truncate)
        assert res == expected

    @pytest.mark.parametrize(
        "latlon_tl, latlon_br",
        [
            (LatLon(lat=45, lon=90), LatLon(lat=-45, lon=-90)),
            (LatLon(lat=90, lon=180), LatLon(lat=-90, lon=-180)),
            (LatLon(lat=90, lon=180), LatLon(lat=0, lon=0)),
            (LatLon(lat=0, lon=0), LatLon(lat=-90, lon=-180)),
        ],
    )
    def test_bbox_lat_clamp(self, latlon_tl, latlon_br):
        test_bbox = LatLonBBox(
            left=latlon_tl.lon,
            top=latlon_tl.lat,
            right=latlon_br.lon,
            bottom=latlon_br.lat,
        )
        test_bbox.clamp_lat()
        print(test_bbox)
        assert test_bbox.top <= constants.max_latitude
        assert test_bbox.bottom >= -constants.max_latitude
