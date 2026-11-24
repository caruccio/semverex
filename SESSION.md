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
  tuple, and the `patches_str` list.
- Drop-in replacement: `import semverex` must behave exactly like
  `import semantic_version` for official SemVer (enforced by test_compat.py).
- Trailing zeros in the extras are insignificant (`1.2.3 == 1.2.3.0`).
- Leading zeros in the numeric components are accepted and preserved by
  `str()` (`01.02.03.04` stays `01.02.03.04`); comparison stays numeric.
  Specs keep rejecting them (upstream rule).
- `next_patch()` bumps the least significant component (`1.2.3.4` -> `1.2.3.5`).
- Spec syntaxes registered as `'simple-ex'` / `'npm-ex'` (the upstream
  registry rejects duplicates of `'simple'`/`'npm'`).

## Run tests

    pip install .          # normal environments
    # sandbox (no pip): the vendored wheel in .deps/ is used instead
    PYTHONPATH=.deps:. python3 -m unittest discover -s tests -v
