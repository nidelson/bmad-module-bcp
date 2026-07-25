"""bcp-rule.yaml is CI&T's framework, released under MIT in May 2026.

Until then the framework circulated under CC BY-NC-ND 4.0, and the
NoDerivatives term made this rule *legally* immutable. Since the
republication (https://github.com/flow-ciandt/bcp-agent) module code and
embedded rule share the same license, and immutability became a **project
decision** instead of a legal constraint: a BCP score is only comparable
across teams when the ruler is identical.

These tests remain a structural tripwire — they fail CI if the canonical
ruler is altered (only the editorial `hints` block, if present, is mutable
and is deliberately not asserted here). What changed is the reason to keep
them, not their value: an accidental edit or a bad merge still ships
numbers that look like BCP and are not.

This is a conformance guard, not a transcription audit: it pins the shape
the deterministic engine and the contract depend on (10 elements, frozen
slugs, the Fibonacci scale, the attribution block).
"""
from __future__ import annotations

FROZEN_SLUGS = {
    "business_rules", "interface_elements", "roles_permissions",
    "solution_variabilities", "boundaries", "domain_entities",
    "new_domain_entities", "background_processes", "notifications",
    "audits",
}
ALWAYS_THERE = {
    "roles_permissions", "solution_variabilities", "boundaries",
    "domain_entities",
}
FIB = {"XS": 1, "S": 2, "M": 3, "L": 5, "XL": 8}


def test_license_block_is_mit(rule):
    lic = rule["license"]
    assert lic["spdx"] == "MIT"
    assert lic["creator"] == "CI&T"
    assert "flow-ciandt/bcp-agent" in lic["source"]
    assert "MIT" in lic["name"]
    assert lic["attribution"].strip(), "attribution string must not be empty"


def test_previous_license_is_recorded(rule):
    """The CC BY-NC-ND provenance stays on record: installations scored
    before May 2026 were produced under it, and the audit trail should not
    silently lose that."""
    assert rule["license"].get("previous_license") == "CC-BY-NC-ND-4.0"


def test_fibonacci_scale_is_verbatim(rule):
    assert rule["sizes"] == FIB, (
        "the size→points scale is part of the canonical ruler — altering "
        "it breaks comparability with every other installation"
    )


def test_exactly_ten_elements_with_frozen_slugs(rule):
    elements = rule["elements"]
    assert len(elements) == 10, f"expected 10 elements, got {len(elements)}"
    slugs = {e["slug"] for e in elements}
    assert slugs == FROZEN_SLUGS, (
        f"element slug set changed: {sorted(slugs)} — the ruler has a "
        f"fixed 10-element taxonomy"
    )


def test_always_there_flag_matches_canonical_bracket(rule):
    flagged = {e["slug"] for e in rule["elements"] if e.get("always_there")}
    assert flagged == ALWAYS_THERE, (
        f"`always_there` set changed: {sorted(flagged)} — the canonical "
        f"ruler brackets exactly these four under 'ALWAYS THERE'"
    )


def test_every_element_has_all_five_size_cells(rule):
    """Every element exposes XS/S/M/L/XL. Blank cells on the ruler are
    `null`, never missing keys — the engine and contract assume the full
    grid."""
    for e in rule["elements"]:
        cells = e["descriptors"]
        assert set(cells) == set(FIB), (
            f"element '{e['slug']}' size keys {sorted(cells)} != "
            f"{sorted(FIB)}"
        )
        assert e.get("definition", "").strip(), (
            f"element '{e['slug']}' missing definition"
        )


def test_rule_version_pinned(rule):
    assert str(rule["rule_version"]) == "1.0"
    assert str(rule["schema_version"]) == "1.0"
