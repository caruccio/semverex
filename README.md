# semverex — Extended Semantic Versioning

`semverex` extends the
[`python-semanticversion`](https://github.com/rbarrois/python-semanticversion)
library (BSD-2-Clause) with *extended* version strings that carry extra numeric
components after the patch level — `patch1`, `patch2`, ...

It is a **drop-in replacement**: replace `import semantic_version` with
`import semverex` and existing client code keeps working, byte-for-byte, for
all official SemVer inputs.

## Examples

Official Semantic Version (unchanged):

```
1.2.3
1.2.3-b100
1.2.3-dbg
1.2.3-dbg.1
1.2.3+alpha
1.2.3+alpha.1
1.2.3+alpha.1.2-dbg
1.2.3+alpha.1.2-dbg.3.4
```

Extended Semantic Version (new):

```
1.2.3.4
1.2.3.4-5
1.2.3.4-dbg
1.2.3.4-dbg.1
1.2.3.4+alpha
1.2.3.4+alpha.1
1.2.3.4+alpha.1.2-dbg
1.2.3.4+alpha.1.2-dbg.3.4
```

Any number of extra numeric components is accepted (`1.2.3.4.5.6+build.7`);
they are strictly numeric. Leading zeroes are accepted in the numeric
components and preserved by `str()` (`01.02.03.04` stays `01.02.03.04`);
comparison remains numeric (`Version('01.2.3') == Version('1.2.3')`).
An optional lowercase `v` prefix is accepted and preserved the same way
(`v1.2.3` stays `v1.2.3`, compares equal to `1.2.3`).

Version **flags** may follow the version: one or more `!name[=value]`
sections (`1.2.3!dbg!channel=beta`). The name matches `[a-zA-Z0-9._-]+`;
the value is any text without `!` (optional, may be empty). Flags are
preserved by `str()`, exposed as `v.flags` (dict, last occurrence wins)
and `v.flags_str` (ordered list of strings), and are ignored in all
comparisons and calculations.

## Usage

```python
import semverex  # replaces `import semantic_version`

v = semverex.Version('1.2.3.4-dbg.1')
v.major, v.minor, v.patch   # 1, 2, 3          (unchanged field names)
v.patch1                    # 4                (first extra component)
v.patch2                    # None
v.patches                   # (4,)
v.patches_str               # ['4']            (extra components as strings)
v.prerelease                # ('dbg', '1')
str(v)                      # '1.2.3.4-dbg.1'

semverex.Version('1.2.3') < semverex.Version('1.2.3.4')   # True
semverex.SimpleSpec('>=1.2.3.4').match(semverex.Version('1.2.3.5'))  # True
semverex.match('>=1.2.3.4', '1.2.3.5')     # True
semverex.validate('1.2.3.4')               # True
semverex.Version.coerce('0.1.2.3')         # Version('0.1.2.3'), patch1 == 3
```

The public API mirrors upstream: `Version`, `SimpleSpec`, `NpmSpec`, `Spec`
(deprecated upstream, kept for compatibility), `SpecItem`, `compare`,
`match`, `validate`.

## Semantics of the extra components

- The **first** component keeps its historical name, `patch` (there is no
  `patch0`); the extra components are `patch1`, `patch2`, ... and the
  `patches` tuple. Absent components read as `None`. `patches_str` returns
  the same components as a list of strings (`['4', '5']` for `1.2.3.4.5`).
- Extra components are strictly numeric. Leading zeroes are accepted in all
  numeric components (`major`, `minor`, `patch` and the extras) and preserved
  by `str()`; the stored values are integers, so comparison, equality and
  hashing stay numeric (`Version('01.2.3') == Version('1.2.3')`). String
  kwargs work the same way: `Version(major='8', minor='322', patch='05')`
  stores ints but renders as `'8.322.05'`.
- **Trailing zeroes are insignificant** (PEP 440-style): `1.2.3`,
  `1.2.3.0` and `1.2.3.0.0` are the same version. `str()` preserves the
  original spelling.
- Ordering: components compare numerically after `patch`, before the
  prerelease: `1.2.3 < 1.2.3.4-rc.1 < 1.2.3.4 < 1.2.3.5`.
- `next_patch()` bumps the least significant component
  (`1.2.3` → `1.2.4`, `1.2.3.4` → `1.2.3.5`); `next_minor()`/`next_major()`
  reset the extras. `truncate('patch')` keeps the extra components.
- `coerce()` maps extra numeric components to patches
  (`coerce('0.1.2.3')` → `0.1.2.3`), instead of upstream's build-data mapping.
- Flags (`!name[=value]`) are metadata only: they ride along in `str()`,
  are exposed via `v.flags` / `v.flags_str`, and never affect ordering,
  equality, hashing or bumping (`1.2.3!dbg` == `1.2.3`). Repeated names
  are allowed; the last occurrence wins in `v.flags`, while `str()`
  preserves the original order and spelling.

## Specification matching

`SimpleSpec`, `NpmSpec` and the legacy `Spec` accept extended versions in
their clauses:

```python
semverex.SimpleSpec('~1.2.3.4')      # >=1.2.3.4, <1.3.0
semverex.SimpleSpec('^1.2.3.4')      # >=1.2.3.4, <2.0.0
semverex.NpmSpec('1.2.3.4 - 2.0.0')
```

They are registered under the `'simple-ex'` and `'npm-ex'` syntax names
(upstream keeps `'simple'`/`'npm'`), which are the defaults for
`semverex.SimpleSpec.parse()` / `semverex.NpmSpec.parse()`.

## Compatibility

The test suite includes a compatibility suite (`tests/test_compat.py`) that
runs the **same operations against both libraries** and asserts identical
results on official SemVer inputs: parsing fields, `str()`/`repr()`, partial
versions, full pairwise ordering, `compare()`, `validate()`, `SimpleSpec` /
`NpmSpec` / `Spec` / `SpecItem` matching, `select()`, `coerce()`,
`next_*()`/`truncate()`, hashes and a drop-in client scenario.

Notes and caveats:

- `semverex.Version` subclasses `semantic_version.Version`
  (`isinstance(v, semantic_version.Version)` holds).
- `iter(v)` yields the upstream 5-tuple `(major, minor, patch, prerelease,
  build)`; the extras are available via `v.patches` / `v.patch1` / ...
- Hashes of extended versions without extras match upstream hashes exactly.
- Avoid mixing the two classes in comparisons with the upstream `Version`
  on the left-hand side: upstream's own `__eq__` ignores the extra
  components, so `semantic_version.Version('1.2.3') == semverex.Version('1.2.3.4')`
  is `True` on that side only. Comparisons with `semverex.Version` on the
  left are always correct.
- Leading-zero components (`01.2.3`), a leading `v` prefix (`v1.2.3`) and
  version flags (`1.2.3!dbg`) are rejected by upstream but accepted by
  semverex — intentional divergences (`tests/test_compat.py` pins them).
  Official SemVer strings behave identically. Specs
  (`SimpleSpec`/`NpmSpec`) keep rejecting leading zeroes and `v` in their
  components (`NpmSpec` still strips a leading `v` from spec expressions,
  as upstream does).

## Install / test

```sh
pip install .        # depends on semantic_version>=2.10
python3 -m unittest discover -s tests -v
```

In the sandboxed environment (no pip), the upstream wheel is extracted under
`.deps/` and tests run with:

```sh
PYTHONPATH=.deps:. python3 -m unittest discover -s tests -v
```

## License

BSD-2-Clause; based on `python-semanticversion` by Raphaël Barrois (see
`UPSTREAM_LICENSE`).
