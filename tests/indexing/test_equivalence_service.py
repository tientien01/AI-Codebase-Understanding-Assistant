from __future__ import annotations

import hashlib

from pydantic import ValidationError
import pytest

from app.services.indexing.equivalence_service import (
    REQUIRED_FAMILIES,
    CanonicalEntry,
    CanonicalFamily,
    CanonicalFamilySnapshot,
    EquivalenceInputError,
    EquivalenceService,
    EquivalenceSnapshot,
    MismatchKind,
)


def _sha(value: str) -> str:
    return hashlib.sha256(value.encode()).hexdigest()


def _snapshot(*, changed_family: CanonicalFamily | None = None, reverse=False, **updates):
    families = []
    for family in REQUIRED_FAMILIES:
        digest = _sha(family.value)
        if family is changed_family:
            digest = _sha(f"{family.value}:changed")
        families.append(
            CanonicalFamilySnapshot(
                family=family,
                entries=(
                    CanonicalEntry(
                        canonical_key=f"{family.value}:v1:item",
                        sha256=digest,
                    ),
                ),
            )
        )
    if reverse:
        families.reverse()
    values = {
        "repository_id": "repo_one",
        "target_snapshot_sha256": "a" * 64,
        "configuration_sha256": "b" * 64,
        "families": tuple(families),
    }
    values.update(updates)
    return EquivalenceSnapshot(**values)


def test_equivalent_snapshots_ignore_declaration_order_and_serialize_canonically() -> None:
    full = _snapshot()
    incremental = _snapshot(reverse=True)
    result = EquivalenceService(max_diagnostics=10).compare(full, incremental)
    assert result.equivalent is True
    assert result.compared_entries == len(REQUIRED_FAMILIES)
    assert result.mismatches == ()
    assert full.canonical_bytes() == incremental.canonical_bytes()


@pytest.mark.parametrize("family", REQUIRED_FAMILIES)
def test_digest_mismatch_in_every_mandatory_family_fails(family) -> None:
    result = EquivalenceService(max_diagnostics=10).compare(
        _snapshot(), _snapshot(changed_family=family)
    )
    assert result.equivalent is False
    assert result.total_mismatches == 1
    assert result.mismatches[0].family is family
    assert result.mismatches[0].kind is MismatchKind.DIGEST_MISMATCH


def test_missing_entries_and_diagnostics_are_stable_and_bounded() -> None:
    full = _snapshot()
    incremental_families = []
    for family in full.families:
        entries = family.entries
        if family.family is CanonicalFamily.FACTS:
            entries = (
                CanonicalEntry(canonical_key="facts:v1:extra", sha256=_sha("extra")),
            )
        incremental_families.append(
            CanonicalFamilySnapshot(family=family.family, entries=entries)
        )
    incremental = full.model_copy(update={"families": tuple(incremental_families)})
    result = EquivalenceService(max_diagnostics=1).compare(full, incremental)
    assert result.total_mismatches == 2
    assert len(result.mismatches) == 1
    assert result.diagnostics_truncated is True
    assert result.mismatches[0].canonical_key == "facts:v1:extra"
    assert result.mismatches[0].kind is MismatchKind.MISSING_FROM_FULL


def test_equivalence_rejects_different_target_identity_or_incomplete_families() -> None:
    with pytest.raises(EquivalenceInputError, match="same target"):
        EquivalenceService(max_diagnostics=10).compare(
            _snapshot(), _snapshot(target_snapshot_sha256="c" * 64)
        )
    with pytest.raises(ValidationError, match="every family"):
        _snapshot(families=_snapshot().families[:-1])
    with pytest.raises(ValidationError, match="unique"):
        CanonicalFamilySnapshot(
            family=CanonicalFamily.FACTS,
            entries=(
                CanonicalEntry(canonical_key="fact:v1:a", sha256="a" * 64),
                CanonicalEntry(canonical_key="fact:v1:a", sha256="b" * 64),
            ),
        )
    with pytest.raises(ValueError, match="positive"):
        EquivalenceService(max_diagnostics=0)
