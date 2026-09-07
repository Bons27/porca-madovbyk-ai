"""Idempotent MV/FIA text enrichment for the Streamlit dashboard."""

import re

from .player_context_v3 import player_suffix


def annotate_text(text, context):
    """Add MV/FIA next to known players without duplicating explicit data.

    A single longest-first regex pass avoids corrupting overlapping names such
    as ``Castro`` / ``Castro S.``. Explainability rows that already expose
    ``Name — MV ... | FIA ...`` are left untouched.
    """

    result = str(text or "")

    names = sorted(
        {
            item["name"]
            for item in context.values()
            if item.get("name")
        },
        key=len,
        reverse=True,
    )

    if not names:
        return result

    pattern = re.compile(
        "|".join(
            re.escape(name)
            for name in names
        )
    )

    def replacement(match):
        name = match.group(0)
        tail = match.string[match.end():match.end() + 100]

        # Già annotato dalla dashboard.
        if re.match(r"\s*\[MV\b", tail):
            return name

        # Riga explainability che espone già MV + FIA.
        if re.match(r"\s*[—-]\s*MV\b", tail):
            return name

        return (
            f"{name} "
            f"[{player_suffix(context, name)}]"
        )

    return pattern.sub(replacement, result)
