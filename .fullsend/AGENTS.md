# AGENTS.md

Repo-specific notes for agents working in the Fullsend sandbox on this
monorepo. General coding guidance lives in the agent definition; this file
covers only the things about *this* repo and *this* sandbox that have
previously led an agent astray.

## Yarn and the sandbox proxy

The sandbox routes outbound HTTP through a proxy. `.yarnrc.yml` already
bridges this — it sets `httpProxy`/`httpsProxy` from `$HTTP_PROXY`/
`$HTTPS_PROXY` if they're set, and does nothing otherwise. You should not
need to touch proxy configuration at all; `yarn install` works the same
way it would outside the sandbox.

If `yarn install` still can't reach the registry, do **not** conclude the
network is blocked just because `yarn` fails. `npm` is wired to the proxy
independently of `yarn`'s config (it honours `HTTP_PROXY`/`HTTPS_PROXY`
directly), so `npm view <pkg>` or `npm ping` is a more reliable reachability
check than `yarn`-side failures alone. And `curl`/`wget` are **not** on the
sandbox's binary allowlist — a failed `curl` proves nothing about network
reachability, only that `curl` isn't permitted to open sockets. Don't use it
to diagnose connectivity.

If you do need to set proxy config by hand for some reason, reference the
environment variable (`yarn config set httpProxy "$HTTP_PROXY"`), never the
literal proxy URL — the sandbox's SSRF filter rejects any tool call whose
text contains that address, so a command with the literal URL in it will be
blocked and cannot be un-blocked by retrying.

## An empty `.yarn/cache` is normal

`.yarnrc.yml` does not set `enableGlobalCache: false`, so Yarn 4 populates
the **global** cache outside the repo. `.yarn/cache` staying empty during a
long `yarn install` is the expected state, not evidence of a blocked
download or a stalled install.

## Let `yarn install` finish

This is a large monorepo with a second workspace under `dynamic-plugins/`. A
cold `yarn install --immutable` can take several minutes. Let it run to
completion rather than killing it on early impatience.

If an install genuinely fails, fix the cause and re-run it. Do **not**
hand-edit `package.json` or `yarn.lock` entries from a version manifest as a
substitute for a real install: the result is unverifiable and desynchronizes
the lockfile. On run 34879198625 this consumed the remaining time budget
without producing a usable commit.
