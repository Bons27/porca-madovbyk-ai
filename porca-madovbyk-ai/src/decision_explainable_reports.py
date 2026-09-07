"""Explainability wrappers for the FIA-aware decision engines.

The underlying engines remain unchanged. These wrappers add a compact,
counterfactual explanation: how much the final score differs from the same
calculation with FIA neutral (=50). This keeps the reports auditable without
pretending FIA is the only reason behind a recommendation.
"""

import html
import os
import re

from .decision_fia import (
    fia_start_score_delta,
    fia_scout_score_delta,
    fia_trade_value_delta,
    get_decision_fia_context,
    player_fia,
)
from .fantacalcio_source import normalize_name


def _safe(value):
    return html.escape(str(value))


def _plain(value):
    text = html.unescape(str(value or ""))
    text = re.sub(r"<br\s*/?>", "\n", text, flags=re.IGNORECASE)
    return re.sub(r"<[^>]+>", "", text)


def _context_names():
    context = get_decision_fia_context()
    return {
        key: data.get("name", "")
        for key, data in context.items()
        if data.get("name")
    }


def _ordered_names_in(text):
    plain = _plain(text)
    found = []

    for key, name in _context_names().items():
        position = plain.find(name)
        if position >= 0:
            found.append((position, key, name))

    found.sort(key=lambda item: item[0])

    seen = set()
    ordered = []
    for _position, key, name in found:
        if key in seen:
            continue
        seen.add(key)
        ordered.append(name)

    return ordered


def _section(text, start_marker, end_marker=None):
    plain = _plain(text)
    start = plain.find(start_marker)
    if start < 0:
        return ""

    start += len(start_marker)
    if end_marker:
        end = plain.find(end_marker, start)
        if end >= 0:
            return plain[start:end]

    return plain[start:]


def _mv_text(name):
    data = player_fia(name)
    mv = data.get("average_vote")
    games = data.get("games", 0)

    if mv is None or mv <= 0 or games <= 0:
        return "n/d"

    return f"{mv:.2f}"


def _fia_text(name):
    value = player_fia(name).get("fia")
    if value is None:
        return "n/d"
    return f"{value:+.2f}"


def _coach_text(name):
    return player_fia(name).get("coach") or "n/d"


def _impact_line(name, engine):
    if engine == "formation":
        delta = fia_start_score_delta(name)
        metric = "SS"
    elif engine == "trade":
        delta = fia_trade_value_delta(name)
        metric = "TV"
    elif engine == "scout":
        delta = fia_scout_score_delta(name)
        metric = "Scout"
    else:
        raise ValueError(f"Motore non supportato: {engine}")

    return (
        f"• <b>{_safe(name)}</b> — MV {_mv_text(name)} "
        f"| FIA {_fia_text(name)} "
        f"| Δ{metric} FIA <b>{delta:+.2f}</b> "
        f"| {_safe(_coach_text(name))}"
    )


def _resolve_input_names(value):
    context_names = _context_names()
    result = []

    for raw in str(value or "").split("+"):
        token = raw.strip()
        if not token:
            continue

        key = normalize_name(token)
        if key in context_names:
            result.append(context_names[key])
            continue

        # Fallback: match normalizzato per prefisso/suffisso, utile per nomi
        # abbreviati come "Castro S." presenti nella lega.
        candidates = [
            name
            for candidate_key, name in context_names.items()
            if key and (
                candidate_key.startswith(key)
                or key.startswith(candidate_key)
            )
        ]
        if len(candidates) == 1:
            result.append(candidates[0])
        else:
            result.append(token)

    return result


def _insert_before(report, marker, block):
    index = report.find(marker)
    if index < 0:
        return report + "\n\n" + block
    return report[:index] + block + "\n\n" + report[index:]


def _formation_ballot_lines(report, xi_names):
    xi_section = _section(report, "XI CONSIGLIATO", "PANCHINA")
    bench_section = _section(report, "PANCHINA", "TOP 5 ALTERNATIVE")
    bench_names = _ordered_names_in(bench_section)

    role_map = {
        name: player_fia(name).get("role")
        for name in xi_names + bench_names
    }

    ss_by_name = {}
    for name in xi_names:
        match = re.search(
            rf"{re.escape(name)}\s+—\s+SS\s+([0-9.]+)",
            xi_section,
        )
        if match:
            ss_by_name[name] = float(match.group(1))

    lines = []

    for role in ("P", "D", "C", "A"):
        starters = [
            name
            for name in xi_names
            if role_map.get(name) == role
        ]
        alternatives = [
            name
            for name in bench_names
            if role_map.get(name) == role
        ]

        if not starters or not alternatives:
            continue

        marginal = min(
            starters,
            key=lambda name: ss_by_name.get(name, 999.0),
        )
        alternative = alternatives[0]

        fia_margin = (
            fia_start_score_delta(marginal)
            - fia_start_score_delta(alternative)
        )

        if abs(fia_margin) < 0.05:
            direction = "quasi neutro"
        elif fia_margin > 0:
            direction = f"favorisce {_safe(marginal)}"
        else:
            direction = f"favorisce {_safe(alternative)}"

        lines.append(
            f"• {role}: {_safe(marginal)} vs {_safe(alternative)} — "
            f"margine FIA {fia_margin:+.2f} SS ({direction})"
        )

    return lines


def build_formation_report():
    from .final_advice_report import build_report

    report = build_report()
    xi_section = _section(report, "XI CONSIGLIATO", "PANCHINA")
    xi_names = _ordered_names_in(xi_section)

    lines = [
        "🧠 <b>IMPATTO FIA SULLA SCELTA</b>",
        "<i>ΔSS FIA = variazione dello Start Score rispetto a FIA neutro.</i>",
    ]

    for name in xi_names:
        lines.append(_impact_line(name, "formation"))

    ballot_lines = _formation_ballot_lines(report, xi_names)
    if ballot_lines:
        lines.extend(
            [
                "",
                "⚖️ <b>MARGINE FIA VS PRIMA ALTERNATIVA DI RUOLO</b>",
                *ballot_lines,
            ]
        )

    block = "\n".join(lines)
    return _insert_before(report, "🪑 <b>PANCHINA</b>", block)


def build_trade_report():
    from .trade_analysis_report import build_report

    report = build_report()

    outgoing = _resolve_input_names(os.environ.get("TRADE_GIVE", ""))
    incoming = _resolve_input_names(os.environ.get("TRADE_RECEIVE", ""))

    lines = [
        "🧠 <b>IMPATTO FIA SUL TRADE</b>",
        "<i>ΔTV FIA = variazione del Trade Value rispetto a FIA neutro.</i>",
        "📤 <b>Ceduti</b>",
    ]

    for name in outgoing:
        lines.append(_impact_line(name, "trade"))

    lines.append("📥 <b>Ricevuti</b>")
    for name in incoming:
        lines.append(_impact_line(name, "trade"))

    outgoing_delta = sum(
        fia_trade_value_delta(name)
        for name in outgoing
    )
    incoming_delta = sum(
        fia_trade_value_delta(name)
        for name in incoming
    )
    net = incoming_delta - outgoing_delta

    lines.extend(
        [
            (
                f"⚖️ Saldo FIA sui TV individuali: <b>{net:+.2f}</b> "
                "a favore del pacchetto ricevuto"
                if net >= 0
                else f"⚖️ Saldo FIA sui TV individuali: <b>{net:+.2f}</b> "
                "a favore del pacchetto ceduto"
            ),
            "<i>Questo saldo spiega solo la quota FIA del Trade Value, non l'intero verdetto.</i>",
        ]
    )

    block = "\n".join(lines)
    return _insert_before(report, "⚖️ <b>VERDETTO:", block)


def build_repair_report():
    from .repair_auction_report import build_report

    report = build_report()
    plain = _plain(report)

    target_names = []
    cut_names = []

    for raw in plain.splitlines():
        line = raw.strip()

        target_match = re.match(
            r"^\d+\.\s+(.+?)\s+\(([PDCA]),\s*.+\)$",
            line,
        )
        if target_match:
            target_names.append(target_match.group(1).strip())
            continue

        if line.startswith("✂️ Taglio:"):
            cut_names.append(line.split(":", 1)[1].strip())

    target_names = list(dict.fromkeys(target_names))[:8]
    cut_names = list(dict.fromkeys(cut_names))[:8]

    lines = [
        "🧠 <b>LETTURA FIA ASTA</b>",
        "<i>L'asta eredita FIA tramite Trade Value e Scout; non viene contato una terza volta.</i>",
    ]

    if target_names:
        lines.append("🎯 <b>Target presenti nei piani</b>")
        for name in target_names:
            lines.append(_impact_line(name, "trade"))

    if cut_names:
        lines.append("✂️ <b>Tagli presenti nei piani</b>")
        for name in cut_names:
            lines.append(_impact_line(name, "trade"))

    block = "\n".join(lines)
    return _insert_before(report, "🔥 <b>PIANO A", block)


def build_simulation_report():
    from .repair_auction_simulation_report import build_report

    report = build_report()
    target_section = _section(
        report,
        "I NOSTRI TARGET",
        "OPPORTUNITÀ DI MERCATO",
    )
    names = _ordered_names_in(target_section)[:10]

    lines = [
        "🧠 <b>IMPATTO FIA SUI TARGET SIMULATI</b>",
        "<i>ΔTV FIA mostra quanto il contesto allenatore×ruolo sposta il valore tecnico usato a monte.</i>",
    ]

    for name in names:
        lines.append(_impact_line(name, "trade"))

    block = "\n".join(lines)
    return _insert_before(report, "💎 <b>OPPORTUNITÀ DI MERCATO", block)
