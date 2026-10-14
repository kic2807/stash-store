# Stash — Umbrel Community App Store

Custom apps for umbrelOS 2.0 that are not in the official Umbrel App Store.
Store id `stash`; every app id starts with `stash-`.

This repository is public. **No secrets, domains, IPs or account details are
committed.** Each app reads them from files you create on the Umbrel server.

## Add the store

umbrelOS → App Store → `⋯` (top right) → **Community App Stores** → add

```
https://github.com/kic2807/stash-store
```

The apps show up under **Stash App Store**.

## Apps

| App | Version | Port | What | Setup |
|-----|---------|------|------|-------|
| [stash-cloudflare-ddns](stash-cloudflare-ddns/README.md) | 1.17.1 | — (30101 placeholder) | Keeps Cloudflare DNS records on this server's public IP. No web UI. | `.env` |
| [stash-gitea-act-runner](stash-gitea-act-runner/README.md) | 5.0.0 | — (30102 placeholder) | Gitea Actions runner with its own Docker-in-Docker. No web UI. | `.env` |
| [stash-qbittorrent](stash-qbittorrent/README.md) | 5.2.4 | 30024 | qBittorrent behind a Tailscale exit node. | `.env` |
| [stash-authelia](stash-authelia/README.md) | 4.39.28 | 30091 | SSO with passkeys: NPM forward auth + OIDC provider. | config files + secret files |
| [stash-hello-world](stash-hello-world/README.md) | 1.0.1 | 4000 | Test app for the store and the `.env` mechanism. | optional `.env` |

"No web UI" apps have no `app_proxy`; the manifest port is only a placeholder
and opening them from the home screen shows nothing. Check them with
`sudo docker logs <container>`.

## Setting secrets and config

App data lives in `~/umbrel/app-data/<app-id>/data/` on the Umbrel server
(Settings → Advanced settings → Terminal → umbrelOS, or SSH). Docker commands
there need `sudo`.

### `.env` apps (cloudflare-ddns, gitea-act-runner, qbittorrent, hello-world)

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
`${...}` inside `docker-compose.yml`. Values that are part of a longer setting
(for example the exit node in `TS_EXTRA_ARGS`) go into `.env` as the whole
value.

App updates replace only `docker-compose.yml`, templates, `exports.sh` and
`hooks/`, so `.env` and everything else under `data/` survive updates.
Files committed under an app's `data/` are copied on **fresh installs only**.

### Authelia

Configuration files under `data/config/` and one secret per file under
`data/secrets/`, passed to Authelia as `AUTHELIA_*_FILE`. See
[stash-authelia/README.md](stash-authelia/README.md).

## Fresh umbrelOS install order

1. Add this store.
2. **stash-cloudflare-ddns** → `.env` → check the log. DNS for the domain now points home.
3. Official **Nginx Proxy Manager** → proxy hosts + certificates.
4. **stash-authelia** → secrets, users, config → NPM `auth.` host → register a passkey.
5. Official **Gitea** → **stash-gitea-act-runner** → `.env` with a runner token.
6. **stash-qbittorrent** → `.env` → check the exit node IP → set the WebUI password.
7. Protect apps with NPM forward auth / connect OIDC apps one by one.

## Updating an app

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

Read the upstream release notes before major updates (Authelia config keys,
Gitea runner 5.x workflow changes).

## Rules for new apps

- Directory name = app id = `stash-<name>`.
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
- Never mount the Docker socket.
- Pin every image as `tag@sha256:digest`.
- Secrets and infrastructure details only in server-side files, never in git.

References: [community store template](https://github.com/getumbrel/umbrel-community-app-store),
[official packaging guide](https://github.com/getumbrel/umbrel-apps/tree/master/.agents/skills/umbrel-package-app).
