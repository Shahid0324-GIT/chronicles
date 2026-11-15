"""Conservative literal argument binding, independent of any model's support verdict."""

import re
from collections.abc import Mapping
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class AtomicSupport:
    supported: bool
    reason: str
    statement: str = ""
    joint: bool = False


def atomic_support(atom: Mapping[str, Any], quotations: list[str]) -> AtomicSupport:
    if atom.get("occurrence_status", "actual") != "actual":
        return AtomicSupport(False, "Nonactual assertions remain unresolved.")
    if atom.get("classification", "ESTABLISHED_CANON") != "ESTABLISHED_CANON":
        return AtomicSupport(False, "Interpretation is not established canon.")
    subject, predicate, target = (
        str(atom.get(k, "")).strip() for k in ("subject", "predicate", "object")
    )
    if not all((subject, predicate, target)) or subject.casefold() == target.casefold():
        return AtomicSupport(False, "Missing or self-referential atomic arguments.")
    if re.search(
        r"\bbecause\b|\bso that\b|\bin order to\b|ので|ために", predicate + " " + target, re.I
    ):
        return AtomicSupport(False, "Compound motive/causal assertions require separate atoms.")
    if not re.match(
        r"(?:helped|assisted|rescued|saved|invented|created|developed|taught|trained|joined|"
        r"met|protected|defeated|consulted|became|started|worked|is|was|are|were|belongs|"
        r"knew|knows|caused|enabled|has|had)\b|助け|救っ|発明|協力|出会|同行|である|だった",
        predicate,
        re.I,
    ):
        return AtomicSupport(False, "Predicate requires further semantic investigation.")
    a, p, b = map(re.escape, (subject, predicate, target))
    directed = (
        rf"(?<!\w){a}\s+(?:(?:has|had)\s+)?{p}\s+(?:(?:a|an|the)\s+)?[\"“‘']?{b}[\"”’']?(?!\w)"
    )
    japanese = rf"{a}(?:は|が){b}(?:を|に){p}"
    joint = rf"(?<!\w)(?:{a}\s+and\s+{b}|{b}\s+and\s+{a})\s+{p}(?!\w)"
    for quote in quotations:
        if re.search(
            r"\b(not|never|might|could|would|perhaps|probably|if|rumou?r|reportedly)\b"
            r"|\bI (?:think|feel|am writing|was writing|am working on|was working on)\b"
            r"|もし|かもしれ|らしい|なかった",
            quote,
            re.I,
        ):
            continue
        for pattern, paired in ((directed, False), (japanese, False), (joint, True)):
            match = re.search(pattern, quote, re.I)
            if match:
                return AtomicSupport(
                    True, "Exact atomic subject/predicate/object binding.", match.group(), paired
                )
    return AtomicSupport(
        False, "Exact subject, predicate, object and direction are not established."
    )


def split_compound_assertion(statement: str) -> list[dict[str, str]]:
    """Expose an assistance assertion, motive assertion and causal link separately."""
    parts = re.split(r"\s+because\s+", statement.rstrip("."), maxsplit=1, flags=re.I)
    if len(parts) == 1:
        return [{"kind": "assertion", "statement": statement}]
    return [
        {"kind": "assertion", "statement": parts[0]},
        {"kind": "assertion", "statement": parts[1]},
        {"kind": "causality", "statement": statement},
    ]


def atomic_payload_support(payload: Mapping[str, Any], quotations: list[str]) -> AtomicSupport:
    atom = payload.get("atomic")
    if not atom:
        return AtomicSupport(True, "Legacy claim uses the existing verification path.")
    if not isinstance(atom, Mapping) or any(
        not isinstance(atom.get(k), str) or not atom[k]
        for k in ("subject", "subject_type", "predicate", "object", "object_type", "event_name")
    ):
        return AtomicSupport(False, "Malformed atomic binding is not evidence.")
    proof = atomic_support(atom, quotations)
    if not proof.supported:
        return proof
    if payload.get("description") != proof.statement:
        return AtomicSupport(False, "Payload asserts more than its bound atomic statement.")
    if "name" in payload:
        expected = {
            atom["subject"]: atom["subject_type"],
            atom["object"]: atom["object_type"],
            atom["event_name"]: "EVENT",
        }
        if expected.get(payload["name"]) != payload["type"]:
            return AtomicSupport(False, "Entity is not a typed argument of this assertion.")
    elif payload.get("type") == "RELATED_TO":
        if (payload.get("source_name"), payload.get("target_name")) != (
            atom["subject"],
            atom["object"],
        ):
            return AtomicSupport(False, "Relationship direction differs from the atomic assertion.")
    elif payload.get("type") == "PARTICIPATED_IN":
        people = {atom[k] for k in ("subject", "object") if atom[k + "_type"] == "CHARACTER"}
        if (
            payload.get("source_name") not in people
            or payload.get("target_name") != atom["event_name"]
        ):
            return AtomicSupport(False, "Participation endpoints are not the bound actual event.")
    else:
        return AtomicSupport(False, "Relationship predicate is not licensed by this atom.")
    return proof
