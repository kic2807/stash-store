# things-qbittorrent

qBittorrent with all traffic routed
through a Tailscale exit node.

## Layout

| Service       | Image                              | Notes |
|---------------|------------------------------------|-------|
| `net`         | `registry.k8s.io/pause`            | owns the shared network namespace, IP and published ports (does nothing else) |
| `tailscale`   | `tailscale/tailscale`              | `network_mode: service:net`; node name `umbrel-qbit-node` |
| `qbittorrent` | `lscr.io/linuxserver/qbittorrent`  | `network_mode: service:net`, WebUI 30024, peers 6881 |

Because `net` owns the namespace, restarting `tailscale` or `qbittorrent`
alone does not cut the other off.

| Port  | Where | What |
|-------|-------|------|
| 30024 | Umbrel app URL (app_proxy → `net:30024`) | qBittorrent WebUI, behind Umbrel login (`/api/*` whitelisted, it has its own login) |
| 6881  | host, tcp+udp | BitTorrent (only useful if forwarded; normal peer traffic goes through the exit node) |

Downloads go to Umbrel's shared Downloads folder, mounted at `/downloads`,
the same path the official Radarr/Sonarr/Jellyfin apps use.

Persistent data under `~/umbrel/app-data/things-qbittorrent/data/`:
`tailscale/` (node identity), `qbittorrent/` (config).

## Setup

1. Tailscale admin console:
   - Settings → Keys → **Generate auth key** (reusable off; tag it if you use ACL tags).
   - Make sure the exit node is approved and the ACL lets this node use it.
2. Install the app, then on the Umbrel terminal:

   ```sh
   cd ~/umbrel/app-data/things-qbittorrent/data
   nano .env        # keys from .env.example, put the exit node IP in TS_EXTRA_ARGS
   chmod 600 .env
   ```

3. Restart the app. In the Tailscale admin console, `umbrel-qbit-node`
   appears; disable key expiry for it.
4. Check that traffic leaves through the exit node:

   ```sh
   sudo docker exec things-qbittorrent_tailscale_1 wget -T 10 -qO- https://ifconfig.me/ip; echo
   ```

   It must print the exit node's public IP, not your home IP.

5. Open the app from the Umbrel home screen (qBittorrent WebUI). The first password is random;
   find it with `sudo docker logs things-qbittorrent_qbittorrent_1 | grep -i password`.
   Then in Tools → Options:
   - WebUI → change the password
   - Check **Advanced → Network interface** is `tailscale0` (kill switch: if
     Tailscale is down, torrents stop instead of using the home connection).
     New installs get this from the seeded `data/qbittorrent/qBittorrent/qBittorrent.conf`.
   - Check Downloads → Default save path is `/downloads` (the *arr apps expect it)

## Connecting Radarr / Sonarr / Prowlarr

Download client → qBittorrent, host `things-qbittorrent_net_1`, port `30024`.

## Kill switch

When the `tailscale` container stops, the shared namespace falls back to the
normal Docker route. Only the `tailscale0` interface binding keeps torrents
from using the home connection then, so do not change it.
