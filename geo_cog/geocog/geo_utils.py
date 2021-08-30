import requests
import re
from dataclasses import dataclass
from pprint import pprint
import PIL.Image as Image
from io import BytesIO

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
    token: str
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
