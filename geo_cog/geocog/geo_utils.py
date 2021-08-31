import requests
import re
from dataclasses import dataclass
from pprint import pprint
import PIL.Image as Image
from io import BytesIO
import mercantile

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
        if high_res and z % 2 != 0:
            z += 1
        params = {"access_token": self.token}
        hr = ""
        if high_res:
            hr = "@2x"
        url = f"v4/mapbox.{style}/{z}/{x}/{y}{hr}.{fmt}"
        res = requests.get(self.base_url + url, params=params)
        if res.status_code == 200:
            img = Image.open(BytesIO(res.content))
            tile = Tile(x, y, z, img, "mapbox")
            return tile
        else:
            print(res.status_code, res.url)
            return None


@dataclass
class GBIF:
    base_url: str = "https://api.gbif.org/"
    srs: str = "EPSG:3857"
    data_key: str = "47f16512-bf31-410f-b272-d151c996b2f6"

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
        url = f"v2/map/occurrence/{source}/{zoom}/{x}/{y}{format}"
        res = requests.get(self.base_url + url, params=params)
        print(res, res.headers)
        print(res.url)
        img = Image.open(BytesIO(res.content))
        return Tile(zoom, x, y, img, "gbif")

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
        print("bbox: ", bbox)
        tile_ids = list(mercantile.tiles(*bbox, zoom))
        print("tile_ids:", tile_ids)
        return tile_ids

    def get_tiles(self, species_code, zoom, grid_scale=100):
        # TODO: make this dynamic.
        tile_ids = self.get_bbox(species_code, zoom)
        r = requests.get(
            f"https://ebird.org/map/rsid?speciesCode={species_code}&gridScale={grid_scale}"
        )
        rsid = r.content.decode("ascii")
        print("rsid: ", rsid, "tiles: ", len(tile_ids))
        tiles = {}
        for t in tile_ids:
            tile = self.download_tile(t.z, t.x, t.y, rsid)
            tiles[(t.z, t.x, t.y)] = tile
            print(t.z, t.x, t.y, tile)
        return tiles

    def download_tile(self, zoom, x, y, rsid):
        url = f"https://geowebcache.birds.cornell.edu/ebird/gmaps?layers=EBIRD_GRIDS_WS2&format=image/png&zoom={zoom}&x={x}&y={y}&CQL_FILTER=result_set_id='{rsid}'"
        print(f"Getting url: {url}")
        res = requests.get(url)
        print(res)
        img = Image.open(BytesIO(res.content))
        return Tile(zoom, x, y, img, name=f"ebird-{rsid}")

    def get_range_map(self, species_code, zoom=0, mapbox_style="satellite"):
        mapbox = MapBox()
        ebird_tiles = self.get_tiles(species_code, zoom)
        print("ebird_tiles:", ebird_tiles)
        ebird_tile_imgs = ebird_tiles.values()
        ebird_img = composite_quad(ebird_tile_imgs)
        with open("ebird_comp_quad.png", "wb") as f:
            ebird_img.save(f, "png")
        mapbox_tiles = [
            mapbox.get_tile(z=a, x=b, y=c, style=mapbox_style, high_res=False)
            for a, b, c in ebird_tiles.keys()
        ]
        mapbox_image = composite_quad(mapbox_tiles)
        with open("mapbox_comp_quad.png", "wb") as f:
            ebird_img.save(f, "png")
        new_img = comp(mapbox_image, ebird_img)
        return new_img


@dataclass
class Tile:
    z: int
    x: int
    y: int
    img: Image
    name: str = "tile"

    @property
    def size(self):
        return self.img.size

    def save(self):
        x_dim, y_dim = self.size
        with open(
            f"{self.name}_{self.z}-{self.x}-{self.y}_{x_dim}x{y_dim}.png", "wb"
        ) as f:
            self.img.save(f, "png")

    def composite(self, tile):
        # This only works with images that share an x, y, and z.
        # Sizes need to match, and no scaling is done otherwise.
        new_img = Image.composite(tile.img, self.img, tile.img)
        new_name = f"c{self.name}+{tile.name}"
        return Tile(self.x, self.y, self.z, new_img, new_name)

    @property
    def asbytes(self):
        d = BytesIO()
        self.img.save(d, "png")
        return BytesIO(d.getvalue())


def composite_quad(tiles):
    """
    Takes 4 tiles and composites then together.
    TODO: change output to a Tile with zoom level and bounds recalculated.
    Ordering goes like this:
    |---|---|
    | 0 | 1 |
    |---|---|
    | 2 | 3 |
    |---|---|
    Args:
        tiles list(Tile): Tiles to stick together.
    Returns:
        Image: Image of the composited tiles.
    """
    if list(tiles)[0].img.mode == "RGB":
        print("RGB")
        new_image = Image.new("RGB", (512, 512))
    else:
        print("RGBA")
        new_image = Image.new("RGBA", (512, 512))
    for i in [(0, 0), (0, 1), (1, 0), (1, 1)]:
        idx = int(f"{i[0]}{i[1]}", 2)
        x_coord, y_coord = [256 * a for a in i]
        print("corner:", x_coord, y_coord)
        t_img = list(tiles)[idx].img

        if t_img.mode == "RGBA":
            print("_RGBA_", new_image.mode)
            new_image.alpha_composite(t_img, (x_coord, y_coord))
        else:
            print("_RGB_", new_image.mode)
            new_image.paste(t_img, (x_coord, y_coord, x_coord + 256, y_coord + 256))
    return new_image

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
    new_b = Image.new('RGBA', b.size)
    new_b.putdata(bp2)

    # Generate transparency mask.
    # If there's a non fully-transparent pixel in b, this should be added to the mast at the specified transparency level.
    # And if it isn't, it can stay at 0 (a==0).
    bp2m = [t if a != 0 else a for _, _, _, a in bp]
    paste_mask = Image.new('L', b.size, 255)
    paste_mask.putdata(bp2m)

    # best not to clobber a, just in case.
    temp_image = a.copy()
    temp_image.paste(new_b, (0, 0, *b.size), mask=paste_mask)
    return temp_image
