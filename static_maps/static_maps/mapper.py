from dataclasses import dataclass, field
from io import BytesIO
from typing import Dict, List, Optional, Tuple

import requests
from copy import deepcopy

import static_maps.imager as imager
from static_maps.geo import (
    LatLon,
    LatLonBBox,
    bounding_pixels_to_lat_lon,
    split_bbox_half,
    remap_split_bbox,
)
from static_maps.imager import (
    Image,
    debug_draw_pix_bbox,
    swap_left_right,
    find_crop_bounds,
)
from static_maps.tiles import Tile, TileArray, TileID, bounding_box_to_tiles


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
        bounding_values = LatLonBBox(0, 0, 0, 0).all_aliases
        vals = {k.lower(): v for k, v in res.items() if k.lower() in bounding_values}
        return LatLonBBox(**vals)

    def get_bbox_tiles(
        self, bbox: LatLonBBox, start_zoom: int = 0, size: int = 512
    ) -> TileArray:
        tiles = bounding_box_to_tiles(bbox, start_zoom, size)
        return tiles

    class AuthMissingError(Exception):
        def __init__(self, message="Missing auth for map.") -> None:
            self.message = message
            super().__init__(self.message)

    def find_image_bbox(self, test_img: Image, zoom: int = 0) -> List[LatLonBBox]:
        """
        Given an image, finds a lat lon bounding box for the image.
        If the image is split across the antimeridian (-180/180) then it returns a split bounding box.
        The algorithm is simple. Cut the image on the prime meridian and paste on the anti-meridian.
            Once that's done, recheck to see if the bbox is smaller. If it is, then the image must've crossed the anti-meridian.
        Args:
            test_img (Image): Image to test to find the bbox(es).
            zoom (int, optional): Zoom level of the input time. Defaults to 0.
                At zoom > 0, this will simply return the latlon bounds for a tile.
        Returns:
            List[LatLonBBox]: One bounding box covering all of the pixels in the picture. Two is crossing the antimeridian results in a tigher bounding box.
        """
        tile_size = test_img.size[0]
        bbox = test_img.getbbox()
        print("bbox:", bbox)
        swapped_image = swap_left_right(test_img)
        swapped_bbox = swapped_image.getbbox()

        if zoom > 0 or swapped_bbox.area >= bbox.area:
            res = bounding_pixels_to_lat_lon(bbox, zoom, tile_size)
            return [LatLonBBox(*res)]
        else:
            left_half, right_half = split_bbox_half(swapped_bbox, tile_size)
            remap_left_half = remap_split_bbox(left_half, tile_size)
            remap_right_half = remap_split_bbox(right_half, tile_size)

            debug_draw_pix_bbox([bbox], test_img, "test_nosplit_bbox")
            debug_draw_pix_bbox([left_half, right_half], test_img, "test_split_bbox")
            debug_draw_pix_bbox(
                [remap_left_half, remap_right_half], test_img, "test_remap_bbox"
            )

            left = bounding_pixels_to_lat_lon(remap_left_half, zoom, tile_size)
            right = bounding_pixels_to_lat_lon(remap_right_half, zoom, tile_size)

            return [LatLonBBox(*left), LatLonBBox(*right)]


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

    @staticmethod
    def size_map(s: int) -> str:
        m = {256: "H", 512: "1", 1024: "2", 2048: "3", 4096: "4"}
        return f"@{m.get(s, '1')}x.png"

    def get_tiles(
        self, taxon_key: int, tile_array: TileArray, mode: str = "hex", **params
    ) -> TileArray:
        print("gt ta:", tile_array)
        params["taxonKey"] = params.get("taxon_key", taxon_key)
        if "mode" in params:
            mode = params.pop("mode")
        funcmap = {"hex": self.get_hex_tile, "square": self.get_square_tile}
        func = funcmap.get(mode, self.get_hex_tile)

        new_tilearray = TileArray()
        for tid in tile_array:
            # TODO: this call can return None on HTTP errors. Handle that.
            tile = func(tile_id=tid, **params)
            new_tilearray[tid] = tile
        return new_tilearray

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
        fmt = self.size_map(params.get("tile_size", self.map_defaults["size"]))
        tile_id = params.get("tile_id", tile_id)
        if tile_id is None:
            raise TypeError("tile_id required for map tile lookup.")

        taxon_key = params.get("taxonKey", "None")
        if params.get("tile_size", None):
            params.pop("tile_size")
        url = f"v2/map/occurrence/density/{tile_id.z}/{tile_id.x}/{tile_id.y}{fmt}"
        resp = requests.get(self.base_url + url, params=params)
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

    def get_bbox(self, taxon_key: int) -> LatLonBBox:
        """
        Given a taxon key, query the GBIF map API for a bounding box for the taxon.
        Args:
            taxon_key (int): The taxon ID to look up.
        Returns:
            LatLonBBox: bounding box for the taxon key.
        """
        params = {"taxonKey": taxon_key}
        url = "v2/map/occurrence/density/capabilities.json"
        metadata = self.get_bbox_meta(url, params)
        left = metadata.left
        right = metadata.right
        top = metadata.top
        bottom = metadata.bottom
        bbox = LatLonBBox(left=left, top=top, right=right, bottom=bottom)
        return bbox


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


def generate_gbif_mapbox_range(
    taxon_key: int, gbif: GBIF, mapbox: MapBox, map_size: int = 512
) -> "Image":
    """
    Given a taxon_key, generates a range map of the given size.
    Requires a configured GBIF object for the foreground, and a MapBox object for the base tiles.
    Args:
        taxon_key (int): taxon key to generate the map for.
        gbif (GBIF): base range map object.
        mapbox (MapBox): base layer map object.
        map_size (int, optional): size of the map, in pixels to generate. Deftaults to 512.
    Returns:
        Image: The finished range map image.
    """
    range_bbox = gbif.get_bbox(taxon_key)
    gbta = gbif.get_bbox_tiles(range_bbox, size=map_size // 2)
    if len(gbta) == 2:
        assert False
    else:
        gbta = gbta[0]

    # TODO: Handle AM crossing and bad bbox.
    mbta = deepcopy(gbta)
    gbif_tiles = gbif.get_tiles(taxon_key, gbta)
    mapbox_tiles = mapbox.get_tiles(mbta)

    # This would be better handled if the TileArray knew the bounding box of the pixels it contained.
    gbif_layer = gbif_tiles._composite_all()
    gbif_layer.save(f"bbox_get-{taxon_key}-{map_size}.png")
    _, _, _, _, _, fill_crop = find_crop_bounds(gbif_layer, map_size)

    c_tiles = mapbox_tiles._composite_layer(gbif_tiles)
    c_tiles.name = "gbif_range+mapbox"
    # This is our output map, but it still needs to be cropped to the proper area.
    uncropped_comp = c_tiles._composite_all()

    final_image = uncropped_comp.crop(fill_crop)
    return final_image
