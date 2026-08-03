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

# meta-repo.py only imports what it uses itself; pull the rest of the engine's
# names onto `mod` here so `mod.<name>` keeps working for everything below
# without meta-repo.py carrying unused imports just to re-export them.
from engine import roster as _roster, git_ops as _git_ops, scaffold as _scaffold  # noqa: E402
for _name in (
    "YAML_NAME", "YamlValidationError", "_scalar", "_unquote",
    "parse_yaml", "dump_yaml", "validate_yaml_data", "load", "save",
):
    setattr(mod, _name, getattr(_roster, _name))
for _name in ("current_branch", "default_branch"):
    setattr(mod, _name, getattr(_git_ops, _name))
for _name in ("ensure_symlink", "discover_symlinks"):
    setattr(mod, _name, getattr(_scaffold, _name))
del _name

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


def git_out(cwd, *args) -> str:
    return subprocess.run(["git", *args], cwd=str(cwd), check=True,
                          capture_output=True, env=_GIT_ENV, text=True).stdout.strip()


def make_repo(path: Path):
    """A git repo with one commit on a real branch (so trunk resolution works)."""
    path.mkdir(parents=True, exist_ok=True)
    git(path, "init", "-q", "-b", "main")
    (path / "README").write_text("seed\n", encoding="utf-8")
    git(path, "add", "-A")
    git(path, "commit", "-q", "-m", "seed")


def make_remote_and_clone(parent: Path, name: str) -> tuple[Path, Path]:
    """A bare 'remote' repo plus a real clone of it wired as `origin` (member layout),
    so `update`'s fetch/merge/ff-only mechanics have something real to talk to."""
    seed = parent / f"_seed_{name}"
    make_repo(seed)
    bare = parent / f"{name}.git"
    git(parent, "clone", "--bare", "-q", str(seed), str(bare))
    shutil.rmtree(seed)
    member = parent / name
    git(parent, "clone", "-q", str(bare), str(member))
    return bare, member


def push_new_commit(bare: Path, branch: str, filename: str = "extra.txt") -> None:
    """Push one new commit onto `branch` in the bare repo, via a scratch clone."""
    tmp = Path(tempfile.mkdtemp())
    try:
        wc = tmp / "wc"
        git(tmp, "clone", "-q", str(bare), str(wc))
        git(wc, "checkout", "-q", branch)
        (wc / filename).write_text("more\n", encoding="utf-8")
        git(wc, "add", "-A")
        git(wc, "commit", "-q", "-m", "advance")
        git(wc, "push", "-q", "origin", branch)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


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


class TestYamlValidation(unittest.TestCase):
    """Load-time validation of a hand-edited meta-repo.yaml (see mod.validate_yaml_data
    and mod.load). Fixtures are written as raw text, never via save()/add(), to
    simulate a real hand-edit."""

    def setUp(self):
        self.tmp = Path(tempfile.mkdtemp())

    def tearDown(self):
        shutil.rmtree(self.tmp, ignore_errors=True)

    def _write(self, text: str) -> Path:
        p = self.tmp / mod.YAML_NAME
        p.write_text(text, encoding="utf-8")
        return p

    def test_missing_repositories_key_rejected(self):
        # parse_yaml always defaults 'repositories' to [] even when the raw text never
        # mentions it, so this can't be produced end-to-end through the real parser —
        # validate defensively guards the contract anyway; exercise it directly.
        with self.assertRaises(mod.YamlValidationError) as cm:
            mod.validate_yaml_data({"name": "WS"})
        self.assertIn("repositories", str(cm.exception))

    def test_repositories_not_a_list_rejected(self):
        # "repositories: oops" (trailing text on the same line) makes the top-level
        # key/value regex match instead of the "repositories:\s*$" trigger, so the
        # hand-rolled parser overwrites the default list with a bare string.
        self._write(
            "name: WS\n"
            "description: \"\"\n"
            "repositories: oops\n"
        )
        with self.assertRaises(SystemExit) as cm:
            mod.load(self.tmp)
        self.assertEqual(cm.exception.code, 1)

    def test_repositories_not_a_list_clean_cli_error(self):
        self._write(
            "name: WS\n"
            "description: \"\"\n"
            "repositories: oops\n"
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit), redirect_stderr(err):
            mod.load(self.tmp)
        msg = err.getvalue()
        self.assertIn("repositories", msg)
        self.assertIn("meta-repo: error:", msg)  # via die(), not a raw traceback

    def test_member_missing_name_rejected(self):
        self._write(
            "name: WS\n"
            "description: \"\"\n"
            "repositories:\n"
            "  - path: ../api\n"
            "    role: Backend\n"
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit) as cm, redirect_stderr(err):
            mod.load(self.tmp)
        self.assertEqual(cm.exception.code, 1)
        msg = err.getvalue()
        self.assertIn("name", msg)
        self.assertIn("repositories[0]", msg)

    def test_member_missing_path_rejected(self):
        self._write(
            "name: WS\n"
            "description: \"\"\n"
            "repositories:\n"
            "  - name: api\n"
            "    role: Backend\n"
        )
        err = io.StringIO()
        with self.assertRaises(SystemExit) as cm, redirect_stderr(err):
            mod.load(self.tmp)
        self.assertEqual(cm.exception.code, 1)
        msg = err.getvalue()
        self.assertIn("'api'", msg)
        self.assertIn("path", msg)

    def test_well_formed_hand_edit_still_loads(self):
        # a legitimate manual tweak (role + an unrecognized status value) using
        # otherwise-correct syntax must NOT be rejected by validation.
        self._write(
            "name: WS\n"
            "description: \"\"\n"
            "repositories:\n"
            "  - name: api\n"
            "    path: ../api\n"
            "    role: Backend, hand-tweaked\n"
            "    status: legacy\n"
        )
        data = mod.load(self.tmp)
        self.assertEqual(data["repositories"][0]["name"], "api")
        self.assertEqual(data["repositories"][0]["status"], "legacy")

    def test_optional_fields_absent_is_fine(self):
        self._write(
            "name: WS\n"
            "description: \"\"\n"
            "repositories:\n"
            "  - name: api\n"
            "    path: ../api\n"
        )
        data = mod.load(self.tmp)
        self.assertEqual(len(data["repositories"]), 1)


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
        for fn in ("AGENTS.md", "README.md", "CLAUDE.md", ".gitignore"):
            self.assertTrue((self.meta / fn).exists(), f"missing scaffold {fn}")
        self.assertTrue((self.meta / ".git").exists())
        self.assertEqual(self.roster()["name"], "WS")

    def test_init_does_not_vendor_engine(self):
        # the engine is never copied into a target meta-repo — it only ever lives
        # wherever the meta-repo skill itself is installed
        self.run_cmd(["init", "--name", "WS"])
        self.assertFalse((self.meta / "scripts").exists())

    def test_init_adopts_only_member_shaped_symlinks(self):
        os.symlink("../api", self.meta / "api")
        os.symlink(os.sep + "tmp", self.meta / "junk")   # absolute — must NOT be adopted
        self.run_cmd(["init", "--name", "WS"])
        names = {r["name"] for r in self.roster()["repositories"]}
        self.assertEqual(names, {"api"})

    def test_init_skips_sibling_symlink_to_non_git_dir_with_visible_note(self):
        # Bug fix: a sibling symlink whose target is a plain (non-git) directory must
        # NOT be silently adopted as a normal `active` member with no remote and no
        # recovery path — init must skip it and say so out loud.
        plain = self.parent / "scratch"
        plain.mkdir()
        os.symlink("../scratch", self.meta / "scratch")
        code, out = self.run_cmd(["init", "--name", "WS"])
        self.assertEqual(code, 0)
        self.assertIn("scratch", out)
        self.assertIn("not a git repository", out.lower())
        names = {r["name"] for r in self.roster()["repositories"]}
        self.assertNotIn("scratch", names, "non-git sibling must not be silently adopted")

    def test_init_skips_dangling_sibling_symlink_with_visible_note(self):
        # Same complaint, different cause: the sibling symlink target doesn't exist at
        # all. Must be handled visibly too, not silently adopted (and not confused with
        # the non-git-dir case's exact wording, though both must be visible).
        os.symlink("../ghost", self.meta / "ghost")
        code, out = self.run_cmd(["init", "--name", "WS"])
        self.assertEqual(code, 0)
        self.assertIn("ghost", out)
        self.assertIn("dangling", out.lower())
        names = {r["name"] for r in self.roster()["repositories"]}
        self.assertNotIn("ghost", names, "dangling sibling must not be silently adopted")


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

    def test_add_status_active_accepted(self):
        code, _ = self.run_cmd(["add", "--name", "api", "--path", "../api", "--status", "active"])
        self.assertEqual(code, 0)
        self.assertEqual(self.roster()["repositories"][0]["status"], "active")

    def test_add_status_rejects_removed_values(self):
        # legacy/greenfield/empty were collapsed away; only active/archived remain.
        # Nuance about a member's lifecycle belongs in the free-text `role` field.
        for bad in ("legacy", "greenfield", "empty", "bogus"):
            code, out = self.run_cmd(["add", "--name", "api", "--path", "../api", "--status", bad])
            self.assertNotEqual(code, 0, f"--status {bad} should have been rejected")
            self.assertIn("active", out)
            self.assertIn("archived", out)

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

    def test_sync_orphan_symlink_alone_exits_zero_but_is_reported(self):
        # Bug fix: an orphan symlink (present on disk, not declared in the yaml) is
        # informational — "you might want to curate this" — not a real failure. It
        # must still be visible in `sync`'s output, just not fail the exit code.
        self.run_cmd(["sync"])  # baseline clean state for the declared member
        os.symlink("../web", self.meta / "web")  # not in roster: orphan
        code, out = self.run_cmd(["sync"])
        self.assertEqual(code, 0, f"an orphan alone must not fail sync:\n{out}")
        self.assertIn("web", out)
        self.assertIn("orphan", out.lower())

    def test_sync_genuine_problem_still_exits_nonzero(self):
        # A phantom entry (declared in yaml, missing on disk, no remote to recover
        # from) is a real failure and must still fail sync, even alongside an orphan.
        source = self.tmp / "src"
        make_repo(source)
        self.run_cmd(["add", "--name", "ghost", "--remote", str(source)])
        shutil.rmtree(self.parent / "ghost")
        (self.meta / "ghost").unlink()  # drop the now-dangling symlink too
        # remove the remote so sync has nothing to clone from -> genuine phantom
        data = self.roster()
        for r in data["repositories"]:
            if r["name"] == "ghost":
                r.pop("remote", None)
        mod.save(self.meta, data)

        code, out = self.run_cmd(["sync"])
        self.assertNotEqual(code, 0, f"a genuine phantom entry must still fail sync:\n{out}")
        self.assertIn("ghost", out)

    def test_heal_does_not_vendor_engine(self):
        # heal fixes hygiene only; it must never write a scripts/ dir into the target
        self.run_cmd(["heal"])
        self.assertFalse((self.meta / "scripts").exists())

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


class TestStatusReadTolerance(CommandTestBase):
    """Removed status values (legacy/greenfield/empty) must be rejected on WRITE
    (`add --status`) but tolerated on READ — an already-created meta-repo.yaml this
    engine didn't write in the current schema must not crash `manifest`/`doctor`."""

    def setUp(self):
        super().setUp()
        self.run_cmd(["init", "--name", "WS"])
        (self.meta / "meta-repo.yaml").write_text(
            "name: WS\n"
            "description: \"\"\n"
            "repositories:\n"
            "  - name: api\n"
            "    path: ../api\n"
            "    status: legacy\n",
            encoding="utf-8",
        )
        os.symlink("../api", self.meta / "api")

    def test_manifest_does_not_crash_on_removed_status_value(self):
        code, out = self.run_cmd(["manifest"])
        self.assertEqual(code, 0)
        import json
        data = json.loads(out)
        self.assertEqual(data["repositories"][0]["status"], "legacy")

    def test_doctor_does_not_crash_on_removed_status_value(self):
        code, out = self.run_cmd(["doctor"])
        self.assertIn("doctor", out.lower())


@unittest.skipUnless(HAVE_GIT, "git not on PATH")
class TestBranchResolution(CommandTestBase):
    def test_default_branch_never_returns_HEAD_when_detached(self):
        # M4: a detached HEAD with no origin/HEAD must not resolve to the literal
        # "HEAD" — cmd_update would otherwise persist that as a branch name in the roster.
        git(self.api, "checkout", "--detach")
        self.assertEqual(mod.current_branch(self.api), "HEAD")  # precondition: detached
        self.assertNotEqual(mod.default_branch(self.api), "HEAD")
        self.assertEqual(mod.default_branch(self.api), "main")  # falls back to the trunk default


@unittest.skipUnless(HAVE_GIT, "git not on PATH")
class TestUpdate(CommandTestBase):
    """`update`'s git mechanics: fast-forward, dirty-skip, feature-branch refresh-only,
    and trunk re-detection. Each member here is a real clone of a real bare 'remote'
    so fetch/merge/ff-only behave exactly as they would for a user."""

    def setUp(self):
        super().setUp()
        self.run_cmd(["init", "--name", "WS"])

    def _add_member(self, name):
        bare, member = make_remote_and_clone(self.parent, name)
        code, _ = self.run_cmd(["add", "--name", name, "--path", f"../{name}"])
        self.assertEqual(code, 0)
        return bare, member

    def test_update_fast_forwards_clean_trunk_member(self):
        bare, member = self._add_member("svc")
        push_new_commit(bare, "main")
        remote_tip = git_out(bare, "rev-parse", "main")
        self.assertNotEqual(git_out(member, "rev-parse", "HEAD"), remote_tip)

        code, out = self.run_cmd(["update"])
        self.assertEqual(code, 0)
        self.assertEqual(git_out(member, "rev-parse", "HEAD"), remote_tip,
                         "clean trunk member must be fast-forwarded to origin")
        self.assertIn("fast-forwarded", out)

    def test_update_skips_dirty_member_and_flags_it(self):
        bare, member = self._add_member("svc")
        before = git_out(member, "rev-parse", "HEAD")
        (member / "README").write_text("local edit\n", encoding="utf-8")  # uncommitted, never staged

        code, out = self.run_cmd(["update"])
        self.assertNotEqual(code, 0, "a dirty member must contribute to a non-zero exit")
        self.assertIn("DIRTY", out)
        self.assertIn("svc", out)
        self.assertEqual(git_out(member, "rev-parse", "HEAD"), before,
                         "dirty member must be left completely untouched")

    def test_update_refreshes_trunk_ref_but_leaves_feature_branch_checked_out(self):
        bare, member = self._add_member("svc")
        git(member, "checkout", "-q", "-b", "feature")
        push_new_commit(bare, "main")
        remote_tip = git_out(bare, "rev-parse", "main")

        code, out = self.run_cmd(["update"])
        self.assertEqual(code, 0, "parking on a feature branch alone is not a failure")
        self.assertEqual(mod.current_branch(member), "feature",
                         "update must NEVER check out a member away from its current branch")
        self.assertEqual(git_out(member, "rev-parse", "main"), remote_tip,
                         "the local trunk ref must still be refreshed for accurate git status/log")
        self.assertIn("on feature branch 'feature'", out)
        self.assertIn("working tree untouched", out)
        self.assertNotIn("switch", out.lower())

    def test_update_skips_archived_member_entirely(self):
        # An `archived` member must be fully out of scope for `update`: no fetch, no
        # fast-forward attempt, not flagged as a problem, and no effect on exit code —
        # while an `active` member in the same roster still updates normally.
        bare_a, member_a = self._add_member("archived_svc")
        code, _ = self.run_cmd(["add", "--name", "archived_svc", "--status", "archived"])
        self.assertEqual(code, 0)
        bare_b, member_b = self._add_member("active_svc")

        push_new_commit(bare_a, "main")
        push_new_commit(bare_b, "main")
        archived_before = git_out(member_a, "rev-parse", "HEAD")
        active_remote_tip = git_out(bare_b, "rev-parse", "main")

        code, out = self.run_cmd(["update"])
        self.assertEqual(code, 0)
        self.assertEqual(git_out(member_a, "rev-parse", "HEAD"), archived_before,
                         "archived member must never be fetched/fast-forwarded")
        self.assertEqual(git_out(member_b, "rev-parse", "HEAD"), active_remote_tip,
                         "active member in the same roster must still be updated normally")
        self.assertIn("archived_svc", out)
        self.assertIn("skipped", out.lower())
        self.assertNotIn("DIRTY", out)

    def test_update_rewrites_default_branch_when_trunk_renamed_upstream(self):
        bare, member = self._add_member("svc")
        self.assertEqual(self.roster()["repositories"][0]["default_branch"], "main")

        # trunk renamed upstream: main -> trunk2 (e.g. a GitHub default-branch rename)
        git(bare, "branch", "-m", "main", "trunk2")
        git(bare, "symbolic-ref", "HEAD", "refs/heads/trunk2")

        code, out = self.run_cmd(["update"])
        entry = self.roster()["repositories"][0]
        self.assertEqual(entry["default_branch"], "trunk2",
                         "update must re-detect the renamed trunk and rewrite the roster")
        self.assertIn("roster trunk main → trunk2", out)


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
