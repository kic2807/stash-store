# stash-cloudflare-ddns

[favonia/cloudflare-ddns](https://github.com/favonia/cloudflare-ddns) keeps
Cloudflare DNS records pointed at this server's public IPv4 address
(proxied, IPv6 disabled). No web UI.

## Setup

1. Create a Cloudflare API token: My Profile → API Tokens → Create Token →
   "Edit zone DNS" template, limited to your zone.
2. Install the app, then on the Umbrel terminal:

   ```sh
   cd ~/umbrel/app-data/stash-cloudflare-ddns/data
   nano .env        # keys from .env.example
   chmod 600 .env
   ```

3. Restart the app from the home screen.

Instead of `.env`, `CLOUDFLARE_API_TOKEN` and `DOMAINS` can be set in the app's
settings (umbrelOS 2.0 → right-click → Settings → environment variables).
Use one place only. To see the list in use without printing the token:

```sh
sudo docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' stash-cloudflare-ddns_ddns_1 | grep '^DOMAINS='
```

`DOMAINS` holds the **public** hosts only (Pocket ID `id.`, `photos.`,
`movies.`, …; Tinyauth's `login.` is private). The private hosts are separate DNS-only records (see
stash-caddy README). Add a hostname here before opening it in a browser, or
the router may cache "does not exist" for a while.

## Check

```sh
sudo docker logs --tail 30 stash-cloudflare-ddns_ddns_1
```

Look for lines saying the record is already up to date or was updated.
