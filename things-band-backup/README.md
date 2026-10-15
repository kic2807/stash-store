# things-band-backup

[band-backup](https://github.com/kic2807/band-backup): BAND → Immich media
backup and a Discord bot that turns schedule photos into BAND / Google Calendar
events. No web UI.

Image: `ghcr.io/kic2807/band-backup` (public, linux/amd64), built by GitHub
Actions in the band-backup repo. **Not** updated by this store's automation;
release it by hand (see below).

## Layout

`~/umbrel/app-data/things-band-backup/data/` is mounted at `/data`:

| File | What |
|------|------|
| `.env` | settings and secrets (from `.env.example`) |
| SQLite database, BAND session cookies | created by the app |
| `google-service-account.json` | optional, for the Google Calendar mirror |

The container runs as root (Playwright's Chromium and the Claude CLI are
installed for root in the image), so files it creates are owned by root. Use
`sudo` to inspect or delete them.

## Setup

1. Install Immich first and create an API key there (Account Settings → API Keys).
2. Install this app, then on the Umbrel terminal:

   ```sh
   cd ~/umbrel/app-data/things-band-backup/data
   nano .env        # keys from .env.example
   chmod 600 .env
   ```

   - `IMMICH_URL`: the Immich app on the Umbrel network works without leaving
     the server, e.g. `http://immich_server_1:2283`.
   - Only `BANDS`, `BAND_PHONE`, `BAND_PASSWORD`, `IMMICH_URL`, `IMMICH_API_KEY`
     are needed for the backup; the Discord, Claude and Google settings are opt-in.
3. Optional Google Calendar mirror: copy the service account key to
   `data/google-service-account.json` (`chmod 600`), see the band-backup
   `docs/google-calendar.md`.
4. Restart the app and watch the first run:

   ```sh
   sudo docker logs -f --tail 50 things-band-backup_server_1
   ```

   BAND may ask for a login code; it is sent to the Discord webhook.

## Releasing a new version

1. In band-backup: bump `src/version.py`, push the `vX.Y.Z` tag; GitHub Actions
   publishes `ghcr.io/kic2807/band-backup:X.Y.Z`.
2. Get the digest:
   `docker buildx imagetools inspect ghcr.io/kic2807/band-backup:X.Y.Z`
3. Here: update the image `tag@sha256:digest` in `docker-compose.yml`, and
   `version` / `releaseNotes` in `umbrel-app.yml`.
