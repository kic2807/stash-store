# stash-caddy

[Caddy](https://caddyserver.com) reverse proxy for all apps, replacing Nginx
Proxy Manager:

- receives the router's 80/443 on host ports **30080/30443** (+ 30443/udp, HTTP/3),
- one wildcard certificate `*.<domain>` from Let's Encrypt through the
  Cloudflare DNS challenge,
- passes requests straight to the app containers over the Umbrel Docker
  network (not through Umbrel's `app_proxy`, which would add Umbrel login),
- protects private apps with Authelia `forward_auth`.

Image: `ghcr.io/kic2807/caddy-cloudflare`, the official Caddy image plus the
[caddy-dns/cloudflare](https://github.com/caddy-dns/cloudflare) module, built
by this repository (root README → "caddy-cloudflare image").

No web UI: the manifest port 30104 is a placeholder.

## Files

Everything lives in `~/umbrel/app-data/stash-caddy/data/`:

| Host | Container | What |
|------|-----------|------|
| `etc/Caddyfile` | `/etc/caddy/Caddyfile` (read-only) | from `Caddyfile.example` (not in git) |
| `caddy/` | `/data` | certificates and ACME account. **Keep it**: losing it means new certificates (Let's Encrypt rate limits) |
| `config/` | `/config` | Caddy's autosaved config |
| `.env` | env | `CLOUDFLARE_API_TOKEN`, `LAN_CIDR` |

The Caddyfile is mounted as the `etc/` directory, not as a single file: if a
single-file mount source is missing, Docker creates a directory in its place.
A fresh install puts a placeholder `etc/Caddyfile` there that serves nothing.

## Ports

| Host | Container | Router forward |
|------|-----------|----------------|
| 30080/tcp | 80 | WAN 80 → 30080 |
| 30443/tcp | 443 | WAN 443 → 30443 |
| 30443/udp | 443 (HTTP/3) | WAN 443/udp → 30443 (optional) |

umbrelOS itself listens on 80 and 443 (dashboard), so Caddy cannot use them,
and 40000–49999 is reserved for Umbrel VMs.

The ports are published on IPv4 only (`0.0.0.0:`). Docker passes connections
to the host's IPv6 addresses through its userland proxy, and the container
would see the Docker gateway (172.x) as the client
([Docker docs](https://docs.docker.com/engine/network/port-publishing/)).

## Setup

1. **Cloudflare token.** My Profile → API Tokens → Create Token → "Edit zone
   DNS" template, limited to your zone. A separate token from
   stash-cloudflare-ddns is fine and easier to revoke.

2. **Install the app.** It starts with the placeholder Caddyfile.

3. **`.env`:**

   ```sh
   cd ~/umbrel/app-data/stash-caddy/data
   nano .env        # keys from .env.example
   chmod 600 .env
   ```

4. **Caddyfile:**

   ```sh
   D=~/umbrel/app-data/stash-caddy/data
   curl -fsSL https://raw.githubusercontent.com/kic2807/stash-store/main/stash-caddy/Caddyfile.example -o $D/etc/Caddyfile
   sed -i 's/example\.com/<your-domain>/g' $D/etc/Caddyfile
   nano $D/etc/Caddyfile     # remove apps you do not run yet
   ```

   The private hosts are commented out. **Leave them that way until the
   client IP test below passes.**

5. **Restart the app** (right-click → Restart; needed once so it reads `.env`).
   Check the log for the certificate:

   ```sh
   sudo docker logs --tail 50 stash-caddy_server_1
   ```

   Look for `certificate obtained successfully` for `*.<domain>`.

6. **Router:** forward WAN 80 → `<umbrel-ip>:30080` and 443 → `<umbrel-ip>:30443`.

7. **Client IP test (required)**, then enable the private hosts. See below.

## Changing the Caddyfile

After editing `etc/Caddyfile`:

```sh
sudo docker exec stash-caddy_server_1 caddy validate --config /etc/caddy/Caddyfile
sudo docker exec stash-caddy_server_1 caddy reload --config /etc/caddy/Caddyfile
```

`reload` applies the change without dropping connections. Changes to `.env`
need an app restart instead.

## Client IP test (required)

The `(private)` snippet only lets in clients whose address (`remote_ip`) is in
`LAN_CIDR` or Tailscale's `100.64.0.0/10`. That only works if Caddy sees the
real client address. If it saw Docker's gateway (172.x) instead, outside
requests could look like LAN ones. **Do not enable films/shows/search/torrents
until all three checks pass.** Authelia (`one_factor`, passkey login) still
protects them if this check ever fails, but it must not be the only protection.

The example has an `ipcheck.<domain>` host that uses `(private)` and answers
with the address Caddy sees.

1. **From the LAN** (a PC on Wi-Fi/Ethernet):

   ```sh
   curl --resolve ipcheck.<domain>:30443:<umbrel-lan-ip> https://ipcheck.<domain>:30443
   ```

   Expected: `allowed, you are 192.168.x.y` (your PC's LAN address).

2. **From outside** (a laptop on the phone's LTE hotspot, Wi-Fi off):

   ```sh
   curl -v --resolve ipcheck.<domain>:443:<wan-ip> https://ipcheck.<domain>
   ```

   Expected: the connection is closed without a response (`abort`). Your WAN
   IP is in the cloudflare-ddns log or at `curl -4 ifconfig.me` on the Umbrel.

3. **Caddy's log** for request 2:

   ```sh
   sudo docker logs stash-caddy_server_1 2>&1 | grep ipcheck | tail -3
   ```

   Expected: `"remote_ip":"<the LTE public address>"`. Compare with
   `curl -4 ifconfig.me` on the hotspot laptop.

Fail = request 2 gets `allowed` or the log shows `172.` / `10.` / your
router's address. Then do not open the private hosts; see "If Caddy sees
172.x" below.

After passing: uncomment the private hosts, remove the `ipcheck` block,
validate, reload. Repeat the test after umbrelOS updates.

## If Caddy sees 172.x

What was checked in the umbrelOS source (`getumbrel/umbrel`):

- **Docker daemon settings (`userland-proxy: false` etc.) cannot be kept.**
  umbrelOS ships `/etc/docker/daemon.json` (log options only) in a read-only
  system image. Its Rugix state config persists only `/data`, and Rugix
  discards the root overlay on every boot by default, so edits to
  `/etc/docker/daemon.json` are lost on reboot and on updates.
- **`network_mode: host` does not work for Caddy here.** Host-network
  containers are not on `umbrel_main_network`, so names like
  `radarr_server_1` do not resolve, and Caddy would also have to bind 30080/30443
  itself.

What can be done instead:

1. **Find which path loses the address.** IPv6 is the known case (Docker
   docs, above). This app already publishes IPv4 only; make sure the router
   forwards IPv4 and the DNS records for these hosts have no AAAA record
   (stash-cloudflare-ddns runs with `IP6_PROVIDER=none`).
2. **Keep the private hosts off the router path.** Publish a second port
   bound only to the Umbrel LAN address (e.g. `<umbrel-lan-ip>:30444:443`) and
   serve the private hosts only on `:30444` in the Caddyfile. The router
   forwards only 30443, so outside clients cannot reach them whatever address
   Caddy sees. This needs a compose change in the store (and a fixed LAN IP
   for the Umbrel); not done yet.

## Opening the private hosts

Private hosts are opened **with the port in the URL**, from the LAN and from
Tailscale alike:

```
https://films.<domain>:30443
```

umbrelOS itself listens on 443 on the LAN (`lan-ingress.ts` in the umbrelOS
source), so `https://films.<domain>` without the port would reach the Umbrel
dashboard instead of Caddy. The wildcard certificate is valid on any port, and
Authelia's session cookie and rules ignore the port.

DNS for the private hosts: a DNS-only (grey cloud) record pointing at the
Umbrel's LAN address. Never proxy them through Cloudflare (see below).

From Tailscale, how the client reaches that address (a subnet route on the
Umbrel, or the Umbrel's Tailscale address in a hosts entry) decides which
source address Caddy sees, and it must be in `LAN_CIDR` or `100.64.0.0/10`.
Not tested yet: open `https://ipcheck.<domain>:30443` from a Tailscale client
the way you plan to use it and check the answer before relying on it.

Alternatives not used (kept for reference):

- point the private hosts at the WAN address and let the router hairpin the
  traffic back; the source address Caddy then sees would have to pass the
  client IP test,
- a router rule on the LAN side that redirects `<umbrel-lan-ip>:443` to `:30443`.

## Hosts

| Host | Target | Access |
|------|--------|--------|
| `auth.` | `stash-authelia_server_1:9091` | public (Authelia portal) |
| `photos.` | `immich_server_1:2283` | public, Immich login / OIDC |
| `movies.` | `jellyfin_server_1:8096` | public, Jellyfin login / OIDC |
| `games.` | `romm_server_1:8080` | public, RomM login / OIDC |
| `requests.` | `jellyseerr_server_1:5055` | public, Jellyseerr login |
| `films.` | `radarr_server_1:7878` | private + Authelia one_factor |
| `shows.` | `sonarr_server_1:8989` | private + Authelia one_factor |
| `search.` | `prowlarr_server_1:9696` | private + Authelia one_factor |
| `torrents.` | `stash-qbittorrent_net_1:30024` | private + Authelia one_factor |

Targets are the official apps' `app_proxy` `APP_HOST`/`APP_PORT` values in
[getumbrel/umbrel-apps](https://github.com/getumbrel/umbrel-apps) (checked
2026-10-15). qBittorrent's target is `net_1`, the container that owns the
network namespace in stash-qbittorrent.

### Check container names

After installing an app, confirm its container and port:

```sh
sudo docker ps --format 'table {{.Names}}\t{{.Networks}}' | grep -E 'server_1|net_1'
sudo docker exec stash-caddy_server_1 wget -qO- -S http://radarr_server_1:7878 2>&1 | head -1
```

`wget` from inside the Caddy container proves the name resolves on the Umbrel
network and the port answers (any HTTP status line is fine).

## Cloudflare proxy and private hosts

Public hosts can be proxied by Cloudflare (orange cloud); apps then see
Cloudflare addresses unless you add Cloudflare's ranges as `trusted_proxies`.
Private hosts must not be proxied: through Cloudflare every client is a
Cloudflare address, so `(private)` blocks everyone.
