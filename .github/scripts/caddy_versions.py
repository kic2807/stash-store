#!/usr/bin/env python3
"""Pick the versions for ghcr.io/kic2807/caddy-cloudflare.

Newest stable official caddy release that has both `X.Y.Z` and
`X.Y.Z-builder` images, and the newest caddy-dns/cloudflare tag. Prints
key=value lines for $GITHUB_OUTPUT: caddy, cloudflare, tag, exists.
"""

import json
import os
import re
import sys
import urllib.error
import urllib.request
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from update_images import list_tags  # noqa: E402

IMAGE = "ghcr.io/kic2807/caddy-cloudflare"
SEMVER = re.compile(r"^v?(\d+)\.(\d+)\.(\d+)$")


def newest(tags):
    return max((t for t in tags if SEMVER.match(t)), key=lambda t: tuple(map(int, SEMVER.match(t).groups())))


def plugin_tags():
    token = os.environ.get("GH_TOKEN") or os.environ.get("GITHUB_TOKEN")
    headers = {"Accept": "application/json", **({"Authorization": f"Bearer {token}"} if token else {})}
    req = urllib.request.Request("https://api.github.com/repos/caddy-dns/cloudflare/tags?per_page=100", headers=headers)
    with urllib.request.urlopen(req, timeout=30) as resp:
        return [t["name"] for t in json.load(resp)]


def main():
    official = set(list_tags("caddy"))
    caddy = os.environ.get("CADDY_VERSION") or newest(t for t in official if f"{t}-builder" in official)
    cloudflare = (os.environ.get("CLOUDFLARE_VERSION") or newest(plugin_tags())).lstrip("v")
    tag = f"{caddy}-cf{cloudflare}"
    try:
        exists = tag in list_tags(IMAGE)
    except urllib.error.HTTPError as err:
        if err.code not in (401, 403, 404):
            raise
        exists = False  # package not created yet (or still private)
    print(f"caddy={caddy}\ncloudflare={cloudflare}\ntag={tag}\nexists={str(exists).lower()}")


if __name__ == "__main__":
    main()
