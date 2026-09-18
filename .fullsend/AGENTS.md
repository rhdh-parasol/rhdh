# AGENTS.md

Repo-specific notes for agents working in the fullsend sandbox on this
monorepo. General coding guidance lives in the agent definition; this file
covers only the things about *this* repo and *this* sandbox that have
previously misled an agent.

## The package registries are reachable

`registry.npmjs.org` and `registry.yarnpkg.com` are both allowlisted
(read-only) by the `fullsend-package-registries` openshell profile. Dependency
installation is expected to work.

That profile's binary allowlist covers `yarn`, `node`, `npm`, `npx`, `pnpm`,
`pip`, `go` and friends — **it does not include `curl` or `wget`**. A failed
`curl` against a registry therefore tells you nothing about whether the
registry is reachable; it only tells you `curl` is not permitted to open
sockets. Do not use `curl` to probe network availability. If you need to
confirm reachability, use a tool that is on the allowlist, e.g.:

```sh
yarn npm info @backstage/cli --json
```

## An empty `.yarn/cache` is normal

`.yarnrc.yml` does not set `enableGlobalCache: false`, so Yarn 4 populates the
**global** cache outside the repo. `.yarn/cache` staying empty during a long
`yarn install` is the expected state, not evidence of a blocked download or a
stalled install.

## Let `yarn install` finish

This is a large monorepo with a second workspace under `dynamic-plugins/`. A
cold `yarn install --immutable` takes many minutes and is quiet for long
stretches. Let it run to completion — a slow install is not a hung one.

If an install genuinely fails, fix the cause and re-run it. Do **not**
hand-edit `package.json` or `yarn.lock` entries from a version manifest as a
substitute for a real install: the result is unverifiable, it desynchronizes
the lockfile, and on run 34879198625 it consumed the entire remaining budget
without producing a PR.
