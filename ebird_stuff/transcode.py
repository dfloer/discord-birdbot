import sys
from collections import namedtuple
from dataclasses import dataclass, field
from datetime import datetime
from io import BytesIO
from typing import NamedTuple
from copy import copy
from typing import Tuple
from bisect import bisect

import loguru
from pydub import AudioSegment
from pydub import utils as pydub_utils


def setup_logger():
    logger = loguru.logger
    # logger.remove(0)
    logger.level("STATS", no=38)
    logger.add(sys.stderr, format="[{time}] | {level} | {message}", level="INFO")
    logger.add(sys.stderr, format="[{time}] | {level} | {message}", level="STATS")
    return logger


OutputMeta = namedtuple("OutputMeta", "data, elapsed, size, transcoded")
InputMeta = namedtuple("InputMeta", "duration, size, bitrate")


@dataclass
class AudioTranscoder:
    logger: loguru.logger = setup_logger()
    bitrate_steps: Tuple[int] = field(
        default=(
            8000,
            16000,
            24000,
            32000,
            40000,
            48000,
            64000,
            80000,
            96000,
            112000,
            128000,
            160000,
            192000,
            224000,
            320000,
        ),
        init=False,
        repr=False,
    )

    def __post__init__(self):
        # self.logger = self.logger()
        print(self.logger)

    def input_meta(self, input_data: BytesIO):
        """
        Gets the metadata on the input file.
        Pydub doesn't always return sane values, so this may be problematic to use.
        """
        audio = AudioSegment.from_file(copy(input_data))
        size = len(input_data.getvalue())
        duration = audio.duration_seconds
        self.logger.log("STATS", f"input_meta: duration {duration}s.")
        bitrate = int(round((size * 8) / duration, -3))
        return InputMeta(duration, size, bitrate)

    def transcode_audio_meta(
        self,
        input_data: BytesIO,
        max_size: int = 7600000,
    ) -> NamedTuple:
        """
        runs transcode_audio, but returns data with metadata.
        Args:
            input_data (BytesIO): input audio file
            max_size (int, optional): Maximum allowed output size, in bytes. Defaults to 7600000.
        Returns:
            NamedTuple[BytesIO, float, int, int]: (audio_data, encode_elapsed_time_seconds, final_size_size, bitrate_bps)
        """
        input_meta = self.input_meta(input_data)

        start_time = datetime.now()
        audio_out = self.transcode_audio(input_data, max_size)
        elapsed = (datetime.now() - start_time).seconds

        in_size = input_meta.size
        out_size = len(audio_out.getvalue())
        transcode_status = True if in_size != out_size else False

        self.logger.log(
            "STATS", f"audio_transcode: elapsed: {elapsed}s, size: {out_size}B."
        )
        return OutputMeta(audio_out, elapsed, out_size, transcode_status)

    def transcode_audio(
        self, input_data: BytesIO, max_size: int = 7600000, force: bool = False
    ) -> BytesIO:
        """
        Given an audio file and a maximum size, transcodes it to be under that maximum size.
        Returns the input if it doesn't need to be transcoded.
        Args:
            input_data (BytesIO): input audio file.
            max_size (int, optional): Maximum size, in bytes, that the file can be. Defaults to 7600000.
            force (bool, optional): If true, force the transcode. Useful to change format to mp3.
        Returns:
            BytesIO: Transcoded file as an mp3.
        """
        # 7600000B = 8MB with a 5% safety factor.
        input_size = len(input_data.getvalue())
        # If the input is under the target size, short circuit the transcode.
        if input_size < max_size and not force:
            self.logger.info("audio_transcode: skip")
            return input_data
        audio_out = self._perform_transcode(input_data, max_size)
        return audio_out

    def _perform_transcode(
        self, input_data: BytesIO, target_size: int, output_format: str = "mp3"
    ) -> BytesIO:
        """
        Perform the transcode. Should probably support VBR here.
        Args:
            input_data (BytesIO): Input audio file
            target_size (int): Target file size to meet or be under.
            output_format (str, optional): output file type. Defaults to "mp3".
        Returns:
            BytesIO: Transcoded file.
        """
        audio = AudioSegment.from_file(input_data)
        input_size = len(input_data.getvalue())
        duration = audio.duration_seconds
        input_bitrate = int((input_size * 8) / duration)
        output_bitrate = int((target_size * 8) / duration)
        output_bitrate = self.bitrate_floor(output_bitrate)
        self.logger.log(
            "STATS",
            f"audio_transcode: input size: {input_size}B, duration: {duration}s, bitrate: {input_bitrate}b/s",
        )
        self.logger.log(
            "STATS",
            f"audio_transcode: output target: {target_size}B, duration: {duration}s, bitrate: {output_bitrate}b/s",
        )

        audio_out = BytesIO()
        audio.export(audio_out, format=output_format, bitrate=str(output_bitrate))
        out_size = len(audio_out.getvalue())
        self.logger.log("STATS", f"audio_transcode: output size: {out_size}B")
        return audio_out

    def bitrate_floor(self, bitrate: int) -> int:
        """
        Makes sure the bitrate is clamped to the floor of the bitrate bin.
        Otherwise the closest bitrate is chosen, which can make too large bitrates.
        """
        brs = self.bitrate_steps
        output_bitrate = max(brs[0], min(bitrate, brs[-1]))
        output_bitrate = brs[bisect(brs, output_bitrate) - 1]
        return output_bitrate

    @staticmethod
    def open_file(path: str) -> BytesIO:
        with open(path, "rb") as f:
            return BytesIO(f.read())

    @staticmethod
    def write_file(path: str, data: BytesIO) -> None:
        with open(path, "wb") as f:
            f.write(data.read())
