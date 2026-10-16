# things-transmission-vpn

Sends the **official Umbrel Transmission app** through a Tailscale Mullvad
exit node, with a kill switch. It does not replace or modify Transmission
(Radarr, Sonarr and Prowlarr depend on the official app); it only adds a
sidecar that joins Transmission's network namespace.

- Transmission's internet traffic leaves through Mullvad.
- Private ranges stay direct: the Umbrel UI, Radarr/Sonarr
  (`transmission_server_1:9091`) and Caddy keep working.
- Nothing else on the Umbrel is affected.

No web UI: keep using the Transmission icon. The manifest port 30107 is a
placeholder.

## How it works

| Service | Image | What |
|---------|-------|------|
| `tailscale` | `tailscale/tailscale` | `network_mode: "container:transmission_server_1"`; kill switch, then Tailscale, then the exit node |
| `watchdog` | `docker:cli` | reattaches `tailscale` when Transmission is recreated or starts later; **uses the Docker socket** |

**Kill switch.** Before tailscaled starts, the sidecar puts a `KILLSWITCH`
chain into Transmission's `OUTPUT` (filter table; Docker's DNS rules in the
nat table are untouched). Allowed: loopback, `tailscale0`, tailscaled's own
packets (bypass mark `0x80000/0xff0000`), `10.0.0.0/8`, `172.16.0.0/12`,
`192.168.0.0/16`. Everything else is rejected; IPv6 only allows loopback,
`tailscale0` and the mark (if `ip6tables` works on this kernel; the Docker
network has no IPv6 anyway). The chain is rebuilt on every start without a
gap and never duplicated. The rules belong to Transmission's namespace, so
they **stay when the sidecar stops**: Transmission is blocked, not leaked.

**Exit node.** `EXIT_NODE` is a MagicDNS name (e.g.
`jp-tyo-wg-001.mullvad.ts.net`), set with `tailscale set` once the node is up
and again whenever Mullvad's own check (`am.i.mullvad.net`) fails, the same
way as in things-qbittorrent. `--reset` stays in `TS_EXTRA_ARGS` because
containerboot runs `tailscale up` on every start.

**Reattaching.** A container joined with `container:<name>` keeps the
namespace it started in. When Transmission is recreated (every update), it
gets a new, empty namespace: no VPN and no kill switch. Docker looks the name
up again on every start, so restarting the sidecar joins the new one, but
Docker's restart policy gives up after one failed start
(`daemon/monitor.go`), so it cannot do this by itself. The watchdog checks
every 3 s: if Transmission runs and the sidecar is stopped, or Transmission
started after the sidecar, it starts/restarts the sidecar. This also covers a
boot where this app comes up before Transmission.

> **Docker socket:** the watchdog mounts `/var/run/docker.sock`, which gives
> it root-level control over the host's Docker. It runs with no network
> (`network_mode: none`) and only runs `docker inspect`, `docker start` and
> `docker restart` on the two containers named in its script.

**Fail-closed layer in Transmission.** Between Transmission being recreated
and the watchdog reattaching (a few seconds), Transmission has no kill
switch. Binding Transmission to this node's Tailscale address closes that
gap for peer connections: without `tailscale0` that address does not exist.
See setup step 5.

## Setup

1. **Tailscale admin console:**
   - Settings → Keys → **Generate auth key**.
   - After step 3: allow the node `things-transmission-vpn` to use Mullvad
     (Settings → Mullvad VPN; check the device limit) and turn off key expiry.
2. **`.env` before installing** (the install keeps files already in the data
   folder):

   ```sh
   D=~/umbrel/app-data/things-transmission-vpn/data
   mkdir -p $D
   nano $D/.env     # TS_AUTHKEY and EXIT_NODE (keys from .env.example)
   chmod 600 $D/.env
   ```

3. **Install** (Transmission must be installed and running). Check:

   ```sh
   sudo docker ps --filter name=things-transmission-vpn --format '{{.Names}}  {{.Status}}'
   sudo docker logs things-transmission-vpn_tailscale_1 2>&1 | grep -E 'kill switch|exit node set'
   sudo docker exec things-transmission-vpn_tailscale_1 wget -T 10 -qO- https://am.i.mullvad.net/connected; echo
   ```

   Expected: `tailscale_1 (healthy)`, `kill switch: IPv4 rules applied`,
   `exit node set: …`, "You are connected to Mullvad".

   If the Mullvad nodes are missing (`tailscale exit-node list | grep -c
   mullvad` inside the container prints 0), restart the container once and
   check the Mullvad VPN settings; see things-qbittorrent README.
4. **Transmission still reachable:** open Transmission from the Umbrel home
   screen; in Radarr/Sonarr, Settings → Download Clients → Transmission →
   **Test** (host `transmission_server_1`, port `9091`).
5. **Fail-closed: bind Transmission to the Tailscale address.**

   ```sh
   sudo docker exec things-transmission-vpn_tailscale_1 tailscale --socket=/tmp/tailscaled.sock ip -4
   ```

   Stop Transmission (right-click → Stop; it rewrites `settings.json` on
   exit, so edit only while it is stopped), then set the address:

   ```sh
   F=~/umbrel/app-data/transmission/data/config/settings.json
   sudo sed -i 's#"bind-address-ipv4": *"[^"]*"#"bind-address-ipv4": "100.x.y.z"#' $F
   sudo grep bind-address-ipv4 $F
   ```

   Replace `100.x.y.z` with the address from above, then start Transmission.
   The node's Tailscale address stays the same as long as its state folder
   (`data/state`) is kept.

## Tests

1. **Mullvad allowed** for `things-transmission-vpn` in the Tailscale console.
2. **Torrent IP:** on [ipleak.net](https://ipleak.net), "Torrent Address
   detection" → copy the magnet link → add it in Transmission. ipleak.net
   must show a **Mullvad** address, not your home IP. Remove the torrent.
3. **Kill switch:** stop the watchdog first (it would restart the sidecar
   within 3 s), then the sidecar:

   ```sh
   sudo docker stop things-transmission-vpn_watchdog_1 things-transmission-vpn_tailscale_1
   sudo docker exec transmission_server_1 curl -s -m 10 https://ifconfig.me; echo
   ```

   The `curl` must fail (rejected), and an active torrent stops. Start both
   again (restart the app) and repeat test 2.
4. **Reattach after a Transmission restart:** restart the Transmission app;
   within ~10 s the watchdog logs `reattaching`
   (`sudo docker logs things-transmission-vpn_watchdog_1`). Repeat test 2.
5. **Reboot** the Umbrel, then repeat test 2.
6. **Radarr/Sonarr → Transmission** test passes, and the Umbrel UI opens
   Transmission.

## Known limits

- **Gap after Transmission is recreated:** a few seconds until the watchdog
  reattaches. Step 5 (bind address) blocks peer traffic in that gap; pause
  torrents before updating Transmission to be safe. Whether HTTP tracker
  announces honour the bind address has to be checked with test 2 after an
  update.
- **DNS:** Transmission's lookups (tracker host names) go to Docker's DNS and
  from there through your router, not through Mullvad (`TS_ACCEPT_DNS=false`).
  The connections themselves go through Mullvad.
- **No port forwarding:** Mullvad does not forward ports, so Transmission is
  not connectable from outside; it still downloads from connectable peers.
  The published port 51413 on the home IP gets no answers (the kill switch
  blocks replies).
- **Mullvad only:** the health check uses Mullvad's own service, so other
  exit nodes never count as healthy.
