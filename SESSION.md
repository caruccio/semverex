# SESSION — semverex

semverex (this repo): a drop-in extension of
[python-semanticversion](https://github.com/rbarrois/python-semanticversion)
(BSD-2-Clause) that accepts extended version strings with extra numeric
components after the patch level (`1.2.3.4`, `1.2.3.4.5-dbg.1+b`).

## Layout

- `semverex/` — the package: `base.py` (extended `Version` + extended
  `SimpleSpec`/`NpmSpec`/`Spec`), `django_fields.py` (upstream copy)
- `tests/` — unittest suites: `test_extended.py` (extended behavior) and
  `test_compat.py` (same corpus run against BOTH semantic_version and
  semverex, results must be identical)
- `pyproject.toml` — package `semverex`; dependency `semantic_version>=2.10,<3`
- `.deps/` — upstream semantic_version wheel extracted, for the pip-less sandbox

## Key decisions (confirmed with the user)

- The first component stays `patch` (**no** `patch0`) — backward compatibility
  with existing client code. Extras are `patch1`, `patch2`, ..., the `patches`
  tuple, and the `patches_str` string (extras joined with '.').
- Drop-in replacement: `import semverex` must behave exactly like
  `import semantic_version` for official SemVer (enforced by test_compat.py).
- Trailing zeros in the extras are insignificant (`1.2.3 == 1.2.3.0`).
- Leading zeros in the numeric components are accepted and preserved by
  `str()` (`01.02.03.04` stays `01.02.03.04`); comparison stays numeric.
  String kwargs are accepted too (`patch='05'`). Specs keep rejecting
  them (upstream rule).
- An optional lowercase `v` prefix is accepted and preserved (`v1.2.3`
  stays `v1.2.3`, compares equal to `1.2.3`); `coerce()` accepts it too.
  Specs keep rejecting it (NpmSpec strips it, as upstream).
- Version flags: trailing `!name[=value]` sections (name
  `[a-zA-Z0-9._-]+`, value anything but `!`, may be empty/absent).
  Preserved by `str()`, exposed via `v.flags` (dict, last occurrence
  wins) and `v.flags_str` (ordered strings); ignored in comparisons,
  hashing, equality and `next_*`/`truncate`. Kwargs accept `flags=`.
- `next_patch()` bumps the least significant component (`1.2.3.4` -> `1.2.3.5`).
- Spec syntaxes registered as `'simple-ex'` / `'npm-ex'` (the upstream
  registry rejects duplicates of `'simple'`/`'npm'`).
- Incomplete versions (`1`, `1.2`, `1-dbg`, `1.2-dbg`) are accepted
  without `partial=True` — auto-detected as partial (missing components
  are `None`), without the deprecation warning.

## Run tests

    pip install .          # normal environments
    # sandbox (no pip): the vendored wheel in .deps/ is used instead
    PYTHONPATH=.deps:. python3 -m unittest discover -s tests -v
