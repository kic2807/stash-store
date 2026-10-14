# stash-stump

[Stump](https://github.com/stumpapp/stump): comics, manga and ebook server with
OPDS, Kobo and KOReader sync, and a mobile app.

## Layout

| Host (`~/umbrel/app-data/stash-stump/data/` unless noted) | Container | What |
|---|---|---|
| `config/` | `/config` | database, thumbnails, logs |
| Umbrel `Downloads/books` (default) | `/data` | your library files |
| `.env` (optional) | env | OIDC settings |

Change the library folder in Umbrel: right-click Stump → Settings → Folder
access → **Books**. Any folder (Home, external drive, network share) works.

## Setup

1. Install, put books into `Downloads/books` (or pick another folder as above).
2. Open Stump from the home screen and create the owner account.
3. Libraries → Create → path `/data` (or a subfolder like `/data/comics`).

Port **10801** (Stump's default, so reader apps can use their usual setting):

- Web UI: `http://<umbrel>:10801` (behind Umbrel login)
- OPDS: `http://<umbrel>:10801/opds/v1.2/catalog`
- Reader endpoints `/opds`, `/api`, `/kobo`, `/koreader` skip Umbrel login and
  use Stump accounts.

## Log in with Authelia (optional)

1. In Authelia, uncomment the `stump` client block in `configuration.yml` and
   put in the client secret digest (see stash-authelia README → OIDC clients).
   Redirect URI: `https://stump.<domain>/api/v2/auth/oidc/callback`.
2. Create `~/umbrel/app-data/stash-stump/data/.env` from `.env.example` with the
   plain client secret, `chmod 600`, restart Stump.

See [Stump's OIDC guide](https://www.stumpapp.dev/docs/guides/access-control/oidc)
for `STUMP_OIDC_DISABLE_LOCAL_AUTH` and other options.
