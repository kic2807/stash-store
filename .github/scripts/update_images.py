#!/usr/bin/env python3
"""Find newer upstream images for the store's apps and open one PR per app.

For each app listed in .github/image-updates.json:
  - look up the newest tag of every pinned image that matches its rule,
  - resolve the multi-arch index digest and check linux/amd64 is present,
  - rewrite `image: repo:tag@sha256:digest` in docker-compose.yml,
  - set umbrel-app.yml `version` (primary image version, or bump the -N
    packaging revision when only other images changed) and `releaseNotes`.

With --apply it commits each app to branch auto-update/<app>, opens or updates
the PR, and merges it when every bump kind is allowed by the image's
`automerge` rule. Without --apply it only prints what it would do.
"""

import argparse
import json
import re
import subprocess
import sys
import urllib.error
import urllib.parse
import urllib.request
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
CONFIG = json.loads((ROOT / ".github/image-updates.json").read_text())

ACCEPT = ", ".join([
    "application/vnd.oci.image.index.v1+json",
    "application/vnd.docker.distribution.manifest.list.v2+json",
    "application/vnd.oci.image.manifest.v1+json",
    "application/vnd.docker.distribution.manifest.v2+json",
])
IMAGE_RE = re.compile(r"^(\s*image:\s*)(\S+):([^@\s]+)@(sha256:[0-9a-f]{64})\s*$", re.M)
KINDS = ["major", "minor", "patch", "build"]


# --- registry -------------------------------------------------------------

def split_ref(name):
    first = name.split("/")[0]
    if "." in first or ":" in first:
        return first, name[len(first) + 1:]
    return "registry-1.docker.io", name if "/" in name else f"library/{name}"


_tokens = {}


def _request(registry, repo, path, method="GET"):
    url = path if path.startswith("http") else f"https://{registry}/v2/{repo}/{path}"
    headers = {"Accept": ACCEPT}
    if (registry, repo) in _tokens:
        headers["Authorization"] = f"Bearer {_tokens[(registry, repo)]}"
    try:
        return urllib.request.urlopen(urllib.request.Request(url, method=method, headers=headers), timeout=30)
    except urllib.error.HTTPError as err:
        if err.code != 401 or (registry, repo) in _tokens:
            raise
        challenge = dict(re.findall(r'(\w+)="([^"]*)"', err.headers.get("WWW-Authenticate", "")))
        query = urllib.parse.urlencode({"service": challenge.get("service", ""), "scope": f"repository:{repo}:pull"})
        with urllib.request.urlopen(f'{challenge["realm"]}?{query}', timeout=30) as resp:
            _tokens[(registry, repo)] = json.load(resp).get("token")
        return _request(registry, repo, path, method)


def list_tags(name):
    registry, repo = split_ref(name)
    tags, path = [], "tags/list?n=1000"
    while path:
        with _request(registry, repo, path) as resp:
            tags += json.load(resp).get("tags") or []
            link = resp.headers.get("Link", "")
        match = re.search(r"<([^>]+)>", link)
        path = urllib.parse.urljoin(f"https://{registry}", match.group(1)) if match else None
    return tags


def index_digest(name, tag):
    registry, repo = split_ref(name)
    with _request(registry, repo, f"manifests/{tag}") as resp:
        digest = resp.headers["Docker-Content-Digest"]
        body = json.load(resp)
    platforms = {
        f'{m["platform"]["os"]}/{m["platform"]["architecture"]}'
        for m in body.get("manifests", [])
        if m.get("platform", {}).get("os") not in (None, "unknown")
    }
    return digest, platforms


# --- versions -------------------------------------------------------------

def parse_tag(rule, tag):
    match = re.match(rule["tag"], tag)
    if not match:
        return None
    version = tuple(int(x) for x in match.group("v").split("."))
    version += (0,) * (3 - len(version))
    if rule.get("even_minor") and version[1] % 2:
        return None
    groups = sorted(match.re.groupindex, key=match.re.groupindex.get)
    build = tuple(int(match.group(k)) for k in groups if k != "v" and match.group(k) is not None)
    return version, build, match.group("v")


def bump_kind(old, new):
    for i, kind in enumerate(KINDS[:3]):
        if old[0][i] != new[0][i]:
            return kind
    return "build"


def next_revision(version):
    base, _, rev = version.partition("-")
    return f"{base}-{int(rev) + 1 if rev.isdigit() else 1}"


def replace_release_notes(manifest, text):
    """Replace the releaseNotes value (single line or indented block)."""
    lines = manifest.split("\n")
    start = next(i for i, line in enumerate(lines) if line.startswith("releaseNotes:"))
    end = start + 1
    while end < len(lines):
        if lines[end].startswith((" ", "\t")):
            end += 1
        elif lines[end] == "" and any(l.startswith((" ", "\t")) for l in lines[end:end + 3] if l):
            # blank line inside a folded block (paragraph break)
            nxt = next((l for l in lines[end:] if l), "")
            if not nxt.startswith((" ", "\t")):
                break
            end += 1
        else:
            break
    return "\n".join(lines[:start] + ["releaseNotes: >-", f"  {text}"] + lines[end:])


# --- planning -------------------------------------------------------------

def plan_app(app, app_cfg):
    compose_path = ROOT / app / "docker-compose.yml"
    compose = compose_path.read_text()
    changes = []
    for _, name, tag, digest in IMAGE_RE.findall(compose):
        rule = CONFIG["images"].get(name)
        if not rule:
            continue
        current = parse_tag(rule, tag)
        if not current:
            print(f"  ! {name}:{tag} does not match its tag rule, skipped", file=sys.stderr)
            continue
        lookup = rule.get("lookup", name)
        candidates = [(parse_tag(rule, t), t) for t in list_tags(lookup)]
        newest = max(((p, t) for p, t in candidates if p), default=None, key=lambda x: x[0][:2])
        if not newest or newest[0][:2] <= current[:2]:
            continue
        new_parsed, new_tag = newest
        new_digest, platforms = index_digest(lookup, new_tag)
        if "linux/amd64" not in platforms:
            print(f"  ! {name}:{new_tag} has no linux/amd64 image, skipped", file=sys.stderr)
            continue
        kind = bump_kind(current, new_parsed)
        changes.append({
            "name": name, "old": f"{name}:{tag}@{digest}", "new": f"{name}:{new_tag}@{new_digest}",
            "old_tag": tag, "new_tag": new_tag, "version": new_parsed[2], "kind": kind,
            "automerge": kind in rule.get("automerge", []),
        })
    if not changes:
        return None

    for change in changes:
        compose = compose.replace(change["old"], change["new"])

    manifest_path = ROOT / app / "umbrel-app.yml"
    manifest = manifest_path.read_text()
    old_version = re.search(r'^version:\s*"?([^"\n]+)"?\s*$', manifest, re.M).group(1)
    primary = next((c for c in changes if c["name"] == app_cfg["primary"]), None)
    if primary and primary["version"] != old_version.partition("-")[0]:
        new_version = primary["version"]
    else:
        new_version = next_revision(old_version)
    notes = " ".join(f"{c['name']} {c['old_tag']} -> {c['new_tag']}." for c in changes)
    manifest = re.sub(r'^version:.*$', f'version: "{new_version}"', manifest, count=1, flags=re.M)
    manifest = replace_release_notes(manifest, f"Updated images: {notes}")
    return {
        "app": app, "changes": changes, "old_version": old_version, "new_version": new_version,
        "files": {compose_path: compose, manifest_path: manifest},
        "automerge": all(c["automerge"] for c in changes),
    }


# --- git / GitHub ---------------------------------------------------------

def run(*cmd, check=True):
    return subprocess.run(cmd, cwd=ROOT, check=check, text=True, capture_output=True).stdout.strip()


def apply_plan(plan):
    app, branch = plan["app"], f"auto-update/{plan['app']}"
    title = f"{app}: {plan['old_version']} -> {plan['new_version']}"
    rows = "\n".join(
        f"| `{c['name']}` | `{c['old_tag']}` | `{c['new_tag']}` | {c['kind']} | {'yes' if c['automerge'] else '**no**'} |"
        for c in plan["changes"]
    )
    body = (
        f"Automated image update for `{app}`.\n\n"
        "| Image | From | To | Kind | Auto-merge |\n|---|---|---|---|---|\n"
        f"{rows}\n\n"
        f"`umbrel-app.yml` version: `{plan['old_version']}` -> `{plan['new_version']}`.\n"
        "Digests are the multi-arch index digests and include linux/amd64.\n"
    )
    if not plan["automerge"]:
        body += "\n**Needs review:** read the upstream release notes before merging.\n"

    run("git", "checkout", "-q", "-B", branch, "origin/main")
    for path, text in plan["files"].items():
        path.write_text(text)
    run("git", "add", app)
    run("git", "commit", "-q", "-m", title)

    remote = run("git", "ls-remote", "--heads", "origin", branch)
    if remote:
        run("git", "fetch", "-q", "origin", branch)
        if not run("git", "diff", "--name-only", f"origin/{branch}", "HEAD", "--", app):
            print(f"  = {branch} already up to date")
            run("git", "checkout", "-q", "main")
            return
    run("git", "push", "-q", "-f", "origin", branch)

    number = run("gh", "pr", "list", "--head", branch, "--state", "open", "--json", "number", "--jq", ".[0].number")
    if number:
        run("gh", "pr", "edit", number, "--title", title, "--body", body)
    else:
        url = run("gh", "pr", "create", "--base", "main", "--head", branch, "--title", title, "--body", body)
        number = url.rstrip("/").split("/")[-1]
    if plan["automerge"]:
        run("gh", "pr", "merge", number, "--squash", "--delete-branch")
        print(f"  merged #{number}")
    else:
        run("gh", "pr", "edit", number, "--add-label", "needs-review", check=False)
        print(f"  opened #{number} for review")
    run("git", "checkout", "-q", "main")


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--apply", action="store_true", help="commit, open PRs and merge allowed ones")
    args = parser.parse_args()

    for app, app_cfg in CONFIG["apps"].items():
        print(f"{app}:")
        plan = plan_app(app, app_cfg)
        if not plan:
            print("  up to date")
            continue
        for c in plan["changes"]:
            print(f"  {c['name']}: {c['old_tag']} -> {c['new_tag']} ({c['kind']}, automerge={c['automerge']})")
        print(f"  version {plan['old_version']} -> {plan['new_version']}")
        if args.apply:
            apply_plan(plan)


if __name__ == "__main__":
    main()
