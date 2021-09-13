from datetime import datetime
from pprint import pprint

import pytest

import ml_api as mlp


class TestUrls:
    mls = mlp.Search()

    def test_search_creation(self):
        t = mlp.Search()
        assert t.base_url

    def get_taxon_assets(self, taxon_id, sort_type, expected_assets_ids):
        results = self.mls.get_taxon_assets(taxon_id, sort_type)
        assert set([x.asset_id for x in results]) == set(expected_assets_ids)


class TestAsset:
    mls = mlp.Search()

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "asset_id, expected_results",
        [
            (
                "307671311",
                {
                    "common_name": "Bushtit",
                    "asset_id": 307671311,
                    "sci_name": "Psaltriparus minimus",
                    "species_code": "bushti",
                    "location": [
                        "806 Coronado Ave, Fort Collins US-CO 40.53593, -105.09000",
                        "Larimer, Colorado, United States",
                    ],
                    "coords": mlp.LatLon(lat=40.5359, lon=-105.09),
                    "media_type": "Photo",
                    "observation_timestamp": "13 Feb 2021",
                    "timestamp": datetime(2021, 2, 13, 0, 0),
                    "user_name": "Cree Bol",
                    "checklist_id": 81111676,
                    "preview_url": "https://cdn.download.ams.birds.cornell.edu/api/v1/asset/307671311/",
                },
            ),
        ],
    )
    def test_get_asset_meta(self, asset_id, expected_results):
        test_asset = self.mls.search_asset(asset_id=asset_id)

        assert test_asset.asset_id == asset_id
        assert test_asset.common_name == expected_results["common_name"]
        assert test_asset.sci_name == expected_results["sci_name"]
        assert test_asset.species_code == expected_results["species_code"]
        assert test_asset.coords == expected_results["coords"]
        assert test_asset.media_type == expected_results["media_type"]
        exp = expected_results["observation_timestamp"]
        assert test_asset.observation_timestamp == exp
        assert test_asset.timestamp == expected_results["timestamp"]
        assert test_asset.user_name == expected_results["user_name"]
        assert test_asset.checklist_id == expected_results["checklist_id"]
        assert test_asset.preview_url == expected_results["preview_url"]

    @pytest.mark.vcr("new")
    def test_no_result(self):
        with pytest.raises(mlp.Search.NoResults):
            test_asset = self.mls.search_asset(asset_id=0)

    @pytest.mark.vcr("new")
    def test_non_public(self):
        # 123456 is a restricted item, at least when this test was written.
        # It exists, but the search API can't find it.
        with pytest.raises(mlp.Search.NoResults):
            test_asset = self.mls.search_asset(asset_id=123456)

    @pytest.mark.vcr("new")
    def test_audio_processing(self):
        with pytest.raises(mlp.APIBase.MediaStillProcessing):
            test_asset = self.mls.search_asset(asset_id=368985981)
            _ = test_asset.media

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "asset_id, results",
        [
            (
                307671311,
                {"asset_id": 307671311, "meta_timestamp": datetime.now()},
            ),
            (
                488784,
                {"asset_id": 488784, "meta_timestamp": datetime.now()},
            ),
        ],
    )
    def test_get_metadata(self, asset_id, results):
        test_asset = self.mls.search_asset(asset_id=asset_id)
        assert test_asset.asset_id == results["asset_id"]
        pprint(test_asset.metadata)
        # assert 488784 != asset_id

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "asset_id, file_type, size",
        [
            (
                307671311,
                "jpeg",
                177110,
            ),
            (
                272370221,
                "mp3",
                306782,
            ),
        ],
    )
    def test_get_media(self, asset_id, file_type, size):
        test_asset = self.mls.search_asset(asset_id=asset_id)
        pprint(test_asset.metadata)
        test_media = test_asset.media.read()
        # print(test_media, len(list(test_media)))
        assert test_asset._file_type == file_type
        assert len(list(test_media)) == size
        # print(test_asset)
        # print(test)
        # assert False

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "intime, mode, outdt",
        [
            (
                "Fri, 10 Sep 2021 00:45:38 GMT",
                "headers",
                datetime(2021, 9, 10, 0, 45, 38),
            ),
            (
                "Sun, 14 Feb 2021 21:59:42 GMT",
                "headers",
                datetime(2021, 2, 14, 21, 59, 42),
            ),
            (
                "10 Sep 2021",
                "obs",
                datetime(2021, 9, 10, 0, 0),
            ),
            (
                "14 Feb 2021",
                "obs",
                datetime(2021, 2, 14, 0, 0),
            ),
            (
                "test",
                "test",
                None,
            ),
        ],
    )
    def test_timestamp_parse(self, intime, mode, outdt):
        test_asset = mlp.Asset(0)
        if outdt is None:
            with pytest.raises(ValueError):
                res = test_asset._ts_to_dt(intime, mode)
        else:
            res = test_asset._ts_to_dt(intime, mode)
            assert res == outdt

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "lazy_load",
        [True, False],
    )
    @pytest.mark.parametrize(
        "url, asset_id, media_type",
        [
            (
                "https://macaulaylibrary.org/asset/307671311",
                307671311,
                "Photo",
            ),
            (
                "https://macaulaylibrary.org/asset/272370221",
                272370221,
                "Audio",
            ),
            (
                "https://macaulaylibrary.org/asset/201759561",
                201759561,
                "Video",
            ),
        ],
    )
    def test_asset_from_url(self, url, asset_id, media_type, lazy_load):
        res = mlp.asset_from_url(url, lazy_load=lazy_load)
        assert res.asset_id == asset_id
        if not lazy_load:
            assert res.media_type == media_type
        else:
            assert res.media_type is None

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "asset_id, common_name, lazy_load",
        [
            (
                315200291,
                None,
                True,
            ),
            (
                315200291,
                "'Bushtit'",
                False,
            ),
        ],
    )
    @pytest.mark.vcr("new")
    def test_repr(self, asset_id, common_name, lazy_load):
        test_asset = mlp.Asset(asset_id, lazy_load=lazy_load)
        print("metadata:")
        pprint(test_asset.metadata)
        print(test_asset)
        r = repr(test_asset)
        assert "asset_id=315200291, " in r
        assert f"common_name={common_name}, " in r

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "url, none_expected",
        [
            ("https://macaulaylibrary.org/123456", True),
            ("https://macaulaylibrary.org/", True),
            ("https://macaulaylibrary.org/asset/", True),
            ("https://www.google.ca", True),
            ("this isn't even a url", True),
            ("this isn't even a url either.org/asset/123456", True),
            ("", True),
            ("https://macaulaylibrary.org/asset123456", True),
            ("https://macaulaylibrary.org/asset/asset/123456", True),
            ("https://macaulaylibrary.org/asset/X23456", True),
            ("https://macaulaylibrary.org/asset/mlx23456", True),
            ("https://macaulaylibrary.org.com/asset/123456", True),
            ("https://macaulaylibrary.org.com/asset/123456", True),
            ("https://macaulaylibrary.com.org/asset/123456", True),
            # And now some valid URLs.
            ("https://macaulaylibrary.org/asset/307671311", False),
            ("https://search.macaulaylibrary.org/asset/307671311", False),
            ("https://www.macaulaylibrary.org/asset/307671311", False),
            ("https://macaulaylibrary.org/asset/ML307671311", False),
        ],
    )
    def test_asset_from_invalid_url(self, url, none_expected):
        res = mlp.get_asset_id(url)
        print("res:", res)
        assert (res is None) if none_expected else (res is not None)
