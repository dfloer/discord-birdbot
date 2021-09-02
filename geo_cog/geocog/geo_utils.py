import requests
import re
from dataclasses import dataclass
from pprint import pprint
import PIL.Image as Image
from io import BytesIO
import mercantile
from collections import namedtuple

TileID = namedtuple("TileID", ("z", "x", "y"))

# Doesn't quite work yet.
def lat_lon_parse2(input_string, r=re):
    s = r.compile(r"^((\-?|\+?)?\d+(\.\d+)?),\s*((\-?|\+?)?\d+(\.\d+)?)$")
    res = r.fullmatch(s, input_string)
    print(res.groups())
    print("res: ", res)
    return res


def get_token():
    with open("creds.txt", "r") as f:
        return f.read().strip()


@dataclass
class MapBox:
    token: str = get_token()
    base_url: str = "https://api.mapbox.com/"

    def geocode(self, input_string, country="", bbox=[]):
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
        params = {"access_token": self.token}
        if country:
            params["country"] = country
        if bbox:
            params["bbox"] = ",".join(bbox)
        url = f"geocoding/v5/mapbox.places/{input_string}.json?"
        res = requests.get(self.base_url + url, params=params).json()
        lat_lon = res["features"][0]["center"]
        return tuple(lat_lon)

    def get_tile(self, z, x, y, fmt="jpg90", style="satellite", high_res=True):
        """[summary]

        Args:
            z (int): slippy zoom level
            x (int): slippy x tilie id
            y (int): slippy y tilie id
            fmt (str, optional): mapbox format. Defaults to "jpg90".
            style (str, optional): mapbox style. Defaults to "satellite".
            high_res (bool, optional): high res?. Defaults to True.
        Returns:
            Tile: A tile representing this map tile or None if something failed.
        """
        # If the resolution is douled, MapBox only server every 2nd zoom level.
        # So if we're in this state, we need to take the next higher zoom level.
        # if high_res and z % 2 != 0:
        #     z += 1
        params = {"access_token": self.token}
        hr = ""
        if high_res:
            hr = "@2x"
        url = f"v4/mapbox.{style}/{z}/{x}/{y}{hr}.{fmt}"
        print("murl:", self.base_url + url)
        res = requests.get(self.base_url + url, params=params)
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content))
            tile = Tile(tid=(z, x, y), img=img, name="mapbox")
            return tile
        else:
            print(res.status_code, res.url)
            return None


@dataclass
class GBIF:
    base_url: str = "https://api.gbif.org/"
    srs: str = "EPSG:3857"
    data_key: str = "47f16512-bf31-410f-b272-d151c996b2f6"
    # This seems like a reasonable default right now.
    max_zoom: int = 12

    def get_hex_map(
        self,
        zoom,
        x,
        y,
        taxon_key,
        year="",
        hex_per_tile=70,
        style="classic-noborder.poly",
        high_res=True,
    ):
        """
        First pass at generating a hex map tile.
        Lots of stuff hardcoded still.
        Args:
            zoom (int): slippy zoom level
            x (int): slippy x tilie id
            y (int): slippy y tilie id
            taxon_key (int): gbif taxon key
            year (str, optional): 4 digit year.. Defaults to ''.
            hex_per_tile (int, optional): Number of hexes per tile. Defaults to 70.
            style (str, optional): gbif map style. Defaults to "classic-noborder.poly".
            high_res (bool, optional): get tiles at 2x mode. Defaults to True.
        Returns:
            Tile: A tile representing this map tile or None if something failed.
        """
        source = "density"
        format = "@2x.png" if high_res else "@1x.png"
        params = {"taxonKey": taxon_key}
        params["bin"] = "hex"
        params["hexPerTile"] = hex_per_tile
        params["style"] = style
        if year:
            params["year"] = year
        params["srs"] = self.srs
        metadata = self.get_occurence_meta(taxon_key)
        print("metadata", metadata)
        bbox = self.get_bbox(metadata)
        print("bbox", bbox)
        tile_ids = self.tileid_from_bbox(bbox)
        print("tile_ids", tile_ids)
        tiles = []
        for t in tile_ids:
            url = f"v2/map/occurrence/{source}/{t.z}/{t.x}/{t.y}{format}"
            res = requests.get(self.base_url + url, params=params)
            img = Image.open(BytesIO(res.content))
            tiles += [Tile(t, img=img, name="gbif")]
        return tiles

    def lookup_species(self, name):
        """
        Searches for a GBIF taxononmy key given a name of a given species.
        Args:
            name (str): Name to search for.
        Returns:
            int: taxonomy key
        """
        name = requests.utils.quote(name)
        u = f"https://api.gbif.org/v1/species/search/?q={name}&rank=SPECIES&limit=1&datasetKey={self.data_key}"
        r = requests.get(u)
        print(u)
        print(r, r.json())
        if r.json()["count"] == 0:
            return (None, None)
        r = r.json()["results"][0]
        if "nubKey" in r.keys():
            res = (r["species"], r["nubKey"])
        else:
            return (None, None)
        return res

    def get_occurence_meta(self, taxon_key):
        u = f"https://api.gbif.org/v2/map/occurrence/density/capabilities.json?taxonKey={taxon_key}"
        r = requests.get(u)
        return r.json()

    def get_bbox(self, metadata):
        left = metadata["maxLng"]
        if left == 0:
            left = -180
        print("left", left)
        right = metadata["minLng"]
        top = metadata["maxLat"]
        bottom = metadata["minLat"]
        bbox = mercantile.Bbox(left=left, right=right, bottom=bottom, top=top)
        return bbox

    def tileid_from_bbox(self, bbox, tile_scale=1):
        """
        Gets the tile_ids given a bounding box.
        Args:
            bbox (tuple): (left, upper, right, bottom) mercantile compatible bounding box.
            tile_scale (int, optional): Essentially how much zoom to add. +ve numbers zoom in, -ve zoom out. 0 treated as 1: no zoom change. Defaults to 1.
        Returns:
            (TileID): Tuple containing TileID objects.
        """
        tile_ids = []
        tm = mercantile.bounding_tile(*bbox)
        if tile_scale < 0:
            start_z = tm.z
            end_z = tm.z + tile_scale
            for _ in range(start_z, end_z, -1):
                tm = mercantile.parent(tm)
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
                    new_ids += mercantile.children(t)
                tile_ids = new_ids
        return [TileID(z=m.z, x=m.x, y=m.y) for m in tile_ids]


@dataclass
class eBirdMap:
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

        bbox = mercantile.Bbox(left=left, right=right, bottom=bottom, top=top)
        # print("bbox: ", bbox)
        # print(f"bbox2: ({', '.join([str(x) for x in bbox])})")
        # target is to find 4 tiles that cover the bounded area. For a larger map, more tiles will be needed.
        while True:
            tile_ids = list(mercantile.tiles(*bbox, zoom))
            if len(tile_ids) >= 4:
                break
            else:
                zoom += 1
        return tile_ids

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

    def get_range_map(self, species_code, zoom=0, mapbox_style="satellite"):
        # TODO: support sizes other than 512x512.
        # TODO: support returning centered range maps.
        # TODO: make zoom set arbitary zoom
        # Currently crops to something that fits in the bounds of the given image, but it'll look better if it's centered.
        # Which means that more image tiles will need to be downloaded.
        out_size = 512  # TODO: Support sizes other than 512x512.
        mapbox = MapBox()
        ebird_tile_imgs = self.get_tiles(species_code, zoom)
        # print("ebird_tiles:", ebird_tiles)
        ebird_img = composite_mxn(ebird_tile_imgs)
        with open("ebird_comp_mxn.png", "wb") as f:
            ebird_img.save(f, "png")
        mapbox_tiles = [
            mapbox.get_tile(z=t.z, x=t.x, y=t.y, style=mapbox_style, high_res=False)
            for t in ebird_tile_imgs
        ]
        mapbox_image = composite_mxn(mapbox_tiles)
        with open("mapbox_comp_mxn.png", "wb") as f:
            mapbox_image.save(f, "png")
        # This is our output map, but it needs a final crop.
        new_img = comp(mapbox_image, ebird_img)
        crop_area, center, bbox, extra_tiles, fill_crop = find_crop_bounds(
            ebird_img, out_size
        )
        new_img_crop = new_img.crop(fill_crop)
        return new_img_crop


@dataclass
class Tile:
    tid: TileID
    img: Image
    name: str = "tile"
    resolution: int = 1

    def __post_init__(self):
        self.resolution = self.size[0] // 256
        # Just a tuple, list or similar.
        if not isinstance(self.tid, TileID):
            t = self.tid
            z, x, y = t
            self.tid = TileID(z=z, x=x, y=y)
            # attempt to detect getting in form of (x, y, z)
            # and convert to (z, x, y)
            # This won't always catch an issue.
            if z > 30 or y > 2 ** z or x > 2 ** z:
                self.tid = TileID(z=y, x=z, y=x)

    @property
    def size(self):
        return self.img.size

    def save(self):
        with open(
            f"{self.name}_z{self.tid.z}-x{self.tid.x}-y{self.tid.y}_r{self.resolution}.png",
            "wb",
        ) as f:
            self.img.save(f, "png")

    def composite(self, tile):
        # This only works with images that share an x, y, and z.
        # Sizes need to match, and no scaling is done otherwise.
        new_img = Image.composite(tile.img, self.img, tile.img)
        new_name = f"c{self.name}+{tile.name}"
        return Tile(self.tid, new_img, new_name)

    @property
    def asbytes(self):
        d = BytesIO()
        self.img.save(d, "png")
        return BytesIO(d.getvalue())

    @property
    def center(self):
        """
        Returns the center of the tile as a (lat, lon) pair. Assumes flat projection.
        """
        bbox = self.bounds
        print("bbox:", bbox)
        return ((bbox.west + bbox.east) / 2, (bbox.north + bbox.south) / 2)

    @property
    def bounds(self):
        """
        Get a mercantile bounding box for tile.
        """
        return mercantile.bounds(self.tid.x, self.tid.y, self.tid.z)

    @property
    def parent(self):
        """
        Return the tile id for the parent, in the form of z, x, y.
        """
        return mercantile.parent(self.tid.x, self.tid.y, self.tid.z)

    @property
    def children(self):
        """
        Returns a list of this tile's 4 child tile ids.
        """
        return mercantile.children(self.tid.x, self.tid.y, self.tid.z)

    @property
    def x(self):
        return self.tid.x

    @property
    def y(self):
        return self.tid.y

    @property
    def z(self):
        return self.tid.z

    @property
    def zoom(self):
        return self.z


def composite_mxn(tiles):
    """
    Composites tiles in an M x N array together. If the tiles are sparse, this won't work.
    Args:
        tiles (Tiles): Iterable of tiles to composite together.
    Returns:
        Image: All if the tiles composited together into one big image.
    Raises:
        TileCompositingError: if errors occuring during compositing or with preconditions.
    """
    print("---------------------")
    print("c2:", tiles)
    x_min = min(t.tid.x for t in tiles)
    x_max = max(t.tid.x for t in tiles)
    y_min = min(t.tid.y for t in tiles)
    y_max = max(t.tid.y for t in tiles)
    x_dim = x_max - x_min + 1
    y_dim = y_max - y_min + 1
    print(f"x=({x_min}, {x_max}), y=({y_min}, {y_max})")
    print(f"x_dim={x_dim}, y_dim={y_dim}")

    # Check for holes.
    if x_dim * y_dim != len(tiles):
        msg = f"{len(tiles)} expected, got {x_dim * y_dim}."
        raise TileCompositingError(msg)
    # Make sure that all of the tiles are the same size.
    if len(set(t.size for t in tiles)) != 1:
        msg = "All tiles need to be the same size."
        raise TileCompositingError(msg)
    # Make sure images are the same mode.
    if len(set(t.img.mode for t in tiles)) != 1:
        msg = "Mixed tile image modes."
        raise TileCompositingError(msg)

    tt = tiles[0]

    tile_size = tt.resolution * 256
    output_size = tile_size * x_dim, tile_size * y_dim
    print("os:", output_size)

    if tt.img.mode == "RGB":
        print("RGB")
        new_image = Image.new("RGB", output_size)
    else:
        print("RGBA")
        new_image = Image.new("RGBA", output_size, (0, 255, 255, 0))
    for x, y in [(a, b) for a in range(x_dim) for b in range(y_dim)]:
        curr_tile = [
            tile for tile in tiles if tile.x == x + x_min and tile.y == y + y_min
        ][0]
        # Get the coordinates of the corner.
        x_coord, y_coord = [tile_size * a for a in (x, y)]
        print("corner:", x_coord, y_coord)
        t_img = curr_tile.img

        if t_img.mode == "RGBA":
            print("_RGBA_", new_image.mode)
            new_image.alpha_composite(t_img, (x_coord, y_coord))
        else:
            print("_RGB_", new_image.mode)
            new_image.paste(
                t_img, (x_coord, y_coord, x_coord + tile_size, y_coord + tile_size)
            )
    print("---------------------")
    return new_image


def calc_extra_tiles(tiles, extra_tiles):
    left = min(t.tid.x for t in tiles) - extra_tiles[0]
    upper = min(t.tid.y for t in tiles) - extra_tiles[1]
    right = max(t.tid.x for t in tiles) + extra_tiles[2]
    lower = max(t.tid.y for t in tiles) + extra_tiles[3]
    return (left, upper, right, lower)


def find_crop_bounds(image, output_size=512):
    """
    Calculates the crop for a given image.
    Args:
        image (Image): input image to calculate the crop for.
        tile_size (int, optional): [description]. Defaults to 512.
    Raises:
        NotRGBAError: We can only find pixels that contain data on RGBA images, as alpha = 0 is no data.
    Returns:
        [tuple]: (crop_area, center, bbox, extra_tiles)
            Where "crop_area" is the area this tile would be cropped to if it was output_size pixels on a side.
            and "center" is the center of the area that was cropped.
            and "bbox" is the maximum bounding box for the pixels in the source image.
            and "extra_tiles" is whether or not extra tiles need to be grabbed in the form (left, upper, right, bottom).
            and "fill_crop" is the bounding box for a crop that stays within the current image.

    """
    if image.mode != "RGBA":
        raise NotRGBAError
    bbox = image.getbbox()
    # x_dim = bbox[2] - bbox[0]
    # y_dim = bbox[3] - bbox[1]
    size_x, size_y = image.size
    center = (bbox[2] + bbox[0]) // 2, (bbox[3] + bbox[1]) // 2
    left = center[0] - output_size // 2
    upper = center[1] - output_size // 2
    right = center[0] + output_size // 2
    lower = center[1] + output_size // 2
    crop_area = (left, upper, right, lower)
    # print("ideal crop:", crop_area)
    # print(f"minimal crop area: {x_dim}, {y_dim}")
    extra_tiles = [0, 0, 0, 0]
    fill_left = left
    fill_upper = upper
    if left < 0:
        extra_tiles[0] = 1
        fill_left = 0
    if upper < 0:
        extra_tiles[1] = 1
        fill_upper = 0
    if right > size_x:
        extra_tiles[2] = 1
        fill_left = 0
    if lower > size_y:
        extra_tiles[3] = 1
        fill_upper = 0
    fill_crop = (
        fill_left,
        fill_upper,
        fill_left + output_size,
        fill_upper + output_size,
    )
    return crop_area, center, bbox, extra_tiles, fill_crop


class NotRGBAError(Exception):
    pass


class TileCompositingError(Exception):
    """
    Raised when Tile compositing fails.
    """

    def __init__(self, message="An error occured in compositing."):
        self.message = message
        super().__init__(self.message)


def composite_quad(tiles):
    """
    Takes 4 tiles and composites then together.
    """
    return composite_mxn(tiles)


def make_parent(tiles, scale=False, quality=1):
    """
    Combines 4 tiles into a parent tile only if they are siblings.
    Args:
        tiles (list(Tile)): List of 4 tiles to combine into a parent tile.
        scale (bool, optional): If True, scale the resulting tile down to preserve the tile resolution.
        quality (int, optional): Quality level, from 0 to 4. Higher quality is slower. Defaults to 1.
    Returns:
        Tile: A parent tile. None if they don't share a parent.
    """
    quality = max(min(quality, 4), 0)
    resample = [
        Image.Nearest,
        Image.BILINEAR,
        Image.HAMMING,
        Image.BICUBIC,
        Image.LANCZOS,
    ]
    if len({tile.parent for tile in tiles}) != 1:
        return None
    new_image = composite_quad(tiles)
    res = tiles[0].resolution + 1
    if scale:
        res -= 1
        size = res * 256
        new_image = new_image.resize((size, size), resample=resample["quality"])
    parent_id = tiles[0].parent
    return Tile(parent_id, new_image, name=tiles[0].name, resolution=res)


def comp(a, b, t=200):
    """
    Composites image b onto image a and adjusts the opacity.
    Why this awful code? It was the only way to support an already partially opaque image.
        Args:
        a (Image): [description]
        b (Image): [description]
        t (int, optional): Opacity level, between 0 and 255 inclusive. Defaults to 200.

    Returns:
        Image: Composited image.
    """
    t = max(min(t, 255), 0)

    # We want to convert our transparent image to a non-transparent image only where there are pixels with a not fully-transparent alpha value.
    # So we end up with two transparency levels, either fully transparent or not at all.
    bp = list(b.getdata())
    bp2 = [(r, g, b, 255) if a != 0 else (r, b, g, 0) for r, g, b, a in bp]
    new_b = Image.new("RGBA", b.size)
    new_b.putdata(bp2)

    # Generate transparency mask.
    # If there's a non fully-transparent pixel in b, this should be added to the mast at the specified transparency level.
    # And if it isn't, it can stay at 0 (a==0).
    bp2m = [t if a != 0 else a for _, _, _, a in bp]
    paste_mask = Image.new("L", b.size, 255)
    paste_mask.putdata(bp2m)

    # best not to clobber a, just in case.
    temp_image = a.copy()
    temp_image.paste(new_b, (0, 0, *b.size), mask=paste_mask)
    return temp_image
