"""Check Yarn Berry workspace declarations without executing project code.

This catches a changed manifest paired with a stale lockfile. It does not replace
Yarn's immutable install, which also checks resolution and package integrity.
"""

import json
import re
import subprocess
from pathlib import Path

import yaml


def read_manifest(path, root):
    if not path.resolve().is_relative_to(root):
        raise ValueError("Manifest escapes repository")
    return json.loads(path.read_text())


def dependency_map(manifest, *sections):
    result = {}
    for section in sections:
        values = manifest.get(section, {})
        if not isinstance(values, dict) or not all(
            isinstance(name, str) and isinstance(version, str)
            for name, version in values.items()
        ):
            raise ValueError("Invalid dependency map")
        result.update(values)
    return result


def descriptor(value):
    return value if re.match(r"^[a-zA-Z][a-zA-Z0-9+.-]*:", value) else f"npm:{value}"


def check_project(project, root):
    lock_path = project / "yarn.lock"
    if not lock_path.resolve().is_relative_to(root):
        raise ValueError("Lockfile escapes repository")
    lock = yaml.safe_load(lock_path.read_text())
    if not isinstance(lock, dict) or "__metadata" not in lock:
        raise ValueError("Expected a Yarn Berry lockfile")
    manifest = read_manifest(project / "package.json", root)
    patterns = manifest.get("workspaces", [])
    if isinstance(patterns, dict):
        patterns = patterns["packages"]
    if not isinstance(patterns, list) or not all(isinstance(p, str) for p in patterns):
        raise ValueError("Invalid workspace patterns")
    manifests = {project / "package.json"}
    for pattern in patterns:
        if (
            pattern.startswith("!")
            or Path(pattern).is_absolute()
            or ".." in Path(pattern).parts
        ):
            raise ValueError("Unsupported workspace pattern")
        manifests.update(project.glob(f"{pattern}/package.json"))

    entries = {
        entry.get("resolution"): entry
        for entry in lock.values()
        if isinstance(entry, dict) and isinstance(entry.get("resolution"), str)
    }
    failures = []
    for path in sorted(manifests):
        package = read_manifest(path, root)
        workspace = path.parent.relative_to(project).as_posix()
        entry = entries.get(f"{package['name']}@workspace:{workspace}")
        dependencies = {
            name: descriptor(version)
            for name, version in dependency_map(
                package, "dependencies", "devDependencies", "optionalDependencies"
            ).items()
        }
        if (
            entry is None
            or dependencies != entry.get("dependencies", {})
            or dependency_map(package, "peerDependencies")
            != entry.get("peerDependencies", {})
        ):
            failures.append(
                f"FAIL: {json.dumps(path.relative_to(root).as_posix())} differs from "
                f"its lockfile workspace entry; run yarn install in "
                f"{json.dumps(project.relative_to(root).as_posix())} and commit yarn.lock."
            )
    return failures


def main():
    root = Path(
        subprocess.run(
            ["git", "rev-parse", "--show-toplevel"],
            check=True,
            capture_output=True,
            text=True,
        ).stdout.strip()
    ).resolve()
    tracked = subprocess.run(
        ["git", "ls-files", "-z"],
        cwd=root,
        check=True,
        capture_output=True,
        text=True,
    ).stdout.split("\0")
    projects = {
        root / Path(path).parent for path in tracked if Path(path).name == "yarn.lock"
    }
    try:
        for path in tracked:
            if Path(path).name == "package.json":
                package = read_manifest(root / path, root)
                if package.get("packageManager", "").startswith("yarn@"):
                    projects.add((root / path).parent)
        failures = []
        for project in sorted(projects):
            try:
                failures.extend(check_project(project, root))
            except (OSError, ValueError, TypeError, KeyError, yaml.YAMLError) as error:
                failures.append(
                    f"FAIL: cannot check Yarn project {json.dumps(project.relative_to(root).as_posix())} "
                    f"({type(error).__name__}); regenerate and commit its yarn.lock with yarn install."
                )
    except (OSError, ValueError, TypeError, yaml.YAMLError) as error:
        print(f"FAIL: cannot discover Yarn projects ({type(error).__name__}).")
        return 1
    if failures:
        print("\n".join(failures))
        return 1
    print(f"PASS: workspace declarations match in {len(projects)} Yarn projects.")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
