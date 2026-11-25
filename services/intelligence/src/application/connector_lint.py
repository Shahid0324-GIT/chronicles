"""Deterministic check for temporal and causal connectors in generated arc prose.

Connectives sit between claims, so claim-by-claim entailment never judges them.
A connector is allowed only when the cited sourced text uses it too, or when the
cited facts are joined by an explicit accepted ``PRECEDES``/``CAUSED``/``ENABLED``
relationship. Adjacency in the draft or the archive never licenses one.
"""

import re
from collections.abc import Iterable

LINKING_TYPES = frozenset({"PRECEDES", "CAUSED", "ENABLED"})

CONNECTOR = re.compile(
    r"\b(later|then|while|meanwhile|after|afterwards?|before|during|when|finally|"
    r"subsequently|soon|eventually|immediately|until|because|therefore|consequently|"
    r"thus|hence|resulted in|led to|setting the stage|as a result)\b",
    re.I,
)


def connectors(text: str) -> list[str]:
    return list(dict.fromkeys(m.group(1).casefold() for m in CONNECTOR.finditer(text)))


def unlicensed_connectors(claim: str, evidence: Iterable[str], linked: bool = False) -> list[str]:
    """Connectors in ``claim`` that neither the cited text nor an explicit link supports."""
    if linked:
        return []
    sourced = " ".join(evidence).casefold()
    return [c for c in connectors(claim) if not re.search(rf"\b{re.escape(c)}\b", sourced)]
