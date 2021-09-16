# from requests import Request, Response, Session
import requests
# from requests.sessions import Session
from requests_cache import CachedSession
from dataclasses import dataclass
from loguru import logger

urls_expiry_config = {
    # Actual media should never change, so it can be safely? cached forever.
    "https://cdn.download.ams.birds.cornell.edu/api/v1/asset/*": -1,
    # Searches should never be cached.
    "https://search.macaulaylibrary.org/catalog.json": 0,
}



@dataclass
class MLSession:
    session: CachedSession = CachedSession(cache_name="api_cache", backend="filesystem")

    def __post_init__(self):
        self.session.timeout = 30
        self.session.urls_expire_after = urls_expiry_config
        self.session.cache_control = True

    def get(self, url, **kwargs):
        logger.info(f"MLSession GET: cached: {self.is_cached} url: {url}, kwargs: {kwargs}")
        return self.session.get(url, **kwargs)

    def head(self, url, **kwargs):
        logger.info(f"MLSession HEAD: cached: {self.is_cached} url: {url}, kwargs: {kwargs}")
        return self.session.head(url, **kwargs)

    @property
    def is_cached(self) -> bool:
        """ Is this session cached? """
        if isinstance(self.session, CachedSession):
            return True
        return False

local_session = MLSession()
no_cache_session = MLSession(session=requests.Session())

def get(url, **kwargs):
    resp = local_session.get(url, **kwargs)
    if local_session.is_cached:
        logger.info(f"MLSession cached: {resp.from_cache}.")
    return resp

def head(url, **kwargs):
    resp = local_session.head(url, **kwargs)
    if local_session.is_cached:
        logger.info(f"MLSession cached: {resp.from_cache}.")
    return resp


def get_nc(url, **kwargs):
    return no_cache_session.get(url, **kwargs)

def head_nc(url, **kwargs):
    return no_cache_session.head(url, **kwargs)
