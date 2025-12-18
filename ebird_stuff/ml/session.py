# from requests import Request, Response, Session
import requests

# from requests.sessions import Session
from requests_cache import CachedSession
from dataclasses import dataclass
from loguru import logger
from datetime import datetime

urls_expiry_config = {
    # Actual media should never change, so it can be safely? cached forever.
    "https://cdn.download.ams.birds.cornell.edu/api/v2/asset/*": -1,
    # Searches should never be cached.
    "https://search.macaulaylibrary.org/catalog.json": 0,
    "https://search.macaulaylibrary.org/": 0,
    "https://search.macaulaylibrary.org/catalog": 0,
    "https://secure.birds.cornell.edu/cassso/login?gateway=true&service=https://search.macaulaylibrary.org/login?path=/catalog": 0,
}


@dataclass
class MLSession:
    session: CachedSession = CachedSession(cache_name="api_cache", backend="filesystem")

    def __post_init__(self):
        self.session.timeout = 30
        self.session.urls_expire_after = urls_expiry_config
        self.session.cache_control = True
        self._get_ml_cookie()

    def get(self, url, **kwargs):
        logger.info(
            f"MLSession GET: cached: {self.is_cached}, url: {url}, kwargs: {kwargs}"
        )
        # check if the cookie is expired and get a new one if so.
        # if self._expired_ml_cookie:
        #     self._get_ml_cookie()
        x = self.session.get(url, **kwargs)
        logger.info(f"MLSession GET url: {x.url}")
        logger.info(self._view_ml_cookie())
        return x


    def head(self, url, **kwargs):
        logger.info(
            f"MLSession HEAD: cached: {self.is_cached} url: {url}, kwargs: {kwargs}"
        )
        return self.session.head(url, **kwargs)

    @property
    def is_cached(self) -> bool:
        """Is this session cached?"""
        if isinstance(self.session, CachedSession):
            return True
        return False

    def _get_ml_cookie(self):
        """
        ML's V2 API requires any API calls to use a session cookie, so we need to get (and periodically update) a session cookie.
        The login flow is:
            1. https://search.macaulaylibrary.org/catalog
            2. https://secure.birds.cornell.edu/cassso/login?gateway=true&service=https://search.macaulaylibrary.org/login?path=/catalog
        """
        logger.error("_get_ml_cookie()")
        if self._expired_ml_cookie:
            self._clear_ml_cookie()
        if not self.session.cookies:
            cat_res = self.session.get("https://search.macaulaylibrary.org/catalog")
            logger.warning(cat_res)
            login_res = self.session.get("https://secure.birds.cornell.edu/cassso/login?gateway=true&service=https://search.macaulaylibrary.org/login?path=/catalog")
            logger.warning(login_res)
        logger.error(self._view_ml_cookie())

    def _clear_ml_cookie(self):
        self.session.cookies.clear()

    @property
    def _expired_ml_cookie(self) -> bool:
        """True if any expired, False otherwise."""
        return any([x.is_expired() for x in self.session.cookies])

    def _view_ml_cookie(self):
        return {k: v for k, v in self.session.cookies.items()}

local_session = MLSession()
no_cache_session = MLSession(session=requests.Session())


def get(url, **kwargs):
    resp = local_session.get(url, **kwargs)
    logger.info(url, kwargs)
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
