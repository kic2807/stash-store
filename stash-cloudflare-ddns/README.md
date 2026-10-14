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

## Check

```sh
sudo docker logs --tail 30 stash-cloudflare-ddns_ddns_1
```

Look for lines saying the record is already up to date or was updated.
