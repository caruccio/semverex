# -*- coding: utf-8 -*-
# Copyright (c) The semverex project
# This code is distributed under the two-clause BSD License.

"""semverex core: an extension of python-semanticversion.

semverex extends `semantic_version <https://github.com/rbarrois/python-semanticversion>`_
with *extended* version strings that carry extra numeric components after the
patch level (``1.2.3.4``, ``1.2.3.4.5``, ...). The extra components are exposed
as ``patch1``, ``patch2``, ... and as the ``patches`` tuple. The first component
keeps its historical name, ``patch``, so client code relying on
``semantic_version`` keeps working unchanged.

Everything else behaves like the upstream library: it is a drop-in
replacement, and all official SemVer strings parse, compare and match exactly
as in ``semantic_version``.
"""

import re
import warnings

from semantic_version.base import (
    AlphaIdentifier,
    Always,
    BaseSpec,
    MaxIdentifier,
    Never,
    NpmSpec,
    NumericIdentifier,
    Range,
    SimpleSpec,
    SpecItem,
    Version as _BaseVersion,
)


class Version(_BaseVersion):
    """A Semantic Version, optionally carrying extra patch components.

    Accepts both official SemVer strings (``1.2.3``, ``1.2.3-b100``, ...) and
    extended ones with one or more extra numeric components after the patch
    level (``1.2.3.4``, ``1.2.3.4.5-dbg.1``, ...).

    Attributes:
        major, minor, patch: unchanged from ``semantic_version.Version``.
        patches (tuple of int): the extra components (``patch1``, ``patch2``,
            ...); empty for official versions.
        patch1, patch2, ...: read-only accessors for the extra components;
            ``None`` when the component is absent.
        prerelease, build, partial: unchanged from ``semantic_version.Version``.
        flags (dict): the version flags; see the ``flags``/``flags_str``
            properties below.

    Unlike upstream, leading zeroes in the numeric components are accepted
    (``01.02.03.04``) and preserved by ``str()``; the stored values are
    integers, so comparison, equality and hashing remain numeric
    (``Version('01.2.3') == Version('1.2.3')``). The same applies to
    kwargs-built versions: string components such as ``patch='05'`` are
    accepted, normalized to ints, and keep their spelling in ``str()``.
    An optional lowercase ``v`` prefix is accepted and preserved too
    (``Version('v1.2.3')`` renders as ``'v1.2.3'`` and compares equal to
    ``Version('1.2.3')``).

    Version flags follow the version: one or more ``!name[=value]`` sections
    after everything else (``1.2.3!dbg!channel=beta``). The name matches
    ``[a-zA-Z0-9._-]+``; the value is any text without ``!`` (may be empty,
    or absent: ``!name``). Flags are preserved by ``str()`` and ignored in
    all comparisons and calculations.
    """

    # Extra components are strictly numeric; leading zeroes are accepted and
    # preserved in ``str()``. The whole extra chunk is captured as one group,
    # then split on '.'. An optional lowercase 'v' prefix is accepted and
    # preserved in ``str()`` as well, and version flags may follow the
    # version ('!name[=value]' sections, ignored by comparisons).
    version_re = re.compile(r'^(?:v)?(\d+)\.(\d+)\.(\d+)'
                            r'((?:\.\d+)*)'
                            r'(?:-([0-9a-zA-Z.-]+))?'
                            r'(?:\+([0-9a-zA-Z.-]+))?'
                            r'(?:![a-zA-Z0-9._-]+(?:=[^!]*)?)*$')
    partial_version_re = re.compile(r'^(?:v)?(\d+)'
                                    r'(?:\.(\d+)'
                                    r'(?:\.(\d+)'
                                    r'((?:\.\d+)*)?'
                                    r')?)?'
                                    r'(?:-([0-9a-zA-Z.-]*))?'
                                    r'(?:\+([0-9a-zA-Z.-]*))?'
                                    r'(?:![a-zA-Z0-9._-]+(?:=[^!]*)?)*$')

    _FLAG_NAME_RE = re.compile(r'^[a-zA-Z0-9._-]+$')

    _PATCHN_RE = re.compile(r'^patch(\d+)$')

    def __init__(
            self,
            version_string=None,
            major=None,
            minor=None,
            patch=None,
            patches=None,
            prerelease=None,
            build=None,
            flags=None,
            partial=False):
        if partial:
            warnings.warn(
                "Partial versions will be removed in 3.0; use SimpleSpec('1.x.x') instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        has_text = version_string is not None
        has_parts = not (major is minor is patch is patches is prerelease is build is flags is None)
        if not has_text ^ has_parts:
            raise ValueError("Call either Version('1.2.3') or Version(major=1, ...).")

        if has_text:
            major, minor, patch, patches, prerelease, build = self.parse(version_string, partial)
            # Keep the original spelling of the numeric components so that
            # str() preserves leading zeroes ('01.02.03' stays '01.02.03');
            # the stored values are ints, so comparison stays numeric.
            raw_core = version_string.split('-', 1)[0].split('+', 1)[0].split('!', 1)[0]
            prefix = ''
            if raw_core.startswith('v'):
                prefix = 'v'
                raw_core = raw_core[1:]
            raw_parts = raw_core.split('.')
            self._raw_parts = tuple(
                raw_parts[i] if i < len(raw_parts) else None
                for i in range(3 + len(patches))
            )
            self._prefix = prefix
            self._flags_raw = self._split_flags(version_string)
        else:
            # Convenience: allow to omit patches/prerelease/build.
            patches = tuple(patches or ())
            prerelease = tuple(prerelease or ())
            if not partial:
                build = tuple(build or ())

            # Numeric components may be given as ints or digit strings
            # (leading zeroes included, e.g. patch='05'); they are normalized
            # to ints, and string components keep their spelling in str().
            raw_major, raw_minor, raw_patch, raw_patches = major, minor, patch, patches
            try:
                major = self._to_int(raw_major)
                minor = self._coerce(raw_minor, partial)
                patch = self._coerce(raw_patch, partial)
                patches = tuple(int(p) for p in raw_patches)
            except (TypeError, ValueError):
                raise ValueError(
                    "Invalid kwargs to Version(major=%r, minor=%r, patch=%r, "
                    "patches=%r, prerelease=%r, build=%r, partial=%r" % (
                        raw_major, raw_minor, raw_patch, raw_patches,
                        prerelease, build, partial,
                    ))
            self._raw_parts = tuple(
                None if part is None else (part if isinstance(part, str) else str(int(part)))
                for part in (raw_major, raw_minor, raw_patch) + raw_patches
            )
            self._prefix = ''
            self._flags_raw = self._normalize_flags_kwargs(flags)
            self._validate_kwargs(major, minor, patch, patches, prerelease, build, partial)

        self.major = major
        self.minor = minor
        self.patch = patch
        self.patches = patches
        self.prerelease = prerelease
        self.build = build

        self.partial = partial

        # Cached precedence keys
        # _cmp_precedence_key is used for semver-precedence comparison
        self._cmp_precedence_key = self._build_precedence_key(with_build=False)
        # _sort_precedence_key is used for self.precedence_key, esp. for sorted(...)
        self._sort_precedence_key = self._build_precedence_key(with_build=True)

    # ------------------------------------------------------------------
    # Extra patch components
    # ------------------------------------------------------------------

    def __getattr__(self, name):
        """Expose extra components by name: ``patch1``, ``patch2``, ...

        The first component keeps its historical name, ``patch``; there is no
        ``patch0``. Absent components return ``None``.
        """
        match = self._PATCHN_RE.match(name)
        if match:
            index = int(match.group(1)) - 1
            if index < 0:
                raise AttributeError(
                    "%r object has no attribute %r; the first component is named 'patch'"
                    % (self.__class__.__name__, name)
                )
            if index < len(self.patches):
                return self.patches[index]
            return None
        raise AttributeError(
            "%r object has no attribute %r" % (self.__class__.__name__, name)
        )

    @property
    def patches_str(self):
        """The extra patch components joined by ``.``, keeping their spelling.

        ``Version('1.2.3.4.5').patches_str`` returns ``'4.5'``; it is
        ``''`` for official versions without extra components. The original
        spelling is kept when the version was parsed from a string, so
        ``Version('1.2.3.04').patches_str`` returns ``'04'``.
        """
        if self._raw_parts is not None:
            return '.'.join(part for part in self._raw_parts[3:] if part is not None)
        return '.'.join(str(p) for p in self.patches)

    @property
    def flags(self):
        """The version flags as a dict.

        Flags follow the version (``1.2.3!dbg!channel=beta``). Repeated
        names are allowed; the last occurrence wins, so
        ``Version('1.2.3!a=1!a=2').flags`` returns ``{'a': '2'}``. A flag
        without ``=value`` maps to ``None``; ``!name=`` maps to ``''``.
        """
        flags = {}
        for name, value in self._flags_raw:
            flags[name] = value
        return flags

    @property
    def flags_str(self):
        """The flags as a list of strings, in order, without the ``!``.

        ``Version('1.2.3!dbg!channel=beta').flags_str`` returns
        ``['dbg', 'channel=beta']``; it is ``[]`` when there are no flags.
        """
        return [
            name if value is None else '%s=%s' % (name, value)
            for name, value in self._flags_raw
        ]

    def to_dict(self):
        """All version components as a dict, with string values.

        Numeric components are returned as strings, keeping the spelling
        given to the constructor (leading zeroes included); prerelease and
        build are tuples of identifier strings; ``flags`` is a dict of
        string-or-``None`` values:

        ``Version('v01.2.3.04-dbg!ch=beta').to_dict()`` returns
        ``{'major': '01', 'minor': '2', 'patch': '3', 'patches': ('04',),
        'patches_str': '04', 'prerelease': ('dbg',), 'build': (),
        'flags': {'ch': 'beta'}, 'flags_str': ['ch=beta'], 'prefix': 'v'}``.

        For versions built from kwargs the numeric components are formatted
        from their int values (``'1'``, ``'2'``, ...).
        """
        if self._raw_parts is not None:
            major, minor, patch = self._raw_parts[0], self._raw_parts[1], self._raw_parts[2]
            patches = tuple(part for part in self._raw_parts[3:] if part is not None)
        else:
            major = str(self.major)
            minor = None if self.minor is None else str(self.minor)
            patch = None if self.patch is None else str(self.patch)
            patches = tuple(str(p) for p in self.patches)
        return {
            'major': major,
            'minor': minor,
            'patch': patch,
            'patches': patches,
            'patches_str': '.'.join(patches),
            'prerelease': self.prerelease,
            'build': self.build,
            'flags': self.flags,
            'flags_str': self.flags_str,
            'prefix': self._prefix,
        }

    @staticmethod
    def _split_flags(version_string):
        """Extract the flags from an already-validated version string.

        The first ``!`` starts the flag section (``!`` cannot appear
        anywhere else in a valid version string). Returns a tuple of
        ``(name, value)`` pairs; ``value`` is ``None`` for ``!name`` and
        ``''`` for ``!name=``.
        """
        bang = version_string.find('!')
        if bang == -1:
            return ()
        flags = []
        for chunk in version_string[bang + 1:].split('!'):
            name, sep, value = chunk.partition('=')
            flags.append((name, value if sep else None))
        return tuple(flags)

    @classmethod
    def _normalize_flags_kwargs(cls, flags):
        """Validate and normalize the ``flags`` kwarg.

        Accepts a dict (``{'dbg': None, 'channel': 'beta'}``) or an
        iterable of ``(name, value)`` pairs. Returns the normalized tuple
        of ``(name, value)`` pairs.
        """
        if flags is None:
            return ()
        if isinstance(flags, dict):
            pairs = tuple(flags.items())
        else:
            try:
                pairs = tuple(flags)
            except TypeError:
                pairs = None
        try:
            normalized = []
            for pair in pairs:
                if isinstance(pair, str):
                    # A bare string would unpack char-by-char; require pairs.
                    raise ValueError(pair)
                name, value = pair
                if not isinstance(name, str) or not cls._FLAG_NAME_RE.match(name):
                    raise ValueError(name)
                if value is not None and (not isinstance(value, str) or '!' in value):
                    raise ValueError(value)
                normalized.append((name, value))
            return tuple(normalized)
        except (TypeError, ValueError):
            raise ValueError("Invalid flags: %r" % (flags,))

    def _patches_key(self):
        """The ``patches`` tuple with insignificant trailing zeroes removed.

        Trailing zeroes are insignificant, as in PEP 440: ``1.2.3``,
        ``1.2.3.0`` and ``1.2.3.0.0`` are the same version.
        """
        key = self.patches
        while key and key[-1] == 0:
            key = key[:-1]
        return key

    # ------------------------------------------------------------------
    # Parsing
    # ------------------------------------------------------------------

    @classmethod
    def parse(cls, version_string, partial=False, coerce=False):
        """Parse a version string into a tuple of components:
           (major, minor, patch, patches, prerelease, build).

        An optional leading ``v`` prefix is accepted and ignored here (the
        ``Version`` object itself preserves it in ``str()``).

        Args:
            version_string (str), the version string to parse
            partial (bool), whether to accept incomplete input
            coerce (bool), unused (kept for signature compatibility with
                semantic_version.Version.parse)
        """
        if not version_string:
            raise ValueError('Invalid empty version string: %r' % version_string)

        if partial:
            version_re = cls.partial_version_re
        else:
            version_re = cls.version_re

        match = version_re.match(version_string)
        if not match:
            raise ValueError('Invalid version string: %r' % version_string)

        major, minor, patch, extras, prerelease, build = match.groups()

        # Leading zeroes are accepted (unlike upstream): the components are
        # converted to ints, and the original spelling is kept separately
        # (see Version.__init__) for str().
        major = int(major)
        minor = cls._coerce(minor, partial)
        patch = cls._coerce(patch, partial)

        if patch is None:
            # No patch level: no extra components either.
            patches = ()
        elif extras:
            extra_parts = [part for part in extras.split('.') if part]
            patches = tuple(int(part) for part in extra_parts)
        else:
            patches = ()

        if prerelease is None:
            if partial and (build is None):
                # No build info, strip here
                return (major, minor, patch, patches, None, None)
            else:
                prerelease = ()
        elif prerelease == '':
            prerelease = ()
        else:
            prerelease = tuple(prerelease.split('.'))
            cls._validate_identifiers(prerelease, allow_leading_zeroes=False)

        if build is None:
            if partial:
                build = None
            else:
                build = ()
        elif build == '':
            build = ()
        else:
            build = tuple(build.split('.'))
            cls._validate_identifiers(build, allow_leading_zeroes=True)

        return (major, minor, patch, patches, prerelease, build)

    @staticmethod
    def _to_int(value):
        """Normalize a numeric component to int.

        Digit strings (leading zeroes included, ``'05'``) and integral
        numbers are accepted; junk strings and non-integral numbers are
        rejected.
        """
        if isinstance(value, str):
            value = int(value)
        if value != int(value):
            raise ValueError("Invalid numeric component: %r" % value)
        return int(value)

    @classmethod
    def _validate_kwargs(cls, major, minor, patch, patches, prerelease, build, partial):
        # Numeric components have already been normalized to ints by
        # Version.__init__; only prerelease/build structure remains to check.
        if (
                prerelease is None and not partial
                or build is None and not partial
        ):
            raise ValueError(
                "Invalid kwargs to Version(major=%r, minor=%r, patch=%r, "
                "patches=%r, prerelease=%r, build=%r, partial=%r" % (
                    major, minor, patch, patches, prerelease, build, partial
                ))
        if prerelease is not None:
            cls._validate_identifiers(prerelease, allow_leading_zeroes=False)
        if build is not None:
            cls._validate_identifiers(build, allow_leading_zeroes=True)

    @classmethod
    def coerce(cls, version_string, partial=False):
        """Coerce an arbitrary version string into a semverex-compatible one.

        Same rules as ``semantic_version.Version.coerce``, except that extra
        numeric components after the patch level become patch components
        (``coerce('0.1.2.3')`` yields ``0.1.2.3`` with ``patch1 == 3``)
        instead of build data, and an optional leading ``v`` prefix is
        accepted and preserved (``coerce('v1.2.3')`` yields ``v1.2.3``).
        """
        base_re = re.compile(r'^(?:v)?\d+(?:\.\d+)*')

        match = base_re.match(version_string)
        if not match:
            raise ValueError(
                "Version string lacks a numerical component: %r"
                % version_string
            )

        version = version_string[:match.end()]
        prefix = ''
        if version.startswith('v'):
            prefix = 'v'
            version = version[1:]
        if not partial:
            # We need a not-partial version.
            while version.count('.') < 2:
                version += '.0'

        # Strip leading zeros in components
        version = '.'.join(
            # If the part was '0', we end up with an empty string.
            part.lstrip('0') or '0'
            for part in version.split('.')
        )
        version = prefix + version

        # Split the numeric core into major/minor/patch + extra patches.
        parts = version.split('.')
        core = parts[:3]
        patches = parts[3:]

        version = '.'.join(core) + ('.' + '.'.join(patches) if patches else '')

        if match.end() == len(version_string):
            return Version(version, partial=partial)

        rest = version_string[match.end():]

        # Cleanup the 'rest'
        rest = re.sub(r'[^a-zA-Z0-9+.-]', '-', rest)

        if rest[0] == '+':
            # A 'build' component
            prerelease = ''
            build = rest[1:]
        elif rest[0] == '.':
            # An extra version component, probably 'build'
            prerelease = ''
            build = rest[1:]
        elif rest[0] == '-':
            rest = rest[1:]
            if '+' in rest:
                prerelease, build = rest.split('+', 1)
            else:
                prerelease, build = rest, ''
        elif '+' in rest:
            prerelease, build = rest.split('+', 1)
        else:
            prerelease, build = rest, ''

        build = build.replace('+', '.')

        if prerelease:
            version = '%s-%s' % (version, prerelease)
        if build:
            version = '%s+%s' % (version, build)

        return cls(version, partial=partial)

    # ------------------------------------------------------------------
    # Bumping and truncation
    # ------------------------------------------------------------------

    def next_major(self):
        if self.prerelease and self.minor == self.patch == 0 and not self._patches_key():
            return Version(
                major=self.major,
                minor=0,
                patch=0,
                partial=self.partial,
            )
        else:
            return Version(
                major=self.major + 1,
                minor=0,
                patch=0,
                partial=self.partial,
            )

    def next_minor(self):
        if self.prerelease and self.patch == 0 and not self._patches_key():
            return Version(
                major=self.major,
                minor=self.minor,
                patch=0,
                partial=self.partial,
            )
        else:
            return Version(
                major=self.major,
                minor=self.minor + 1,
                patch=0,
                partial=self.partial,
            )

    def next_patch(self):
        """Return the next version at patch level.

        Bumps the least significant component: the last extra patch when
        present (``1.2.3.4`` -> ``1.2.3.5``), the patch itself otherwise
        (``1.2.3`` -> ``1.2.4``).
        """
        if self.prerelease:
            return Version(
                major=self.major,
                minor=self.minor,
                patch=self.patch,
                patches=self.patches,
                partial=self.partial,
            )
        elif self.patches:
            patches = self.patches[:-1] + (self.patches[-1] + 1,)
            return Version(
                major=self.major,
                minor=self.minor,
                patch=self.patch,
                patches=patches,
                partial=self.partial,
            )
        else:
            return Version(
                major=self.major,
                minor=self.minor,
                patch=self.patch + 1,
                partial=self.partial,
            )

    def truncate(self, level='patch'):
        """Return a new Version object, truncated up to the selected level.

        Truncating to 'patch' keeps the extra patch components, so prerelease
        matching policies keep distinguishing ``1.2.3-a1`` from ``1.2.3.4-a1``.
        """
        if level == 'build':
            return self
        elif level == 'prerelease':
            return Version(
                major=self.major,
                minor=self.minor,
                patch=self.patch,
                patches=self.patches,
                prerelease=self.prerelease,
                partial=self.partial,
            )
        elif level == 'patch':
            return Version(
                major=self.major,
                minor=self.minor,
                patch=self.patch,
                patches=self.patches,
                partial=self.partial,
            )
        elif level == 'minor':
            return Version(
                major=self.major,
                minor=self.minor,
                patch=None if self.partial else 0,
                partial=self.partial,
            )
        elif level == 'major':
            return Version(
                major=self.major,
                minor=None if self.partial else 0,
                patch=None if self.partial else 0,
                partial=self.partial,
            )
        else:
            raise ValueError("Invalid truncation level `%s`." % level)

    # ------------------------------------------------------------------
    # Representation, hashing and ordering
    # ------------------------------------------------------------------

    def __iter__(self):
        # Unchanged 5-tuple, so `major, minor, patch, prerelease, build = v`
        # keeps working for existing client code; use `v.patches` (or
        # `v.patch1`, ...) to access the extra components.
        return iter((self.major, self.minor, self.patch, self.prerelease, self.build))

    def __str__(self):
        if self._raw_parts is not None:
            # Parsed from a string: preserve the original spelling (leading
            # zeroes included). Slots for absent (partial) components are None.
            version = '.'.join(
                part
                for part, value in zip(
                    self._raw_parts,
                    (self.major, self.minor, self.patch) + self.patches,
                )
                if value is not None
            )
        else:
            version = '%d' % self.major
            if self.minor is not None:
                version = '%s.%d' % (version, self.minor)
            if self.patch is not None:
                version = '%s.%d' % (version, self.patch)
            if self.patches:
                version = '%s.%s' % (version, '.'.join('%d' % p for p in self.patches))

        if self._prefix:
            version = self._prefix + version

        if self.prerelease or (self.partial and self.prerelease == () and self.build is None):
            version = '%s-%s' % (version, '.'.join(self.prerelease))
        if self.build or (self.partial and self.build == ()):
            version = '%s+%s' % (version, '.'.join(self.build))
        if self._flags_raw:
            version = '%s%s' % (version, ''.join(
                '!%s' % (name if value is None else '%s=%s' % (name, value))
                for name, value in self._flags_raw
            ))
        return version

    def __hash__(self):
        # When no extra components are present, keep the exact hash of a plain
        # semantic_version.Version, so objects are interchangeable in dicts.
        key = self._patches_key()
        if key:
            return hash((self.major, self.minor, self.patch, key, self.prerelease, self.build))
        return hash((self.major, self.minor, self.patch, self.prerelease, self.build))

    def _build_precedence_key(self, with_build=False):
        """Build a precedence key.

        The "build" component should only be used when sorting an iterable
        of versions.
        """
        if self.prerelease:
            prerelease_key = tuple(
                NumericIdentifier(part) if part.isdigit() else AlphaIdentifier(part)
                for part in self.prerelease
            )
        else:
            prerelease_key = (
                MaxIdentifier(),
            )

        if not with_build:
            return (
                self.major,
                self.minor,
                self.patch,
                self._patches_key(),
                prerelease_key,
            )

        build_key = tuple(
            NumericIdentifier(part) if part.isdigit() else AlphaIdentifier(part)
            for part in self.build or ()
        )

        return (
            self.major,
            self.minor,
            self.patch,
            self._patches_key(),
            prerelease_key,
            build_key,
        )

    def __cmp__(self, other):
        if not isinstance(other, _BaseVersion):
            return NotImplemented
        if self < other:
            return -1
        elif self > other:
            return 1
        elif self == other:
            return 0
        else:
            return NotImplemented

    def __eq__(self, other):
        if not isinstance(other, _BaseVersion):
            return NotImplemented
        other_patches = other._patches_key() if isinstance(other, Version) else ()
        return (
            self.major == other.major
            and self.minor == other.minor
            and self.patch == other.patch
            and self._patches_key() == other_patches
            and (self.prerelease or ()) == (other.prerelease or ())
            and (self.build or ()) == (other.build or ())
        )

    def __ne__(self, other):
        if not isinstance(other, _BaseVersion):
            return NotImplemented
        return not self.__eq__(other)

    def __lt__(self, other):
        if not isinstance(other, _BaseVersion):
            return NotImplemented
        return _cmp_key(self) < _cmp_key(other)

    def __le__(self, other):
        if not isinstance(other, _BaseVersion):
            return NotImplemented
        return _cmp_key(self) <= _cmp_key(other)

    def __gt__(self, other):
        if not isinstance(other, _BaseVersion):
            return NotImplemented
        return _cmp_key(self) > _cmp_key(other)

    def __ge__(self, other):
        if not isinstance(other, _BaseVersion):
            return NotImplemented
        return _cmp_key(self) >= _cmp_key(other)


def _cmp_key(version):
    """Normalized semver-precedence key for semverex *and* semantic_version objects."""
    if isinstance(version, Version):
        # semverex key: (major, minor, patch, patches_key, prerelease_key[, build_key])
        return (
            version.major,
            version.minor,
            version.patch,
            version._cmp_precedence_key[3],
            version._cmp_precedence_key[4],
        )
    # Plain semantic_version.Version: no extra components.
    return (
        version.major,
        version.minor,
        version.patch,
        (),
        version._cmp_precedence_key[3],
    )


# ----------------------------------------------------------------------
# Requirement specifications
# ----------------------------------------------------------------------

DEFAULT_SYNTAX = 'simple-ex'


@BaseSpec.register_syntax
class ExtendedSimpleSpec(SimpleSpec):
    """semverex version of SimpleSpec: clauses may use extended versions."""

    SYNTAX = 'simple-ex'

    @classmethod
    def parse(cls, expression, syntax=DEFAULT_SYNTAX):
        return BaseSpec.SYNTAXES[syntax](expression)

    class Parser(SimpleSpec.Parser):
        NUMBER = r'\*|0|[1-9][0-9]*'
        EXTRAS = r'(?:\.(?:0|[1-9][0-9]*))*'

        NAIVE_SPEC = re.compile(r"""^
            (?P<op><|<=||=|==|>=|>|!=|\^|~|~=)
            (?P<major>{nb})(?:\.(?P<minor>{nb})(?:\.(?P<patch>{nb}))?)?
            (?P<extras>{extras})?
            (?:-(?P<prerel>[a-z0-9A-Z.-]*))?
            (?:\+(?P<build>[a-z0-9A-Z.-]*))?
            $
            """.format(nb=NUMBER, extras=EXTRAS),
            re.VERBOSE,
        )

        @classmethod
        def parse_block(cls, expr):
            match = cls.NAIVE_SPEC.match(expr)
            if not match:
                raise ValueError("Invalid simple spec component: %r" % expr)
            prefix = match.group('op')
            major_t = match.group('major')
            minor_t = match.group('minor')
            patch_t = match.group('patch')
            extras_t = match.group('extras') or ''
            prerel = match.group('prerel')
            build = match.group('build')
            prefix = cls.PREFIX_ALIASES.get(prefix, prefix)

            major = None if major_t in cls.EMPTY_VALUES else int(major_t)
            minor = None if minor_t in cls.EMPTY_VALUES else int(minor_t)
            patch = None if patch_t in cls.EMPTY_VALUES else int(patch_t)
            patches = tuple(int(x) for x in extras_t.split('.') if x)

            if major is None:  # '*'
                target = Version(major=0, minor=0, patch=0)
                if prefix not in (cls.PREFIX_EQ, cls.PREFIX_GTE):
                    raise ValueError("Invalid simple spec: %r" % expr)
            elif minor is None:
                target = Version(major=major, minor=0, patch=0)
            elif patch is None:
                target = Version(major=major, minor=minor, patch=0)
            else:
                target = Version(
                    major=major,
                    minor=minor,
                    patch=patch,
                    patches=patches,
                    prerelease=prerel.split('.') if prerel else (),
                    build=build.split('.') if build else (),
                )

            if (major is None or minor is None or patch is None) and (prerel or build or patches):
                raise ValueError("Invalid simple spec: %r" % expr)

            if build is not None and prefix not in (cls.PREFIX_EQ, cls.PREFIX_NEQ):
                raise ValueError("Invalid simple spec: %r" % expr)

            if prefix == cls.PREFIX_CARET:
                # Accept anything with the same most-significant digit
                if target.major:
                    high = target.next_major()
                elif target.minor:
                    high = target.next_minor()
                else:
                    high = target.next_patch()
                return Range(Range.OP_GTE, target) & Range(Range.OP_LT, high)

            elif prefix == cls.PREFIX_TILDE:
                assert major is not None
                # Accept any higher patch in the same minor
                # Might go higher if the initial version was a partial
                if minor is None:
                    high = target.next_major()
                else:
                    high = target.next_minor()
                return Range(Range.OP_GTE, target) & Range(Range.OP_LT, high)

            elif prefix == cls.PREFIX_COMPATIBLE:
                assert major is not None
                # ~1 is 1.0.0..2.0.0; ~=2.2 is 2.2.0..3.0.0; ~=1.4.5 is 1.4.5..1.5.0
                if minor is None or patch is None:
                    # We got a partial version
                    high = target.next_major()
                else:
                    high = target.next_minor()
                return Range(Range.OP_GTE, target) & Range(Range.OP_LT, high)

            elif prefix == cls.PREFIX_EQ:
                if major is None:
                    return Range(Range.OP_GTE, target)
                elif minor is None:
                    return Range(Range.OP_GTE, target) & Range(Range.OP_LT, target.next_major())
                elif patch is None:
                    return Range(Range.OP_GTE, target) & Range(Range.OP_LT, target.next_minor())
                elif build == '':
                    return Range(Range.OP_EQ, target, build_policy=Range.BUILD_STRICT)
                else:
                    return Range(Range.OP_EQ, target)

            elif prefix == cls.PREFIX_NEQ:
                assert major is not None
                if minor is None:
                    # !=1.x => <1.0.0 || >=2.0.0
                    return Range(Range.OP_LT, target) | Range(Range.OP_GTE, target.next_major())
                elif patch is None:
                    # !=1.2.x => <1.2.0 || >=1.3.0
                    return Range(Range.OP_LT, target) | Range(Range.OP_GTE, target.next_minor())
                elif prerel == '':
                    # !=1.2.3-
                    return Range(Range.OP_NEQ, target, prerelease_policy=Range.PRERELEASE_ALWAYS)
                elif build == '':
                    # !=1.2.3+ or !=1.2.3-a2+
                    return Range(Range.OP_NEQ, target, build_policy=Range.BUILD_STRICT)
                else:
                    return Range(Range.OP_NEQ, target)

            elif prefix == cls.PREFIX_GT:
                assert major is not None
                if minor is None:
                    # >1.x => >=2.0
                    return Range(Range.OP_GTE, target.next_major())
                elif patch is None:
                    return Range(Range.OP_GTE, target.next_minor())
                else:
                    return Range(Range.OP_GT, target)

            elif prefix == cls.PREFIX_GTE:
                return Range(Range.OP_GTE, target)

            elif prefix == cls.PREFIX_LT:
                assert major is not None
                if prerel == '':
                    # <1.2.3-
                    return Range(Range.OP_LT, target, prerelease_policy=Range.PRERELEASE_ALWAYS)
                return Range(Range.OP_LT, target)

            else:
                assert prefix == cls.PREFIX_LTE
                assert major is not None
                if minor is None:
                    # <=1.x => <2.0
                    return Range(Range.OP_LT, target.next_major())
                elif patch is None:
                    return Range(Range.OP_LT, target.next_minor())
                else:
                    return Range(Range.OP_LTE, target)


@BaseSpec.register_syntax
class ExtendedNpmSpec(NpmSpec):
    """semverex version of NpmSpec: clauses may use extended versions."""

    SYNTAX = 'npm-ex'

    @classmethod
    def parse(cls, expression, syntax='npm-ex'):
        return BaseSpec.SYNTAXES[syntax](expression)

    class Parser(NpmSpec.Parser):
        NUMBER = r'x|X|\*|0|[1-9][0-9]*'
        PART = r'[a-zA-Z0-9.-]*'
        EXTRAS = r'(?:\.(?:0|[1-9][0-9]*))*'

        NPM_SPEC_BLOCK = re.compile(r"""
            ^(?:v)?                     # Strip optional initial v
            (?P<op><|<=|>=|>|=|\^|~|)   # Operator, can be empty
            (?P<major>{nb})(?:\.(?P<minor>{nb})(?:\.(?P<patch>{nb}))?)?
            (?P<extras>{extras})?
            (?:-(?P<prerel>{part}))?    # Optional re-release
            (?:\+(?P<build>{part}))?    # Optional build
            $""".format(nb=NUMBER, part=PART, extras=EXTRAS),
            re.VERBOSE,
        )

        @classmethod
        def parse_simple(cls, simple):
            match = cls.NPM_SPEC_BLOCK.match(simple)

            prefix = match.group('op')
            major_t = match.group('major')
            minor_t = match.group('minor')
            patch_t = match.group('patch')
            extras_t = match.group('extras') or ''
            prerel = match.group('prerel')
            build = match.group('build')

            prefix = cls.PREFIX_ALIASES.get(prefix, prefix)
            major = None if major_t in cls.EMPTY_VALUES else int(major_t)
            minor = None if minor_t in cls.EMPTY_VALUES else int(minor_t)
            patch = None if patch_t in cls.EMPTY_VALUES else int(patch_t)
            patches = tuple(int(x) for x in extras_t.split('.') if x)

            if build is not None and prefix not in [cls.PREFIX_EQ]:
                # Ignore the 'build' part when not comparing to a specific part.
                build = None

            if major is None:  # '*', 'x', 'X'
                target = Version(major=0, minor=0, patch=0)
                if prefix not in [cls.PREFIX_EQ, cls.PREFIX_GTE]:
                    raise ValueError("Invalid expression %r" % simple)
                prefix = cls.PREFIX_GTE
            elif minor is None:
                target = Version(major=major, minor=0, patch=0)
            elif patch is None:
                target = Version(major=major, minor=minor, patch=0)
            else:
                target = Version(
                    major=major,
                    minor=minor,
                    patch=patch,
                    patches=patches,
                    prerelease=prerel.split('.') if prerel else (),
                    build=build.split('.') if build else (),
                )

            if (major is None or minor is None or patch is None) and (prerel or build or patches):
                raise ValueError("Invalid NPM spec: %r" % simple)

            if prefix == cls.PREFIX_CARET:
                if target.major:  # ^1.2.4 => >=1.2.4 <2.0.0 ; ^1.x => >=1.0.0 <2.0.0
                    high = target.truncate().next_major()
                elif target.minor:  # ^0.1.2 => >=0.1.2 <0.2.0
                    high = target.truncate().next_minor()
                elif minor is None:  # ^0.x => >=0.0.0 <1.0.0
                    high = target.truncate().next_major()
                elif patch is None:  # ^0.2.x => >=0.2.0 <0.3.0
                    high = target.truncate().next_minor()
                else:  # ^0.0.1 => >=0.0.1 <0.0.2
                    high = target.truncate().next_patch()
                return [cls.range(Range.OP_GTE, target), cls.range(Range.OP_LT, high)]

            elif prefix == cls.PREFIX_TILDE:
                assert major is not None
                if minor is None:  # ~1.x => >=1.0.0 <2.0.0
                    high = target.next_major()
                else:  # ~1.2.x => >=1.2.0 <1.3.0; ~1.2.3 => >=1.2.3 <1.3.0
                    high = target.next_minor()
                return [cls.range(Range.OP_GTE, target), cls.range(Range.OP_LT, high)]

            elif prefix == cls.PREFIX_EQ:
                if major is None:
                    return [cls.range(Range.OP_GTE, target)]
                elif minor is None:
                    return [cls.range(Range.OP_GTE, target), cls.range(Range.OP_LT, target.next_major())]
                elif patch is None:
                    return [cls.range(Range.OP_GTE, target), cls.range(Range.OP_LT, target.next_minor())]
                else:
                    return [cls.range(Range.OP_EQ, target)]

            elif prefix == cls.PREFIX_GT:
                assert major is not None
                if minor is None:  # >1.x
                    return [cls.range(Range.OP_GTE, target.next_major())]
                elif patch is None:  # >1.2.x => >=1.3.0
                    return [cls.range(Range.OP_GTE, target.next_minor())]
                else:
                    return [cls.range(Range.OP_GT, target)]

            elif prefix == cls.PREFIX_GTE:
                return [cls.range(Range.OP_GTE, target)]

            elif prefix == cls.PREFIX_LT:
                assert major is not None
                return [cls.range(Range.OP_LT, target)]

            else:
                assert prefix == cls.PREFIX_LTE
                assert major is not None
                if minor is None:  # <=1.x => <2.0.0
                    return [cls.range(Range.OP_LT, target.next_major())]
                elif patch is None:  # <=1.2.x => <1.3.0
                    return [cls.range(Range.OP_LT, target.next_minor())]
                else:
                    return [cls.range(Range.OP_LTE, target)]


class ExtendedLegacySpec(ExtendedSimpleSpec):
    """semverex version of the deprecated ``Spec`` class."""

    def __init__(self, *expressions):
        warnings.warn(
            "The Spec() class will be removed in 3.1; use SimpleSpec() instead.",
            PendingDeprecationWarning,
            stacklevel=2,
        )

        if len(expressions) > 1:
            warnings.warn(
                "Passing 2+ arguments to SimpleSpec will be removed in 3.0; concatenate them with ',' instead.",
                DeprecationWarning,
                stacklevel=2,
            )
        expression = ','.join(expressions)
        super(ExtendedLegacySpec, self).__init__(expression)

    @property
    def specs(self):
        return list(self)

    def __iter__(self):
        warnings.warn(
            "Iterating over the components of a SimpleSpec object will be removed in 3.0.",
            DeprecationWarning,
            stacklevel=2,
        )
        try:
            clauses = list(self.clause)
        except TypeError:  # Not an iterable
            clauses = [self.clause]
        for clause in clauses:
            yield SpecItem.from_matcher(clause)


# Upstream-style aliases: `from semverex.base import SimpleSpec, NpmSpec, Spec`.
SimpleSpec = ExtendedSimpleSpec
NpmSpec = ExtendedNpmSpec
Spec = ExtendedLegacySpec


def compare(v1, v2):
    return Version(v1).__cmp__(Version(v2))


def match(spec, version):
    return Spec(spec).match(Version(version))


def validate(version_string):
    """Validates a version string againt the semverex version grammar."""
    try:
        Version.parse(version_string)
        return True
    except ValueError:
        return False
