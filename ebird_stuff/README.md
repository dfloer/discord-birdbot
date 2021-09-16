# ebird_stuff

The eventual home of a bunch of stuff for interacting with eBird. Code considered to be alpha quality.

Currently, there's the beginnings of an API in `ml_api.py` and `ml_session.py` and pytest tests at `test_ml_media.py`.

`transcode.py` is a frontend for pydub to do transcoding of audio from ML for us on a platform that limits file upload size, such as Discord.

By default `requests-cache` is set up for caching to `api_cache/` directory using the filesystem backend, because this was the easiest, and SQLite is slow at storing files.

Logs go to the `logs/` directory.

## pydub notes

pydub is seeminly the only maintained library to do easy audio transcoding in Python, and it's completely broken. Hopefully upsteam will fix it so that it's actually usable, but until then, two simple fixes need to be applied.

1. `pydyb/utils.py` line 279 change:

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
