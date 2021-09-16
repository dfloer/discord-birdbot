import pytest
from pprint import pprint
import mercantile
from dataclasses import FrozenInstanceError
from dataclasses import dataclass

import sys
import os

sys.path.append(os.getcwd())

from static_maps.tiles import Tile, TileArray, TileID, constants


import PIL.Image as Img


def create_blank_image(size=256, mode="RGB"):
    return Img.new(mode, (size, size))


def no_warnings(func):
    def wrapper_no_warnings(*args, **kwargs):
        with pytest.warns(None) as warnings:
            func(*args, **kwargs)
        if len(warnings) > 0:
            raise AssertionError(
                "Warnings were raised: " + ", ".join([str(w) for w in warnings])
            )

    return wrapper_no_warnings


class TestTileIDs:
    @pytest.mark.parametrize(
        "input_tileid, expected_tileid, warn",
        [
            (
                (0, 0, 0),
                (0, 0, 0),
                None,
            ),
            (
                (0, 0, 0),
                (0, 0, 0),
                None,
            ),
            (
                ((0, 0, 0)),
                (0, 0, 0),
                None,
            ),
            (
                mercantile.Tile(2, 4, 6),
                (6, 2, 4),
                None,
            ),
            (
                (35, 11, 8),
                (35, 11, 8),
                UserWarning,
            ),
            (
                (2, -1, 0),
                (2, -1, 0),
                UserWarning,
            ),
            (
                (0, 64, 64),
                (0, 64, 64),
                UserWarning,
            ),
        ],
    )
    # Test creation of TileIDs and potential warnings.
    def test_creation(self, input_tileid, expected_tileid, warn):
        print("itid", input_tileid)
        print("exid:", expected_tileid)
        with pytest.warns(warn) as warnings:
            new_tid = TileID(input_tileid)
        # if len(warnings) == 0 and warn:
        #     print(warnings)
        #     raise AssertionError("Warnings weren't raised.")

        # else:
        #     new_tid = TileID(0, x=0, y=0)
        rz = new_tid.z
        rx = new_tid.x
        ry = new_tid.y
        assert expected_tileid == (rz, rx, ry)

    def test_assignment_fail(self):
        new_tid = TileID(0, 0, 0)
        with pytest.raises(FrozenInstanceError):
            new_tid.z = 42

    @pytest.mark.parametrize(
        "input_val, exc",
        [
            (
                (2),
                TypeError,
            ),
            (
                (2, 1),
                TypeError,
            ),
            (
                (2, 1, 6, 5),
                TypeError,
            ),
        ],
    )
    def test_exceptions(self, input_val, exc):
        with pytest.raises(exc):
            new_tid = TileID(input_val)

    @pytest.mark.parametrize(
        "args, kwargs, exc, result",
        [
            (([2]), {"x": 1, "y": 0}, None, (2, 1, 0)),
            ((2, 1), {"y": 0}, None, (2, 1, 0)),
            ((), {"z": 2, "x": 1, "y": 0}, None, (2, 1, 0)),
            (([3]), {"z": 2, "x": 1, "y": 0}, TypeError, (2, 1, 0)),
        ],
    )
    # Test how mixed args and kwargs are handled.
    def test_args_kwargs_creation(self, args, kwargs, exc, result):
        print("a", args, "k", kwargs)
        if exc:
            print("EXCEPTION!!!!!")
            with pytest.raises(exc):
                _ = TileID(*args, **kwargs)
        else:
            n = TileID(*args, **kwargs)
            assert (n.z, n.x, n.y) == result

    @pytest.mark.parametrize(
        "test_id",
        [
            (8, 4, 2),
        ],
    )
    # Test to make sure the custom iterator works and returns values in the correct orders.
    def test_iterable_tileid(self, test_id):
        z, x, y = TileID(test_id)
        assert (z, x, y) == (test_id)

    def test_as_url(self):
        tid = TileID(6, -8, 42)
        assert tid.urlform == "6/-8/42"


class TestTile:
    @pytest.mark.parametrize(
        "tile_ids, images, names, tile_size",
        [
            (
                [TileID(0, 0, 0)],
                [create_blank_image(256, "RGB")],
                ["test_tile_creation"],
                256,
            ),
        ],
    )
    def test_creation(self, tile_ids, images, names, tile_size):
        for tid, img, name in zip(tile_ids, images, names):
            tile = Tile(tid=tid, img=img, name=name)
            assert tile.tid == tid
            assert tile.img == img
            assert tile.name == name
            assert tile.resolution == tile_size

    @pytest.mark.parametrize(
        "test_tile, m_tile",
        [
            (
                Tile(TileID(8, 4, 2), img=create_blank_image()),
                mercantile.Tile(z=8, x=4, y=2),
            ),
        ],
    )
    def test_to_mercantile(self, test_tile, m_tile):
        assert test_tile.asmercantile == m_tile


# Just a 2x2 tilearray.
@pytest.mark.parametrize(
    "tile_ids, images",
    [
        (
            [
                TileID(1, 1, 1),
                TileID(1, 1, 0),
                TileID(1, 0, 1),
                TileID(1, 0, 0),
            ],
            [
                create_blank_image(256, "RGB"),
                create_blank_image(256, "RGB"),
                create_blank_image(256, "RGB"),
                create_blank_image(256, "RGB"),
            ],
        ),
        (
            [
                TileID(15, 16826, 10770),
                TileID(15, 16826, 10771),
                TileID(15, 16827, 10770),
                TileID(15, 16827, 10771),
            ],
            [
                create_blank_image(256, "RGB"),
                create_blank_image(256, "RGB"),
                create_blank_image(256, "RGB"),
                create_blank_image(256, "RGB"),
            ],
        ),
    ],
)
class TestTileArray:
    def create_tilearray(self, tids, imgs):
        tile_array = TileArray()
        for tid, img in zip(tids, imgs):
            tile = Tile(tid=tid, img=img)
            tile_array[tid] = tile
        return tile_array

    def test_creation(self, tile_ids, images):
        tile_array = self.create_tilearray(tile_ids, images)
        for tid, tile in tile_array.items():
            assert tid in tile_ids
        pprint(tile_array)

    def test_creation_constructor(self, tile_ids, images):
        tile_array = TileArray().from_dict(
            {TileID(k): Tile(TileID(k), v) for k, v in zip(tile_ids, images)}
        )
        for tid in tile_ids:
            assert tid in tile_array
        pprint(tile_array)

    def test_set_name(self, tile_ids, images):
        ta = TileArray(name="testname")
        assert ta.name == "testname"

        ta.name = "newtestname"
        assert ta.name == "newtestname"

        ts2 = TileArray()
        ts2.name = "anothertestname"
        assert ts2.name == "anothertestname"

    @pytest.mark.parametrize(
        "dims",
        [
            (2, 2),
        ],
    )
    def test_dims(self, tile_ids, images, dims):
        tile_array = self.create_tilearray(tile_ids, images)
        assert tile_array.xy_dims == dims

    def test_mixed_zoom(self, tile_ids, images):
        fiddled_ids = [TileID(z + 1 if x % 2 == 0 else z, x, y) for z, x, y in tile_ids]
        with pytest.raises(TileArray.MixedZoomError):
            _ = self.create_tilearray(fiddled_ids, images)

    def test_change_zoom(self, tile_ids, images):
        tile_array = self.create_tilearray(tile_ids, images)
        with pytest.raises(TileArray.MixedZoomError):
            tile_array.zoom = tile_ids[0].z + 1

    @pytest.mark.parametrize(
        "zoom, exc",
        [
            ([1], None),
            ([1, 2], None),
            ([constants.max_zoom + 1], TileArray.ZoomRangeError),
            ([constants.min_zoom - 1], TileArray.ZoomRangeError),
        ],
    )
    def test_change_zoom_empty(self, tile_ids, images, zoom, exc):
        print("zoom", zoom)
        print("exc", exc)
        tile_array = TileArray()
        for z in zoom:
            if exc:
                with pytest.raises(exc):
                    tile_array.zoom = z
            else:
                tile_array.zoom = z

    @pytest.mark.parametrize(
        "test_line_ids, expected_sibling_ids",
        [
            (
                [TileID(x=0, y=1, z=2), TileID(x=1, y=1, z=2), TileID(x=2, y=1, z=2)],
                [
                    TileID(x=2, y=0, z=2),
                    TileID(x=1, y=1, z=2),
                    TileID(x=2, y=1, z=2),
                    TileID(x=0, y=0, z=2),
                    TileID(x=0, y=1, z=2),
                    TileID(x=1, y=0, z=2),
                ],
            ),
            (
                [TileID(x=0, y=1, z=2), TileID(x=0, y=2, z=2), TileID(x=0, y=3, z=2)],
                [
                    TileID(x=1, y=3, z=2),
                    TileID(x=1, y=1, z=2),
                    TileID(x=1, y=2, z=2),
                    TileID(x=0, y=1, z=2),
                    TileID(x=0, y=2, z=2),
                    TileID(x=0, y=3, z=2),
                ],
            ),
            (
                [TileID(x=0, y=0, z=3), TileID(x=0, y=1, z=3)],
                [
                    TileID(x=1, y=1, z=3),
                    TileID(x=0, y=1, z=3),
                    TileID(x=1, y=0, z=3),
                    TileID(x=0, y=0, z=3),
                ],
            ),
            (
                [TileID(x=0, y=0, z=4), TileID(x=1, y=0, z=4)],
                [
                    TileID(x=0, y=0, z=4),
                    TileID(x=1, y=1, z=4),
                    TileID(x=0, y=1, z=4),
                    TileID(x=1, y=0, z=4),
                ],
            ),
            (
                [TileID(x=3, y=0, z=5), TileID(x=4, y=0, z=5)],
                [
                    TileID(x=4, y=1, z=5),
                    TileID(x=3, y=0, z=5),
                    TileID(x=3, y=1, z=5),
                    TileID(x=4, y=0, z=5),
                ],
            ),
            (
                [TileID(x=3, y=3, z=6), TileID(x=3, y=4, z=6)],
                [
                    TileID(x=3, y=4, z=6),
                    TileID(x=2, y=3, z=6),
                    TileID(x=3, y=3, z=6),
                    TileID(x=2, y=4, z=6),
                ],
            ),
            (
                [TileID(x=-4, y=160, z=8), TileID(x=-3, y=160, z=8)],
                [
                    TileID(x=-4, y=160, z=8),
                    TileID(x=-3, y=160, z=8),
                    TileID(x=-4, y=161, z=8),
                    TileID(x=-3, y=161, z=8),
                ],
            ),
        ],
    )
    def test_find_filtered_siblings(
        self, test_line_ids, expected_sibling_ids, tile_ids, images
    ):
        tile_array = self.create_tilearray(
            test_line_ids, [create_blank_image() for _ in range(len(test_line_ids))]
        )

        res = tile_array.find_line_sibling_tile_ids()
        assert isinstance(res, TileArray)
        for tid in expected_sibling_ids:
            assert tid in res.keys()
