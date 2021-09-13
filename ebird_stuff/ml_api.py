from collections import namedtuple
from dataclasses import dataclass, field
from datetime import datetime, timezone
from io import BytesIO
from typing import Dict, List, NamedTuple, TypedDict, Union

import requests

LatLonT = NamedTuple  # [float, float]
LatLon: LatLonT = namedtuple("LatLon", "lat, lon")


class HotSpotT(TypedDict):
    name: str
    latlon: LatLon


@dataclass
class APIBase:
    pass

    class MediaStillProcessing(Exception):
        pass


@dataclass
class Search(APIBase):
    base_url: str = field(
        default="https://search.macaulaylibrary.org/catalog.json", init=False
    )
    asset_url: str = field(default="https://macaulaylibrary.org/asset/", init=False)
    download_url: str = field(
        default="https://cdn.download.ams.birds.cornell.edu/api/v1/asset/", init=False
    )
    checklist_url: str = field(default="https://ebird.org/view/checklist/", init=False)
    public_ebird_key: str = "jfekjedvescr"

    def get(self, url: str, params: dict = {}):
        # error checking here would be good.
        # self.logger.info(f"Getting: {url} with params: {params}.")
        return requests.get(url, params=params)

    def get_head(self, url: str, params: dict = {}):
        return requests.head(url, params=params)

    def search_user(self, name: str) -> Dict[int, str]:
        """
        Gets a list of all (most, there's probably a limit) users with names matching the input name.

        Args:
            name (str): Sting to search for. Needs to be 3 or mor characters long.
            1 = january,
        Returns:
            Dict[int, str]: results, in the form of {user_id: "Name"}
        """
        if len(name) < 3:
            return None
        url = f"https://search.macaulaylibrary.org/api/v1/find/user?fullName={name}"
        res = self.get.json(url)
        if res is None:
            return None
        else:
            uid_as_int = {int(x["code"].replace("USER", "")): x["name"] for x in res}
            return uid_as_int

    def _search(self, **params: dict) -> dict:
        """
        Perform a search against the ML API. This is currently a stub that performs no validation.

        Available search parameters:
        'searchField': what field to search on. Not sure how impoertant this is.
            species = species, animals = animals, region = region, hotspot = hotspot, user = user.
        'q': taxon code display/full name.
            xxxxxxn = taxon code.
        'taxonCode': taxon code to search for
            xxxxxxn = taxon code
        'hotspotCode': Hotspot code
            Lnnnnnnnn = the code for the hotspot. L needs to be included.
        'regionCode': Code for the region.
            AA-BB-CC = region code AA: county, BB: stats, CC: county. AA is country only, AA-BB is state, AA-BB-CC is county.
        'customRegion': Custom region name.
            n = display/full name
        'customRegionCode': Custom region code. Currently only appears to be one.
            USFWS_nnn = region code.
        'userId': ID for the user to search for.
            USERxxxxxx = user id.
        '_mediaType': Something to do with mediatype
            on = on?
        'mediaType': Type of media to limit search to.
            all = all, p = photos, a = audio, v = video. Only 1 at once?
        'species': Unused to searching?
            appearst to only be used during the autocomplete search.
        'region': region to search for,
            full/display name of region. This may be optional.
        'hotspot': hotspot to search for.
            full/display name of the hotspot. This may be optional.
        'mr': preset range. Exclusive of bmo and emo
            M1TO12 = year round, M3TO5 = March - May, M6TO7 = june to july, M8TO11 august to november, M12TO2 december to february, MCUSTOM if using bmo and emo.
        'bmo': date range, beginning month
            1 = january ... 12 = december
        'emo': date range, end month
            1 = january ... 12 = december
        'fyr': first? year
            1900 all the time.
        'yr': preset year range. Exclusive of by and ey.
            YPAST10 = past 10 years, YALL = all years, YCURRENT = current year, YCUSTOM if using fy and ey
        'by': date range, beginning year
            Year beterrn 1900 (fyr) and the current year.
        'ey': date range, ending year
            Year beterrn 1900 (fyr) and the current year.
        'user': user name
            name = User name searched for. This may not be a search query directly.
        'view': how are the search results display?
            Grid = grid, List = list, Gallery = gallery
        'sort': Sorting options
            '' = recent, rating_rank_desc = highest rated first, rating_count_asc = lowest rated media first, obs_date_desc = newest media first, obs_date_asc = oldest media first.
        'req' and '_req': commercially licensable media
            true and 0 = limit to commercially licensable media
        'cap': captive birds
            no = no, y = yes, all = both
        'subId': eBird checklist number, form is Snnnnnnnn
        'catId': catalog number.
            xxxxxxxx or xxxxxxxx, yyyyyyyy, ..., zzzzzzzz No ML prefix.
        '_spec' or 'spec': Was a specimen collected? Only valid for audio, it seems.
            true/on = yes
        'specId': specimen id
            nnnnnnnn or 'XX nnnnnnnn'.
        'collection': Which collection is this from?
            COLL1 = Colección de Sonidos Ambientales, COLL58 = IBC, COLL62 = The Sound Approach.
        'collectionCatalogId': Unknown, but it's different from above.
            ???
        'dsu': Unknown, seems related to display
            -1
        'dbu': Unknown, seems related to display
            -1
        'start': ?
            0 = ?
        '_': ???
            ????
        'age': Age group of a bird. Available choices are:
            a = adult, i = immature, j = juvenile, u = unknown. Multiples like "a, i, j, u"
        'sex': biological sex of the bird.
            f = femal, m = male, u = unknown
        'beh': Behaviours that a bird is doing in the media.
            e = foraging or eating, f = flying, p = preening, vocalizing = vocalizing, molting = molting
        'bre' breeding behaviour in the media.
            cdc = courtship, display or copulation, fy = feeding young, cfs = carrying fecal sack, nb = nest building
        'sounds': type of sound recorded in the media.
            s = song, c = call, nv = non-vocal, ds = dawn song, fs = flight song, fc = flight call, dt = duet
        'tag': Image tas as per: https://support.ebird.org/en/support/solutions/articles/48001064365-tagging-media
            mul = multiple species, in = in hand, nes = nest, egg = egg(s), hab = habitat, wat = is watermarked, bac = back-of-camera, dead = dead, fie = field notes or drawing, non = non-bird media
            peo' = People. Unused?, env = Environmental. Unused?
        'qua': quality
            0 = no rating, ...
        'includeUnconfirmed': unconfirmed or pending media.
            T = show unconfirmed, O = only unconfirmed
        'initialCursorMark': where in the search results to start.
            Don't set this directly, only use it for pagination. Will be in the result from a previous search.
        """
        return self.get(self.base_url, params=params)

    def search(self, **params: dict) -> dict:
        return self._search(**params).json()

    def search_with_headers(self, **params: dict) -> dict:
        res = self._search(**params)
        return res.json(), res.headers

    def taxon_media_stats(self, species_code):
        url = f"https://search.macaulaylibrary.org/api/v1/stats/media-count?taxonCode={species_code}"
        return self.get(url).json()

    def get_taxon_assets(
        self, taxon_code: str, sort_type: str = "quality"
    ) -> List["Asset"]:
        """
        Get images from ML using the API.
        Arguments:
            taxon_code (str): eBird's 6 character taxon code.
            sort_type (str): How the results should be sorted (default: {"quality"})
                Choices are "recent": "Recently Uploaded", "quality": "Best Quality", "least": "Least Rated", "newest": "Date: Newest First", "oldest": "Date: Oldest First".
        Returns:
            List['Asset']: A list of asset IDs for the bird as sorted, empty if no results.
        """
        sort_map = {
            "recent": "",
            "quality": "rating_rank_desc",
            "least": "rating_count_asc",
            "newest": "obs_date_desc",
            "oldest": "obs_date_asc",
        }
        search_results = self.search(
            searchField="species", taxonCode=taxon_code, sort=sort_map[sort_type]
        )
        assets = [Asset(x["catId"], x) for x in search_results["results"]["content"]]
        return assets

    def search_asset(self, asset_id: str) -> "Asset":
        metadata = self.search(catId=asset_id, cap="all")
        metadata = metadata["results"]["content"]
        if len(metadata) == 0:
            raise self.NoResults
        assert len(metadata) == 1
        na = Asset(asset_id)
        na.metadata = metadata[0]
        self.meta_timestamp = datetime.now(timezone.utc)
        return na

    class NoResults(Exception):
        pass


@dataclass
class Asset(APIBase):
    """
    A class to store a single ML asset.
    Various properties to access some of the metadata as a shortcut.
    Everything but the asset ID is lazily loaded on first access.
    Attributes:
        asset_id (int): The ML asset id, without the "ML" part on front.
        metadata (dict): entire metadata returned on the asset from the ML search API.
        media_timestamp (datetime): timestamp of when the media was downloaded.
        meta_timestamp (datetime): timestamp of when the metadata was downloaded.
        lazy_load (bool, optional): set to True to load the media and metadata at the same time as the metadata. Otherwise media is lazily loaded when the media property is accessed. Defaults to False.
            This is useful for anything that doesn't require the actual media file or metadata, such as just using this as an assetID.
    """

    asset_id: int
    metadata: dict = field(repr=False, default_factory=dict)
    media_timestamp: datetime = field(init=False, default=None)
    meta_timestamp: datetime = field(init=False, default=None)
    lazy_load: bool = True

    _file_type: dict = field(init=False, repr=False, default=None)
    _media: BytesIO = field(init=False, repr=False, default=None)
    _media_size: int = field(init=False, repr=False, default=None)

    # logger: 'loguru.logger' = field(default=logger, init=False, repr=False)

    def __post_init__(self):
        if not self.lazy_load:
            self._load_meta()
            self._get_media()

    @property
    def asset_url(self):
        """The asset URL for this asset."""
        return f"{self.asset_url}{self.asset_id}"

    @property
    def file_url(self):
        """The direct URL to the media file for this asset."""
        if not self._file_type:
            self._get_media_metadata()
        return f"{self.download_url}{self.asset_id}.{self._file_type}"

    @property
    def media(self) -> BytesIO:
        """The raw media file, getting it if it isn't already loaded due to lazy loading."""
        if self._media is None:
            # self.logger.debug("No media, getting some.")
            self._get_media()
        return self._media

    @property
    def common_name(self) -> str:
        """The common name for the species in the asset."""
        return self._get_property(["commonName"])

    @property
    def sci_name(self) -> str:
        """The scientific name for the species in the asset."""
        return self._get_property(["sciName"])

    @property
    def species_code(self) -> str:
        """The ebird species code the species in the asset."""
        return self._get_property(["speciesCode"])

    @property
    def location(self) -> List[str]:
        """The ebird hotspots's name for the species in the asset."""
        return self._get_property(["locationLine1", "locationLine2"])

    @property
    def coords(self) -> LatLon:
        """The ebird hotspots's latitude and longitude for the species in the asset."""
        lat, lon = self._get_property(["latitude", "longitude"])
        return LatLon(lat, lon)

    @property
    def media_type(self) -> str:
        """The type of media in the asset. Currently should only be 'Photo', "Audio' and 'Video'."""
        return self._get_property(["mediaType"])

    @property
    def observation_timestamp(self) -> str:
        """The timestamp of when the asset was added to ML, as the source string."""
        return self._get_property(["obsDttm"])

    @property
    def timestamp(self) -> datetime:
        """The timestamp of when the asset was added to ML, as a datetime object."""
        ts = self._get_property(["obsDttm"])
        return self._ts_to_dt(ts, "obs")

    @property
    def user_name(self) -> str:
        """The ebird username of the submitter of the asset.."""
        return self._get_property(["userDisplayName"])

    @property
    def checklist_id(self) -> int:
        """The ebird checklist ID related to the asset, without the leading S."""
        return int(self._get_property(["eBirdChecklistId"]).replace("S", ""))

    @property
    def preview_url(self) -> str:
        """The asset's media preview url."""
        return self._get_property(["previewUrl"])

    @property
    def media_url(self) -> str:
        """The asset's media url."""
        return self._get_property(["mediaUrl"])

    @property
    def media_size(self) -> int:
        """ Get the size of the media. If the media isn't downloaded, will use head to find it. """
        if self._media_size is None:
            self._get_media_metadata()
        return self._media_size

    def _get_property(
        self, properties: List[str], is_repr: bool = False
    ) -> Union[List[Union[int, str]], Union[int, str]]:
        """
        Gets a property or list of properties from the metadata. The various @property functions use this.
        Args:
            properties (List[str]): Properties to look up from the metadata.
            is_repr (bool, optional): used when calling repr so as not to fill in the lazy metadata. Defaults to False.
        Returns:
            Union[List[Union[int, str]], Union[int, str]]: value of the property if one given, or list of properties if multiple asked for.
                None if the lookup failed.
        """
        if not self.metadata and not is_repr:
            self._load_meta()
        res = []
        for p in properties:
            try:
                res += [self.metadata[p]]
            except (KeyError, TypeError):
                res += [None]
        # res = [self.metadata[p] for p in properties]
        return res[0] if len(res) == 1 else res

    def _load_meta(self) -> None:
        """
        Loads the metadata if it isn't already loaded.
        """
        # self.logger.debug("Loading metadata...")
        if not self.metadata:
            # self.logger.debug("No metadata already")
            s = Search()
            metadata = s.search(catId=self.asset_id)["results"]["content"]
            assert len(metadata) == 1
            self.metadata = metadata[0]
            self.meta_timestamp = datetime.now(timezone.utc)

    def _get_media_metadata(self, headers: Dict[str, str] = {}) -> None:
        """
        Gets the metadata for the media file itself, based on the file's HTTP headers.
        Args:
            headers (Dict[str, str], optional): Headers, if they are known, otherwise gets headers.. Defaults to {}.
        """
        headers = requests.head(self.media_url).headers
        content_type = headers["content-type"].split("/")[1]
        # These should be the formats eBird currently supports.
        # Note: disabled until this is better checked.
        # if self.media_type == "Photo":
        #     assert content_type.casefold() in ("jpeg", "png", "gif")
        # elif self.media_type == "Audio":
        #     assert content_type.casefold() in ("wav", "mp3", "m4a", "mpeg")
        # elif self.media_type == "Video":
        #     assert content_type.casefold() in ("mp4", "m4v", "mov", "mpeg")
        self._file_type = content_type
        if self.media_type == "Audio":
            # ML appears to transcode everything to MP3.
            self._file_type = "mp3"
        self.meta_timestamp = datetime.now(timezone.utc)
        self._media_size = int(headers.get("content-length", 0))

    def _ts_to_dt(self, timestring, mode: str = "headers") -> datetime:
        """
        Convert timestamps to datetime objects.
        Args:
            timestring (str): string to convert.
            mode (str, optional): Can either be "obs" for observation form or "header" for the form in HTTP headers. Defaults to "headers".
        Raises:
            ValueError: If a unrecognized mode is used.
        Returns:
            datetime: datetime representation.
        """
        if mode == "headers":
            time_format = "%a, %d %b %Y %H:%M:%S %Z"
        elif mode == "obs":
            time_format = "%d %b %Y"
        else:
            raise ValueError(f"Mode {mode} not supported.")
        return datetime.strptime(timestring, time_format)

    def _get_media(self) -> None:
        """
        Downloads the media, or none if an error occurred.
        """
        url = self.media_url
        res = requests.get(url)

        # ML uses 476 to denote is still loading.
        if res.status_code == 476:
            print("sta")
            self._media = None
            raise APIBase.MediaStillProcessing
        if res.status_code not in (200, 304, 206):
            # self.logger.debug(f"ml_get_media: status_code {res.status_code}")
            self._media = None
        else:
            self._get_media_metadata(res.headers)
            # self.logger.debug(res.headers)
            data = BytesIO(res.content)
            # self.logger.debug("payload:", content_len, self._file_type)
            self._media = data
            self.media_timestamp = datetime.now(timezone.utc)

    def __len__(self) -> int:
        """
        The length of the asset is the size of the media it stores. 0 if there isn't any.
        """
        return len(self._media.getvalue())

    def __repr__(self) -> str:
        keys = {
            "commonName": "common_name",
            "sciName": "scientific_name",
            "speciesCode": "species_code",
            "location": "location",
            "mediaType": "media_type",
            "obsDttm": "observation_timestampe",
            "userDisplayName": "user_name",
            "coords": "coords",
        }
        attribs = {}
        for k in keys:
            if k == "coords":
                lat, lon = self._get_property(["latitude", "longitude"], True)
                attribs[k] = f"{LatLon(lat, lon)}"
            if k == "location":
                attribs[
                    k
                ] = f"{self._get_property(['locationLine1', 'locationLine2'], True)}"
            v = self._get_property([k], True)
            attribs[k] = f"'{v}'" if isinstance(v, str) else f"{v}"
        s = ", ".join([f"{keys[k]}={v}" for k, v in attribs.items()])
        return f"Asset(asset_id={self.asset_id}, {s})"


def asset_from_url(url: str, lazy_load: bool = True) -> "Asset":
    """
    Creates an Asset from the ML url.
    Args:
        url (str): url of the form https://macaulaylibrary.org/asset/<asset id>.
        lazy_load (bool, optional): Whether or not to lazy load this object. If None, does whatever the default is. Defaults to None.
    Returns:
        Asset: A new asset instance.
    """
    asset_id = get_asset_id(url)
    return Asset(asset_id, lazy_load)


def get_asset_id(url):
    p = requests.utils.urlparse(url).path
    if p == "":
        return ""
    else:
        aid = p.split("/")[-1]
        try:
            aid = int(aid)
        except ValueError:
            return ""
    return aid
