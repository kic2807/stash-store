# things-gitea-act-runner

[Gitea Runner](https://gitea.com/gitea/runner) (formerly `act_runner`) with a
separate Docker-in-Docker daemon for jobs. No web UI.

## Layout

| Service  | Image                | Notes |
|----------|----------------------|-------|
| `dind`   | `docker:*-dind`      | privileged; dockerd listens on `127.0.0.1:2375` only, no published ports |
| `runner` | `gitea/runner`       | `network_mode: service:dind`, talks to `tcp://localhost:2375` |

Persistent data under `~/umbrel/app-data/things-gitea-act-runner/data/`:

- `runner/` — registration state (`.runner`). Delete it to force re-registration.
- `dind/` — job image cache. Excluded from Umbrel backups; safe to delete while the app is stopped.

## Setup

1. Install Gitea first and make sure it is reachable at its public URL.
2. In Gitea: Site Administration → Actions → Runners → **Create new runner**, copy the token.
3. Install this app, then on the Umbrel terminal:

   ```sh
   cd ~/umbrel/app-data/things-gitea-act-runner/data
   nano .env        # keys from .env.example
   chmod 600 .env
   ```

4. Restart the app. The runner registers once as `umbrel_dind_runner` and
   appears as idle in Gitea. After that the registration token is no longer
   used and can be removed from `.env`.

## Check

```sh
sudo docker logs --tail 30 things-gitea-act-runner_runner_1
```

## Upgrade notes

Runner 5.0 requires `runs-on` on every job and changes `builtin:checkout`
(cleans untracked files unless `clean: false`). See the
[v5.0.0 release notes](https://gitea.com/gitea/runner/releases/tag/v5.0.0).
