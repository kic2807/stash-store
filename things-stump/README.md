# things-stump

[Stump](https://github.com/stumpapp/stump): comics, manga and ebook server with
OPDS, Kobo and KOReader sync, and a mobile app.

## Nightly builds

This app runs Stump's **nightly** image (`aaronleopold/stump:nightly`, pinned
by digest). The store's update job follows that tag: when a new nightly is
published it re-pins the digest and sets the version to
`nightly-<UTC time found>`, so Umbrel shows an update. Nightlies can break or
migrate the database in ways an older build cannot read; back up
`data/config/` before updating if your library matters, and there is no way
back to the 0.1.x release with the same data.

## Layout

| Host (`~/umbrel/app-data/things-stump/data/` unless noted) | Container | What |
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

## Log in with Pocket ID (optional)

1. In Pocket ID, add an OIDC client `Stump` with callback URL
   `https://comics.<domain>/api/v2/auth/oidc/callback` and the `admins` group
   (see things-pocket-id README → Connecting apps).
2. Create `~/umbrel/app-data/things-stump/data/.env` from `.env.example` with the
   client ID and secret, `chmod 600`, restart Stump.
3. Stump is served at `https://comics.<domain>` (Caddy host `comics.` →
   `things-stump_server_1:10801`, already in the Caddyfile example; add
   `comics.<domain>` to cloudflare-ddns `DOMAINS`).

See [Stump's OIDC guide](https://www.stumpapp.dev/docs/guides/access-control/oidc)
for `STUMP_OIDC_DISABLE_LOCAL_AUTH` and other options.
