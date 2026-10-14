# stash-qbittorrent

qBittorrent + [qui](https://github.com/autobrr/qui) with all traffic routed
through a Tailscale exit node.

## Layout

| Service       | Image                              | Notes |
|---------------|------------------------------------|-------|
| `tailscale`   | `tailscale/tailscale`              | owns the network namespace and all ports; hostname `umbrel-qbit-node` |
| `qbittorrent` | `lscr.io/linuxserver/qbittorrent`  | `network_mode: service:tailscale`, WebUI 30024, peers 6881 |
| `qui`         | `ghcr.io/autobrr/qui`              | `network_mode: service:tailscale`, listens on 7476 |

| Port  | Where | What |
|-------|-------|------|
| 30476 | Umbrel app URL (app_proxy → `tailscale:7476`) | qui, behind Umbrel login |
| 30024 | host | qBittorrent WebUI |
| 6881  | host, tcp+udp | BitTorrent (only useful if forwarded; normal peer traffic goes through the exit node) |

Downloads go to Umbrel's shared Downloads folder, mounted at `/downloads`,
the same path the official Radarr/Sonarr/Jellyfin apps use.

Persistent data under `~/umbrel/app-data/stash-qbittorrent/data/`:
`tailscale/` (node identity), `qbittorrent/` (config), `qui/` (config).

## Setup

1. Tailscale admin console:
   - Settings → Keys → **Generate auth key** (reusable off; tag it if you use ACL tags).
   - Make sure the exit node is approved and the ACL lets this node use it.
2. Install the app, then on the Umbrel terminal:

   ```sh
   cd ~/umbrel/app-data/stash-qbittorrent/data
   nano .env        # keys from .env.example, put the exit node IP in TS_EXTRA_ARGS
   chmod 600 .env
   ```

3. Restart the app. In the Tailscale admin console, `umbrel-qbit-node`
   appears; disable key expiry for it.
4. Check that traffic leaves through the exit node:

   ```sh
   sudo docker exec stash-qbittorrent_tailscale_1 wget -qO- https://ifconfig.me; echo
   ```

   It must print the exit node's public IP, not your home IP.

5. qBittorrent WebUI `http://<umbrel-ip>:30024`. The first password is random;
   find it with `sudo docker logs stash-qbittorrent_qbittorrent_1 | grep -i password`.
   Then in Tools → Options:
   - **Advanced → Network interface: `tailscale0`** (kill switch: if Tailscale
     is down, qBittorrent stops instead of using the home connection)
   - Downloads → Default save path: `/downloads` (keep it, the *arr apps expect it)
   - WebUI → change the password
6. Open the app from the Umbrel home screen (qui), create the qui account and
   add the qBittorrent instance: URL `http://localhost:30024` with the WebUI
   credentials.

## Connecting Radarr / Sonarr / Prowlarr

Download client → qBittorrent, host `stash-qbittorrent_tailscale_1`, port `30024`.

## Known limitation

If the `tailscale` container is restarted on its own, qBittorrent and qui
lose their network until they are restarted too. Restart the whole app from
the Umbrel home screen instead of single containers.
