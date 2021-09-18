import math
from collections import defaultdict, namedtuple
from dataclasses import dataclass, field
from typing import Any, DefaultDict, Dict, Iterable, List, Tuple, Union

import static_maps.constants as constants

Point = namedtuple("Point", ("x", "y"))
Pixel = namedtuple("Pixel", ("x", "y"))
LatLon = namedtuple("LatLon", ("lat", "lon"))

BBoxT = Union["BBoxBase", "DynamicBBox", "LatLonBBox", "PixBbox"]


@dataclass
class BBoxAlias(dict):
    base_names: Tuple[str] = ("left", "top", "right", "bottom", "xy_dims")
    """
    Stores aliases for a bounding box's attribute names. Se BBox for more.
    Usage notes:
        While the str() and repr() return sorted lists of mappings, the internal representation and reverse_map() is unsorted.
    """

    def __init__(self) -> None:
        bbox_aliases = {
            "top": ["maxy", "ymax"],
            "bottom": ["miny", "ymin"],
            "left": ["minx", "xmin"],
            "right": ["maxx", "xmin"],
        }
        for k, v in bbox_aliases.items():
            for a in v:
                self[a] = k
            self[k] = k

    def add(self, aliases: Dict[str, List]) -> None:
        for k, v in aliases.items():
            if k not in self.base_names:
                raise AttributeError("Can't add an alias to a non-existent attr.")
            for a in v:
                self[a] = k

    @property
    def reverse_map(self) -> DefaultDict[str, List]:
        d = defaultdict(list)
        for k, v in self.items():
            d[v] += [k]
        return d

    def __str__(self) -> str:
        s = ""
        rm = self.reverse_map
        for v in self.base_names:
            s += f"'{v}' aliases: {sorted(rm[v])}\n"
        return s

    def __repr__(self) -> str:
        a = dict((k, sorted(v)) for k, v in self.reverse_map.items())
        s = f"{type(self).__name__}(aliases={a}, base_names={self.base_names})"
        return s


@dataclass
class BBoxBase:
    left: float
    top: float
    right: float
    bottom: float
    point_type: namedtuple = field(default=Point, init=False, repr=False)

    @property
    def tl(self) -> int:
        return self.point_type(self.left, self.top)

    @property
    def br(self) -> int:
        return self.point_type(self.right, self.bottom)

    @property
    def x_dim(self) -> int:
        return max(self.left, self.right) - min(self.left, self.right)

    @property
    def y_dim(self) -> int:
        return max(self.top, self.bottom) - min(self.top, self.bottom)

    @property
    def xy_dims(self) -> Tuple[int, int]:
        return self.x_dim, self.y_dim

    @property
    def area(self) -> int:
        return self.x_dim * self.y_dim

    @property
    def center(self) -> Any:
        c_x = self.left + (self.right - self.left) / 2
        c_y = self.top + (self.bottom - self.top) / 2
        return self.point_type(c_x, c_y)

    def __iter__(self) -> Iterable[Tuple[int, int, int, int]]:
        return iter((self.left, self.top, self.right, self.bottom))

    def __eq__(self, cmp: Any) -> bool:
        if (
            isinstance(cmp, (tuple, list))
            and len(cmp) == 4
            or isinstance(cmp, type(self))
        ):
            a, b, c, d = cmp
            if (a, b, c, d) == (self.left, self.top, self.right, self.bottom):
                return True
        return False

    def __ne__(self, cmp: Any) -> bool:
        return not self.__eq__(cmp)


@dataclass
class DynamicBBox(BBoxBase):
    """
    Dynamic bounding box class. This is to make moving between different, disparate ways of doing bboxs easier by allowing attribute aliases.
    This means that bbox.top is equivalent to bbox.xmax, and allows for subclasses to add further aliases, such as bbox.top to bbox.maxlat or bbox.north
    There's also convenience functions to get the points for the corners, dimensions, center, area etc.

    This basically uses the base BBox class as the normal class, with this class effectively being a __pre__init__() function that dataclasses don't have.
    Yes, this is a hack and a half, but dynamic attribute names was important to make it easy to schlep data between figgerent formats.
    Usage notes:
         - Attribute names are case insensitive.
    Raises:
        AttributeError: If an attribute can't be get or set.
    """

    def __init__(self, *args, **kwargs):
        self._set_aliases_once(BBoxAlias())
        # print("args:", args)
        # print("aliases:", self.aliases)
        # print("kwargs:", kwargs)

        # Need to remap kwargs according to their aliases before storing them in the base class.
        new_kwargs = {self.aliases[k]: v for k, v in kwargs.items()}
        super().__init__(*args, **new_kwargs)

    def __setattr__(self, name: str, value: Any) -> None:
        new_name = self._alias(name)
        if not new_name:
            raise AttributeError(
                f"type object '{type(self).__name__}' has no attribute '{name}' (alias missing?)"
            )
        self._set(new_name, value)

    def _get(self, name: str) -> Any:
        return object.__getattribute__(self, name)

    def _set(self, name: str, value: Any) -> None:
        object.__setattr__(self, name, value)

    def _set_aliases_once(self, aliases: BBoxAlias) -> None:
        try:
            self._get("aliases")
        except AttributeError:
            self._set("aliases", aliases)

    def __getattr__(self, name: str) -> Any:
        new_name = self._alias(name)
        if not new_name:
            raise AttributeError(
                f"type object '{type(self).__name__}' has no attribute '{name}' (alias missing?)"
            )
        attr_name = self.aliases.get(name)
        return object.__getattribute__(self, attr_name)

    def _alias(self, alias: str) -> Union[str, None]:
        a = self._get("aliases")
        return a.get(alias.lower(), None)

    # Note that this does not ensure that the aliases are the same, just the values of the bounding box itself.
    # for that, repr(bboxa) == repr(bboxb) should work.
    def __eq__(self, cmp: Any) -> bool:
        return super().__eq__(cmp)

    def from_dict(self, d: Dict[str, Union[int, float]]) -> None:
        if len(d) != 4:
            raise ValueError("4 values required")
        for k, v in d.items():
            try:
                self._set(k, v)
            except AttributeError:
                raise AttributeError(
                    f"type object '{type(self).__name__}' has no attribute '{k}' (alias missing?)"
                )


latlon_aliases = BBoxAlias()
latlon_aliases.add(
    {
        "top": ["north", "maxlat"],
        "bottom": ["south", "minlat"],
        "left": ["west", "minlon", "minlng"],
        "right": ["east", "maxlon", "maxlng"],
        "xy_dims": ["range"],
    }
)


@dataclass
class LatLonBBox(DynamicBBox):
    srs: str = field(default="EPSG:3857", init=True)
    point_type: namedtuple = field(default=LatLon, init=False, repr=False)

    def __init__(self, *args, **kwargs):
        if "srs" in kwargs:
            self._set("srs", kwargs["srs"])
            del kwargs["srs"]
        super()._set("aliases", latlon_aliases)
        super().__init__(*args, **kwargs)

    @property
    def all_aliases(self):
        """Get a list of all the possible aliases. Useful for filtering larger dicts."""
        s = set()
        for x in self.aliases.reverse_map.values():
            for y in x:
                s.add(y)
        return list(s)

    # Note, lat/lon ordering is y/x ordering, so these are swapped from the superclass.
    @property
    def tl(self) -> int:
        return self.point_type(self.top, self.left)

    @property
    def br(self) -> int:
        return self.point_type(self.bottom, self.right)

    @property
    def area(self):
        raise NotImplementedError("Area for LatLonBBox not supported.")

    def __eq__(self, cmp: Any) -> bool:
        print("cmpL", cmp)
        if isinstance(cmp, type(self)) and cmp.srs != self.srs:
            return False
        return super().__eq__(cmp)

    def __ne__(self, cmp: Any) -> bool:
        return not self.__eq__(cmp)

    def contains(self, c: "LatLonBBox") -> bool:
        """True if self contains the candidate bbox completely."""
        return (
            self.left <= c.left
            and self.right >= c.right
            and self.top >= c.top
            and self.bottom <= c.bottom
        )

    def am_split(self) -> Union[Tuple["LatLonBBox"], None]:
        """Splits this bbox into two if it crosses the anti-meridian, west then east. If it doesn't, returns None."""
        if self.west > self.east or abs(self.east) > 180 or abs(self.west) > 180:
            west_part_west = self.west
            east_part_east = self.east
            # This means that west=-190, east=-170 becomes w=170, e=180, w=-180W, e=-170
            if self.west < -180:
                west_part_west = 360 + self.west
            elif self.east > 180:
                east_part_east = self.east - 360
            west_part = LatLonBBox(
                west=west_part_west, east=180.0, north=self.north, south=self.south
            )
            east_part = LatLonBBox(
                west=-180.0, east=east_part_east, north=self.north, south=self.south
            )
            return west_part, east_part
        else:
            return None


@dataclass(eq=False)
class PixBbox(BBoxBase):
    point_type: namedtuple = Pixel

    @property
    def center(self) -> Pixel:
        cx, cy = super().center
        return Pixel(round(cx), round(cy))


def truncate_latlon_precision(latlon: LatLon, zoom: int) -> LatLon:
    """
    Truncates the lat and lon to a proper precision level given the pixel size.
    https://wiki.openstreetmap.org/wiki/Precision_of_coordinates
    2^N is the ratio between pixel size (in meters) at zoom=0 and zoom=M. This is longitude invariant.
    Per the wiki page, this results in one decimal of precision for each decimal order of magnitude the ratio changes.
    Args:
        lat (float): latitude
        lon (float): longitude
        zoom (int): What zoom level is the tile these pixels came from?
    Returns:
        (int, int): (lat, lon) truncated.
    """
    decimal_accuracy = math.floor(math.log(2 ** zoom, 10)) + 1
    return LatLon(
        round(latlon.lat, decimal_accuracy), round(latlon.lon, decimal_accuracy)
    )


def lat_lon_to_pixels(latlon: LatLon, zoom: int, tile_size: int = 256) -> Pixel:
    """
    Calculates the (lat, lon) -> pixel(x, y) mapping.
    Args:
        lat (float): latitude
        lon (float): longitude
        zoom (int): zoom level of the tile.
        tile_size (int, optional): Size of the tile. Defaults to 256.
    Returns:
        (int, int): pixel (x, y) coordinate pair.
    """
    equator = constants.equator
    # Need to shift the origin.
    shift = equator / 2
    # What is the resolution of a pixel at the equator in meters, for our zoom level?
    resolution = (equator / tile_size) / (2 ** zoom)
    # Convert the lat and long to map xy coords.
    # Longitude is constant, but latitude varies based on distance from the equator.
    map_x = (latlon.lon * shift) / 180.0
    ex = math.degrees(math.log(math.tan((90 + latlon.lat) * math.pi / 360.0)))
    map_y = (ex * shift) / 180.0
    # Convert from xy to pixel coordinates.
    pixel_x = (shift + map_x) / resolution
    pixel_y = (shift + map_y) / resolution
    return Pixel(round(pixel_x), round(pixel_y))


def pixels_to_lat_lon(
    pix: Pixel, zoom: int, tile_size: int = 256, truncate: bool = True
) -> LatLon:
    """
    Calculates the pixel(x, y) -> (lat, lon) mapping.
    Args:
        pixel_x (int): pixel x coordinate.
        pixel_y (int): pixel y coordinate.
        zoom (int): zoom level of the tile.
        tile_size (int, optional): Size of the tile. Defaults to 256.
        truncate (bool, optional): Truncate the output to the actual level of precision the caltulation has. Defaults to True.
    Returns:
        (float, float): (lat, lon) coordinate pair.
    """
    equator = constants.equator
    # Need to shift the origin.
    shift = equator / 2
    # What is the resolution of a pixel at the equator in meters, for our zoom level?
    print("eq", equator, "ts", tile_size, "z", zoom)
    resolution = (equator / tile_size) / (2 ** zoom)
    # Convert from pixels to the mercator projection coords.
    map_x = pix.x * resolution - shift
    map_y = pix.y * resolution - shift
    # And the convert from the map xy to lat and lon.
    # Longitude is constant, but latitude varies based on distance from the equator.
    lon = 180 * (map_x / shift)
    ex = math.radians(180 * (map_y / shift))
    lat = math.degrees(2 * math.atan(math.exp(ex)) - math.pi / 2)
    latlon = LatLon(lat, lon)
    if truncate:
        return truncate_latlon_precision(latlon, zoom)
    return latlon


def bounding_pixels_to_lat_lon(
    pixels_bbox: PixBbox, zoom: int, tile_size: int = 256, truncate: bool = True
) -> LatLonBBox:
    """
    Convenience function for pixels_to_lat_lon() that takes a pixel bbox instead of just two pixels.
    """
    tl = pixels_to_lat_lon(pixels_bbox.tl, zoom, tile_size, truncate)
    br = pixels_to_lat_lon(pixels_bbox.br, zoom, tile_size, truncate)
    return LatLonBBox(*tl, *br)


def bounding_lat_lon_to_pixels(
    latlon: LatLonBBox, zoom: int, tile_size: int = 256
) -> PixBbox:
    """
    Convenience function for pixels_to_lat_lon() that takes a pixel bbox instead of just two pixels.
    Note that that origin is the bottom left, not the top left as pillow expects.
    """
    tl = lat_lon_to_pixels(latlon.tl, zoom, tile_size)
    br = lat_lon_to_pixels(latlon.br, zoom, tile_size)
    return PixBbox(*tl, *br)


def split_bbox_half(bbox: BBoxT, tile_size: int) -> List[BBoxT]:
    """Spluts a bounding box in halt."""
    tlx, tly = bbox.tl
    brx, bry = bbox.br
    ts = tile_size // 2
    T = type(bbox)
    return [
        T(left=tlx, top=tly, right=ts, bottom=bry),
        T(left=ts + 1, top=tly, right=brx, bottom=bry),
    ]


def remap_split_bbox(bbox: BBoxT, tile_size: int) -> BBoxT:
    """
    Remaps the coordinates in a split bounding box.
    """
    tlx, tly = bbox.tl
    brx, bry = bbox.br
    ts = tile_size // 2
    if tlx < ts:
        tlx += ts
        brx += ts
    else:
        tlx -= ts
        brx -= ts
    T = type(bbox)
    return T(left=tlx, top=tly, right=brx, bottom=bry)
