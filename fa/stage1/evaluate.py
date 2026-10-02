"""Deterministic Stage 1 evaluation from filled answers → process_outcome.

Heuristics (documented; no LLM required for v1):
- null / empty string / whitespace-only = unanswered
- hand-wave for G1-M1–M4: unanswered OR length < MIN_SUBSTANTIVE_CHARS
  after strip, OR matches known non-answers
- G1-M7: unanswered, empty list, or no substantive falsifier text → TOO_HARD
- G1-M8: unanswered OR explicit unwilling (no/false/unwilling/…) → TOO_HARD
- Gate 0 ≠ operating → TOO_HARD (OOS)
- Missing G2-M2 on quality path → STOP_NO_THESIS
- Empty G2-M7 kill-shots → REVIEW_REQUIRED
- Ban-list one-liner → REVIEW_REQUIRED
- Incomplete other MUST → REVIEW_REQUIRED
- All MUST + thesis OK → PROCEED
SHOULD/LEARNABLE = warnings only (never alone force stop).
"""
from __future__ import annotations

from typing import Any

from ..ids import utc_now
from ..models import QuestionAnswer, Stage1Report, Stage1Thesis
from .questions import (
    GATE0_ALLOWED,
    GATE0_MUST,
    GATE1_LEARNABLE,
    GATE1_MUST,
    GATE1_SHOULD,
    GATE2_MUST,
    GATE2_SHOULD,
    G1_TOO_HARD_CORE,
    THESIS_ONE_SENTENCE_BAN_LIST,
)

MIN_SUBSTANTIVE_CHARS = 12

_HANDWAVE_PHRASES = frozenset(
    {
        "idk",
        "n/a",
        "na",
        "tbd",
        "unknown",
        "not sure",
        "unsure",
        "?",
        "-",
        "—",
        "todo",
        "handwave",
        "hand-wave",
        "see above",
        "etc",
        "whatever",
    }
)

_UNWILLING_TOKENS = frozenset(
    {
        "no",
        "n",
        "false",
        "unwilling",
        "cannot",
        "can't",
        "not willing",
        "not able",
        "nope",
        "0",
    }
)


def _as_text(value: Any) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "yes" if value else "no"
    if isinstance(value, (list, tuple)):
        parts = [_as_text(x) for x in value]
        return "; ".join(p for p in parts if p)
    return str(value).strip()


def _is_unanswered(value: Any) -> bool:
    if value is None:
        return True
    if isinstance(value, (list, tuple)):
        return len(value) == 0 or all(_is_unanswered(x) for x in value)
    if isinstance(value, bool):
        return False
    return _as_text(value) == ""


def _is_handwave(value: Any) -> bool:
    """Empty or trivially non-substantive answer."""
    if _is_unanswered(value):
        return True
    text = _as_text(value).lower()
    if text in _HANDWAVE_PHRASES:
        return True
    # strip punctuation for phrase check
    compact = "".join(ch for ch in text if ch.isalnum() or ch.isspace()).strip()
    if compact in _HANDWAVE_PHRASES:
        return True
    if len(text) < MIN_SUBSTANTIVE_CHARS:
        return True
    return False


def _is_unwilling_m8(value: Any) -> bool:
    if _is_unanswered(value):
        return True
    if isinstance(value, bool):
        return value is False
    text = _as_text(value).lower()
    if text in _UNWILLING_TOKENS:
        return True
    for tok in ("not willing", "not able", "unwilling", "cannot follow", "no time"):
        if tok in text:
            return True
    # Affirmative short answers OK
    if text in {"yes", "y", "true", "willing", "able", "1"}:
        return False
    # Longer affirmative prose counts as willing if not unwilling tokens
    return False


def _ban_list_hits(one_sentence: str) -> list[str]:
    low = (one_sentence or "").lower()
    hits = []
    for phrase in THESIS_ONE_SENTENCE_BAN_LIST:
        if phrase in low:
            hits.append(phrase)
    return hits


def _get_answer(payload: dict[str, Any], qid: str) -> Any:
    """Answers may live under answers{}, top-level qid, or thesis fields."""
    answers = payload.get("answers") or {}
    if qid in answers:
        return answers[qid]
    if qid in payload:
        return payload[qid]
    return None


def _thesis_from_payload(payload: dict[str, Any]) -> Stage1Thesis:
    raw = payload.get("thesis") or {}
    if not isinstance(raw, dict):
        raw = {}
    monitors = raw.get("monitors") or payload.get("monitors") or []
    if isinstance(monitors, str):
        monitors = [monitors] if monitors.strip() else []
    fin = raw.get("financial_validation_later") or []
    if isinstance(fin, str):
        fin = [fin] if fin.strip() else []
    return Stage1Thesis(
        one_sentence=_as_text(raw.get("one_sentence") or payload.get("one_sentence")),
        customer_value_job=_as_text(raw.get("customer_value_job")),
        customer_value_why=_as_text(raw.get("customer_value_why")),
        advantage_type=_as_text(raw.get("advantage_type")),
        advantage_persist=_as_text(raw.get("advantage_persist")),
        advantage_evidence=_as_text(raw.get("advantage_evidence")),
        runway_what=_as_text(raw.get("runway_what")),
        runway_confidence=_as_text(raw.get("runway_confidence")),
        reinvestment_where=_as_text(raw.get("reinvestment_where")),
        capital_intensity=_as_text(raw.get("capital_intensity")),
        margins_note=_as_text(raw.get("margins_note")),
        management_worry=_as_text(raw.get("management_worry")),
        kill_shot_primary=_as_text(raw.get("kill_shot_primary")),
        kill_shot_secondary=_as_text(raw.get("kill_shot_secondary")),
        monitors=list(monitors),
        financial_validation_later=list(fin),
        language=_as_text(raw.get("language") or "EN") or "EN",
    )


def _qa(
    qid: str,
    qtext: str,
    value: Any,
    *,
    must: bool,
    status_override: str | None = None,
    summary_override: str | None = None,
) -> QuestionAnswer:
    if status_override:
        status = status_override
        summary = summary_override or _as_text(value) or "(empty)"
    elif _is_unanswered(value):
        status = "missing"
        summary = "(unanswered)"
    elif must and qid in G1_TOO_HARD_CORE and _is_handwave(value):
        status = "partial"
        summary = f"(hand-wave / too thin) {_as_text(value)}"
    else:
        status = "answered"
        summary = _as_text(value)
    return QuestionAnswer(
        question_id=qid,
        question=qtext,
        status=status,  # type: ignore[arg-type]
        answer_summary=summary,
        evidence=[],
        must=must,
    )


def evaluate_stage1(ticker: str, payload: dict[str, Any] | None = None) -> Stage1Report:
    """
    Evaluate filled Stage 1 answers → process_outcome.

    payload keys:
      gate0_class | answers{qid: value} | thesis{...} | one_sentence
      Optional direct qid keys.
    """
    ticker = (ticker or "").upper()
    payload = payload or {}
    thesis = _thesis_from_payload(payload)

    # Gate 0
    gate0_raw = payload.get("gate0_class") or _get_answer(payload, "G0-M1")
    gate0 = _as_text(gate0_raw).lower().replace(" ", "_")
    if gate0 in {"fi", "financial", "bank", "financial_institution"}:
        gate0 = "financial_institution"
    elif gate0 in {"commodity", "commodities", "emtia"}:
        gate0 = "commodity"
    elif gate0 in {"operating", "opco", "operating_company"}:
        gate0 = "operating"

    answers_out: list[QuestionAnswer] = []
    warnings: list[str] = []
    block_reasons: list[str] = []

    # G0-M1
    if gate0 not in GATE0_ALLOWED:
        answers_out.append(
            _qa(
                "G0-M1",
                GATE0_MUST[0][1],
                gate0_raw,
                must=True,
                status_override="missing" if _is_unanswered(gate0_raw) else "partial",
                summary_override=_as_text(gate0_raw) or "(unanswered)",
            )
        )
    else:
        answers_out.append(_qa("G0-M1", GATE0_MUST[0][1], gate0, must=True))

    # Collect Gate 1/2 answer values (G2-M2/M7 may come from thesis)
    def resolve(qid: str) -> Any:
        v = _get_answer(payload, qid)
        if not _is_unanswered(v):
            return v
        # Thesis bridges for common Gate 2 fields
        if qid == "G2-M1":
            return thesis.customer_value_job or thesis.customer_value_why or None
        if qid == "G2-M2":
            return thesis.advantage_type or None
        if qid == "G2-M3":
            return thesis.advantage_persist or None
        if qid == "G2-M4":
            return thesis.runway_what or None
        if qid == "G2-M5":
            return thesis.reinvestment_where or None
        if qid == "G2-M6":
            return thesis.capital_intensity or thesis.margins_note or None
        if qid == "G2-M7":
            kills = [thesis.kill_shot_primary, thesis.kill_shot_secondary]
            kills = [k for k in kills if k]
            return kills or None
        if qid == "G2-M8":
            return thesis.financial_validation_later or None
        return v

    for qid, qtext in GATE1_MUST:
        answers_out.append(_qa(qid, qtext, resolve(qid), must=True))
    for qid, qtext in GATE1_SHOULD:
        qa = _qa(qid, qtext, resolve(qid), must=False)
        answers_out.append(qa)
        if qa.status == "missing":
            warnings.append(f"SHOULD unanswered: {qid}")
    for qid, qtext in GATE1_LEARNABLE:
        qa = _qa(qid, qtext, resolve(qid), must=False)
        answers_out.append(qa)

    for qid, qtext in GATE2_MUST:
        answers_out.append(_qa(qid, qtext, resolve(qid), must=True))
    for qid, qtext in GATE2_SHOULD:
        qa = _qa(qid, qtext, resolve(qid), must=False)
        answers_out.append(qa)
        if qa.status == "missing":
            warnings.append(f"SHOULD unanswered: {qid}")


    # --- Outcome ladder ---
    process_outcome: str
    enough_why: str
    narrative: str

    # 1) Gate 0
    if gate0 not in GATE0_ALLOWED:
        process_outcome = "REVIEW_REQUIRED"
        enough_why = "Gate 0 unit of analysis unanswered or invalid"
        block_reasons.append(enough_why)
        narrative = "REVIEW REQUIRED — Gate 0 incomplete"
    elif gate0 != "operating":
        process_outcome = "TOO_HARD"
        enough_why = (
            f"Gate 0 class is '{gate0}' — OOS for v1 OpCo Stage 1→2 path "
            "(FI/commodity separate module later)"
        )
        block_reasons.append(enough_why)
        narrative = "TOO HARD — unit of analysis out of scope for v1 OpCo path"
    else:
        process_outcome = ""  # continue
        enough_why = ""
        narrative = ""

    if not process_outcome:
        # 2) Gate 1 TOO_HARD: M1–M4 handwave, M7 falsifiers, M8 unwilling
        m1_m4_bad = []
        for qid in ("G1-M1", "G1-M2", "G1-M3", "G1-M4"):
            if _is_handwave(resolve(qid)):
                m1_m4_bad.append(qid)
        m7_val = resolve("G1-M7")
        m7_bad = _is_handwave(m7_val) if not isinstance(m7_val, (list, tuple)) else (
            _is_unanswered(m7_val) or all(_is_handwave(x) for x in m7_val)
        )
        m8_bad = _is_unwilling_m8(resolve("G1-M8"))

        if m1_m4_bad:
            process_outcome = "TOO_HARD"
            enough_why = f"Cannot answer {m1_m4_bad} without hand-waving (G1-M1–M4)"
            block_reasons.append(enough_why)
            narrative = "TOO HARD — circle of competence incomplete (core explain)"
        elif m7_bad:
            process_outcome = "TOO_HARD"
            enough_why = "Missing falsifiers (G1-M7) — cannot update/abandon thesis on facts"
            block_reasons.append(enough_why)
            narrative = "TOO HARD — no falsifiers"
        elif m8_bad:
            process_outcome = "TOO_HARD"
            enough_why = "G1-M8 unanswered or unwilling/unable to monitor within time budget"
            block_reasons.append(enough_why)
            narrative = "TOO HARD — monitoring commitment absent"

    if not process_outcome:
        # Ban list on one-sentence
        hits = _ban_list_hits(thesis.one_sentence)
        if hits:
            process_outcome = "REVIEW_REQUIRED"
            enough_why = f"Thesis one-sentence hits ban list: {hits}"
            block_reasons.append(enough_why)
            narrative = "REVIEW REQUIRED — ban-list one-liner"
        elif _is_unanswered(thesis.one_sentence):
            # one-sentence required for thesis OK
            process_outcome = "REVIEW_REQUIRED"
            enough_why = "Thesis one-sentence empty"
            block_reasons.append(enough_why)
            narrative = "REVIEW REQUIRED — thesis one-sentence missing"

    if not process_outcome:
        # G2-M2 missing → STOP_NO_THESIS (quality path)
        if _is_handwave(resolve("G2-M2")):
            process_outcome = "STOP_NO_THESIS"
            enough_why = (
                "No durable-advantage hypothesis (G2-M2) — v1 quality/moat path "
                "does not rescue with cheapness"
            )
            block_reasons.append(enough_why)
            narrative = "STOP — no ownership thesis (no durable advantage hypothesis)"

    if not process_outcome:
        # Empty kill-shots G2-M7
        if _is_handwave(resolve("G2-M7")):
            process_outcome = "REVIEW_REQUIRED"
            enough_why = "Empty kill-shots (G2-M7) — how the thesis fails must be named"
            block_reasons.append(enough_why)
            narrative = "REVIEW REQUIRED — kill-shots empty"

    if not process_outcome:
        # Other incomplete MUST (G1-M5/M6, remaining G2)
        incomplete = []
        for qid, _ in GATE1_MUST + GATE2_MUST:
            if qid in G1_TOO_HARD_CORE or qid in {"G1-M7", "G1-M8", "G2-M2", "G2-M7"}:
                continue  # already handled
            if qid == "G0-M1":
                continue
            val = resolve(qid)
            # G2 remaining: handwave counts incomplete
            if qid.startswith("G2-") and _is_handwave(val):
                incomplete.append(qid)
            elif qid.startswith("G1-") and _is_unanswered(val):
                incomplete.append(qid)
        if incomplete:
            process_outcome = "REVIEW_REQUIRED"
            enough_why = f"Incomplete MUST answers: {incomplete}"
            block_reasons.append(enough_why)
            narrative = "REVIEW REQUIRED — incomplete MUST spine"

    if not process_outcome:
        process_outcome = "PROCEED"
        enough_why = "All Gate 0–2 MUST answered; thesis one-sentence OK; quality-path advantage present"
        narrative = "Pass to financial stages (Stage 2+)"
        block_reasons = []

    ban_hits = _ban_list_hits(thesis.one_sentence)
    block_stage2 = process_outcome != "PROCEED"

    return Stage1Report(
        ticker=ticker,
        date=utc_now(),
        gate0_class=gate0 if gate0 in GATE0_ALLOWED else _as_text(gate0_raw) or "unanswered",
        process_outcome=process_outcome,  # type: ignore[arg-type]
        narrative_verdict=narrative,
        enough_to_proceed="Yes" if process_outcome == "PROCEED" else "No",
        enough_why=enough_why,
        question_answers=answers_out,
        thesis=thesis,
        warnings=warnings,
        block_reasons=block_reasons,
        ban_list_hits=ban_hits,
        block_stage2=block_stage2,
    )
