# -*- coding: utf-8 -*-
"""Compatibility tests: semverex must behave exactly like semantic_version
on official (non-extended) SemVer inputs.

Each test runs the same operation against both libraries and asserts the
results are identical, so semverex can replace `import semantic_version`
in existing client code.
"""

import itertools
import unittest
import warnings

import semantic_version
import semverex


OFFICIAL_VERSIONS = [
    '0.0.0', '0.0.4', '0.1.0', '1.2.3', '1.2.3-0', '1.2.3-b100',
    '1.2.3-dbg', '1.2.3-dbg.1', '1.2.3-rc.1.2', '1.2.3-1', '1.2.3-1.10',
    '1.2.3+alpha', '1.2.3+alpha.1', '1.2.3+alpha.1.2-dbg',
    '1.2.3+alpha.1.2-dbg.3.4', '1.2.3-a1+b2', '1.2.4', '1.10.0', '2.0.0',
    '10.20.30', '0.0.1', '1.2.3-zzz', '1.2.3-9', '1.2.3-9.10',
]

INVALID_BOTH = [
    '1.2', '1.2.3-01', '1.2.3.', 'a.b.c',
    '', '1.2.3-', '1.2.3+', 'v1.2.3', '1.2.3..4', '1.2.3.dbg',
]

# Accepted by semverex (leading zeroes preserved in str()), rejected by
# upstream — an intentional, pinned divergence. See ExtensionBoundaryTestCase.
LEADING_ZERO_VERSIONS = [
    '01.2.3', '1.02.3', '1.2.03', '1.2.3.04', '01.02.03.04',
]

EXTENDED_VERSIONS = [
    '1.2.3.4', '1.2.3.4-5', '1.2.3.4-dbg', '1.2.3.4-dbg.1', '1.2.3.4+alpha',
    '1.2.3.4+alpha.1', '1.2.3.4+alpha.1.2-dbg', '1.2.3.4+alpha.1.2-dbg.3.4',
    '1.2.3.4.5', '1.2.3.4.5.6+build.7',
]


class CompatibilityTestCase(unittest.TestCase):
    """Shared helpers."""

    def run_op(self, func):
        """Run `func(lib)` for both libs; return {lib_name: ('ok', value) | ('err', type)}."""
        out = {}
        for lib in (semantic_version, semverex):
            try:
                out[lib.__name__] = ('ok', func(lib))
            except Exception as exc:
                out[lib.__name__] = ('err', type(exc).__name__)
        return out

    def assert_same(self, func, msg=''):
        results = self.run_op(func)
        upstream = results[semantic_version.__name__]
        for name, result in results.items():
            self.assertEqual(result, upstream, msg='%s differs: %s' % (msg, name))

    def test_parse_fields(self):
        self.assert_same(lambda lib: [
            (v.major, v.minor, v.patch, v.prerelease, v.build)
            for s in OFFICIAL_VERSIONS
            for v in [lib.Version(s)]
        ], 'parse fields')

    def test_str_and_repr(self):
        self.assert_same(lambda lib: [
            (str(lib.Version(s)), repr(lib.Version(s)))
            for s in OFFICIAL_VERSIONS
        ], 'str/repr')

    def test_parse_classmethod(self):
        base_out = [semantic_version.Version.parse(s) for s in OFFICIAL_VERSIONS]
        mine_out = [semverex.Version.parse(s) for s in OFFICIAL_VERSIONS]
        for s, base_t, mine_t in zip(OFFICIAL_VERSIONS, base_out, mine_out):
            # semverex returns (major, minor, patch, patches, prerelease, build);
            # patches is () for official versions.
            self.assertEqual(base_t, (mine_t[0], mine_t[1], mine_t[2], mine_t[4], mine_t[5]), msg=s)
            self.assertEqual(mine_t[3], (), msg=s)

    def test_partial_parse(self):
        def op(lib):
            out = []
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for s in ['1', '1.2', '1.2.3', '1.2.3-', '1.2.3+', '1.2.3-a', '1.2.3+b']:
                    v = lib.Version(s, partial=True)
                    out.append((str(v), (v.major, v.minor, v.patch, v.prerelease, v.build)))
            return out
        self.assert_same(op, 'partial parse')

    def test_ordering_matrix(self):
        self.assert_same(lambda lib: [
            (i, j, a < b, a == b, a > b, a <= b, a >= b, a != b)
            for i, s1 in enumerate(OFFICIAL_VERSIONS)
            for a in [lib.Version(s1)]
            for j, s2 in enumerate(OFFICIAL_VERSIONS)
            for b in [lib.Version(s2)]
        ], 'ordering matrix')

    def test_compare_function(self):
        self.assert_same(lambda lib: [
            lib.compare(a, b)
            for a, b in itertools.product(OFFICIAL_VERSIONS, OFFICIAL_VERSIONS)
        ], 'compare()')

    def test_validate(self):
        self.assert_same(lambda lib: [
            lib.validate(s) for s in OFFICIAL_VERSIONS + INVALID_BOTH
        ], 'validate()')

    def test_simple_specs(self):
        SPECS = [
            '*', '>=1.2.3', '>1.2.3', '<=1.2.3', '<1.2.3', '==1.2.3', '!=1.2.3',
            '~1.2', '~1.2.3', '^1.2.3', '^0.2.3', '^0.0.3', '~=1.4', '~=1.4.5',
            '>=1.0.0,<2.0.0', '1.2.*', '1.x', '!=1.2.3-', '<1.2.3-', '==1.2.3+',
            '==1.2.3-a1+b', '>1.2.3-rc.1',
        ]

        def op(lib):
            return [
                (spec_s, v_s, lib.SimpleSpec(spec_s).match(lib.Version(v_s)))
                for spec_s in SPECS
                for v_s in OFFICIAL_VERSIONS
            ]
        self.assert_same(op, 'SimpleSpec')

    def test_npm_specs(self):
        SPECS = [
            '^1.2.3', '~1.2.3', '>=1.2.3 <2.0.0', '1.2.3 - 1.4.5',
            '>=1.2.3 || <1.0.0', '1.2.x', '~1.2', '^0.2.3', '>=1.2.3-a1',
            '<=1.2.3-a1', '>1.2.3-a1', '1.2.3', '=1.2.3', '>=1.2.3+b',
        ]

        def op(lib):
            return [
                (spec_s, v_s, lib.NpmSpec(spec_s).match(lib.Version(v_s)))
                for spec_s in SPECS
                for v_s in OFFICIAL_VERSIONS
            ]
        self.assert_same(op, 'NpmSpec')

    def test_legacy_spec(self):
        def op(lib):
            out = []
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for spec_s in ['>=1.2.3', '~1.2', '>=1.0.0,<2.0.0']:
                    spec = lib.Spec(spec_s)
                    for v_s in OFFICIAL_VERSIONS:
                        out.append((spec_s, v_s, spec.match(lib.Version(v_s))))
            return out
        self.assert_same(op, 'Spec')

    def test_specitem(self):
        def op(lib):
            out = []
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for s in ['*', '>=1.2.3', '<0.0.0-', '~1.2']:
                    item = lib.SpecItem(s)
                    out.append((item.kind, str(item.spec)))
            return out
        self.assert_same(op, 'SpecItem')

    def test_spec_select(self):
        self.assert_same(
            lambda lib: str(lib.SimpleSpec('>=1.2.0,<2.0.0').select(
                [lib.Version(s) for s in OFFICIAL_VERSIONS])),
            'spec select',
        )

    def test_match_helper(self):
        def op(lib):
            out = []
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for spec_s in ['>=1.2.3', '~1.2', '!=1.2.3-rc.1']:
                    for v_s in OFFICIAL_VERSIONS:
                        out.append((spec_s, v_s, lib.match(spec_s, v_s)))
            return out
        self.assert_same(op, 'match()')

    def test_coerce(self):
        COERCE = ['0.1', '1', '1.2', '1.2.3', '1.2.3+b', '1.2.3-rc.1',
                  '0.1+2-3+4_5', '1.2.3-rc+dbg', 'v1.2.3']

        def op(lib):
            out = []
            for s in COERCE:
                out.append(('coerce', s, str(lib.Version.coerce(s))))
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                for s in ['1', '1.2']:
                    out.append(('partial', s, str(lib.Version.coerce(s, partial=True))))
            return out
        self.assert_same(op, 'coerce')

    def test_bump_truncate(self):
        def op(lib):
            out = []
            for s in ['0.1.2', '1.2.3', '1.2.3-rc', '1.2.3+b', '2.0.0-rc', '0.0.1']:
                v = lib.Version(s)
                out.append((s, str(v.next_major()), str(v.next_minor()), str(v.next_patch())))
                for level in ['build', 'prerelease', 'patch', 'minor', 'major']:
                    out.append((s, level, str(v.truncate(level))))
            return out
        self.assert_same(op, 'bump/truncate')

    def test_hash_matches_upstream(self):
        for s in OFFICIAL_VERSIONS:
            self.assertEqual(
                hash(semantic_version.Version(s)), hash(semverex.Version(s)), msg=s)

    def test_cross_library_equality(self):
        for s in OFFICIAL_VERSIONS:
            a = semantic_version.Version(s)
            b = semverex.Version(s)
            self.assertEqual(a, b, msg=s)
            self.assertEqual(b, a, msg=s)

    def test_mixed_class_ordering(self):
        for s1, s2 in itertools.product(OFFICIAL_VERSIONS, OFFICIAL_VERSIONS):
            expected = semantic_version.Version(s1) < semantic_version.Version(s2)
            got = semverex.Version(s1) < semantic_version.Version(s2)
            self.assertEqual(expected, got, msg=(s1, s2))

    def test_drop_in_client(self):
        """A client using the upstream public API, run against both libraries."""
        def client(sv):
            results = []
            v = sv.Version('1.2.3-b100')
            results.append((v.major, v.minor, v.patch, v.prerelease, v.build))
            results.append(str(v))
            results.append(str(sv.Version.coerce('1.2')))
            results.append(sv.SimpleSpec('>=1.2.3').match(sv.Version('1.2.4')))
            results.append(sv.NpmSpec('~1.2').match(sv.Version('1.2.9')))
            results.append(sv.validate('1.2.3'))
            results.append(sv.validate('1.2'))
            results.append(sv.compare('1.2.3', '1.2.4'))
            results.append([str(x) for x in sorted(
                [sv.Version(s) for s in ['1.2.10', '1.2.3-rc.1', '1.2.3', '2.0.0']],
                key=lambda x: x.precedence_key)])
            with warnings.catch_warnings():
                warnings.simplefilter('ignore')
                results.append(sv.Spec('>=1.2.3').match(sv.Version('1.2.5')))
            return results
        self.assertEqual(client(semantic_version), client(semverex))


class ExtensionBoundaryTestCase(unittest.TestCase):
    """Pin down the *intentional* differences between the two libraries."""

    def test_extended_strings_rejected_by_upstream(self):
        for s in EXTENDED_VERSIONS:
            with self.assertRaises(ValueError, msg=s):
                semantic_version.Version(s)

    def test_extended_strings_accepted_by_semverex(self):
        for s in EXTENDED_VERSIONS:
            self.assertEqual(str(semverex.Version(s)), s)

    def test_extended_strings_invalid_upstream_but_valid_semverex(self):
        for s in EXTENDED_VERSIONS:
            self.assertFalse(semantic_version.validate(s))
            self.assertTrue(semverex.validate(s))

    def test_coerce_divergence_is_intentional(self):
        # Upstream maps extra numeric components to build data; semverex makes
        # them extra patch components.
        self.assertEqual(str(semantic_version.Version.coerce('0.1.2.3')), '0.1.2+3')
        self.assertEqual(str(semverex.Version.coerce('0.1.2.3')), '0.1.2.3')

    def test_leading_zero_divergence_is_intentional(self):
        # Upstream rejects leading zeroes in numeric components; semverex
        # accepts them and preserves the original spelling in str(), while
        # the numeric value and comparisons stay normal.
        for s in LEADING_ZERO_VERSIONS:
            with self.assertRaises(ValueError, msg=s):
                semantic_version.Version(s)
            v = semverex.Version(s)
            self.assertEqual(str(v), s)
            self.assertTrue(semverex.validate(s))
            self.assertFalse(semantic_version.validate(s))


if __name__ == '__main__':
    unittest.main()
