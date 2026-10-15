# stash-tinyauth

[Tinyauth](https://tinyauth.app) 5.x: a small forward-auth server. Caddy asks
it before passing a request to a private app; visitors without a session are
sent to [Pocket ID](../stash-pocket-id/README.md), sign in with a passkey, and
come back.

Protects the apps that have no single sign-on of their own: Radarr
(`movies.`), Sonarr (`shows.`), Prowlarr (`search.`), qBittorrent (`torrents.`).

It is opened at `https://login.<domain>:30443` through [stash-caddy](../stash-caddy/README.md),
like the private hosts (LAN or Tailscale only).
There is no Umbrel home-screen UI: the manifest port 30106 is a placeholder.

## How it is set up here

- **Pocket ID only.** No local Tinyauth users; `TINYAUTH_OAUTH_AUTOREDIRECT=pocketid`
  sends you straight to Pocket ID. Who may sign in is decided in Pocket ID
  (the client's allowed group).
- **No Docker socket.** Tinyauth can read access rules from container labels,
  which needs the Docker socket; that is off (`TINYAUTH_LABELPROVIDER=none`).
  Every app behind it is allowed for any signed-in user.
- **Server-to-server calls stay inside Docker.** The token and userinfo URLs
  point at `http://stash-pocket-id_server_1:1411`, so they do not depend on
  the Umbrel reaching its own WAN address. Only your browser uses
  `https://id.<domain>`.
- The session cookie is set for `<domain>` (taken from `TINYAUTH_APPURL`), so
  one sign-in covers all private hosts.
- **`TINYAUTH_APPURL` carries the `:30443` port.** After sign-in Tinyauth only
  returns to an address it considers safe (`isRedirectSafe`): it compares the
  port first, and only on a matching port falls back to "any subdomain of the
  cookie domain". With `https://login.<domain>` (no port) the return address
  `https://movies.<domain>:30443/` fails with *port mismatch* and you end up on
  Tinyauth's own `/logout` page. Hence `login.<domain>` is a private host too:
  a DNS-only record pointing at the Umbrel's Tailscale address, not in
  cloudflare-ddns (Cloudflare cannot proxy port 30443 anyway).

## Files

`~/umbrel/app-data/stash-tinyauth/data/` → `/data`: session database
(`tinyauth.db`), OIDC keys (`oidc/`), and `.env`.

## Setup

Pocket ID must be set up first (admin account, `admins` group).

1. **Pocket ID client:** in Pocket ID, Administration → OIDC Clients → Add:
   - Name: `Tinyauth`
   - Callback URL: `https://login.<domain>:30443/api/oauth/callback/pocketid`
   - Access tab: group `admins`

   Keep the page open for the client ID and secret.

2. **Install the app**, then write `.env` (replace the three `<...>`):

   ```sh
   DOMAIN=<your-domain>
   D=~/umbrel/app-data/stash-tinyauth/data
   cat > $D/.env <<EOF2
   TINYAUTH_APPURL=https://login.$DOMAIN:30443
   TINYAUTH_OAUTH_PROVIDERS_POCKETID_CLIENTID=<client id>
   TINYAUTH_OAUTH_PROVIDERS_POCKETID_CLIENTSECRET=<client secret>
   TINYAUTH_OAUTH_PROVIDERS_POCKETID_AUTHURL=https://id.$DOMAIN/authorize
   TINYAUTH_OAUTH_PROVIDERS_POCKETID_REDIRECTURL=https://login.$DOMAIN:30443/api/oauth/callback/pocketid
   EOF2
   chmod 600 $D/.env
   ```

3. **Caddy:** the `login.` host and the `(tinyauth)` snippet are already in
   stash-caddy's `Caddyfile.example`. Validate and reload Caddy.

4. **Restart the app** and check the log:

   ```sh
   sudo docker logs --tail 20 stash-tinyauth_server_1
   ```

5. **Test:** open a private host, e.g. `https://movies.<domain>:30443`. You should
   go to Pocket ID, sign in with the passkey, and land back on movies (a 502
   there only means Radarr is not installed yet).
