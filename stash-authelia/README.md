# stash-authelia

[Authelia](https://www.authelia.com) 4.39: one account and passkey login for
every service.

- **Forward auth** through Nginx Proxy Manager (`auth_request`) for apps without
  SSO: Radarr, Sonarr, Prowlarr, qBittorrent, the NPM admin UI.
- **OpenID Connect provider** for Immich, Gitea, RomM and Jellyfin (SSO plugin).
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

- Nginx Proxy Manager reaches Authelia over the Umbrel Docker network as
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
   sudo docker run --rm -u 1000:1000 -v $D/secrets:/secrets $IMG \
     authelia crypto pair rsa generate --bits 2048 --directory /secrets/oidc
   ls -la $D/secrets $D/secrets/oidc     # files should be -rw------- umbrel
   ```

   Back these files up somewhere safe (password manager). Umbrel backups include them too.

3. **Users:** copy the example and add a password hash.

   ```sh
   IMG=authelia/authelia:4.39.28; D=~/umbrel/app-data/stash-authelia/data
   sudo docker run --rm -it $IMG authelia crypto hash generate argon2   # prompts for the password
   nano $D/config/users_database.yml     # paste users_database.example.yml, set name/email/digest
   ```

4. **Configuration:** paste `configuration.example.yml` into
   `$D/config/configuration.yml` and replace `example.com` everywhere. Set up the
   OIDC clients you need (see below) or delete the `identity_providers` block
   until then. Check it:

   ```sh
   IMG=authelia/authelia:4.39.28; D=~/umbrel/app-data/stash-authelia/data
   sudo docker run --rm -u 1000:1000 -e X_AUTHELIA_CONFIG_FILTERS=template \
     -e AUTHELIA_IDENTITY_VALIDATION_RESET_PASSWORD_JWT_SECRET_FILE=/secrets/jwt_secret \
     -e AUTHELIA_SESSION_SECRET_FILE=/secrets/session_secret \
     -e AUTHELIA_STORAGE_ENCRYPTION_KEY_FILE=/secrets/storage_encryption_key \
     -e AUTHELIA_IDENTITY_PROVIDERS_OIDC_HMAC_SECRET_FILE=/secrets/oidc_hmac_secret \
     -v $D/config:/config -v $D/secrets:/secrets:ro $IMG \
     authelia validate-config --config /config/configuration.yml
   ```

5. **Restart the app** and check `sudo docker logs --tail 20 stash-authelia_server_1`
   for `Startup complete`.

6. **NPM portal host** (see below), then open `https://auth.<domain>`, log in with
   the password, go to **Settings → Security keys / Passkeys → Add**. Authelia
   asks for a one-time code first; read it with
   `sudo tail -n 20 ~/umbrel/app-data/stash-authelia/data/db/notification.txt`. From then on use **Sign in with a passkey**.

## Nginx Proxy Manager

### Snippets (once)

The official NPM app mounts `~/umbrel/app-data/nginx-proxy-manager/data/npm-data`
at `/data`, so put the snippets there:

```sh
S=~/umbrel/app-data/nginx-proxy-manager/data/npm-data/snippets
mkdir -p $S
```

`$S/proxy.conf`:

```nginx
proxy_set_header Host $host;
proxy_set_header X-Original-URL $scheme://$host$request_uri;
proxy_set_header X-Forwarded-Proto $scheme;
proxy_set_header X-Forwarded-Host $host;
proxy_set_header X-Forwarded-URI $request_uri;
proxy_set_header X-Forwarded-Ssl on;
proxy_set_header X-Forwarded-For $remote_addr;
proxy_set_header X-Real-IP $remote_addr;
proxy_http_version 1.1;
proxy_set_header Upgrade $http_upgrade;
proxy_set_header Connection $http_connection;
```

`$S/authelia-location.conf`:

```nginx
set $upstream_authelia http://stash-authelia_server_1:9091/api/authz/auth-request;

location /internal/authelia/authz {
    internal;
    proxy_pass $upstream_authelia;

    proxy_set_header X-Original-Method $request_method;
    proxy_set_header X-Original-URL $scheme://$host$request_uri;
    proxy_set_header X-Forwarded-For $remote_addr;
    proxy_set_header Content-Length "";
    proxy_set_header Connection "";

    proxy_pass_request_body off;
    proxy_http_version 1.1;
    proxy_cache_bypass $cookie_session;
    proxy_no_cache $cookie_session;
    proxy_buffers 4 32k;
    client_body_buffer_size 128k;
}
```

`$S/authelia-authrequest.conf`:

```nginx
auth_request /internal/authelia/authz;

auth_request_set $user $upstream_http_remote_user;
auth_request_set $groups $upstream_http_remote_groups;
auth_request_set $name $upstream_http_remote_name;
auth_request_set $email $upstream_http_remote_email;
proxy_set_header Remote-User $user;
proxy_set_header Remote-Groups $groups;
proxy_set_header Remote-Email $email;
proxy_set_header Remote-Name $name;

auth_request_set $redirection_url $upstream_http_location;
error_page 401 =302 $redirection_url;
```

These follow Authelia's [NGINX snippets](https://www.authelia.com/integration/proxies/nginx/#supporting-configuration-snippets)
with the upstream changed to the Umbrel container name. If your sites sit
behind Cloudflare's proxy, `$remote_addr` is a Cloudflare IP; see Authelia's
trusted-proxies notes before relying on per-IP bans.

### Authelia portal: `auth.<domain>`

- Details: scheme `http`, forward host `stash-authelia_server_1`, port `9091`
- SSL: your certificate, Force SSL on
- Advanced:

  ```nginx
  location / {
      include /data/snippets/proxy.conf;
      proxy_pass $forward_scheme://$server:$port;
  }
  ```

### Protected app (example: qBittorrent at `qbit.<domain>`)

- Details: forward host `stash-qbittorrent_net_1`, port `30024`
  (Radarr/Sonarr/Prowlarr: their Umbrel container name and port)
- SSL: your certificate, Force SSL on
- Advanced (the Details-tab switches and Custom Locations are ignored/unprotected
  when you use this):

  ```nginx
  include /data/snippets/authelia-location.conf;
  location / {
      include /data/snippets/proxy.conf;
      include /data/snippets/authelia-authrequest.conf;
      proxy_pass $forward_scheme://$server:$port;
  }
  ```

Every protected domain also needs a matching rule in `access_control`
(the default is `deny`).

## OIDC clients

For each app:

1. Generate a client secret and its digest:
   `sudo docker run --rm authelia/authelia:4.39.28 authelia crypto hash generate pbkdf2 --variant sha512 --random --random.length 72 --random.charset rfc3986`
   The plain secret goes into the app, the digest into `configuration.yml`.
2. Copy the client block from Authelia's integration page for that app into
   `identity_providers.oidc.clients`, set the domain and the digest.
3. Restart Authelia, then configure the app with issuer
   `https://auth.<domain>` (discovery: `https://auth.<domain>/.well-known/openid-configuration`),
   the client ID and the plain secret.

| App | Authelia guide | Where in the app |
|-----|----------------|------------------|
| Immich | [immich](https://www.authelia.com/integration/openid-connect/clients/immich/) (example already in `configuration.example.yml`, includes `app.immich:///oauth-callback` for the mobile app) | Administration → Settings → Authentication → OAuth |
| Gitea | [gitea](https://www.authelia.com/integration/openid-connect/clients/gitea/) | Site Administration → Identity & Access → Authentication Sources → Add (OAuth2, OpenID Connect) |
| RomM | [romm](https://www.authelia.com/integration/openid-connect/clients/romm/) | `OIDC_*` environment variables of the RomM app |
| Jellyfin | [jellyfin](https://www.authelia.com/integration/openid-connect/clients/jellyfin/) | install the SSO plugin (9p4/jellyfin-plugin-sso), then its settings page |

## Passkeys and `two_factor`

A passkey login counts as **one** factor. Domains with `two_factor` (and OIDC
clients with `authorization_policy: two_factor`) will additionally ask for the
password. To make a user-verified passkey (Face ID, fingerprint, PIN) count as
two factors, set `webauthn.experimental_enable_passkey_uv_two_factors: true`;
upstream marks it experimental and plans to replace it with custom policies.

## Upgrading

Authelia changes configuration keys between minor versions and logs
deprecation warnings first. Before raising the image tag, read the release
notes and run the `validate-config` command from step 4 with the new image.
