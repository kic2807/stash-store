# stash-hello-world

Test app for the Stash store. Used to verify that secrets can be kept out of
this public repo by reading them from a `.env` file in the app data folder.

## How the `.env` file is loaded

`docker-compose.yml` reads `${APP_DATA_DIR}/data/.env` with `env_file`
(`required: false`, so the app still starts when the file does not exist).
App updates only replace `docker-compose.yml`, templates, `exports.sh` and
`hooks/`, so the `.env` file you create survives updates.

## Put the `.env` file on Umbrel

On the Umbrel terminal (Settings → Advanced settings → Terminal → umbrelOS), or over SSH:

```sh
cd ~/umbrel/app-data/stash-hello-world/data
nano .env            # keys from .env.example, one KEY=value per line
chmod 600 .env
```

Then restart the app from the Umbrel home screen (right-click → Restart).

## Check

```sh
docker inspect stash-hello-world_server_1 \
  --format '{{range .Config.Env}}{{println .}}{{end}}' | grep STASH_TEST
```
