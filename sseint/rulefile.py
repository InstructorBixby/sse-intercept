"""Load rules from YAML.

Flags were the first attempt and they do not survive contact with a
real test: a session has five or six rules, each with two or three
conditions, and they get edited between runs. A file is also the thing
that goes in the report appendix -- "here is the exact configuration
that produced this" -- which a shell history does not do.

Unknown keys are an error, not a warning. A typo in a rule file is a
rule that silently never fires, and a rule that never fires looks
exactly like a client that handled the case correctly.
"""
from __future__ import annotations

import pathlib

import yaml

from sseint import rules as R

MATCH_KEYS = {"host", "path", "seq", "seq_from", "seq_to", "kind",
              "event", "data_contains", "data_matches"}


class RuleFileError(Exception):
    pass


def load(path) -> tuple[list[str], R.Engine]:
    """Return (allow_hosts, engine)."""
    doc = yaml.safe_load(pathlib.Path(path).read_text()) or {}
    if not isinstance(doc, dict):
        raise RuleFileError("top level must be a mapping")
    unknown = set(doc) - {"allow_hosts", "rules"}
    if unknown:
        raise RuleFileError(f"unknown top-level key(s): "
                            f"{', '.join(sorted(unknown))}")
    hosts = list(doc.get("allow_hosts") or [])
    rules = [_rule(i, r) for i, r in enumerate(doc.get("rules") or [])]
    ids = [r.id for r in rules]
    dupes = {i for i in ids if ids.count(i) > 1}
    if dupes:
        raise RuleFileError(f"duplicate rule id(s): "
                            f"{', '.join(sorted(dupes))}")
    return hosts, R.Engine(rules)


def _rule(index: int, raw) -> R.Rule:
    if not isinstance(raw, dict):
        raise RuleFileError(f"rule {index}: must be a mapping")
    unknown = set(raw) - {"id", "match", "action", "actions", "limit"}
    if unknown:
        raise RuleFileError(f"rule {index}: unknown key(s): "
                            f"{', '.join(sorted(unknown))}")
    rid = raw.get("id") or f"rule-{index}"
    match = raw.get("match") or {}
    if not isinstance(match, dict):
        raise RuleFileError(f"{rid}: match must be a mapping")
    bad = set(match) - MATCH_KEYS
    if bad:
        raise RuleFileError(
            f"{rid}: unknown match key(s): {', '.join(sorted(bad))}. "
            f"Known: {', '.join(sorted(MATCH_KEYS))}")
    actions = raw.get("actions")
    if actions is None:
        actions = [raw["action"]] if "action" in raw else []
    if not isinstance(actions, list):
        actions = [actions]
    return R.Rule(id=str(rid), match=R.Match(**match),
                  ops=[_op(rid, a) for a in actions],
                  limit=raw.get("limit"))


def _op(rid, spec):
    if isinstance(spec, str):
        spec = {spec: True}
    if not isinstance(spec, dict) or len(spec) != 1:
        raise RuleFileError(
            f"{rid}: an action is one name, optionally with arguments")
    (name, arg), = spec.items()
    if name == "drop":
        return R.Drop()
    if name == "pause":
        return R.Pause()
    if name == "cut":
        return R.Cut()
    if name == "delay":
        return R.Delay(ms=_ms(rid, arg))
    if name == "rewrite":
        if not isinstance(arg, dict) or "find" not in arg:
            raise RuleFileError(f"{rid}: rewrite needs find/replace")
        return R.Rewrite(find=arg["find"],
                         replace=arg.get("replace", ""),
                         regex=bool(arg.get("regex")))
    if name == "set_field":
        return R.SetField(name=arg["name"], value=str(arg["value"]))
    if name == "inject":
        if isinstance(arg, str):
            return R.Inject(text=arg)
        return R.Inject(text=arg["text"], where=arg.get("where", "after"))
    raise RuleFileError(f"{rid}: unknown action {name!r}")


def _ms(rid, arg) -> int:
    if isinstance(arg, dict):
        if "ms" in arg:
            return int(arg["ms"])
        if "s" in arg:
            return int(float(arg["s"]) * 1000)
        raise RuleFileError(f"{rid}: delay takes ms or s")
    return int(arg)
