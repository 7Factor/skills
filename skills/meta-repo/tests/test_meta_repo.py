#!/usr/bin/env python3
"""Standalone tests for the meta-repo engine — stdlib only, no pip install.

Run any of:
    python3 tests/test_meta_repo.py            # from the skill root
    python3 -m unittest -v                     # discovery from tests/
    ./tests/test_meta_repo.py                  # if executable

The engine shells out to real `git`; these are integration tests that build
throwaway workspaces (a `parent/` with sibling member repos) under a tempdir
and drive the CLI exactly as a user would. Nothing touches your real repos or
global git config — git identity/config are isolated per subprocess call.
"""
from __future__ import annotations

import importlib.util
import io
import os
import shutil
import subprocess
import tempfile
import unittest
from contextlib import redirect_stderr, redirect_stdout
from pathlib import Path
from unittest import mock

# ----------------------------------------------------------------------------
# load the hyphenated engine as a module
# ----------------------------------------------------------------------------
ENGINE = Path(__file__).resolve().parent.parent / "scripts" / "meta-repo.py"
_spec = importlib.util.spec_from_file_location("meta_repo_engine", ENGINE)
mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(mod)

HAVE_GIT = shutil.which("git") is not None

# git config/identity isolated so tests never read or write the user's real config
_GIT_ENV = {
    **os.environ,
    "GIT_CONFIG_GLOBAL": os.devnull,
    "GIT_CONFIG_SYSTEM": os.devnull,
    "GIT_AUTHOR_NAME": "t", "GIT_AUTHOR_EMAIL": "t@example.com",
    "GIT_COMMITTER_NAME": "t", "GIT_COMMITTER_EMAIL": "t@example.com",
}


def git(cwd, *args):
    subprocess.run(["git", *args], cwd=str(cwd), check=True,
                   capture_output=True, env=_GIT_ENV)


def make_repo(path: Path):
    """A git repo with one commit on a real branch (so trunk resolution works)."""
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    (path / "README").write_text("seed\n", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "seed")


# ----------------------------------------------------------------------------
# pure-function tests (no filesystem / git)
# ----------------------------------------------------------------------------
class TestYamlRoundtrip(unittest.TestCase):
    def test_scalar_quoting(self):
        # values needing quotes because the parser would otherwise misread them
        for raw in ["", " leading", "trailing ", "a: b", "has#hash", "*star", "@at", "[bracket"]:
            self.assertEqual(mod._unquote(mod._scalar(raw)), raw, f"round-trip failed for {raw!r}")

    def test_plain_scalar_stays_plain(self):
        self.assertEqual(mod._scalar("main"), "main")
        # a git remote has no colon-SPACE, so it stays unquoted yet still round-trips
        remote = "git@github.com:o/r.git"
        self.assertEqual(mod._scalar(remote), remote)
        self.assertEqual(mod._unquote(mod._scalar(remote)), remote)
        # colon-space DOES force quoting
        self.assertEqual(mod._scalar("a: b"), '"a: b"')

    def test_full_document_roundtrip(self):
        data = {
            "name": "LT Platform",
            "description": "Backend: clients",  # colon-space forces quoting
            "repositories": [
                {"name": "api", "path": "../api", "role": "Backend API",
                 "remote": "git@github.com:org/api.git", "default_branch": "main", "status": "active"},
                {"name": "web", "path": "../web", "role": "", "status": "archived"},
            ],
        }
        parsed = mod.parse_yaml(mod.dump_yaml(data))
        self.assertEqual(parsed["name"], "LT Platform")
        self.assertEqual(parsed["description"], "Backend: clients")
        self.assertEqual(len(parsed["repositories"]), 2)
        api = parsed["repositories"][0]
        self.assertEqual(api["remote"], "git@github.com:org/api.git")
        self.assertEqual(api["default_branch"], "main")
        # empty role is omitted on dump; absent on read
        self.assertNotIn("role", parsed["repositories"][1])
        self.assertEqual(parsed["repositories"][1]["status"], "archived")


class TestSymlinkHelpers(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def test_ensure_symlink_created_then_idempotent_normpath(self):
        # H3: a cosmetic trailing slash must NOT churn a relink
        self.assertEqual(mod.ensure_symlink(self.tmp, "api", "../api"), "created")
        self.assertEqual(mod.ensure_symlink(self.tmp, "api", "../api/"), "ok")
        self.assertEqual(mod.ensure_symlink(self.tmp, "api", "./../api"), "ok")

    def test_ensure_symlink_fixes_real_change(self):
        mod.ensure_symlink(self.tmp, "api", "../api")
        self.assertEqual(mod.ensure_symlink(self.tmp, "api", "../other"), "fixed")

    def test_ensure_symlink_conflict_on_real_file(self):
        (self.tmp / "api").mkdir()
        self.assertEqual(mod.ensure_symlink(self.tmp, "api", "../api"), "conflict")

    def test_ensure_symlink_actionable_error_when_unsupported(self):
        # Simulate native Windows without symlink privilege (OSError 1314): the engine
        # must exit with an actionable message pointing at WSL/POSIX, not a raw traceback.
        err = io.StringIO()
        with mock.patch.object(Path, "symlink_to",
                               side_effect=OSError(1314, "A required privilege is not held by the client")):
            with self.assertRaises(SystemExit) as cm, redirect_stderr(err):
                mod.ensure_symlink(self.tmp, "api", "../api")
        self.assertEqual(cm.exception.code, 1)
        msg = err.getvalue().lower()
        self.assertIn("symlink", msg)
        self.assertTrue(any(w in msg for w in ("wsl", "windows", "posix")),
                        f"message not actionable about platform: {msg!r}")

    def test_discover_symlinks_only_member_shaped(self):
        # H2: only relative `..`-prefixed links count as member wiring
        os.symlink("../sibling", self.tmp / "member")   # included
        os.symlink("sub/inside", self.tmp / "rel")      # excluded (not `..`)
        os.symlink(os.sep + "tmp", self.tmp / "abs")    # excluded (absolute)
        (self.tmp / "realdir").mkdir()                   # excluded (not a symlink)
        self.assertEqual(set(mod.discover_symlinks(self.tmp)), {"member"})


# ----------------------------------------------------------------------------
# command-level tests (real git + symlinks in a throwaway workspace)
# ----------------------------------------------------------------------------
@unittest.skipUnless(HAVE_GIT, "git not on PATH")
class CommandTestBase(unittest.TestCase):
    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())
        self.parent = self.tmp / "parent"
        self.meta = self.parent / "meta"
        self.meta.mkdir(parents=True)
        self.api = self.parent / "api"
        self.web = self.parent / "web"
        make_repo(self.api)
        make_repo(self.web)

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def run_cmd(self, argv, cwd=None):
        """Drive the CLI like main() would; return (exit_code, combined_output)."""
        cwd = cwd or self.meta
        old = os.getcwd()
        os.chdir(cwd)
        buf = io.StringIO()
        code = 0
        try:
            with redirect_stdout(buf), redirect_stderr(buf):
                args = mod.build_parser().parse_args(argv)
                args.func(args)
        except SystemExit as e:
            code = e.code if isinstance(e.code, int) else 1
        finally:
            os.chdir(old)
        return code, buf.getvalue()

    def roster(self):
        return mod.load(self.meta)


class TestInit(CommandTestBase):
    def test_init_scaffolds_and_git_inits(self):
        self.run_cmd(["init", "--name", "WS", "--description", "d"])
        self.assertTrue((self.meta / "meta-repo.yaml").exists())
        for fn in ("AGENTS.md", "README.md", "CLAUDE.md", ".gitignore", "scripts/meta-repo.py"):
            self.assertTrue((self.meta / fn).exists(), f"missing scaffold {fn}")
        self.assertTrue((self.meta / ".git").exists())
        self.assertEqual(self.roster()["name"], "WS")

    def test_init_adopts_only_member_shaped_symlinks(self):
        os.symlink("../api", self.meta / "api")
        os.symlink(os.sep + "tmp", self.meta / "junk")   # absolute — must NOT be adopted
        self.run_cmd(["init", "--name", "WS"])
        names = {r["name"] for r in self.roster()["repositories"]}
        self.assertEqual(names, {"api"})


class TestAddRemove(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.run_cmd(["init", "--name", "WS"])

    def test_add_by_path(self):
        code, out = self.run_cmd(["add", "--name", "api", "--path", "../api", "--role", "Backend"])
        self.assertEqual(code, 0)
        self.assertTrue((self.meta / "api").is_symlink())
        entry = self.roster()["repositories"][0]
        self.assertEqual(entry["name"], "api")
        self.assertEqual(entry["role"], "Backend")
        self.assertEqual(entry["default_branch"], "main")

    def test_add_by_remote_clones(self):
        source = self.tmp / "src"
        make_repo(source)
        code, out = self.run_cmd(["add", "--name", "cloned", "--remote", str(source)])
        self.assertEqual(code, 0)
        self.assertTrue((self.parent / "cloned" / ".git").exists(), "clone did not land as sibling")
        self.assertEqual(self.roster()["repositories"][0]["remote"], str(source))

    def test_add_can_clear_role_via_upsert(self):
        # M1: re-adding with --role "" (alongside --path) must clear the role, matching
        # the metadata-only path — not silently keep the old value.
        self.run_cmd(["add", "--name", "api", "--path", "../api", "--role", "Backend"])
        code, _ = self.run_cmd(["add", "--name", "api", "--path", "../api", "--role", ""])
        self.assertEqual(code, 0)
        self.assertEqual(self.roster()["repositories"][0].get("role", ""), "")

    def test_add_metadata_only_edit(self):
        self.run_cmd(["add", "--name", "api", "--path", "../api"])
        code, _ = self.run_cmd(["add", "--name", "api", "--status", "archived"])
        self.assertEqual(code, 0)
        self.assertEqual(self.roster()["repositories"][0]["status"], "archived")

    def test_add_conflict_does_not_mutate_roster(self):
        # H1: a real dir squatting the member name must abort BEFORE writing yaml
        (self.meta / "svc").mkdir()
        before = (self.meta / "meta-repo.yaml").read_text(encoding="utf-8")
        code, out = self.run_cmd(["add", "--name", "svc", "--path", "../svc"])
        self.assertEqual(code, 1)
        self.assertIn("occupies", out)
        after = (self.meta / "meta-repo.yaml").read_text(encoding="utf-8")
        self.assertEqual(before, after, "roster was mutated despite the conflict")

    def test_remove_keeps_real_clone(self):
        self.run_cmd(["add", "--name", "api", "--path", "../api"])
        code, _ = self.run_cmd(["remove", "api"])
        self.assertEqual(code, 0)
        self.assertFalse((self.meta / "api").is_symlink())
        self.assertTrue(self.api.exists(), "remove must never delete the real clone")
        self.assertEqual(self.roster()["repositories"], [])


class TestSyncHealDoctor(CommandTestBase):
    def setUp(self):
        super().setUp()
        self.run_cmd(["init", "--name", "WS"])
        self.run_cmd(["add", "--name", "api", "--path", "../api"])

    def test_sync_is_idempotent(self):
        self.run_cmd(["sync"])
        code, out = self.run_cmd(["sync"])
        self.assertEqual(code, 0)
        self.assertIn("(all ok)", out)

    def test_heal_leaves_unrelated_broken_symlink_alone(self):
        # H2: heal must not delete a user's own dangling, non-member symlink
        os.symlink(os.sep + "nonexistent" + os.sep + "thing", self.meta / "mylink")
        code, out = self.run_cmd(["heal"])
        self.assertNotIn("mylink", out)
        self.assertTrue((self.meta / "mylink").is_symlink(), "heal removed a non-member symlink")

    def test_heal_removes_broken_member_shaped_orphan(self):
        os.symlink("../ghost", self.meta / "ghost")  # member-shaped, dangling, not in roster
        code, out = self.run_cmd(["heal"])
        self.assertIn("ghost", out)
        self.assertFalse((self.meta / "ghost").is_symlink())

    def test_doctor_reports_dangling_member_once(self):
        # M3: a declared member with a remote whose clone is gone (dangling symlink)
        # must be reported ONCE under STRUCTURAL, not doubled as "missing on disk"
        # AND "broken symlink".
        source = self.tmp / "src"
        make_repo(source)
        self.run_cmd(["add", "--name", "ghost", "--remote", str(source)])
        shutil.rmtree(self.parent / "ghost")  # clone gone; roster keeps remote + symlink
        code, out = self.run_cmd(["doctor"])
        self.assertEqual(code, 1)
        self.assertEqual(out.count("- ghost:"), 1, f"member reported more than once:\n{out}")

    def test_doctor_clean_after_docs_refresh(self):
        # adding a member drifts the scaffolded prose; docs --force realigns it
        self.run_cmd(["docs", "--force"])
        code, out = self.run_cmd(["doctor"])
        self.assertIn("STRUCTURAL", out)
        self.assertEqual(code, 0, f"doctor should be clean, got:\n{out}")

    def test_manifest_reports_engine_version(self):
        code, out = self.run_cmd(["manifest"])
        self.assertEqual(code, 0)
        import json
        data = json.loads(out)
        self.assertEqual(data["engine_version"], mod.META_REPO_VERSION)
        self.assertEqual(data["repositories"][0]["name"], "api")


@unittest.skipUnless(HAVE_GIT, "git not on PATH")
class TestBranchResolution(CommandTestBase):
    def test_default_branch_never_returns_HEAD_when_detached(self):
        # M4: a detached HEAD with no origin/HEAD must not resolve to the literal
        # "HEAD" — cmd_update would otherwise persist that as a branch name in the roster.
        git(self.api, "checkout", "--detach")
        self.assertEqual(mod.current_branch(self.api), "HEAD")  # precondition: detached
        self.assertNotEqual(mod.default_branch(self.api), "HEAD")
        self.assertEqual(mod.default_branch(self.api), "main")  # falls back to the trunk default


class TestGitGuard(unittest.TestCase):
    def test_missing_git_binary_dies_cleanly(self):
        # C1: no traceback when git is absent — a clear error and non-zero exit
        orig = mod.shutil.which
        mod.shutil.which = lambda name: None
        try:
            buf = io.StringIO()
            with self.assertRaises(SystemExit) as cm, redirect_stderr(buf):
                mod.main(["doctor"])
            self.assertEqual(cm.exception.code, 1)
            self.assertIn("git", buf.getvalue().lower())
        finally:
            mod.shutil.which = orig


if __name__ == "__main__":
    unittest.main(verbosity=2)
