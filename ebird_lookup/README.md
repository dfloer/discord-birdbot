# Species Lookup Tools

The species lookup tools are currently in development, and have both of the following full-text search backends in testing.

## Text Search Backends

Basic setup info using docker.

### Typesense

- Make sure to change the API key to something else, both here and in the bot.
- `-v/tmp/data:/data` change the part before the `:` to where the container should store persistent data.
- `latest` can be a different version, but the code is generally tested againstly `latest` only.

`docker pull typesense/typesense:latest`

`docker run -p 8108:8108 -v/tmp/data:/data typesense/typesense:latest --data-dir /data --api-key=changeMe!`

### Meiliesearch

- Make sure to change the API key to something else, both here and in the bot.

**Note:** This configuration does not persist data.

`docker pull getmeili/meilisearch:latest`

`docker run -it --rm --env MEILI_NO_ANALYTICS=true -p 7700:7700 getmeili/meilisearch:latest ./meilisearch --master-key=changeMe!`

Presently, there isn't a good setup script outside of the tests, so run that to get the data parsed and loaded.
