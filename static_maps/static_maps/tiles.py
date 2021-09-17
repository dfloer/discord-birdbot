from types import new_class
import warnings
from collections import namedtuple
from dataclasses import dataclass, field, InitVar
from io import BytesIO
from pathlib import Path
from typing import Dict, List, Tuple
from typing import Any, Iterable, Optional, Union

import constants
import mercantile
import PIL.ImageDraw as ImageDraw

import static_maps.geo as geo
import static_maps.imager as imager
from static_maps.imager import Image

from pprint import pprint


Point = namedtuple("Point", ("x", "y"))


@dataclass(frozen=True)
class BaseID:
    z: int
    x: int
    y: int


class TileID(BaseID):
    """
    TileID to represent the z(zoom), x and y coordinates of a tile.
    Accepts either a single mercantile.Tile, and a combination list iterables (lists and tuples) and kwargs.
    While this may on the surface look hacky, it works better than several alternatives attempted.
    """

    warn: bool = True

    def __init__(self, *args: Tuple[Any], **kwargs: Dict[str, Any]) -> None:
        new_args = []
        for a in args:
            if isinstance(a, mercantile.Tile):
                new_args += [a.z, a.x, a.y]
            else:
                try:
                    iter(a)
                    new_args += [x for x in a]
                except TypeError:
                    new_args += [a]
        args = tuple(new_args)
        super().__init__(*args, **kwargs)
        self._warn()

    def _warn(self) -> None:
        """
        Warnings for things that will probably be a problem, but may not always be.
         - Warns if z and y are outside the maximum bounds of the zxy tile system.
         - Warns is the zoom out outside the allowed range specified in constants.py
        """
        if self.warn:
            if self.y > 2 ** self.z or self.x > 2 ** self.z:
                warnings.warn("x and y should be in the range [0..2 ** z].")
            if self.x < 0 or self.y < 0:
                warnings.warn("x and y sould be > 0")
            if not constants.min_zoom <= self.z <= constants.max_zoom:
                warnings.warn(
                    f"zoom not in [{constants.min_zoom}..{constants.max_zoom}]."
                )

    @property
    def zoom(self) -> int:
        return self.z

    def __iter__(self) -> Iterable[Tuple[int, int, int]]:
        return iter((self.z, self.x, self.y))

    def __len__(self) -> int:
        return 3

    @property
    def asmrcantile(self) -> mercantile.Tile:
        return mercantile.Tile(x=self.x, y=self.y, z=self.z)

    @property
    def urlform(self):
        return f"{self.z}/{self.x}/{self.y}"

    @property
    def parent(self) -> "TileID":
        """
        Return the TileId for the parent.
        """
        return TileID(mercantile.parent(self.asmrcantile))

    @property
    def children(self) -> List["TileID"]:
        """
        Returns a list of this tile's 4 child tile ids.
        """
        return [TileID(mt) for mt in mercantile.children(self.asmrcantile)]

    @property
    def siblings(self) -> List["TileID"]:
        """
        Returns a list of this tile's siblings.
        """
        return [
            TileID(mt)
            for mt in mercantile.children(mercantile.parent(self.asmrcantile))
        ]


@dataclass
class Tile:
    tid: TileID
    img: "Image" = field(default=imager.blank())
    name: str = "tile"
    resolution: int = 256
    blank: bool = True

    def __post_init__(self):
        self.resolution = self.img.size[0]

    @property
    def size(self) -> Tuple[int, int]:
        return self.img.size

    def save(self, path: Path = Path(".")) -> None:
        b = "_b" if self.blank else ""
        fn = path / Path(
            f"{self.name}_z{self.tid.z}-x{self.tid.x}-y{self.tid.y}_r{self.resolution}{b}.png"
        )
        self.img.save(fn, "png")

    def __setattr__(self, name: str, value: Any) -> None:
        """
        The purpose of this function is because there can't be a @setter on a field.
        And it'd be useful to have tile.img = img, True to ensure the tiles knows this image is blank.
        Maybe there's a better way of doing this, but there wasn't an obvious way to do this.
        Consider the below essentially:
        @img.setter
        def img(self, img, blank=True):
            ...
        """
        if name == "img":
            img = value
            self.blank = False
            blank = False
            if isinstance(value, tuple):
                img, blank = value
            if blank:
                self.blank = blank
            self.resolution = img.size[0]
            object.__setattr__(self, "img", img)
        else:
            object.__setattr__(self, name, value)

    @property
    def asbytes(self) -> bytes:
        d = BytesIO()
        self.img.save(d, "png")
        return BytesIO(d.getvalue())

    @property
    def center(self) -> Point:
        """
        Returns the center of the tile as a (lat, lon) pair. Assumes flat projection.
        """
        bbox = self.bounds
        return Point((bbox.west + bbox.east) / 2, (bbox.north + bbox.south) / 2)

    @property
    def bounds(self) -> geo.LatLonBBox:
        """
        Get a mercantile bounding box for tile.
        """
        mt = mercantile.bounds(self.asmercantile)
        return geo.LatLonBBox(
            west=mt.west, south=mt.south, east=mt.east, north=mt.north
        )

    @property
    def parent(self) -> "Tile":
        """
        Return the TileId for the parent.
        """
        return self.blank(self.tid.parent)

    @property
    def children(self) -> "TileArray":
        """
        Returns an empty TileArray of this tile's 4 child tile ids.
        """
        tiles = {t: Tile(t) for t in self.tid.children}
        ta = TileArray()
        return ta.from_dict(tiles)

    @property
    def siblings(self) -> "TileArray":
        """
        Returns an empty TileArray of this tile's siblings.
        """
        tiles = {t: Tile(t) for t in self.tid.siblings}
        ta = TileArray()
        return ta.from_dict(tiles)

    @property
    def x(self) -> int:
        return self.tid.x

    @property
    def y(self) -> int:
        return self.tid.y

    @property
    def z(self) -> int:
        return self.tid.z

    @property
    def zoom(self) -> int:
        return self.z

    @property
    def asmercantile(self) -> mercantile.Tile:
        return mercantile.Tile(z=self.z, x=self.x, y=self.y)

    def __len__(self) -> int:
        return 0 if self.blank else self.resolution

    def composite_image(self, foreground_tile: "Tile") -> "Tile":
        new_img = imager.transparency_composite(self.img, foreground_tile.img)
        return Tile(self.tid, img=new_img)


@dataclass
class TileArray(dict):
    """
    Stores a 2d array of tiles. Tiles are accessed by their TileID.
    Internally, stores data as a dictionary, with the key being a TileID and the value being the Tile.
    """

    zoom_level: int = None
    name: str = "TileArray"

    def __post__init__(self) -> None:
        s = set(t.z for t in self.keys())
        if len(s) != 1:
            raise self.MixedZoomError

    # Couldn't figure out a clean way to do this in init, so it's here.
    def from_dict(self, d: Dict[TileID, Tile]) -> "TileArray":
        for k, v in d.items():
            self[k] = v
        return self

    def __str__(self) -> str:
        return str(dict(self))

    def __repr__(self) -> str:
        return str(dict(self))

    def __getitem__(self, k: TileID) -> Tile:
        return super().__getitem__(k)

    def __setitem__(self, k: TileID, v: Tile) -> None:
        if not isinstance(k, TileID):
            raise ValueError("key must be a TileID")
        if not isinstance(v, Tile):
            raise ValueError("value must be a Tile")
        if self.zoom is None:
            self.zoom = k.z
        elif self.zoom != k.z:
            raise self.MixedZoomError
        return super().__setitem__(k, v)

    @property
    def zoom(self) -> int:
        return self.zoom_level

    @zoom.setter
    def zoom(self, new_zoom: int) -> None:
        """
        Sets the zoom level of this TileArray.
        Args:
            new_zoom (int): New zoom level to set.
        Raises:
            self.ZoomRangeError: If the zoom range is outside that allowed.
            self.MixedZoomError: If the tiles have mixed zooms.
        """
        # Make sure we keep within our zoom bounds.
        if not constants.min_zoom <= new_zoom <= constants.max_zoom:
            raise self.ZoomRangeError(
                f"zoom: {new_zoom} not between {constants.min_zoom} and {constants.max_zoom}"
            )
        # Is this the first item getting added to the array?
        if len(self) != 0 and self.zoom_level is not None:
            # Are we changing an existing zoom not as the first item?
            if self.zoom_level != new_zoom:
                msg = "Can't change zoom level with existing non-empty TileArray."
                raise self.MixedZoomError(msg)
        else:
            self.zoom_level = int(new_zoom)

    @property
    def x_min(self) -> int:
        return min(t.x for t in self.keys())

    @property
    def x_max(self) -> int:
        return max(t.x for t in self.keys())

    @property
    def y_min(self) -> int:
        return min(t.y for t in self.keys())

    @property
    def y_max(self) -> int:
        return max(t.y for t in self.keys())

    @property
    def xy_dims(self) -> Tuple[int, int]:
        return (self.x_max - self.x_min + 1, self.y_max - self.y_min + 1)

    @property
    def bounds(self) -> geo.LatLonBBox:
        """Returns the maximal bounds that this TileArray covers."""
        bboxes = [t.bounds for t in self.values()]
        left = min([x.left for x in bboxes])
        right = max([x.right for x in bboxes])
        top = max([x.top for x in bboxes])
        bottom = min([x.bottom for x in bboxes])
        return geo.LatLonBBox(left=left, right=right, top=top, bottom=bottom)

    def ids_to_mercantiles(self) -> List[mercantile.Tile]:
        return [t.asmercantile for t in self.keys()]

    def find_line_sibling_tile_ids(self) -> Optional["TileArray"]:
        """
        This function finds the sibling tiles that are above/below or left/right of a line of tiles.
        Which direction to take the extra tiles from depends on which direction shares the same parent tile.
        Returns:
            TileArray: The new tiles, or None if they aren't in a line.
                This array will be populated with any tiles that are in the source TileArray.
        """
        x_dim, y_dim = self.xy_dims
        if x_dim != 1 and y_dim != 1:
            return None
        if x_dim == y_dim == 1:
            return None
        # print(f"x=({self.x_min}, {self.x_max}), y=({self.y_min}, {self.y_max})")
        # print(f"x_dim={x_dim}, y_dim={y_dim}")

        # Find the siblings of the tile
        sibling_tile_ids = set()
        for t in self.values():
            # print("T  ", t)
            for s_tid in t.siblings:
                # print("s_tid", s_tid)
                sibling_tile_ids.add(s_tid)
        # print(f"sibling_tile_ids: {len(sibling_tile_ids)}")

        filtered_siblings = TileArray()
        for sid in sibling_tile_ids:
            blank = Tile(sid)
            tile = self.get(sid, blank)
            if x_dim == 1:
                if sid.y in range(self.y_min, self.y_min + y_dim):
                    filtered_siblings[sid] = tile
            if y_dim == 1:
                if sid.x in range(self.x_min, self.x_min + x_dim):
                    filtered_siblings[sid] = tile
        # print(f"filtered_siblings: {len(filtered_siblings)}")
        # print(filtered_siblings)
        return filtered_siblings

    # def make_parent(tiles, scale=False, quality=1):
    #     """
    #     Combines 4 tiles into a parent tile only if they are siblings.
    #     Args:
    #         tiles (list(Tile)): List of 4 tiles to combine into a parent tile.
    #         scale (bool, optional): If True, scale the resulting tile down to preserve the tile resolution.
    #         quality (int, optional): Quality level, from 0 to 4. Higher quality is slower. Defaults to 1.
    #     Returns:
    #         Tile: A parent tile. None if they don't share a parent.
    #     """

    #     if len({tile.parent for tile in tiles}) != 1:
    #         return None
    #     # new_image = composite_quad(tiles)
    #     # res = tiles[0].resolution + 1
    #     # if scale:
    #     #     res -= 1
    #     #     size = res * 256
    #     #     new_image = new_image.resize((size, size), resample=resample["quality"])
    #     parent_id = tiles[0].parent
    #     return Tile(parent_id, new_image, name=tiles[0].name, resolution=res)

    def _composite_all(self) -> "Image":
        """
        Takes all of the tiles in the TileArray and composited them into one big image.
        Returns:
            Image: the output image.
        """
        idx_imgs = {(tid.x, tid.y): img.img for tid, img in self.items()}
        return imager.composite_mxn(idx_imgs)

    def _composite_layer(self, foreground_ta: "TileArray") -> "TileArray":
        """
        Composites a given tiliearray over this tile array.
        If foreground tiles fall outside the lower layer, they are ignored.
        Zoom needs to match on the two arrays at this point.
        Args:
            foreground_ta (TileArray): forground image to composite. Needs to be RBGA.
        Returns:
            TileArray: new composited tiles.
        """
        x_range = range(self.x_min, self.x_max + 1)
        y_range = range(self.y_min, self.y_max + 1)
        z = self.zoom_level
        fg_z = foreground_ta.zoom_level
        if z != fg_z:
            raise self.MixedZoomError(
                f"Can't composite with different zoom levels (bg={z}, fg={fg_z})"
            )
        tids_check = [TileID(z, x, y) for x in x_range for y in y_range]
        fg_tids = [x for x in foreground_ta.keys() if x in tids_check]
        result = TileArray()
        for tid, tile in self.items():
            if tid in fg_tids:
                result[tid] = tile.composite_image(foreground_ta[tid])
                fg_tids.remove(tid)
            else:
                result[tid] = tile
        for tid in fg_tids:
            result[tid] = foreground_ta[tid]
        return result

    def composite_layers_out(self, foreground_ta: "TileArray") -> "Image":
        """
        Composites two tilearrays together and produces a final image.
        Args:
            foreground_ta (TileArray): forground image to composite. Needs to be RBGA.
        Returns:
            Image: The final output image.
        """
        imgs = self._composite_layer(foreground_ta)
        return imgs._composite_all()

    class MixedZoomError(Exception):
        def __init__(
            self, message="Multiple zoom levels in a TileArray not supported."
        ) -> None:
            self.message = message
            super().__init__(self.message)

    class ZoomRangeError(Exception):
        def __init__(self, message) -> None:
            self.message = message
            super().__init__(self.message)


def tileid_from_bbox(self, bbox: geo.LatLonBBox, tile_scale: int = 1) -> List[TileID]:
    """
    Gets the tile_ids given a bounding box.
    Args:
        bbox (tuple): (left, upper, right, bottom) mercantile compatible bounding box.
        tile_scale (int, optional): Essentially how much zoom to add. +ve numbers zoom in, -ve zoom out. 0 treated as 1: no zoom change. Defaults to 1.
    Returns:
        List[TileID]: TileIDs covering the box.
    """
    tile_ids = []
    mt = mercantile.bounding_tile(*bbox)
    tm = TileID(z=mt.z, x=mt.x, y=mt.y)
    if tile_scale < 0:
        start_z = tm.z
        end_z = tm.z + tile_scale
        for _ in range(start_z, end_z, -1):
            tm = tm.parent()
            if tm.z == 0:
                break
        tile_ids = [tm]
    elif tile_scale in (0, 1):
        tile_ids = [tm]
    else:
        tile_ids = [tm]
        start_z = tm.z
        end_z = tm.z + tile_scale
        for _ in range(start_z, min(end_z, self.max_zoom)):
            new_ids = []
            for t in tile_ids:
                new_ids += t.children()
            tile_ids = new_ids
    return [TileID(z=m.z, x=m.x, y=m.y) for m in tile_ids]


def empty_tilearray_from_ids(tile_ids: List[Union[TileID, Tuple[int]]]) -> TileArray:
    tile_array = TileArray()
    for tid in tile_ids:
        tile_id = TileID(tid)
        tile = Tile(tid=tile_id)
        tile_array[tile_id] = tile
    return tile_array


def bounding_box_to_tiles(
    bbox: geo.LatLonBBox, start_zoom: int = 0, size: int = 512
) -> "TileArray":
    """
    Takes a bounding box and finds the TileArray that best covers that bounding box.
    This may result in tiles that are across the anti-meridian from the rest.

    The end result is a TileArray of either 4, 6 or 9 tiles that fully contain the bounding box.


    """
    n = bbox.north
    w = bbox.west
    s = bbox.south
    e = bbox.east
    zoom_level = start_zoom

    bad_bbox = False
    # Is this likely to be an incorrect bounding box that forgets that the map is actually a cynlinder?
    # This is really just a heuristic test for an incorrect bounding box, because it's hard to deal with bad data.
    if w < -178.0 or e > 178.0:
        print("Probable incorrect bounding box due to antimeridian crossing.")
        bad_bbox = True

    if w > e and not bad_bbox:
        print("Bbox crosses anti-meridian.")
        bbox_west, bbox_east = bbox.am_split()
        tile_west, alt_west, zoom_west = _bounding_box_candidates(
            bbox_west, zoom_level, size
        )
        tile_east, alt_east, zoom_east = _bounding_box_candidates(
            bbox_east, zoom_level, size
        )
        best_west = _best_tile_covering(bbox_west, tile_west, alt_west, zoom_west)
        best_east = _best_tile_covering(bbox_east, tile_east, alt_east, zoom_east)
        return best_west, best_east
    else:
        tile_ids, tile_ids_alt, end_zoom_level = _bounding_box_candidates(
            bbox, zoom_level, size
        )
        best = _best_tile_covering(bbox, tile_ids, tile_ids_alt, end_zoom_level)
        if not bad_bbox:
            return (best,)
        else:
            return TileArray(zoom_level=end_zoom_level)
    # print("am:", am)
    # print("tile_ids:")
    # pprint(tile_ids)
    # print("tile_ids_alt: ")
    # pprint(tile_ids_alt)


def _best_tile_covering(
    in_bbox: geo.LatLonBBox,
    tile_ids: TileArray,
    alt_tile_ids: TileArray,
    zoom_level: int,
) -> TileArray:
    max_idx = max(max(tile_ids.keys()), max(alt_tile_ids.keys()))
    best = alt_tile_ids.get(max_idx, tile_ids[max_idx])
    print("input bounds:\n", in_bbox)
    bbox_pix = geo.bounding_lat_lon_to_pixels(in_bbox, zoom_level)
    print("pixels:", bbox_pix, bbox_pix.xy_dims)
    print("new bounds:\n", best.bounds)
    nb_pix = geo.bounding_lat_lon_to_pixels(best.bounds, zoom_level)
    print("pixels:", nb_pix, nb_pix.xy_dims)
    print("contains?", best.bounds.contains(in_bbox))
    return best


def _bounding_box_candidates(
    bbox: geo.LatLonBBox, zoom_level: int, size: int
) -> Tuple[Dict[int, "TileArray"], int]:
    n = bbox.north
    w = bbox.west
    s = bbox.south
    e = bbox.east
    tile_ids = {}
    tile_ids_alt = {}
    while zoom_level < constants.max_zoom:
        # If the bounding box at this zoom is larger than our maximum size, we've gone too far.
        bbox_pix = geo.bounding_lat_lon_to_pixels(bbox, zoom_level)
        x_dim, y_dim = bbox_pix.xy_dims
        print("xy dims:", bbox_pix.xy_dims, zoom_level)
        if x_dim > size or y_dim > size:
            break

        # First, get the bounding box for this zoom level.
        mt_tids = list(
            mercantile.tiles(east=e, north=n, west=w, south=s, zooms=zoom_level)
        )
        ta = empty_tilearray_from_ids(mt_tids)
        tile_ids[zoom_level] = ta

        # Do our current set of tiles still cover the whole bounding box?
        if not ta.bounds.contains(bbox):
            break

        # Do we have a line of tiles that would better cover this bbox?
        if len(ta) in (2, 3):
            tile_ids_alt[zoom_level] = ta.find_line_sibling_tile_ids()
        zoom_level += 1

    return tile_ids, tile_ids_alt, zoom_level
