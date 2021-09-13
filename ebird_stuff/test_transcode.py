from copy import deepcopy
from pathlib import Path

import pytest

import ml_api as mlp
from transcode import AudioTranscoder


class TestAudio:
    tf = Path("./ebird_stuff/tests/test-files")
    transcoder = AudioTranscoder()

    @pytest.mark.parametrize(
        "input_path, maximum_size, output_path",
        [
            ("night_owl.mp3", 7600000, "result-night_owl.mp3"),
        ],
    )
    def test_transcode_audio(self, input_path, maximum_size, output_path):
        input_data = self.transcoder.open_file(self.tf / Path(input_path))
        output = self.transcoder.transcode_audio_meta(input_data)
        self.transcoder.write_file(path=self.tf / Path(output_path), data=output.data)

        assert output.size < maximum_size
        assert output.size > 0
        assert False

    @pytest.mark.skip(reason="pydub's duration finding is non-deterministic.")
    @pytest.mark.parametrize(
        "input_path, input_size, input_bitrate, input_duration",
        [
            ("night_owl.mp3", 7758411, 320000, 193.9),
        ],
    )
    def test_metadata(self, input_path, input_size, input_bitrate, input_duration):
        input_data = self.transcoder.open_file(self.tf / Path(input_path))
        metadata = self.transcoder.input_meta(input_data)
        print(metadata)
        # Why the rounding? Because pydub can't reliably determine a file's length.
        assert metadata.size == input_size
        assert metadata.bitrate == input_bitrate
        assert round(metadata.duration, 1) == input_duration

        # Do it a second time to make sure we're not consuming the stream.
        metadata2 = self.transcoder.input_meta(input_data)
        assert metadata2.size == metadata.size
        assert metadata2.bitrate == metadata.bitrate
        assert round(metadata2.duration, 1) == round(metadata.duration, 1)


class TestMLTranscode:
    mls = mlp.Search()
    transcoder = AudioTranscoder()
    tf = Path("./ebird_stuff/tests/test-files")

    @pytest.mark.vcr("new")
    @pytest.mark.parametrize(
        "asset_id, maximum_size, transcode",
        [
            (
                272370221,
                7600000,
                False,
            ),
            (
                227594,
                7600000,
                True,
            ),
            (
                305988,
                7600000,
                True,
            )
        ],
    )
    def test_audio_transcode(self, asset_id, maximum_size, transcode):
        test_asset = self.mls.search_asset(asset_id=asset_id)
        media = test_asset.media

        input_size = len(deepcopy(media).read())
        output = self.transcoder.transcode_audio_meta(media)
        if transcode:
            assert input_size >= maximum_size
            assert input_size >= output.size
            assert output.transcoded == transcode
        self.transcoder.write_file(
            path=self.tf / Path(f"result_tat-{asset_id}.mp3"), data=output.data
        )


class TestMisc:
    transcoder = AudioTranscoder()
    @pytest.mark.parametrize(
        "bitrate, expected_rate",
        [
            (500000, 320000),
            (5000, 8000),
            (320000, 320000),
            (8000, 8000),
            (312000, 224000),
            (319999, 224000),
            (320001, 320000),
            (17842, 16000),
            (178492, 160000),
            (1, 8000),
            (7999, 8000),
            (8001, 8000),
        ],
    )
    def test_bitrate_floor(self, bitrate, expected_rate):
        assert expected_rate == self.transcoder.bitrate_floor(bitrate)
        # assert False