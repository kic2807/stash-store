# things-pocket-id

[Pocket ID](https://pocket-id.org) 2.x: a small OpenID Connect provider that
signs users in with **passkeys only** (no passwords).

- Apps with OIDC (Immich, Jellyfin, RomM, Stump) log in through it directly.
- Apps without it (Radarr, Sonarr, Prowlarr, Transmission) are protected by
  [things-tinyauth](../things-tinyauth/README.md), which signs in through Pocket ID.

It is opened at `https://id.<domain>` through [things-caddy](../things-caddy/README.md).
There is no Umbrel home-screen UI: the manifest port 30105 is a placeholder,
because passkeys only work on the domain in `APP_URL`.

## Files

Everything lives in `~/umbrel/app-data/things-pocket-id/data/`:

| Host | Container | What |
|------|-----------|------|
| `data/` | `/app/data` | SQLite database (users, passkeys, clients) and uploads |
| `secrets/encryption_key` | `/secrets` (read-only) | encrypts the signing keys in the database. **Losing it makes the database unusable.** (not in git) |
| `.env` | env | `APP_URL` |

## Setup

1. **Install the app.** It keeps restarting until steps 2–3 are done.

2. **Encryption key** (written straight to the file, never printed):

   ```sh
   D=~/umbrel/app-data/things-pocket-id/data
   head -c 32 /dev/urandom | base64 | tr -d '\n' > $D/secrets/encryption_key
   chmod 600 $D/secrets/encryption_key
   ls -la $D/secrets
   ```

   Back it up somewhere safe (password manager).

3. **`.env`:**

   ```sh
   D=~/umbrel/app-data/things-pocket-id/data
   printf 'APP_URL=https://id.%s\n' "<your-domain>" > $D/.env
   chmod 600 $D/.env
   cat $D/.env
   ```

4. **Caddy host** `id.<domain>` → `things-pocket-id_server_1:1411` (already in
   things-caddy's `Caddyfile.example`), then validate and reload Caddy.

5. **Restart the app** and check the log:

   ```sh
   sudo docker logs --tail 20 things-pocket-id_server_1
   ```

6. **Admin account:** open `https://id.<domain>/setup`, enter username, email
   and name, and register a passkey. The setup page only works until the first
   account exists. Register a second passkey (another device) under
   **My Account** so losing one device does not lock you out.

7. **Group:** Administration → User Groups → create `admins` and add yourself.
   Clients below allow only this group.

## Connecting apps

Create each app under **Administration → OIDC Clients → Add**: a name, the
callback URL(s) below, then on the client's **Access** tab select the
`admins` group. Pocket ID shows the **client ID** and **client secret**; the
app gets those plus:

| Setting | Value |
|---------|-------|
| Issuer / provider URL | `https://id.<domain>` |
| Discovery URL | `https://id.<domain>/.well-known/openid-configuration` |
| Scopes | `openid profile email` (+ `groups` if the app uses roles) |

| App | Callback URL(s) | Where in the app |
|-----|-----------------|------------------|
| Tinyauth | `https://login.<domain>:30443/api/oauth/callback/pocketid` | `things-tinyauth` `.env` (see its README) |
| Immich | `https://photos.<domain>/auth/login`, `https://photos.<domain>/user-settings`, `app.immich:///oauth-callback` | Administration → Settings → Authentication → OAuth |
| Jellyfin | `https://watch.<domain>/sso/OID/redirect/pocketid` | Dashboard → Plugins → **SSO Authentication** (9p4) → provider named `pocketid` |
| RomM | `https://games.<domain>/api/oauth/openid` | RomM app settings → environment: `OIDC_ENABLED=true`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI` (the callback), `OIDC_SERVER_APPLICATION_URL=https://id.<domain>`; check RomM's OIDC docs for `OIDC_PROVIDER` |
| Stump | `https://comics.<domain>/api/v2/auth/oidc/callback` | `things-stump` `.env` (see its README) |

**The app's server must reach `https://id.<domain>` too**, not only your
browser (Pocket ID docs). From the Umbrel, its own WAN address is refused by
the router (no hairpin), so this works when `id.<domain>` is proxied by
Cloudflare (orange cloud). If an app cannot fetch the discovery URL, check
that first. Tinyauth avoids the issue by calling Pocket ID inside Docker.

## Updating

Read the [release notes](https://github.com/pocket-id/pocket-id/releases)
before major updates (`/docs/setup/major-releases` on pocket-id.org). The
database is migrated on start; back up `data/` first.
