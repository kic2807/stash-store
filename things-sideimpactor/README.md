# things-sideimpactor

[Side Impactor](https://github.com/lbr77/SideImpactor): sign IPA files with
your Apple ID and install them on an iPhone, entirely in the browser. The
iPhone is plugged into **the computer running the browser** (WebUSB), not
into the Umbrel.

- Browser: **Chrome or Edge on desktop** (Safari and Firefox have no WebUSB).
- **HTTPS only**: WebUSB and the in-browser crypto need a secure context, so
  it is opened through things-caddy, never via the Umbrel home-screen icon
  (the manifest port 30108 is a placeholder).

## How it is built

| Service | Image | What |
|---------|-------|------|
| `web` | `ghcr.io/lbr77/sideimpactor` (`main`, pinned by digest) | upstream's frontend (nginx, port 3000) |
| `wisp` | `ghcr.io/kic2807/wisp-relay` (this repo, `.github/wisp-relay`) | Wisp WebSocket relay at `/wisp/` |

The page reaches Apple's servers (login, certificates, provisioning) through
a Wisp relay on its own origin. TLS to Apple runs inside the browser, so the
relay only forwards encrypted bytes and never sees your Apple ID password.
Upstream only ships that relay as a Cloudflare Worker; `wisp-relay` is the
same thing for Docker with the same limits: only `auth/buy/init/p*-buy.
itunes.apple.com`, `gsa.apple.com` and `developerservices2.apple.com`, port
443, no direct/private/loopback IPs, no UDP (tested: an Apple host connects,
`example.com` and `127.0.0.1` are refused).

Caddy serves both on one origin: `sideload.<domain>/wisp/*` → `wisp`,
everything else → `web`. The host is private (LAN/Tailscale + Tinyauth).

Upstream publishes only the moving `main` tag; the store's update job follows
its digest and sets the version to `main-<UTC time found>`.

## Setup

1. Install the app.
2. Caddy: the `sideload.` block is in the Caddyfile example (private hosts
   section). Add it to the live Caddyfile, validate, reload.
3. Cloudflare: DNS-only A record `sideload` → the Umbrel's Tailscale address
   (like `movies`), and a UniFi local DNS record → the Umbrel LAN address if
   you use those at home.
4. Open `https://sideload.<domain>:30443` in Chrome/Edge, sign in through
   Tinyauth/Pocket ID.

## Using it

1. Plug the iPhone into the computer (USB), unlock it, trust the computer.
2. Pair the device in the page (WebUSB prompt), sign in with your Apple ID
   (two-factor code on your Apple devices), drop in an IPA, install.
3. With a free Apple ID, installed apps expire after 7 days and need
   re-signing (same as AltStore/Sideloadly).

If the page reports that libcurl/WISP cannot start, check the relay:
`sudo docker logs --tail 20 things-sideimpactor_wisp_1` (it logs each
connection and refused hosts) and that Caddy routes `/wisp/*` to it.
