# -*- coding: utf-8 -*-
"""semverex extension tests: extra patch components (patch1, patch2, ...)."""

import unittest
import warnings

import semverex
from semverex import (
    NpmSpec,
    SimpleSpec,
    Spec,
    Version,
    compare,
    match,
    validate,
)


class ParsingTestCase(unittest.TestCase):
    # (version string, (major, minor, patch, patches, prerelease, build))
    CASES = [
        # Official Semantic Version
        ('1.2.3', (1, 2, 3, (), (), ())),
        ('1.2.3-b100', (1, 2, 3, (), ('b100',), ())),
        ('1.2.3-dbg', (1, 2, 3, (), ('dbg',), ())),
        ('1.2.3-dbg.1', (1, 2, 3, (), ('dbg', '1'), ())),
        ('1.2.3+alpha', (1, 2, 3, (), (), ('alpha',))),
        ('1.2.3+alpha.1', (1, 2, 3, (), (), ('alpha', '1'))),
        ('1.2.3+alpha.1.2-dbg', (1, 2, 3, (), (), ('alpha', '1', '2-dbg'))),
        ('1.2.3+alpha.1.2-dbg.3.4', (1, 2, 3, (), (), ('alpha', '1', '2-dbg', '3', '4'))),
        # Extended Semantic Version
        ('1.2.3.4', (1, 2, 3, (4,), (), ())),
        ('1.2.3.4-5', (1, 2, 3, (4,), ('5',), ())),
        ('1.2.3.4-dbg', (1, 2, 3, (4,), ('dbg',), ())),
        ('1.2.3.4-dbg.1', (1, 2, 3, (4,), ('dbg', '1'), ())),
        ('1.2.3.4+alpha', (1, 2, 3, (4,), (), ('alpha',))),
        ('1.2.3.4+alpha.1', (1, 2, 3, (4,), (), ('alpha', '1'))),
        ('1.2.3.4+alpha.1.2-dbg', (1, 2, 3, (4,), (), ('alpha', '1', '2-dbg'))),
        ('1.2.3.4+alpha.1.2-dbg.3.4', (1, 2, 3, (4,), (), ('alpha', '1', '2-dbg', '3', '4'))),
        # Multiple extra components
        ('1.2.3.4.5', (1, 2, 3, (4, 5), (), ())),
        ('1.2.3.4.5.6+build.7', (1, 2, 3, (4, 5, 6), (), ('build', '7'))),
        ('1.2.3.4.5-rc.1+meta', (1, 2, 3, (4, 5), ('rc', '1'), ('meta',))),
    ]

    def test_parse_fields(self):
        for version_string, expected in self.CASES:
            v = Version(version_string)
            self.assertEqual(
                (v.major, v.minor, v.patch, v.patches, v.prerelease, v.build),
                expected,
                msg=version_string,
            )

    def test_str_roundtrip(self):
        for version_string, _ in self.CASES:
            self.assertEqual(str(Version(version_string)), version_string)

    def test_repr(self):
        self.assertEqual(repr(Version('1.2.3.4')), "Version('1.2.3.4')")

    def test_parse_classmethod(self):
        self.assertEqual(Version.parse('1.2.3.4'), (1, 2, 3, (4,), (), ()))

    def test_iter_keeps_upstream_tuple(self):
        # `major, minor, patch, prerelease, build = v` must keep working.
        major, minor, patch, prerelease, build = Version('1.2.3.4+b')
        self.assertEqual((major, minor, patch, prerelease, build),
                         (1, 2, 3, (), ('b',)))

    def test_patch_stays_patch(self):
        # The first component is `patch` (backward compatible), not `patch0`.
        v = Version('1.2.3.4')
        self.assertEqual(v.patch, 3)
        with self.assertRaises(AttributeError):
            v.patch0

    def test_patchn_accessors(self):
        v = Version('1.2.3.4.5')
        self.assertEqual(v.patch1, 4)
        self.assertEqual(v.patch2, 5)
        self.assertIsNone(v.patch3)
        self.assertIsNone(v.patch9)
        self.assertEqual(getattr(v, 'patch3', 'sentinel'), None)
        with self.assertRaises(AttributeError):
            v.unknown_attribute

    def test_patches_str(self):
        self.assertEqual(Version('1.2.3.4.5').patches_str, ['4', '5'])
        self.assertEqual(Version('1.2.3.4').patches_str, ['4'])
        self.assertEqual(Version('1.2.3').patches_str, [])
        self.assertEqual(Version('1.2.3.10').patches_str, ['10'])
        # always a list, even for kwargs-built versions
        v = Version(major=1, minor=2, patch=3, patches=(7, 8))
        self.assertEqual(v.patches_str, ['7', '8'])
        self.assertIsInstance(v.patches_str, list)

    def test_patchn_accessors_official_version(self):
        v = Version('1.2.3')
        self.assertIsNone(v.patch1)
        self.assertIsNone(v.patch2)

    def test_kwargs_construction(self):
        v = Version(major=1, minor=2, patch=3, patches=(4, 5), prerelease=('rc',), build=('b',))
        self.assertEqual(str(v), '1.2.3.4.5-rc+b')
        # patches/prerelease/build are optional
        v = Version(major=1, minor=2, patch=3)
        self.assertEqual(str(v), '1.2.3')
        self.assertEqual(v.patches, ())

    def test_invalid_strings(self):
        for bad in [
                '1.2', '1.2.3.dbg', '1.2.3..4', 'a.b.c', '', '1.2.3-',
                '1.2.3+', '1.2.3.4.', 'v1.2.3', '1.2.3.4-01']:
            with self.assertRaises(ValueError, msg=bad):
                Version(bad)

    def test_partial(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.assertEqual(str(Version('1.2.3.4', partial=True)), '1.2.3.4')
            self.assertEqual(str(Version('1.2', partial=True)), '1.2')
            v = Version('1.2.3.4-', partial=True)
            self.assertEqual((v.patch, v.patches, v.prerelease), (3, (4,), ()))
            self.assertEqual(str(v), '1.2.3.4-')
            with self.assertRaises(ValueError):
                Version('1.2.3.dbg', partial=True)

    def test_validate(self):
        for version_string, _ in self.CASES:
            self.assertTrue(validate(version_string), msg=version_string)
        self.assertFalse(validate('1.2.3.dbg'))
        self.assertFalse(validate('1.2'))


class LeadingZeroTestCase(unittest.TestCase):
    """Leading zeroes in numeric components: accepted, preserved by str(),
    numerically compared."""

    def test_parse_fields_numeric(self):
        v = Version('01.02.03.04.05')
        self.assertEqual(
            (v.major, v.minor, v.patch, v.patches),
            (1, 2, 3, (4, 5)),
        )
        self.assertEqual(v.patch1, 4)
        self.assertEqual(v.patch2, 5)

    def test_str_preserves_original_spelling(self):
        for s in ['01.2.3', '1.02.3', '1.2.03', '1.2.3.04', '01.02.03.04',
                  '001.0002.0003']:
            self.assertEqual(str(Version(s)), s, msg=s)

    def test_equality_and_hash_are_numeric(self):
        self.assertEqual(Version('01.2.3'), Version('1.2.3'))
        self.assertEqual(Version('1.2.3.04'), Version('1.2.3.4'))
        self.assertEqual(hash(Version('01.2.3')), hash(Version('1.2.3')))
        self.assertEqual(hash(Version('1.2.3.04')), hash(Version('1.2.3.4')))

    def test_comparison_is_numeric(self):
        self.assertFalse(Version('01.2.3') < Version('1.2.3'))
        self.assertFalse(Version('01.2.3') > Version('1.2.3'))
        self.assertEqual(compare('01.2.3', '1.2.3'), 0)
        self.assertLess(Version('01.2.3'), Version('1.2.4'))
        self.assertLess(Version('1.2.3.04'), Version('1.2.3.5'))

    def test_trailing_zero_interaction(self):
        # Leading zeroes are cosmetic; trailing zeroes stay insignificant.
        self.assertEqual(Version('1.2.3.00'), Version('1.2.3'))
        self.assertEqual(str(Version('1.2.3.00')), '1.2.3.00')

    def test_patches_str_preserves_spelling(self):
        self.assertEqual(Version('1.2.3.04.05').patches_str, ['04', '05'])
        self.assertEqual(Version('1.2.3').patches_str, [])

    def test_partial_preserves_spelling(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            self.assertEqual(str(Version('01.02', partial=True)), '01.02')
            v = Version('01.02.03.04-', partial=True)
            self.assertEqual(str(v), '01.02.03.04-')
            self.assertEqual((v.major, v.patch, v.patch1), (1, 3, 4))

    def test_validate(self):
        self.assertTrue(validate('01.02.03.04'))
        self.assertTrue(validate('01.2.3'))

    def test_kwargs_and_bumps_normalize(self):
        # Versions built from int kwargs (or returned by next_*) have no
        # original spelling to preserve, so their str() is normalized.
        v = Version('01.02.03.04')
        self.assertEqual(str(v.next_patch()), '1.2.3.5')
        self.assertEqual(str(v.next_minor()), '1.3.0')
        self.assertEqual(str(v.truncate('patch')), '1.2.3.4')
        self.assertEqual(str(Version(major=1, minor=2, patch=3, patches=(4,))), '1.2.3.4')
        self.assertEqual(Version(major=1, minor=2, patch=3, patches=(4,)).patches_str, ['4'])

    def test_string_kwargs_preserve_spelling(self):
        v = Version(major='8', minor='322', patch='05')
        self.assertEqual(str(v), '8.322.05')
        self.assertEqual((v.major, v.minor, v.patch), (8, 322, 5))
        self.assertEqual(v, Version('8.322.5'))
        self.assertEqual(hash(v), hash(Version('8.322.5')))

        v = Version(major='01', minor='2', patch='3', patches=('04', '05'))
        self.assertEqual(str(v), '01.2.3.04.05')
        self.assertEqual(v.patches, (4, 5))
        self.assertEqual(v.patches_str, ['04', '05'])

    def test_string_kwargs_invalid(self):
        for kwargs in [
                dict(major='abc'), dict(major='8.5'), dict(major=8.5),
                dict(major='1', minor='2x'), dict(major='1', patch='05a'),
                dict(major='1', patches=('04x',)),
        ]:
            with self.assertRaises(ValueError, msg=kwargs):
                Version(**kwargs)

    def test_specs_still_reject_leading_zeroes(self):
        for bad in ['==01.2.3', '>=1.02.3', '~1.2.03']:
            with self.assertRaises(ValueError, msg=bad):
                SimpleSpec(bad)


class OrderingTestCase(unittest.TestCase):
    def assert_order(self, sequence):
        versions = [Version(s) for s in sequence]
        for lower, higher in zip(versions, versions[1:]):
            self.assertLess(lower, higher, msg='%r < %r' % (lower, higher))
            self.assertGreater(higher, lower)
        self.assertEqual(versions, sorted(versions))

    def test_extended_ordering(self):
        self.assert_order([
            '1.2.3', '1.2.3.4', '1.2.3.5', '1.2.3.10', '1.2.3.10.1',
            '1.2.4', '1.3.0', '2.0.0',
        ])

    def test_numeric_not_lexicographic(self):
        # (10,) > (5,) even though '10' < '5' lexicographically.
        self.assertLess(Version('1.2.3.5'), Version('1.2.3.10'))

    def test_trailing_zeroes_insignificant(self):
        self.assertEqual(Version('1.2.3.4'), Version('1.2.3.4.0'))
        self.assertEqual(Version('1.2.3'), Version('1.2.3.0'))
        self.assertEqual(Version('1.2.3.0.0'), Version('1.2.3'))
        self.assertEqual(hash(Version('1.2.3.4')), hash(Version('1.2.3.4.0')))
        # ...but str() preserves the original spelling.
        self.assertEqual(str(Version('1.2.3.4.0')), '1.2.3.4.0')

    def test_missing_vs_zero(self):
        self.assertLess(Version('1.2.3'), Version('1.2.3.0.4'))
        self.assertLess(Version('1.2.3.0.4'), Version('1.2.3.4'))

    def test_prerelease_ordering(self):
        self.assertLess(Version('1.2.3.4-dbg'), Version('1.2.3.4'))
        self.assertLess(Version('1.2.3.4-dbg.1'), Version('1.2.3.4-dbg.2'))
        self.assertLess(Version('1.2.3.4'), Version('1.2.3.5-dbg'))
        self.assertLess(Version('1.2.3.4-5'), Version('1.2.3.4-dbg'))
        self.assertLess(Version('1.2.3.4-1'), Version('1.2.3.4-2'))

    def test_build_metadata_ignored_for_precedence(self):
        a, b = Version('1.2.3.4+1'), Version('1.2.3.4+2')
        self.assertFalse(a < b)
        self.assertFalse(b < a)
        self.assertNotEqual(a, b)
        # precedence_key (used by sorted()) includes build metadata
        self.assertEqual(
            [str(v) for v in sorted([Version('1.2.3.4+1'), Version('1.2.3.4+2')])],
            ['1.2.3.4+1', '1.2.3.4+2'],
        )

    def test_compare(self):
        self.assertEqual(compare('1.2.3.4', '1.2.3.5'), -1)
        self.assertEqual(compare('1.2.3.5', '1.2.3.4'), 1)
        self.assertEqual(compare('1.2.3.4', '1.2.3.4'), 0)
        self.assertEqual(compare('1.2.3', '1.2.3.0'), 0)

    def test_equality_against_upstream_official(self):
        import semantic_version
        self.assertEqual(Version('1.2.3-rc.1+b'), semantic_version.Version('1.2.3-rc.1+b'))
        self.assertEqual(
            hash(Version('1.2.3-rc.1+b')), hash(semantic_version.Version('1.2.3-rc.1+b')))

    def test_is_subclass_of_upstream(self):
        import semantic_version
        self.assertTrue(issubclass(Version, semantic_version.Version))


class BumpTruncateCoerceTestCase(unittest.TestCase):
    def test_next_patch(self):
        self.assertEqual(str(Version('1.2.3').next_patch()), '1.2.4')
        self.assertEqual(str(Version('1.2.3.4').next_patch()), '1.2.3.5')
        self.assertEqual(str(Version('1.2.3.4.5').next_patch()), '1.2.3.4.6')
        self.assertEqual(str(Version('1.2.3.4-rc').next_patch()), '1.2.3.4')

    def test_next_minor_major(self):
        self.assertEqual(str(Version('1.2.3.4').next_minor()), '1.3.0')
        self.assertEqual(str(Version('1.2.3.4').next_major()), '2.0.0')

    def test_next_returns_extended_class(self):
        self.assertIsInstance(Version('1.2.3.4').next_major(), Version)
        self.assertIsInstance(Version('1.2.3.4').next_patch(), Version)

    def test_truncate(self):
        v = Version('1.2.3.4-rc.1+b.2')
        self.assertEqual(str(v.truncate('build')), '1.2.3.4-rc.1+b.2')
        self.assertEqual(str(v.truncate('prerelease')), '1.2.3.4-rc.1')
        self.assertEqual(str(v.truncate('patch')), '1.2.3.4')  # extra patches are kept
        self.assertEqual(str(v.truncate('minor')), '1.2.0')
        self.assertEqual(str(v.truncate('major')), '1.0.0')

    def test_coerce(self):
        self.assertEqual(str(Version.coerce('0.1')), '0.1.0')
        self.assertEqual(str(Version.coerce('0.1.2.3')), '0.1.2.3')
        self.assertEqual(str(Version.coerce('1.2.3.4.5')), '1.2.3.4.5')
        self.assertEqual(str(Version.coerce('0.1.2.3+4')), '0.1.2.3+4')
        v = Version.coerce('1.2.3.4')
        self.assertEqual(v.patches, (4,))
        self.assertEqual(v.patch1, 4)
        # non-numeric extra components still become build data (upstream rule)
        self.assertEqual(str(Version.coerce('0.1.2.db')), '0.1.2+db')
        with self.assertRaises(ValueError):
            Version.coerce('v1.2.3')


class SpecTestCase(unittest.TestCase):
    def assert_matches(self, spec, version, expected=True):
        self.assertIs(spec.match(Version(version)), expected,
                      msg='%r x %r' % (spec, version))

    def test_simple_spec_gte(self):
        spec = SimpleSpec('>=1.2.3.4')
        for good in ['1.2.3.4', '1.2.3.5', '1.2.3.10', '1.2.4', '1.3.0', '2.0.0']:
            self.assert_matches(spec, good)
        for bad in ['1.2.3', '1.2.3.3', '1.2.2.9', '1.2.3.4-rc']:
            self.assert_matches(spec, bad, False)

    def test_simple_spec_eq(self):
        spec = SimpleSpec('==1.2.3.4')
        self.assert_matches(spec, '1.2.3.4')
        self.assert_matches(spec, '1.2.3.4.0')  # trailing zero is the same version
        for bad in ['1.2.3', '1.2.3.5', '1.2.3.4.1']:
            self.assert_matches(spec, bad, False)

    def test_tilde_caret(self):
        spec = SimpleSpec('~1.2.3.4')
        for good in ['1.2.3.4', '1.2.3.9', '1.2.9.1']:
            self.assert_matches(spec, good)
        for bad in ['1.2.3.3', '1.3.0']:
            self.assert_matches(spec, bad, False)

        spec = SimpleSpec('^1.2.3.4')
        for good in ['1.2.3.4', '1.9.9.9']:
            self.assert_matches(spec, good)
        for bad in ['1.2.3.3', '2.0.0']:
            self.assert_matches(spec, bad, False)

    def test_gt_lt(self):
        spec = SimpleSpec('>1.2.3.4')
        self.assert_matches(spec, '1.2.3.5')
        self.assert_matches(spec, '1.2.3.4', False)

        spec = SimpleSpec('<1.2.3.4')
        self.assert_matches(spec, '1.2.3.3')
        self.assert_matches(spec, '1.2.3.4-a1', False)  # natural prerelease policy
        self.assert_matches(spec, '1.2.3.4', False)

        spec = SimpleSpec('<=1.2.3.4')
        self.assert_matches(spec, '1.2.3.4')
        self.assert_matches(spec, '1.2.3.3')
        self.assert_matches(spec, '1.2.3.5', False)

    def test_neq(self):
        spec = SimpleSpec('!=1.2.3.4')
        self.assert_matches(spec, '1.2.3.5')
        self.assert_matches(spec, '1.2.3.4', False)

    def test_legacy_spec(self):
        with warnings.catch_warnings():
            warnings.simplefilter('ignore')
            spec = Spec('>=1.2.3.4')
            self.assert_matches(spec, '1.2.3.5')
            self.assert_matches(spec, '1.2.3', False)
            spec = Spec('>=1.2.3.4', '!=1.2.3.5')
            self.assert_matches(spec, '1.2.3.6')
            self.assert_matches(spec, '1.2.3.5', False)

    def test_npm_spec(self):
        spec = NpmSpec('~1.2.3.4')
        self.assert_matches(spec, '1.2.3.9')
        self.assert_matches(spec, '1.3.0', False)

        spec = NpmSpec('^1.2.3.4')
        self.assert_matches(spec, '1.9.9')
        self.assert_matches(spec, '2.0.0', False)

        spec = NpmSpec('1.2.3.4 - 2.0.0')
        self.assert_matches(spec, '1.5.0')
        self.assert_matches(spec, '2.0.0')
        self.assert_matches(spec, '1.2.3.3', False)
        self.assert_matches(spec, '2.0.1', False)

    def test_syntaxes_registry(self):
        from semverex.base import BaseSpec
        spec = BaseSpec.parse('>=1.2.3.4', 'simple-ex')
        self.assertTrue(spec.match(Version('1.2.3.5')))
        spec = SimpleSpec.parse('>=1.2.3.4')
        self.assertTrue(spec.match(Version('1.2.3.5')))
        spec = NpmSpec.parse('~1.2.3.4')
        self.assertTrue(spec.match(Version('1.2.3.5')))
        with self.assertRaises(KeyError):
            BaseSpec.parse('>=1.2.3.4', 'no-such-syntax')

    def test_match_helper(self):
        self.assertTrue(match('>=1.2.3.4', '1.2.3.4'))
        self.assertFalse(match('>=1.2.3.4', '1.2.3'))

    def test_filter_select(self):
        versions = [Version(x) for x in ['1.2.3', '1.2.3.4', '1.2.3.9', '1.2.4', '1.3.0']]
        spec = SimpleSpec('>=1.2.3.4,<1.3.0')
        selected = sorted(str(v) for v in spec.filter(versions))
        self.assertEqual(selected, ['1.2.3.4', '1.2.3.9', '1.2.4'])
        self.assertEqual(str(spec.select(versions)), '1.2.4')


if __name__ == '__main__':
    unittest.main()
