from collections import namedtuple
from dataclasses import dataclass, field
# from static_maps.geo_utils.geo_utils import LatLonBBox, LatLon
import requests
from io import BytesIO

from typing import List, NamedTuple, Tuple, Optional, Dict
# import sys
# import os


# sys.path.append(os.getcwd())
from static_maps.tiles import Tile, TileID, TileArray

from static_maps.tiles import Tile, TileID, TileArray, Any
from static_maps.imager import Image
import static_maps.imager as imager
# import static_maps.geo_utils.geo_utils as geo_utils
from static_maps.geo import LatLonBBox, LatLon

import pygbif as _pygbif

def new_init(self, x):
    super(_pygbif.maps.GbifMap, self).__init__()
    self.response = x
_pygbif.maps.GbifMap.__init__ = new_init


def get_token():
    with open("creds.txt", "r") as f:
        return f.read().strip()

@dataclass
class BaseMap:
    base_url: str
    map_name: str = "maptile"

    def download_tile_url(
        self, tid: TileID, tile_url: str, params: Dict[str, str] = {}
    ) -> Optional[Tile]:
        res = requests.get(self.base_url + tile_url, params=params)
        if res.status_code == 200:
            img = imager.image_from_response(res)
            tile = Tile(tid=tid, img=img, name=self.map_name)
            return tile
        else:
            print(res.status_code, res.url)
            return None

    def get_bbox_meta(self, bbox_url: str, url_params: Dict = {}) -> requests.Response:
        res = requests.get(self.base_url + bbox_url, params=url_params).json()
        vals = {k: v for k, v in res if k in LatLonBBox.aliases}
        return LatLonBBox(**vals)

    class AuthMissingError(Exception):
        def __init__(self, message="Missing auth for map.") -> None:
            self.message = message
            super().__init__(self.message)


@dataclass
class MapBox(BaseMap):
    token: str = ""
    base_url: str = "https://api.mapbox.com/"
    fmt: str = "jpg90"
    style: str = "satellite"
    high_res: bool = True
    map_name: str = "mapbox"

    def get_tiles(self, tile_ids: List[TileID]) -> TileArray:
        tile_array = TileArray(name="Mapbox")
        for tid in tile_ids:
            tile_array[tid] = self.get_tile(tid)
        return tile_array

    def get_tile(self, tid: TileID, **kwargs) -> Tile:
        """
        Downloads a tile given by the z, x and y coordinates with various options.
        Note that setting any of the parameters overrides the defaults from the object.
        Args:
            tid (TileID): tile id to download.
            fmt (str, optional): mapbox format. Defaults to "jpg90".
            style (str, optional): mapbox style. Defaults to "satellite".
            high_res (bool, optional): Enable high res (512x512) mode. Defaults to True.
        Raises:
            self.TokenMissingError: If there isn't a token.
        Returns:
            Tile: A tile representing this map tile or None if something failed.
        """
        fmt = self.fmt
        style = self.style
        high_res = self.high_res
        if "fmt" in kwargs:
            fmt = kwargs["fmt"]
        if "style" in kwargs:
            style = kwargs["style"]
        if "high_res" in kwargs:
            high_res = kwargs["high_res"]

        z, x, y = tid
        # If the resolution is douled, MapBox only server every 2nd zoom level.
        # So if we're in this state, we need to take the next higher zoom level.
        # if high_res and z % 2 != 0:
        #     z += 1
        if not self.token:
            raise self.AuthMissingError("Mapbox auth token not set.")
        params = {"access_token": self.token}
        hr = ""
        if high_res:
            hr = "@2x"
        url = f"v4/mapbox.{style}/{z}/{x}/{y}{hr}.{fmt}"
        print("murl:", self.base_url + url)
        tile_id = TileID(z=z, x=x, y=y)
        tile = self.download_tile_url(tid=tile_id, tile_url=url, params=params)
        return tile

    def get_geocode(
        self, input_string: str, country: str = "", bbox: LatLonBBox = None
    ) -> LatLon:
        """
        Given a text string, find a lat lon pair that matches is. This is only as good as the input string is.
        Currently has 0 error handling.
        Args:
            input_string (str): Text string to search.
            country (str, optional): ISO 3166 alpha2 country code to use. Multiple countries separated by commas. Defaults to ''.
            bbox (list, optional): List of the form: [min_lon, min_lat, max_lon, max_lat]. Defaults to [].

        Returns:
            tuple(float, float): A float containing the lat, long pair for the geocode.
        """
        if not self.token:
            raise self.AuthMissingError("Mapbox auth token not set.")
        params = {"access_token": self.token}
        if country:
            params["country"] = country
        if bbox:
            params["bbox"] = ",".join(bbox)
        url = f"geocoding/v5/mapbox.places/{input_string}.json?"
        res = requests.get(self.base_url + url, params=params).json()
        lat_lon = res["features"][0]["center"]
        return LatLon(*lat_lon)


@dataclass
class GBIF(BaseMap):
    base_url: str = "https://api.gbif.org/"
    # Don't change unless you are not using mapbox/really want to reproject tiles.
    srs: str = "EPSG:3857"
    # eBird Observational Dataset (EOD)
    dataset_key: str = "47f16512-bf31-410f-b272-d151c996b2f6"
    # This seems like a reasonable default right now.
    map_name: str = "gbif"
    noisy_http_errors: bool = True
    map_defaults: Dict = field(
        default_factory=lambda: {
            "style": "classic-noborder.poly",
            "size": 512,
            "HexPerTile": 30,
            "squareSize": 32,
        }
    )
    # Currently doesn't support vector tiles.
    _tile_size: int = field(default=512, init=False, repr=True)
    pygbif: Any = field(default=_pygbif, init=False, repr=True)

    def __post__init__(self):
        self._pygbif.caching(cache=False)

    @staticmethod
    def size_map(s: int) -> str:
        m = {256: "H", 512: "1", 1024: "2", 2048: "3", 4096: "4"}
        return f"@{m.get(s, '1')}x.png"

    def get_tiles(self, taxon_key: int, tile_array: TileArray, mode: str = "hex", **params) -> TileArray:
        params["taxonKey"] = params.get("taxon_key", taxon_key)
        if "mode" in params:
            mode = params.pop("mode")
        funcmap = {"hex": self.get_hex_tile, "square": self.get_square_tile}
        func = funcmap.get(mode, self.get_hex_tile)
        for tid in tile_array:
            tile = func(tile_id=tid, **params)
            if tile:
                tile_array[tid] = tile
        return tile_array

    def _get_tile(self, tile_id: TileID = None, **params) -> Tile:
        """
        Gets a tile for a specific taxon_key.
        Parameters that can be used as per: https://github.com/gbif/pygbif/blob/master/pygbif/maps/map.py
        Raises:
            TypeError: TileID is a required parameter
        Returns:
            Tile: Tile with the downloaded tile image attached to it.
        """
        params["style"] = params.get("style", self.map_defaults["style"])
        params["srs"] = params.get("srs", self.srs)
        # params["format"] = params.get("format", "@1x.png")
        params["format"] = self.size_map(
            params.get("tile_size", self.map_defaults["size"])
        )
        tile_id = params.get("tile_id", tile_id)
        if tile_id is None:
            raise TypeError("tile_id required for map tile lookup.")

        params["z"] = tile_id.z
        params["x"] = tile_id.x
        params["y"] = tile_id.y
        taxon_key = params.get('taxonKey', 'None')

        # print("gt_params", params)
        gbif_map = self.pygbif.maps.map(**params)
        resp = gbif_map.response
        print("gurl:", resp.url)

        sc = resp.status_code
        if sc in (200, 304):
            img = imager.image_from_response(resp)
        # the gbif api seems to return this in both error conditions and when there legitimately isn't any data.
        elif sc == 204:
            img = imager.blank("RGBA", (self._tile_size, self._tile_size)), True
        else:
            if self.noisy_http_errors:
                resp.raise_for_status()
            return None
        return Tile(tile_id, img=img, name=f"gbifmap_{taxon_key}")

    def get_hex_tile(self, tile_id: TileID, **params) -> Tile:
        """
        Gets a hex tile for a specific taxon_key.
        Raises:
            TypeError: TileID is a required parameter
        Returns:
            Tile: Tile with the downloaded tile image attached to it.
        """
        params["bin"] = params.get("bin", "hex")
        params["HexPerTile"] = params.get("HexPerTile", self.map_defaults["HexPerTile"])
        tile = self._get_tile(tile_id, **params)
        tile.name = "H" + tile.name
        return tile

    def get_square_tile(self, tile_id: TileID, **params) -> Tile:
        """
        Gets a square tile for a specific taxon_key.
        Args:
            taxon_key (int): GBIF taxon key to look up.
            tile_id (TileID): Tile we want to get.
        Raises:
            TypeError: TileID is a required parameter
        Returns:
            Tile: Tile with the downloaded tile image attached to it.
        """
        params["bin"] = params.get("bin", "square")
        params["squareSize"] = params.get("squareSize", self.map_defaults["squareSize"])
        tile = self._get_tile(tile_id, **params)
        tile.name = "S" + tile.name
        return tile

    def lookup_species(self, name: str) -> Optional[Tuple[str, str]]:
        """
        Searches for a GBIF taxononmy key given a name of a given species.
        Args:
            name (str): Name to search for.
        Returns:
            Optional[Tuple[str, str]]: ("species", "taxon_key") or (None, None)
        """
        name = requests.utils.quote(name)
        u = f"{self.base_url}v1/species/search/?q={name}&rank=SPECIES&limit=1&datasetKey={self.dataset_key}"
        r = requests.get(u)
        # print("url", u)
        # print("r", r, r.json())
        if r.json()["count"] == 0:
            return (None, None)
        r = r.json()["results"][0]
        if "nubKey" in r.keys():
            res = (r["species"], r["nubKey"])
        else:
            return (None, None)
        return res

    def get_bbox(self, taxon_key: str) -> LatLonBBox:
        params = {"taxonKey": taxon_key}
        url = "v2/map/occurrence/density/capabilities.json"
        metadata = self.get_bbox_meta(url, params)
        left = metadata["maxLng"]
        # if left == 0:
        #     left = -180
        # print("left", left)
        right = metadata["minLng"]
        top = metadata["maxLat"]
        bottom = metadata["minLat"]
        bbox = LatLonBBox(left=left, top=top, right=right, bottom=bottom)
        return bbox



#     def tileid_from_bbox(self, bbox, tile_scale=3):
#         """
#         Gets the tile_ids given a bounding box.
#         Args:
#             bbox (tuple): (left, upper, right, bottom) mercantile compatible bounding box.
#             tile_scale (int, optional): Essentially how much zoom to add. +ve numbers zoom in, -ve zoom out. 0 treated as 1: no zoom change. Defaults to 1.
#         Returns:
#             (TileID): Tuple containing TileID objects.
#         """
#         tile_ids = []
#         tm = mercantile.bounding_tile(*bbox)
#         if tile_scale < 0:
#             start_z = tm.z
#             end_z = tm.z + tile_scale
#             for _ in range(start_z, end_z, -1):
#                 tm = mercantile.parent(tm)
#                 if tm.z == 0:
#                     break
#             tile_ids = [tm]
#         elif tile_scale in (0, 1):
#             tile_ids = [tm]
#         else:
#             tile_ids = [tm]
#             start_z = tm.z
#             end_z = tm.z + tile_scale
#             for _ in range(start_z, min(end_z, self.max_zoom)):
#                 new_ids = []
#                 for t in tile_ids:
#                     new_ids += mercantile.children(t)
#                 tile_ids = new_ids
#         return [TileID(z=m.z, x=m.x, y=m.y) for m in tile_ids]


@dataclass
class eBirdMap:
    max_zoom: int = 12
    """
    Generates an eBird range map.
    Note that this isn't using a documented API, and so could break at any time.
    """

    def get_bbox(self, species_code, zoom=0):
        res = requests.get(
            f"https://ebird.org/map/env?rsid=&speciesCode={species_code}"
        )
        left, right, bottom, top = res.json().values()
        print("rbb: ", res.json())

        bbox = LatLonBbox(left=left, right=right, bottom=bottom, top=top)
        print("tiles bbox: ", bbox)


    def get_tiles(self, species_code, zoom):
        tile_ids = self.get_bbox(species_code, zoom)
        grid_scale = 20 if tile_ids[0].z >= 6 else 100
        r = requests.get(
            f"https://ebird.org/map/rsid?speciesCode={species_code}&gridScale={grid_scale}"
        )
        rsid = r.content.decode("ascii")
        print("rsid: ", rsid, "tiles: ", len(tile_ids))
        tiles = []
        for t in tile_ids:
            print(t)
            tile = self.download_tile(zoom=t.z, x=t.x, y=t.y, rsid=rsid)
            # print("Tile: ", tile)
            tile.name = f"ebird-{species_code}"
            tiles += [tile]
            # print(tile.z, tile.x, tile.y, tile.center, tile)
        return tiles

    def download_tile(self, zoom, x, y, rsid):
        url = f"https://geowebcache.birds.cornell.edu/ebird/gmaps?layers=EBIRD_GRIDS_WS2&format=image/png&zoom={zoom}&x={x}&y={y}&CQL_FILTER=result_set_id='{rsid}'"
        # print(f"Getting url: {url}")
        res = requests.get(url)
        # print(res)
        img = Image.open(BytesIO(res.content))
        return Tile(TileID(z=zoom, x=x, y=y), img=img, name=f"ebird-{rsid}")