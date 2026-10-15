# stash-authelia

[Authelia](https://www.authelia.com) 4.39: one account and passkey login for
every service.

- **Forward auth** through Caddy (`forward_auth`, stash-caddy) for apps without
  SSO: Radarr, Sonarr, Prowlarr, qBittorrent.
- **OpenID Connect provider** for Immich, RomM and Jellyfin (SSO plugin).
- Single container, SQLite storage, in-memory sessions (no Redis/PostgreSQL).
  Sessions are lost when Authelia restarts; everyone logs in again.

## Files

Everything lives in `~/umbrel/app-data/stash-authelia/data/`:

| Path (host)               | Container            | What |
|---------------------------|----------------------|------|
| `config/configuration.yml`| `/config`            | from `configuration.example.yml` (not in git) |
| `config/users_database.yml`| `/config`           | from `users_database.example.yml` (not in git) |
| `secrets/*`               | `/secrets` (read-only) | secrets, one per file (not in git) |
| `db/db.sqlite3`           | `/var/lib/authelia`  | users' passkeys, TOTP, consent, OIDC state |
| `db/notification.txt`     | `/var/lib/authelia`  | one-time codes (no SMTP) |

Secrets are passed as files (`AUTHELIA_*_FILE`), so they never appear in
`docker inspect`, the config file, or this repo.

| File | Used for |
|------|----------|
| `secrets/jwt_secret` | password reset tokens |
| `secrets/session_secret` | session cookies |
| `secrets/storage_encryption_key` | encrypts the SQLite database. **Losing it makes the database unreadable.** |
| `secrets/oidc_hmac_secret` | OIDC tokens |
| `secrets/oidc/private.pem` | OIDC signing key (RSA 2048) |

## Ports

- Caddy (stash-caddy) reaches Authelia over the Umbrel Docker network as
  `stash-authelia_server_1:9091`, so no host port is published. (9091 itself is
  already the official Transmission app's port.)
- The Umbrel home screen icon uses port **30091** with Umbrel login turned off
  (`PROXY_AUTH_ADD: "false"`), so there is no double login. It shows an
  Authelia error page there because the request is not for your domain; use
  `https://auth.<domain>`.

## Setup

All commands run on the Umbrel terminal. Each block starts by setting `IMG` and
`D`; run those lines again whenever you open a new terminal, otherwise the
commands fail with `Unable to find image 'authelia:latest'`.

1. **Install the app.** It keeps restarting until steps 2–4 are done; that is expected.

2. **Secrets** (random values are written straight to files, never printed):

   ```sh
   IMG=authelia/authelia:4.39.28; D=~/umbrel/app-data/stash-authelia/data
   sudo docker run --rm -u 1000:1000 -v $D/secrets:/secrets $IMG \
     authelia crypto rand --length 64 --charset alphanumeric \
     --file /secrets/jwt_secret,/secrets/session_secret,/secrets/storage_encryption_key,/secrets/oidc_hmac_secret
   mkdir -p $D/secrets/oidc && chmod 700 $D/secrets $D/secrets/oidc   # rsa generate does not create it
   sudo docker run --rm -u 1000:1000 -v $D/secrets:/secrets $IMG \
     authelia crypto pair rsa generate --bits 2048 --directory /secrets/oidc
   ls -la $D/secrets $D/secrets/oidc     # files should be -rw------- umbrel
   ```

   Back these files up somewhere safe (password manager). Umbrel backups include them too.

3. **Users** (`users_database.yml` is the list of accounts; one is enough).

   Make a password hash. It asks for the password twice and prints
   `Digest: $argon2id$v=19$m=65536,...`; copy everything from `$argon2id$` to
   the end. Keep the password in a password manager: it is needed for the first
   login and for registering passkeys.

   ```sh
   sudo docker run --rm -it authelia/authelia:4.39.28 authelia crypto hash generate argon2
   ```

   Create the file:

   ```sh
   nano ~/umbrel/app-data/stash-authelia/data/config/users_database.yml
   ```

   ```yaml
   users:
     <login id, e.g. alice>:
       disabled: false
       displayname: '<display name>'
       password: '<the whole $argon2id$... digest>'
       email: '<email>'
       groups:
         - 'admins'
   ```

   - The login id is what you type on the login page. Lowercase letters are safest.
   - Keep the single quotes around the digest; it contains `$`.
   - No mail is sent (no SMTP), but Immich matches OIDC logins by email,
     so use the same email as your accounts there.
   - `groups` is only used if `access_control` rules use `group:admins`.
   - Indent with spaces, never tabs.

   Save (`Ctrl+O`, `Enter`, `Ctrl+X`) and lock it:

   ```sh
   chmod 600 ~/umbrel/app-data/stash-authelia/data/config/users_database.yml
   ```

4. **Configuration** (`configuration.yml`).

   a. Download the example into place (it already has OIDC commented out, so it
      starts as is):

      ```sh
      D=~/umbrel/app-data/stash-authelia/data
      curl -fsSL https://raw.githubusercontent.com/kic2807/stash-store/main/stash-authelia/configuration.example.yml \
        -o $D/config/configuration.yml
      ```

   b. Put your domain in (replace `mydomain.tld`; the file never leaves the server):

      ```sh
      sed -i 's/example\.com/mydomain.tld/g' $D/config/configuration.yml
      grep -n 'mydomain.tld' $D/config/configuration.yml     # check the result
      ```

   c. Check the parts that depend on you with `nano $D/config/configuration.yml`:

      | Key | What to check |
      |-----|---------------|
      | `session.cookies[0].authelia_url` | the Authelia portal, `https://auth.<domain>` |
      | `session.cookies[0].default_redirection_url` | where to land after logging in at the portal directly |
      | `access_control.rules` | one entry per subdomain protected through Caddy `forward_auth`; anything not listed is denied |
      | `webauthn.display_name` | name shown in the passkey prompt |

   d. Lock it and validate:

      ```sh
      chmod 600 $D/config/configuration.yml
      sudo docker run --rm -u 1000:1000 -e X_AUTHELIA_CONFIG_FILTERS=template \
        -e AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET_FILE=/secrets/jwt_secret \
        -e AUTHELIA_SESSION_SECRET_FILE=/secrets/session_secret \
        -e AUTHELIA_STORAGE_ENCRYPTION_KEY_FILE=/secrets/storage_encryption_key \
        -v $D/config:/config -v $D/secrets:/secrets:ro authelia/authelia:4.39.28 \
        authelia validate-config --config /config/configuration.yml
      ```

      `Configuration parsed and loaded successfully without errors.` means it is
      fine. Otherwise the message names the key to fix.

5. **Restart the app** and check `sudo docker logs --tail 20 stash-authelia_server_1`
   for `Startup complete`.

6. **Caddy portal host** (`auth.` in stash-caddy's Caddyfile, see below), then open `https://auth.<domain>`, log in with
   the password, go to **Settings → Security keys / Passkeys → Add**. Authelia
   asks for a one-time code first; read it with
   `sudo tail -n 20 ~/umbrel/app-data/stash-authelia/data/db/notification.txt`. From then on use **Sign in with a passkey**.

## Caddy (stash-caddy)

Caddy reaches Authelia over the Umbrel Docker network as
`stash-authelia_server_1:9091`. Both pieces are already in
[stash-caddy's `Caddyfile.example`](../stash-caddy/Caddyfile.example), following
[Authelia's Caddy guide](https://www.authelia.com/integration/proxies/caddy/):

```caddyfile
(authelia) {
	forward_auth stash-authelia_server_1:9091 {
		uri /api/authz/forward-auth
		copy_headers Remote-User Remote-Groups Remote-Email Remote-Name
	}
}

# portal
@auth host auth.example.com
handle @auth {
	reverse_proxy stash-authelia_server_1:9091
}

# protected host
@films host films.example.com
handle @films {
	import private
	import authelia
	reverse_proxy radarr_server_1:7878
}
```

`/api/authz/forward-auth` is enabled in `configuration.yml` under
`server.endpoints.authz.forward-auth` (`implementation: 'ForwardAuth'`).

| Host | Opened as | Caddy | Authelia rule |
|------|-----------|-------|---------------|
| `auth.` | `https://auth.<domain>` | public | — (the portal) |
| `films.` `shows.` `search.` `torrents.` | `https://<name>.<domain>:30443` from LAN or Tailscale | `(private)` + `(authelia)` | `one_factor` |
| `photos.` `movies.` `games.` `requests.` | `https://<name>.<domain>` | public, no forward auth | — (OIDC clients / app login) |

- **The private hosts use port 30443 in the URL.** umbrelOS itself owns 443 on
  the LAN, see stash-caddy README. Authelia matches rules on the host name
  only, so the port needs no rule changes, and the session cookie (domain
  `<domain>`) is sent on any port.
- **Every protected host needs a rule in `access_control`**; the default is
  `deny`, so a host added to Caddy but not here returns 403.
- **One passkey login is enough** (`one_factor`) for all of them. Caddy
  already limits them to LAN and Tailscale clients.
- Caddy does not trust forwarded headers from clients (no `trusted_proxies`),
  so Authelia sees the address Caddy saw. Check it with Authelia's
  [validating forwarded authentication](https://www.authelia.com/reference/guides/validating-forwarded-authentication/)
  guide after setup.

## OIDC clients

Apps that can log in through Authelia: **Immich, RomM, Jellyfin** (SSO
plugin), **autobrr** and **Stump**. Radarr, Sonarr, Prowlarr and qBittorrent have no
OIDC support; they are protected with forward auth instead.

`configuration.yml` contains a commented-out block for each of them. To add
the first app:

1. Generate the client secret. It prints a `Random Password` (goes into the
   app) and a `Digest` (goes into Authelia):

   ```sh
   sudo docker run --rm authelia/authelia:4.39.28 authelia crypto hash generate pbkdf2 \
     --variant sha512 --random --random.length 72 --random.charset rfc3986
   ```

2. `nano ~/umbrel/app-data/stash-authelia/data/config/configuration.yml`, go to the
   bottom, and remove the leading `# ` from:
   - the `identity_providers:`, `oidc:`, `jwks:` block and `clients:` lines (first time only)
   - every line of that app's client block

   Replace `$pbkdf2-sha512$310000$REPLACE_WITH_DIGEST` with the Digest (keep the
   single quotes). Keep the indentation exactly as it is.

   First time only, put in the templates that read the OIDC secrets
   (`secrets/oidc_hmac_secret` and `secrets/oidc/private.pem`) in place of
   `HMAC_SECRET_TEMPLATE` and `SIGNING_KEY_TEMPLATE`:

   ```sh
   C=~/umbrel/app-data/stash-authelia/data/config/configuration.yml
   sed -i 's#HMAC_SECRET_TEMPLATE#{{ secret "/secrets/oidc_hmac_secret" | msquote }}#' $C
   sed -i 's#SIGNING_KEY_TEMPLATE#{{ secret "/secrets/oidc/private.pem" | mindent 10 "|" | msquote }}#' $C
   ```

   Never put `{{ ... }}` anywhere else in the file, comments included.

3. Run the `validate-config` command from setup step 4d, then restart the app.

4. Configure the app with the plain secret:

| App | Issuer / discovery | Client ID | Where | Notes |
|-----|-------------------|-----------|-------|-------|
| Immich | `https://auth.<domain>/.well-known/openid-configuration` | `immich` | Administration → Settings → Authentication → OAuth | mobile app login uses `app.immich:///oauth-callback` (already in the block) |
| RomM | `https://auth.<domain>` | `romm` | Umbrel → RomM app settings → environment: `OIDC_ENABLED=true`, `OIDC_PROVIDER=authelia`, `OIDC_CLIENT_ID`, `OIDC_CLIENT_SECRET`, `OIDC_REDIRECT_URI=https://games.<domain>/api/oauth/openid`, `OIDC_SERVER_APPLICATION_URL=https://auth.<domain>` | names from the Authelia RomM guide |
| Jellyfin | `https://auth.<domain>` | `jellyfin` | Dashboard → Plugins → install **SSO Authentication** (9p4) → add provider named `authelia` | the provider name is in the redirect URI |
| autobrr | `https://auth.<domain>` | `autobrr` | `~/umbrel/app-data/autobrr/data/config.toml`: `oidcEnabled`, `oidcIssuer`, `oidcClientId`, `oidcClientSecret`, `oidcRedirectUrl = "https://autobrr.<domain>/api/auth/oidc/callback"` | not covered by Authelia's guides; check autobrr's logs |
| Stump | `https://auth.<domain>` | `stump` | `~/umbrel/app-data/stash-stump/data/.env` from `stash-stump/.env.example` | see stash-stump README |

Authelia's per-app guides:
[Immich](https://www.authelia.com/integration/openid-connect/clients/immich/),
[RomM](https://www.authelia.com/integration/openid-connect/clients/romm/),
[Jellyfin](https://www.authelia.com/integration/openid-connect/clients/jellyfin/).

The redirect URIs use the stash-caddy host names `photos.` (Immich), `games.`
(RomM), `movies.` (Jellyfin), plus `autobrr.` and `stump.` (not in the Caddyfile
example; add a public host for them first). If you use other names, change
them in both the client block and the Caddyfile.

## Passkeys

A passkey login counts as **one** factor
([`enable_passkey_login`](https://www.authelia.com/configuration/second-factor/webauthn/#enable_passkey_login)).
That is why every rule and OIDC client here uses `one_factor`: one passkey
login and you are in. A `two_factor` rule would ask for the password after the
passkey. `webauthn.experimental_enable_passkey_uv_two_factors` stays off:
upstream marks it unsupported and plans to make it a startup error.

## Upgrading

Authelia changes configuration keys between minor versions and logs
deprecation warnings first. Before raising the image tag, read the release
notes and run the `validate-config` command from step 4 with the new image.
