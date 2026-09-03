# Fullsend instructions

When a GitHub issue requests a Backstage version bump for
redhat-developer/rhdh:

1. Fetch the issue with /rhdh-forge.
2. Validate the target version as exact stable semver.
3. Prepare a clean branch from fresh origin/main.
4. Invoke /rhdh-backstage-upgrade to bump the root workspace.
5. Also bump `backstage.json`, `package.json`, and the lockfile under
   `dynamic-plugins/` the same way. `/rhdh-backstage-upgrade` does not
   discover this second workspace on its own
   (redhat-developer/rhdh-skills#106).
6. Normalize any `@backstage/*` version ranges `versions:bump` wrote
   as carets back to exact pins, matching this repo's existing
   convention.
7. Review the root `package.json` `resolutions` field and remove any
   entry no longer needed after the bump, verifying with
   `yarn install` and `yarn build`.
8. Compose and create the PR through /prose-editing, /rhdh-forge, and
   /mutation-gate.

Steps 5-7 are a stopgap for known gaps in `/rhdh-backstage-upgrade`
(redhat-developer/rhdh-skills#106). Remove them once that issue is
fixed upstream.

If Claude auto-backgrounds a verification command, invoke `TaskStop`
before finishing.
