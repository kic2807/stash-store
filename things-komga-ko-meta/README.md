# things-komga-ko-meta

Add-on for [things-komga](../things-komga/README.md):
[komga-ko-meta](https://github.com/kic2807/komga-ko-meta) fills Komga with
Korean metadata and artwork. No web UI.

For each series:

| What | Where it goes in Komga | Source |
|---|---|---|
| Korean title | alternate title `ko` (main title with `--rename-title`) | Ridibooks, Wikidata, AniList |
| Synopsis, publisher, genres, status | series metadata | Ridibooks (AniList English synopsis as fallback) |
| Authors | book authors | Ridibooks, AniList |
| Characters (Korean edition names, e.g. 강백호) | book notable entities, kind `character` | Wikidata, AniList |
| Korean edition cover (960×1436) | series thumbnail, selected only while Komga's generated cover is in use | Ridibooks |
| Textless wide and square art | extra series thumbnails, not selected | Kitsu, AniList, TMDB (optional) |

It only fills empty fields; locked fields are never changed. Links to the
matched AniList / MyAnimeList / Ridibooks / Wikidata pages are added to each
series. To fix a wrong match, edit the series' AniList link in Komga to the
right `https://anilist.co/manga/<id>`; it takes priority over searching.

## Layout

| Host (`~/umbrel/app-data/things-komga-ko-meta/data/`) | Container | What |
|---|---|---|
| `.env` | env | `KOMGA_API_KEY`, optional `TMDB_API_KEY`, `KOMGA_KO_META_FLAGS` |
| `state.json` | `/data/state.json` | processed series (delete to redo everything) |

Runs as `1000:1000` with a read-only root filesystem and no capabilities.
Reaches Komga at `http://things-komga_server_1:25600` (Umbrel's app network),
so it does not go through Umbrel login or Caddy.

## Setup

1. Install **things-komga** and add your libraries.
2. In Komga, log in as an **admin** → Account settings → API keys → create a
   key for this add-on.
3. Install this app, then:

   ```sh
   cd ~/umbrel/app-data/things-komga-ko-meta/data
   nano .env          # KOMGA_API_KEY=<key>   (see .env.example)
   chmod 600 .env
   ```

4. Restart the app (right-click → Restart) and watch the log:

   ```sh
   sudo docker logs -f things-komga-ko-meta_meta_1
   ```

   It goes through the whole library once, then handles new series as Komga
   adds them (and re-checks everything every 6 hours). Unmatched series are
   retried after 7 days.

Without `.env` the app waits and logs what is missing.

## One-off commands

The image also runs the other commands (`inspect`, `push`), e.g. to preview a
title or redo one series:

```sh
sudo docker exec things-komga-ko-meta_meta_1 komga-ko-meta inspect "장송의 프리렌"
sudo docker exec things-komga-ko-meta_meta_1 komga-ko-meta push --search "원피스" --force --overwrite
sudo docker exec things-komga-ko-meta_meta_1 komga-ko-meta push --dry-run --force
```

## Releases

The image is released by hand from github.com/kic2807/komga-ko-meta: a
`vX.Y.Z` tag builds `ghcr.io/kic2807/komga-ko-meta:X.Y.Z`. Update the pinned
`image:` (tag and digest) and `version` here afterwards.
