# TODO

Setup progress on the Umbrel (fresh install with store id `things`).
Placeholders only: `<domain>` is the real domain, kept out of git.

## Done

- [x] Store renamed to Haus Things (id `things`, apps `things-*`, repo `things-store`)
- [x] things-cloudflare-ddns: token + `DOMAINS` (public hosts) + `PROXIED=is(id.<domain>)`
      in the app settings; `photos`, `watch`, `games`, `requests` switched to DNS only
- [x] things-caddy: `.env`, Caddyfile for `<domain>`, wildcard certificate,
      client IP tests (LAN, Tailscale = `10.21.0.1`, outside blocked)
- [x] Private hosts `movies`, `shows`, `search`, `download`, `login`: DNS-only
      records → Umbrel Tailscale IP, opened on `:30443`
- [x] things-pocket-id: key file, `APP_URL`, admin + passkey, `admins` group,
      Tinyauth client
- [x] things-tinyauth: `.env` on `login.<domain>:30443`; private host → Pocket ID
      passkey → app works
- [x] things-qbittorrent 5.2.4-4: exit node by MagicDNS name, Mullvad check
      healthy, kill switch test passed

## Next

- [ ] qBittorrent: turn off key expiry for `umbrel-qbit-node` (Tailscale admin)
- [ ] qBittorrent: change the WebUI password; check Network interface =
      `tailscale0` and save path = `/downloads`
- [ ] Radarr / Sonarr: download client qBittorrent, host
      `things-qbittorrent_net_1`, port `30024`
- [ ] Hairpin check from home for the DNS-only public hosts:
      `curl -sS -o /dev/null -w "%{http_code}\n" https://photos.<domain>/`
      (502 before Immich = OK; refused/timeout = enable NAT hairpin in UniFi)
- [ ] Immich (`photos.`) → Pocket ID OIDC client (things-pocket-id README)
- [ ] things-band-backup: `.env` (Immich API key, BAND login), then
      `sudo docker logs -f things-band-backup_server_1`
- [ ] Jellyfin (`watch.`) → SSO plugin + Pocket ID client; Jellyseerr (`requests.`)
- [ ] RomM (`games.`) → Pocket ID client
- [ ] things-stump (`comics.`): install, owner account, `comics.<domain>` in
      DDNS `DOMAINS`; optional Pocket ID client
- [ ] Optional: Radarr/Sonarr/Prowlarr auth "Disabled for Local Addresses" so
      Tinyauth is the only login (test on Radarr first)
- [ ] Optional: delete the old domain's DNS records and token access

## Notes for later

- Create an app's `.env` **before** installing when its first start depends
  on it (qBittorrent); a failed install leaves containers running:
  `sudo docker rm -f $(sudo docker ps -aq --filter name=<app-id>_)`.
- Add a DNS record before opening a new name, or the router caches NXDOMAIN
  (~30 min).
- If qBittorrent's tailscale turns unhealthy: check
  `tailscale exit-node list | grep -c mullvad` in the container; 0 = Tailscale
  is not sending Mullvad nodes (restart the container, check Mullvad VPN
  settings / `autogroup:internet`).
