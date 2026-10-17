# Haus Things — Umbrel Community App Store

Custom apps for umbrelOS 2.0 that are not in the official Umbrel App Store.
Store id `things`; every app id starts with `things-` (umbrelOS requires app
ids to start with the store id).

This repository is public. **No secrets, domains, IPs or account details are
committed.** Each app reads them from files you create on the Umbrel server.

## Add the store

umbrelOS → App Store → `⋯` (top right) → **Community App Stores** → add

```
https://github.com/kic2807/things-store
```

The apps show up under **Haus Things App Store**.

## Apps

| App | Version | Port | What | Setup |
|-----|---------|------|------|-------|
| [things-cloudflare-ddns](things-cloudflare-ddns/README.md) | 1.17.1 | — (30101 placeholder) | Keeps Cloudflare DNS records on this server's public IP. No web UI. | `.env` |
| [things-caddy](things-caddy/README.md) | 2.11.7-1 | 30080, 30443 (30104 placeholder) | Reverse proxy: wildcard certificate (Cloudflare DNS), forward auth for private apps. No web UI. | `.env` + Caddyfile |
| [things-pocket-id](things-pocket-id/README.md) | 2.18.0 | — (30105 placeholder) | Passkey-only sign-in (OIDC provider) at `id.<domain>`. | `.env` + key file, then web setup |
| [things-tinyauth](things-tinyauth/README.md) | 5.2.0 | — (30106 placeholder) | Pocket ID login in front of the private apps (Caddy forward auth) at `login.<domain>:30443`. | `.env` |
| [things-gitea-act-runner](things-gitea-act-runner/README.md) | 5.1.0 | — (30102 placeholder) | Gitea Actions runner with its own Docker-in-Docker. No web UI. **Not used: needs a Gitea server, which this setup no longer has. Do not install.** Kept just in case. | `.env` |
| [things-transmission-vpn](things-transmission-vpn/README.md) | 1.104.1 | — (30107 placeholder) | Add-on for the official Transmission app: Mullvad exit node + kill switch via a Tailscale sidecar. No web UI. Uses the Docker socket (watchdog). | `.env` |
| [things-stump](things-stump/README.md) | nightly | 10801 | Comics, manga and ebook server (OPDS, Kobo/KOReader sync). | none (optional `.env` for OIDC) |
| [things-komga](things-komga/README.md) | 1.29.1 | 25600 | Comics, manga and ebook server (OPDS, Kobo sync, Mihon API); candidate to replace Stump. | none (optional `application.yml` for OIDC) |
| [things-band-backup](things-band-backup/README.md) | 2.4.0 | — (30103 placeholder) | BAND → Immich backup and schedule-photo → calendar bot. No web UI. | `.env` |

"No web UI" apps have no `app_proxy`; the manifest port is only a placeholder
and opening them from the home screen shows nothing. Check them with
`sudo docker logs <container>`.

## Setting secrets and config

App data lives in `~/umbrel/app-data/<app-id>/data/` on the Umbrel server
(Settings → Advanced settings → Terminal → umbrelOS, or SSH). Docker commands
there need `sudo`.

### `.env` apps (cloudflare-ddns, caddy, pocket-id, tinyauth, gitea-act-runner, transmission-vpn, stump, band-backup)

`docker-compose.yml` loads `${APP_DATA_DIR}/data/.env` with
`env_file: required: false`, so the app installs without it and picks it up on
the next restart.

1. Install the app (this creates `data/`).
2. Look at the app's `.env.example` for the key names, then:

   ```sh
   cd ~/umbrel/app-data/<app-id>/data
   nano .env          # KEY=value per line, no quotes, no spaces around =
   chmod 600 .env
   ```

3. Restart the app from the home screen (right-click → Restart).

`env_file` only sets container environment variables; it cannot fill in
`${...}` inside `docker-compose.yml`. A value needed inside a command is read
at runtime instead (for example Transmission VPN's `EXIT_NODE`, used by a shell
wrapper as `$$EXIT_NODE`). A variable set under `environment:` in the compose
file wins over the same name in `.env`.

App updates replace only `docker-compose.yml`, templates, `exports.sh` and
`hooks/`, so `.env` and everything else under `data/` survive updates.
Files committed under an app's `data/` are copied on **fresh installs only**.

## Fresh umbrelOS install order

1. Add this store.
2. **things-cloudflare-ddns** → `.env` → check the log. DNS for the domain now points home.
3. **things-caddy** → `.env` + Caddyfile → router 80→30080, 443→30443 → certificate in the log → **client IP test** (required before any private host).
4. **things-pocket-id** → key file + `.env` → `https://id.<domain>/setup` (admin + passkey, `admins` group).
5. **things-tinyauth** → Pocket ID client → `.env` → open a private host to test.
6. Official **Transmission** → **things-transmission-vpn** (`.env` before installing) → its README tests (ipleak, kill switch, reattach, reboot).
7. Official **Immich** → **things-band-backup** → `.env` (Immich API key, BAND login).
8. Uncomment the private hosts in the Caddyfile / connect OIDC apps to Pocket ID one by one.

things-gitea-act-runner is not part of the install.

## Automatic image updates

`.github/workflows/update-images.yml` runs daily (04:23 KST, or manually from
the Actions tab). `.github/scripts/update_images.py` checks every pinned image
against the rules in `.github/image-updates.json` and, per app with a newer
image:

- updates `image: tag@sha256:digest` (multi-arch index digest, must include linux/amd64),
- sets `version` to the primary image's upstream version, or bumps the `-N`
  revision when only a secondary image changed (e.g. docker:cli in transmission-vpn),
- opens a PR on branch `auto-update/<app>`.

The PR is merged automatically unless a change needs review; then it stays
open with the `needs-review` label and you merge it yourself (no approval
needed, just **Merge**). A change needs review when:

1. the upstream release notes for any version between the installed and the
   new one mention a breaking change ("breaking change", `BREAKING`, ⚠,
   "action required", "manual migration", "incompatible"); the matching lines
   are quoted in the PR, or
2. the image is listed as always reviewed for that kind of update, or
3. the image has no usable release notes and the update kind is not in its
   fallback list.

| Image | Release notes from | Always reviewed | Fallback without notes |
|-------|--------------------|-----------------|------------------------|
| favonia/cloudflare-ddns | GitHub releases | — | minor, patch |
| gitea/runner | gitea.com releases | — | minor, patch |
| docker (dind) | moby/moby releases | — | minor, patch |
| docker (cli, watchdog) | moby/moby releases | — | minor, patch |
| tailscale | none (links only) | — | minor, patch |
| aaronleopold/stump (`nightly`) | none: follows the tag's digest | — | every new build |
| gotson/komga | GitHub releases | major | minor, patch |
| pocketid/pocket-id | GitHub releases | major | minor, patch |
| ghcr.io/tinyauthapp/tinyauth | GitHub releases | major | patch |
| ghcr.io/kic2807/caddy-cloudflare | caddyserver/caddy releases | major | patch, plugin-only rebuild |

### caddy-cloudflare image

The official Caddy image has no Cloudflare DNS module, so this repository
builds its own: `.github/workflows/build-caddy.yml` runs daily at 03:53 KST
(30 minutes before the image updates) and builds
`ghcr.io/kic2807/caddy-cloudflare:<caddy>-cf<plugin>` (e.g. `2.11.7-cf0.2.4`,
linux/amd64) from the official `caddy` and `caddy:<ver>-builder` images with
`xcaddy` and [caddy-dns/cloudflare](https://github.com/caddy-dns/cloudflare)
(`.github/caddy/Dockerfile`). It only builds when that tag does not exist yet,
after checking that `dns.providers.cloudflare` is in the binary. The image
update job then sees the new tag and opens the things-caddy PR like for any
other image; Caddy marks breaking changes in its release notes, so those PRs
wait for review.

Rebuild by hand: Actions → Build caddy-cloudflare → Run workflow (optionally
pin versions; tick *force* to overwrite an existing tag).

`things-band-backup` is not part of this: its image is released by hand from
the band-backup repo (see its README).

Merged updates only make the update button appear in Umbrel; nothing is
installed until you press it. Run `python3 .github/scripts/update_images.py`
locally to see pending updates without changing anything.

## Updating an app by hand

Umbrel shows an update when the `version` in `umbrel-app.yml` differs from the
installed one. To update:

1. Pick the new upstream release and get its multi-arch digest, e.g.
   `docker buildx imagetools inspect <image>:<tag>` (use the index digest, not
   a per-architecture one).
2. In `docker-compose.yml`, set `image: <image>:<tag>@sha256:<digest>`. Always
   keep tag and digest together.
3. In `umbrel-app.yml`, set `version` to the upstream version and update
   `releaseNotes`.
4. For a packaging-only change (no new upstream version), add a revision:
   `5.2.4` → `5.2.4-1` → `5.2.4-2`. Do not use `5.2.4.1`: umbrelOS normalizes
   it back to `5.2.4` and no update appears.
5. Commit and push to `main`. Umbrel picks it up on its next store refresh.

Read the upstream release notes before major updates (e.g. Gitea runner 5.x
workflow changes).

## Rules for new apps

- Directory name = app id = `things-<name>`.
- Persistent data only under `${APP_DATA_DIR}/data/...` bind mounts (directories,
  never single files; no named volumes). Commit `data/<dir>/.gitkeep` for
  empty mount sources.
- Shared Downloads: `${UMBREL_ROOT}/data/storage/downloads:/downloads` +
  `permissions: [STORAGE_DOWNLOADS]`.
- GPU: `permissions: [GPU]`, never map `/dev/dri`.
- Web UI through `app_proxy` (`APP_HOST: <app-id>_<service>_1`, `APP_PORT`).
  With `network_mode: service:<x>`, `APP_HOST` must be the container that owns
  the network namespace.
- Avoid host ports 80, 443, 2000, 40000–49999 and ports of official apps.
- Never mount the Docker socket, except where the README says why and the
  owner agreed (things-transmission-vpn watchdog).
- Pin every image as `tag@sha256:digest`.
- Secrets and infrastructure details only in server-side files, never in git.

References: [community store template](https://github.com/getumbrel/umbrel-community-app-store),
[official packaging guide](https://github.com/getumbrel/umbrel-apps/tree/master/.agents/skills/umbrel-package-app).
