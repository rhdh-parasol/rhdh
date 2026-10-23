import json
import subprocess
import sys
import tempfile
import unittest
from pathlib import Path

import yaml


CHECKER = Path(__file__).resolve().parents[1] / "check-yarn-lockfiles.py"


class CheckYarnLockfilesTest(unittest.TestCase):
    def setUp(self):
        self.temp = tempfile.TemporaryDirectory()
        self.addCleanup(self.temp.cleanup)
        self.root = Path(self.temp.name)
        subprocess.run(["git", "init", "--quiet"], cwd=self.root, check=True)

    def manifest(self, path, name, dependencies=None, **fields):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(json.dumps({"name": name, "dependencies": dependencies or {}, **fields}))

    def lockfile(self, path, workspaces):
        file = self.root / path
        file.parent.mkdir(parents=True, exist_ok=True)
        file.write_text(yaml.safe_dump({"__metadata": {"version": 10}, **{
            f"{name}@workspace:{directory}": {
                "resolution": f"{name}@workspace:{directory}",
                **fields,
            }
            for name, directory, fields in workspaces
        }}))

    def check(self):
        subprocess.run(["git", "add", "--all"], cwd=self.root, check=True)
        return subprocess.run(
            [sys.executable, str(CHECKER)], cwd=self.root,
            capture_output=True, text=True,
        )

    def root_project(self):
        self.manifest("package.json", "root", packageManager="yarn@4.17.1")
        self.lockfile("yarn.lock", [("root", ".", {})])

    def test_consistent_root_and_independent_project_pass(self):
        self.root_project()
        self.manifest("e2e-tests/package.json", "e2e-tests", {"@backstage/catalog-model": "1.10.0"})
        self.lockfile("e2e-tests/yarn.lock", [("e2e-tests", ".", {
            "dependencies": {"@backstage/catalog-model": "npm:1.10.0"},
        })])
        self.assertEqual(self.check().returncode, 0)

    def test_missed_e2e_lockfile_fails_even_when_root_is_consistent(self):
        self.root_project()
        self.manifest("e2e-tests/package.json", "e2e-tests", {"@backstage/catalog-model": "1.10.0"})
        self.lockfile("e2e-tests/yarn.lock", [("e2e-tests", ".", {
            "dependencies": {"@backstage/catalog-model": "npm:1.9.0"},
        })])
        result = self.check()
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("e2e-tests/package.json", result.stdout)
        self.assertIn("yarn install", result.stdout)

    def test_workspace_globs_and_explicit_protocols_pass(self):
        self.manifest("package.json", "root", workspaces={"packages": ["packages/*"]})
        self.manifest("packages/app/package.json", "app", {"local": "workspace:*", "alias": "npm:other@^2"})
        self.lockfile("yarn.lock", [("root", ".", {}), ("app", "packages/app", {
            "dependencies": {"local": "workspace:*", "alias": "npm:other@^2"},
        })])
        self.assertEqual(self.check().returncode, 0)

    def test_workspace_missing_from_lockfile_fails(self):
        self.manifest("package.json", "root", workspaces=["packages/*"])
        self.manifest("packages/new/package.json", "new")
        self.lockfile("yarn.lock", [("root", ".", {})])
        self.assertNotEqual(self.check().returncode, 0)

    def test_later_dependency_bump_is_also_rejected(self):
        self.root_project()
        self.manifest("e2e-tests/package.json", "e2e-tests", {"example": "2.0.0"})
        self.lockfile("e2e-tests/yarn.lock", [("e2e-tests", ".", {
            "dependencies": {"example": "npm:2.0.0"},
        })])
        self.assertEqual(self.check().returncode, 0)
        self.manifest("e2e-tests/package.json", "e2e-tests", {"example": "3.0.0"})
        self.assertNotEqual(self.check().returncode, 0)

    def test_changed_root_workspace_dependency_fails(self):
        self.manifest("package.json", "root", workspaces=["plugins/*"])
        self.manifest("plugins/example/package.json", "plugin", {"example": "2"})
        self.lockfile("yarn.lock", [("root", ".", {}), ("plugin", "plugins/example", {
            "dependencies": {"example": "npm:1"},
        })])
        self.assertNotEqual(self.check().returncode, 0)

    def test_dev_optional_and_peer_dependencies_are_checked(self):
        self.manifest("package.json", "root", devDependencies={"dev": "2"},
                      optionalDependencies={"optional": "3"}, peerDependencies={"peer": "^4"})
        self.lockfile("yarn.lock", [("root", ".", {
            "dependencies": {"dev": "npm:2", "optional": "npm:3"},
            "peerDependencies": {"peer": "^4"},
        })])
        self.assertEqual(self.check().returncode, 0)
        self.manifest("package.json", "root", devDependencies={"dev": "5"},
                      optionalDependencies={"optional": "3"}, peerDependencies={"peer": "^4"})
        self.assertNotEqual(self.check().returncode, 0)

    def test_removed_dependency_fails(self):
        self.root_project()
        self.lockfile("yarn.lock", [("root", ".", {"dependencies": {"old": "npm:1"}})])
        self.assertNotEqual(self.check().returncode, 0)

    def test_hidden_project_is_checked(self):
        self.root_project()
        self.manifest(".ci/package.json", ".ci", {"tool": "2"})
        self.lockfile(".ci/yarn.lock", [(".ci", ".", {"dependencies": {"tool": "npm:1"}})])
        self.assertNotEqual(self.check().returncode, 0)

    def test_yarn_project_without_lockfile_fails(self):
        self.root_project()
        self.manifest("new/package.json", "new", packageManager="yarn@4.17.1")
        self.assertNotEqual(self.check().returncode, 0)

    def test_unrelated_manifest_without_yarn_project_is_ignored(self):
        self.root_project()
        self.manifest("fixtures/example/package.json", "fixture", {"unused": "1"})
        self.assertEqual(self.check().returncode, 0)

    def test_malformed_lockfile_fails(self):
        self.root_project()
        (self.root / "yarn.lock").write_text("broken: [")
        self.assertNotEqual(self.check().returncode, 0)


if __name__ == "__main__":
    unittest.main()
