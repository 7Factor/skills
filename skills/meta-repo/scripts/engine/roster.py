"""roster.py — meta-repo.yaml persistence: tiny, constrained YAML I/O.

`meta-repo.yaml` is written ONLY by this engine (init/add/remove). Because this
script is the sole writer, reading it back is safe string work — we do NOT
depend on PyYAML or yq, and there is exactly ONE yaml mechanism here.
"""
from __future__ import annotations

import json
import re
from pathlib import Path

META_REPO_VERSION = "0.7.0"
YAML_NAME = "meta-repo.yaml"
FIELD_ORDER = ["path", "role", "remote", "default_branch", "status"]
VALID_STATUS = ["active", "archived"]


# ----------------------------------------------------------------------------
# tiny YAML I/O for our constrained, self-written schema
# ----------------------------------------------------------------------------
def _scalar(v) -> str:
    s = "" if v is None else str(v)
    if s == "" or s != s.strip() or ": " in s or "#" in s or (s and s[0] in "\"'[]{}>|*&!%@`"):
        return json.dumps(s)
    return s


def _unquote(s: str):
    s = s.strip()
    if len(s) >= 2 and s[0] == s[-1] and s[0] in "\"'":
        if s[0] == '"':
            try:
                return json.loads(s)
            except Exception:
                return s[1:-1]
        return s[1:-1]
    return s


def parse_yaml(text: str) -> dict:
    data = {"name": "", "description": "", "repositories": []}
    in_repos = False
    cur = None
    for raw in text.splitlines():
        line = raw.rstrip()
        if not line.strip() or line.lstrip().startswith("#"):
            continue
        if not in_repos:
            if re.match(r"^repositories:\s*$", line):
                in_repos = True
                continue
            m = re.match(r"^([A-Za-z_]\w*):\s?(.*)$", line)
            if m:
                data[m.group(1)] = _unquote(m.group(2))
            continue
        m_item = re.match(r"^\s*-\s+([A-Za-z_]\w*):\s?(.*)$", line)
        if m_item:
            cur = {m_item.group(1): _unquote(m_item.group(2))}
            data["repositories"].append(cur)
            continue
        m_kv = re.match(r"^\s+([A-Za-z_]\w*):\s?(.*)$", line)
        if m_kv and cur is not None:
            cur[m_kv.group(1)] = _unquote(m_kv.group(2))
    return data


def dump_yaml(data: dict) -> str:
    lines = [
        f"name: {_scalar(data.get('name', ''))}",
        f"description: {_scalar(data.get('description', ''))}",
        "repositories:",
    ]
    for r in data.get("repositories", []):
        lines.append(f"  - name: {_scalar(r.get('name', ''))}")
        for k in FIELD_ORDER:
            v = r.get(k)
            if v not in (None, ""):
                lines.append(f"    {k}: {_scalar(v)}")
    return "\n".join(lines) + "\n"


class YamlValidationError(Exception):
    """Raised when a parsed meta-repo.yaml doesn't match the documented schema.

    `parse_yaml` is a permissive line-scanner with no schema awareness of its own —
    on anything that doesn't match its expected shape it silently mis-parses or
    drops data rather than complaining. This is the schema check that sits on top
    of it, so a hand-edit gone wrong (despite the "engine writes it" contract)
    surfaces as one clear, specific error instead of a silently corrupted roster.
    """


def validate_yaml_data(data) -> None:
    """Validate the *structure* of a parsed meta-repo.yaml roster.

    Checks (per REFERENCE.md's `meta-repo.yaml schema` section):
      * top level is a mapping with a `repositories` key
      * `repositories` is a list
      * each entry in it is a mapping with the two strictly-required fields,
        `name` and `path`, present and non-empty

    Deliberately does NOT validate field *values* — e.g. an unrecognized
    `status` (a value this engine's own `add --status` would reject on write)
    is tolerated here on read, matching the read-tolerance the engine already
    guarantees for files it didn't originate. Optional fields (`role`,
    `remote`, `default_branch`, `status`, `description`) being absent is fine.
    """
    if not isinstance(data, dict):
        raise YamlValidationError(
            f"{YAML_NAME} did not parse to a mapping at the top level "
            f"(got {type(data).__name__}). The file may be corrupted."
        )
    if "repositories" not in data:
        raise YamlValidationError(
            f"{YAML_NAME} is missing the required top-level 'repositories' key."
        )
    repos = data["repositories"]
    if not isinstance(repos, list):
        raise YamlValidationError(
            f"{YAML_NAME}: 'repositories' must be a list of members, but parsed as "
            f"{type(repos).__name__} ({repos!r}). Check for a stray value after "
            f"'repositories:' or bad indentation under it."
        )
    for i, r in enumerate(repos):
        label = f"repositories[{i}]"
        if not isinstance(r, dict):
            raise YamlValidationError(
                f"{YAML_NAME}: {label} is not a valid member entry "
                f"(got {type(r).__name__}: {r!r}). Each member must be a "
                f"'- name: ...' block with indented fields underneath."
            )
        display = r.get("name") or f"<unnamed, {label}>"
        for field in ("name", "path"):
            v = r.get(field)
            if not isinstance(v, str) or not v.strip():
                raise YamlValidationError(
                    f"{YAML_NAME}: member '{display}' ({label}) is missing the "
                    f"required '{field}' field. Every member needs both 'name' "
                    f"and 'path'."
                )


def load(root: Path) -> dict:
    # Lazy import to avoid a module-load-time cycle: git_ops needs YAML_NAME
    # from this module, and this function needs die() from git_ops.
    from .git_ops import die

    data = parse_yaml((root / YAML_NAME).read_text(encoding="utf-8"))
    try:
        validate_yaml_data(data)
    except YamlValidationError as e:
        die(str(e))
    return data


def save(root: Path, data: dict) -> None:
    (root / YAML_NAME).write_text(dump_yaml(data), encoding="utf-8")
