# things-cloudflare-ddns

[favonia/cloudflare-ddns](https://github.com/favonia/cloudflare-ddns) keeps
Cloudflare DNS records pointed at this server's public IPv4 address
(IPv6 disabled). No web UI.

## Setup

1. Create a Cloudflare API token: My Profile → API Tokens → Create Token →
   "Edit zone DNS" template, limited to your zone.
2. Install the app, then on the Umbrel terminal:

   ```sh
   cd ~/umbrel/app-data/things-cloudflare-ddns/data
   nano .env        # keys from .env.example
   chmod 600 .env
   ```

3. Restart the app from the home screen.

Instead of `.env`, `CLOUDFLARE_API_TOKEN` and `DOMAINS` can be set in the app's
settings (umbrelOS 2.0 → right-click → Settings → environment variables).
Use one place only. To see the list in use without printing the token:

```sh
sudo docker inspect --format '{{range .Config.Env}}{{println .}}{{end}}' things-cloudflare-ddns_ddns_1 | grep '^DOMAINS='
```

### Proxied or DNS only

`PROXIED` decides which records go through Cloudflare's proxy (orange cloud).
Here only Pocket ID is proxied:

```
PROXIED=is(id.example.com)
```

Everything else is DNS only (grey cloud), i.e. reached directly at the home
IP. On the Free plan Cloudflare serves Korea from overseas locations (often
LA or Tokyo), which makes proxied photo/video apps slow; Cloudflare's terms
also limit serving heavy media through the proxy. Grey hosts expose the home
IP and need the router's NAT hairpin to work from inside the LAN.

`PROXIED` only applies when the updater **creates** a record. Existing
records keep their status; switch them in the Cloudflare dashboard (DNS →
Records → Edit → proxy status).

`DOMAINS` holds the **public** hosts only (Pocket ID `id.`, `photos.`,
`watch.`, …; Tinyauth's `login.` is private). The private hosts are separate DNS-only records (see
things-caddy README). Add a hostname here before opening it in a browser, or
the router may cache "does not exist" for a while.

## Check

```sh
sudo docker logs --tail 30 things-cloudflare-ddns_ddns_1
```

Look for lines saying the record is already up to date or was updated.
