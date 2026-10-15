# things-qbittorrent

qBittorrent with all traffic routed
through a Tailscale exit node.

## Layout

| Service       | Image                              | Notes |
|---------------|------------------------------------|-------|
| `net`         | `registry.k8s.io/pause`            | owns the shared network namespace, IP and published ports (does nothing else) |
| `tailscale`   | `tailscale/tailscale`              | `network_mode: service:net`; node name `umbrel-qbit-node`; sets the exit node, healthy only while it is online |
| `qbittorrent` waits | | starts only after `tailscale` is healthy (`depends_on: service_healthy`) |
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

## Exit node

The exit node is set by **MagicDNS name** (`EXIT_NODE` in `.env`, e.g.
`jp-tyo-wg-001.mullvad.ts.net`), so it keeps working when the node's
address changes.

- **Why not in `TS_EXTRA_ARGS`:** a name only resolves once tailscaled has its
  peer list; at `tailscale up` time it fails with *cannot resolve exit node by
  hostname while Tailscale is starting up*.
- **How it is set:** the `tailscale` service runs a small wrapper around the
  image's own `containerboot`. Once the node is up (containerboot's
  `/healthz`), it checks whether traffic really leaves through Mullvad
  (`https://am.i.mullvad.net/json`, `"mullvad_exit_ip":true`). If not, it runs
  `tailscale set --exit-node=$EXIT_NODE --exit-node-allow-lan-access=true`
  and checks again after 10 s; while connected it checks every 60 s. Each
  `set` looks the name up again, so a changed exit node IP is picked up. A
  wrapper keeps this in one container with direct access to tailscaled's
  socket; a separate service would need the socket shared through a volume
  and its own restart handling.
- **Why Mullvad's check and not `tailscale status`:** with a Mullvad exit node
  set and working, `tailscale status --json` still had no `ExitNodeStatus`
  (tested), so a check based on it never passed. Mullvad's service tests the
  real traffic path. This ties the app to Mullvad exit nodes: any other exit
  node never counts as healthy.
- **`--reset` stays** (fixed in the compose file, not in `.env`):
  containerboot runs `tailscale up` on every start, and `up` refuses to run
  when persisted settings, such as the exit node from `tailscale set`, are not
  repeated in its flags. `--reset` clears them at start and the wrapper sets
  the exit node again right after, so `.env` stays the single source of truth.
- **Health:** `tailscale` is healthy only while Mullvad's check says the
  traffic leaves through Mullvad (every 30 s). qBittorrent starts only after
  that. If the exit node goes away later, the container turns unhealthy
  (visible in `sudo docker ps`); qBittorrent keeps running but its torrents
  are bound to `tailscale0`, so they stop (see Kill switch).
- **Mullvad nodes must be visible to this device.** If
  `tailscale exit-node list | grep -c mullvad` inside the container prints 0,
  Tailscale is not sending Mullvad nodes to it: check Settings → Mullvad VPN
  in the admin console (the device must be on the list) and that the ACL
  allows `autogroup:internet`. Nothing in the app can fix that.
- **A failed install leaves containers running.** umbrelOS forgets the app but
  does not stop `net` and `tailscale`. Before installing again:
  `sudo docker rm -f $(sudo docker ps -aq --filter name=things-qbittorrent_)`
  (keeps the data folder, i.e. `.env` and the node identity).

## Setup

1. Tailscale admin console:
   - Settings → Keys → **Generate auth key** (reusable off; tag it if you use ACL tags).
   - Make sure the exit node is approved and the ACL lets this node use it.
2. **Create `.env` before installing.** qBittorrent only starts once the exit
   node is online, and umbrelOS drops an install whose first start fails
   (it hangs at 1% and disappears). The install copies the app's files into
   the data folder with `rsync` and keeps files already there, so a `.env`
   created beforehand survives:

   ```sh
   D=~/umbrel/app-data/things-qbittorrent/data
   mkdir -p $D
   nano $D/.env     # TS_AUTHKEY and EXIT_NODE (keys from .env.example)
   chmod 600 $D/.env
   ```

3. Install the app. Tailscale logs in, the exit node is set and qBittorrent
   starts, all within the first start. In the Tailscale admin console,
   `umbrel-qbit-node` appears; disable key expiry for it.

   Check that the exit node was set and is online:

   ```sh
   sudo docker logs things-qbittorrent_tailscale_1 2>&1 | grep 'exit node set'
   sudo docker ps --filter name=things-qbittorrent --format '{{.Names}}  {{.Status}}'
   sudo docker exec things-qbittorrent_tailscale_1 wget -T 10 -qO- https://am.i.mullvad.net/connected; echo
   ```

   `tailscale_1` should show `(healthy)` and `qbittorrent_1` should be `Up`.
4. Check that traffic leaves through the exit node:

   ```sh
   sudo docker exec things-qbittorrent_tailscale_1 wget -T 10 -qO- https://ifconfig.me/ip; echo
   ```

   It must print the exit node's public IP, not your home IP. (Run it in the
   `tailscale_1` container: `net_1` is a bare `pause` container with no shell
   or `wget`. All three share one network namespace, so the result is the
   same.)

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

qBittorrent is bound to the `tailscale0` interface: **Tools → Options →
Advanced → Network interface → `tailscale0`** (new installs get this from the
seeded `data/qbittorrent/qBittorrent/qBittorrent.conf`; check it once). With
it, torrent traffic can only leave through Tailscale:

- exit node offline or unset: `tailscale0` has no internet route, so
  torrents stop;
- `tailscale` container stopped: `tailscale0` is gone, so torrents stop.

Without it, qBittorrent would fall back to the normal Docker route, i.e. your
home connection. Do not change it.

### Test that downloads stop

Tested 2026-10-16 with a Mullvad exit node: downloads stopped while
`tailscale` was down and resumed after the restart.

1. Start a legal test torrent (e.g. a Linux ISO) and let it download.
2. Check the address torrents use (the same interface binding):

   ```sh
   sudo docker exec things-qbittorrent_qbittorrent_1 curl -s -m 10 --interface tailscale0 https://ifconfig.me; echo
   ```

   It prints the exit node's public IP.
3. Take the exit path away by stopping Tailscale:

   ```sh
   sudo docker stop things-qbittorrent_tailscale_1
   ```

4. Within a few seconds the WebUI's download speed drops to 0, and the
   command from step 2 fails (no `tailscale0`). For comparison, without
   `--interface` it prints your **home** IP: that is the route torrents would
   leak to without the interface binding.

   ```sh
   sudo docker exec things-qbittorrent_qbittorrent_1 curl -s -m 10 --interface tailscale0 https://ifconfig.me; echo
   sudo docker exec things-qbittorrent_qbittorrent_1 curl -s -m 10 https://ifconfig.me; echo
   ```

5. Restore: restart the app from the home screen (or
   `sudo docker start things-qbittorrent_tailscale_1`). The exit node is set
   again within about a minute and downloads resume.

Turning the exit node off with `tailscale set --exit-node=` is not a useful
test: the wrapper sets it again within 10 s.
