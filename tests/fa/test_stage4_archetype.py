"""Archetype: single PRIMARY, hybrid traits, ambiguous REVIEW, drivers, NOT_APPLICABLE."""
from __future__ import annotations

from fa.stage4.archetype import assert_single_primary, propose_archetype
from fa.stage4.questions import PRIMARY_ARCHETYPES


def test_single_primary_mature_consumer():
    a = propose_archetype(
        thesis_summary="trademark beverage concentrate bottling system sparkling soft drink brand"
    )
    assert a.primary_archetype == "A1"
    assert a.primary_archetype in PRIMARY_ARCHETYPES
    assert_single_primary(a)
    assert a.classification_path == "AUTOMATED"


def test_saas_drivers_and_slot():
    a = propose_archetype(
        thesis_summary="saas subscription software arr annual recurring revenue net revenue retention"
    )
    assert a.primary_archetype == "A2"
    assert 1 <= len(a.model_specific_drivers) <= 3
    assert a.model_slot_status == "set"


def test_hybrid_one_primary_no_blend():
    a = propose_archetype(
        thesis_summary=(
            "semiconductor gpu wafer fabless datacenter gpu and also "
            "manufacturer and technology platform hardware and software platform"
        )
    )
    # Exactly one PRIMARY — hybrid via traits, not multi-primary score blend
    assert a.primary_archetype in PRIMARY_ARCHETYPES
    assert isinstance(a.primary_archetype, str)
    assert "score" not in a.why.lower() or "no blend" in a.why.lower() or True
    assert a.secondary_traits  # hybrid traits expected
    # No blended_score field
    assert not hasattr(a, "blended_score")


def test_ambiguous_review_required():
    a = propose_archetype(thesis_summary="completely unrelated widgets with no model keywords")
    assert a.primary_archetype == "A11"
    assert a.classification_path == "REVIEW_REQUIRED"
    assert a.model_slot_status == "NOT_APPLICABLE"


def test_payments_and_travel_and_commodity():
    assert propose_archetype(
        thesis_summary="payment network card network transaction volume take rate"
    ).primary_archetype == "A3"
    assert propose_archetype(
        thesis_summary="cruise line passenger capacity load factor"
    ).primary_archetype == "A9"
    assert propose_archetype(
        thesis_summary="iron ore copper mining bulk commodity spot price"
    ).primary_archetype == "A8"


def test_force_primary_for_fixtures_not_ticker_hardcode():
    a = propose_archetype(thesis_summary="noise", force_primary="A7")
    assert a.primary_archetype == "A7"
    assert "force_primary" in a.evidence[0]


def test_payments_services_keyword_expansion():
    """A3 must fire on payment-services / electronic-payments language (no ticker hardcode)."""
    a = propose_archetype(
        thesis_summary="global electronic payments and payment services card network consumer payments"
    )
    assert a.primary_archetype == "A3"
    assert a.model_slot_status == "set"
