# ebird_stuff

The eventual home of a bunch of stuff for interacting with eBird and ML. Code considered to be alpha quality.

Currently, there's the beginnings of an API for the [Macaulay Library](https://www.macaulaylibrary.org/) (ML) in `ml/api.py` and `ml/session.py` and pytest tests at `tests/test_ml_media.py`. Docs on the ML API forthcoming in `ml/docs/`.

By default `requests-cache` is set up for caching to `api_cache/` directory using the filesystem backend, because this was the easiest, and SQLite is slow at storing files.

Logs go to the `logs/` directory.

## Requirements

### Required

- Python: tested on versions 3.8, 3.9 and 3.10, but consider anything older than 3.10 unsupported.
- pipenv: for creation and management of virtual environments and dependency installation.

To use:

- Clone this repo.
- run `pipenv install` to install the dependencies and create a virtualenv.
- run `pipenv shell` to have a shell with access to this library.

### Development

Running pipenv install 
