# Transcoder

`transcoder.py` is a frontend for pydub to do transcoding of audio for use on a platform that limits file sizes, such as Discord.

## Requirements

### Required

- `Python`: only tested on versions >= 3.8, though 3.10 is target for support.
- `pydub`: python transcoding library
- `loguru`: for logging
- `ffmpeg`: version >= 4.4.
- `pipenv`: for creation and management of virtualenvs.

### Development

- `pytest`: running tests
- `black`: code formatting

## Using

```python
# instantiate the object
transcoder = AudioTranscoder()
# get raw data from audio file
raw_data = transcoder.open_file(file_path))
# print input duration, size and estimated bitrate.
print(input_meta(raw_data))
# Run the transcode, output.data is BytesIO
# max_size argument makes sure the file is < this size in Bytes.
output = transcoder.transcode_audio_meta(raw_data, max_size=8000000)
# print time elapsed for transcoding, final size in bytes and whether or not  it transcoded.
print(output.elapsed, output.size, output.transcoded)
# save the resulting output
transcoder.write_file(path=outout_path, data=output.data)
```

## pydub notes

pydub doesn't accurately report the duration of files.

pydub is seeminly the only maintained library to do easy audio transcoding in Python, and it's completely broken. Hopefully upsteam will fix it so that it's actually usable, but until then, two simple fixes need to be applied.

1. `pydub/utils.py` line 279 change:

    ```python
    info = json.loads(output)

    if not info:
        # If ffprobe didn't give any information, just return it
        # (for example, because the file doesn't exist)
        return info
    ```

    to:

    ```python
    try:
        info = json.loads(output)
    except json.decoder.JSONDecodeError:
        # If ffprobe didn't give any information, just return it
        # (for example, because the file doesn't exist)
        return None
    ```

    Because `try` and `except` are how you catch exceptions, not by checking to see if a value is `None`.

2. `pydub/audio_segment.py` line 717 change:

    ```python
    if cls.converter == 'ffmpeg':
        conversion_command += ["-read_ahead_limit", str(read_ahead_limit),
            "-i", "cache:pipe:0"]
    ```

    to:

    ```python
    if cls.converter == 'ffmpeg':
        conversion_command += ["-i", "cache:pipe:0"]
    ```

    This is needed because modern ffmpeg doesn't have this option and this bug will cause the conversion to fail.
