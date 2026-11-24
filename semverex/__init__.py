# -*- coding: utf-8 -*-
# Copyright (c) The semverex project
# This code is distributed under the two-clause BSD License.

"""semverex: Extended Semantic Versioning.

A drop-in extension of `semantic_version
<https://github.com/rbarrois/python-semanticversion>`_ that additionally
accepts version strings with extra numeric components after the patch level
(``1.2.3.4``, ``1.2.3.4.5-dbg.1``, ...).

Usage: replace ``import semantic_version`` with ``import semverex``; the
public API (``Version``, ``SimpleSpec``, ``NpmSpec``, ``Spec``, ``SpecItem``,
``compare``, ``match``, ``validate``) behaves exactly like upstream for
official SemVer strings, and additionally accepts the extended forms.
"""

import semantic_version

from .base import (
    DEFAULT_SYNTAX,
    NpmSpec,
    SimpleSpec,
    Spec,
    SpecItem,
    Version,
    compare,
    match,
    validate,
)


__author__ = "semverex project (based on python-semanticversion by Raphaël Barrois)"
try:
    # Python 3.8+
    from importlib.metadata import version as _metadata_version

    __version__ = _metadata_version("semverex")
except Exception:  # pragma: no cover - fallback when not installed as a package
    __version__ = "0.1.0"


__all__ = [
    "DEFAULT_SYNTAX",
    "NpmSpec",
    "SimpleSpec",
    "Spec",
    "SpecItem",
    "Version",
    "compare",
    "match",
    "validate",
    "semantic_version",
]
