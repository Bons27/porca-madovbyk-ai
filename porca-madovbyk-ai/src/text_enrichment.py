"""Idempotent MV/FIA text enrichment for the Streamlit dashboard."""

import re

from .player_context_v3 import player_suffix


def annotate_text(text, context):
    """Add MV/FIA next to known players without duplicating explicit data.

    Explainability reports may already contain ``Name — MV ... | FIA ...``.
    The old plain ``str.replace`` annotator would add MV/FIA a second time.
    """

    result = str(text or "")

    names = sorted(
        (
            item["name"]
            for item in context.values()
            if item.get("name")
        ),
        key=len,
        reverse=True,
    )

    for name in names:
        if name not in result:
            continue

        pattern = re.compile(re.escape(name))

        def replacement(match):
            tail = match.string[match.end():match.end() + 100]

            # Già annotato dalla dashboard.
            if re.match(r"\s*\[MV\b", tail):
                return match.group(0)

            # Riga explainability che espone già MV + FIA.
            if re.match(r"\s*[—-]\s*MV\b", tail):
                return match.group(0)

            return (
                f"{match.group(0)} "
                f"[{player_suffix(context, name)}]"
            )

        result = pattern.sub(replacement, result)

    return result
