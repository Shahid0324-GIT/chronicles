"""Conservative source-level rejection of editorial frames and reversed active roles."""

import re
from typing import Any


def event_support_issue(payload: dict[str, Any]) -> str | None:
    event = payload.get("event") or {}
    text = payload.get("description", "")
    if re.search(
        r"\b(?:this (?:moment|scene|chapter)|the (?:chapter|scene|story)) "
        r"(?:cements?|symbolizes?|emphasizes?|illustrates?|showcases?)\b",
        text,
        re.I,
    ):
        return "editorial_description_not_occurrence"
    trigger = event.get("trigger", "")
    if not re.match(r"^(?:refus\w*|accept\w*|attack\w*|sav\w*|rescu\w*)\b", trigger, re.I):
        return None
    index = text.find(trigger)
    if index < 0:
        return None
    before, after = text[:index].casefold(), text[index + len(trigger) :].casefold()
    roles = event.get("participant_roles", {})
    actors = [n.casefold().split()[-1] for n, role in roles.items() if role == "actor"]
    recipients = [n.casefold().split()[-1] for n, role in roles.items() if role == "recipient"]
    if actors and all(n not in before for n in actors) and any(n in before for n in recipients):
        # This rejects a conflicting active-clause assignment, never swaps the roles.
        if any(n in after or n in trigger.casefold() for n in actors):
            return "active_clause_roles_reversed"
    return None
