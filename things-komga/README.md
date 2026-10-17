# things-komga

[Komga](https://komga.org): media server for comics, manga, BDs, magazines
and ebooks, with a web reader, OPDS, Kobo sync and an API used by apps like
Mihon/Tachiyomi.

## Layout

| Host (`~/umbrel/app-data/things-komga/data/` unless noted) | Container | What |
|---|---|---|
| `config/` | `/config` | database, thumbnails, logs, optional `application.yml` |
| Umbrel `Downloads/books` (default) | `/data` | your library files |

The library defaults to Umbrel's `Downloads/books`. Change it in Umbrel:
right-click Komga → Settings → Folder access → **Books**.

Runs as `1000:1000` (Komga's recommendation); the app data folders belong to
that user.

## Setup

1. Install, put books into `Downloads/books` (or pick another folder as above).
2. Open Komga from the Umbrel home screen (port **25600**) and create the
   admin account.
3. Libraries → **+** → root folder `/data` (or a subfolder like `/data/comics`).

Reader apps use the same address and port: `/api`, `/opds` and `/kobo` skip
Umbrel login and use Komga's own accounts.

- OPDS: `http://<umbrel>:25600/opds/v1.2/catalog` (or `/opds/v2/catalog`)
- Kobo sync and Mihon/Tachiyomi: see Komga's docs; they use an API key from
  your Komga account settings.

Through Caddy it is the public host `comics.<domain>`
(`things-komga_server_1:25600`, in the Caddyfile example); add
`comics.<domain>` to cloudflare-ddns `DOMAINS`. Do not put Tinyauth in
front of it: reader apps cannot do that login.

## Log in with Pocket ID (optional)

Komga supports OpenID Connect through its Spring configuration
([Komga docs: Social login](https://komga.org/docs/installation/oauth2)). It
matches the login to a Komga user by **email**, and the email must be marked
as verified.

1. Pocket ID → OIDC Clients → Add: name `Komga`, callback URL
   `https://comics.<domain>/login/oauth2/code/pocketid`, Access tab `admins`.
2. Create `~/umbrel/app-data/things-komga/data/config/application.yml`
   (`chmod 600`; not in git):

   ```yaml
   komga:
     oauth2-account-creation: false   # only existing Komga users (matched by email)
     oidc-email-verification: true
   spring:
     security:
       oauth2:
         client:
           registration:
             pocketid:
               provider: pocketid
               client-id: <client id>
               client-secret: <client secret>
               client-name: Pocket ID
               scope: openid,email,profile
               authorization-grant-type: authorization_code
               redirect-uri: "{baseUrl}/{action}/oauth2/code/{registrationId}"
           provider:
             pocketid:
               user-name-attribute: sub
               issuer-uri: https://id.<domain>
   ```

3. Restart Komga. The login page shows **Pocket ID**.

The Komga user's email must equal the Pocket ID email. If login fails with
an email-verification error, check that the email is verified in Pocket ID
(Administration → Users), or set `oidc-email-verification: false`.
Komga must reach `https://id.<domain>` from the Umbrel (works while `id.` is
proxied by Cloudflare). Reader apps keep using Komga's own login / API keys.
