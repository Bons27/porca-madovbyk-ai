import html
import os
import subprocess
import sys

from .telegram_bot import (
    send_long_message,
    send_message,
)


def clean_command_name(value):
    """
    Telegram nei gruppi può inviare:
    /status@NomeBot

    Lo normalizziamo in:
    /status
    """

    value = (
        value.strip()
        .lower()
    )

    if not value.startswith("/"):
        value = "/" + value

    if "@" in value:
        value = (
            value.split(
                "@",
                1,
            )[0]
        )

    return value


def split_command(text):
    text = (
        str(text or "")
        .strip()
    )

    if not text:
        return (
            "",
            "",
        )

    parts = text.split(
        maxsplit=1
    )

    command = (
        clean_command_name(
            parts[0]
        )
    )

    arguments = (
        parts[1].strip()
        if len(parts) > 1
        else ""
    )

    return (
        command,
        arguments,
    )


def help_report():
    return "\n".join(
        [
            "🤖 <b>PORCA MADOVBYK AI</b>",
            "",
            "Comandi disponibili:",
            "",
            "🧠 <b>/status</b>",
            "Control Center generale.",
            "",
            "🏆 <b>/formazione</b>",
            "Analisi completa della prossima giornata.",
            "",
            "🕵️ <b>/scout</b>",
            "Aggiorna e mostra il Talent Scout.",
            "",
            "🛠 <b>/asta</b>",
            "Piano asta di riparazione.",
            "",
            "🎲 <b>/simulaasta</b>",
            "Simulazione asta contro le altre 7 squadre.",
            "",
            "🤝 <b>/trade</b>",
            "Valuta uno scambio specifico.",
            "",
            "Formato:",
            "<code>/trade Giocatore 1 + Giocatore 2 | Giocatore 3 + Giocatore 4</code>",
            "",
            "Esempio:",
            "<code>/trade Da Cunha + Castro S. | Rowe + Hojlund</code>",
        ]
    )


def run_module(
    module,
    extra_env=None,
):
    env = os.environ.copy()

    if extra_env:
        env.update(
            extra_env
        )

    print(
        "Avvio modulo:",
        module,
    )

    subprocess.run(
        [
            sys.executable,
            "-m",
            module,
        ],
        env=env,
        check=True,
    )


def parse_trade(
    arguments,
):
    if "|" not in arguments:
        raise ValueError(
            "Formato trade non valido."
        )

    give, receive = (
        arguments.split(
            "|",
            1,
        )
    )

    give = give.strip()
    receive = receive.strip()

    if not give:
        raise ValueError(
            "Mancano i giocatori "
            "che vuoi cedere."
        )

    if not receive:
        raise ValueError(
            "Mancano i giocatori "
            "che vuoi ricevere."
        )

    return (
        give,
        receive,
    )


def trade_usage():
    return "\n".join(
        [
            "🤝 <b>TRADE ANALYZER</b>",
            "",
            "Usa questo formato:",
            "",
            "<code>/trade CEDO | RICEVO</code>",
            "",
            "Per più giocatori usa +",
            "",
            "Esempio:",
            "<code>/trade Da Cunha + Castro S. | Rowe + Hojlund</code>",
        ]
    )


def execute_command(
    text,
):
    command, arguments = (
        split_command(
            text
        )
    )

    print(
        "Comando ricevuto:",
        command,
    )

    if command in (
        "/start",
        "/help",
    ):
        send_long_message(
            help_report()
        )

        return

    if command in (
        "/status",
        "/dashboard",
    ):
        run_module(
            "src.dashboard_report"
        )

        return

    if command in (
        "/formazione",
        "/lineup",
    ):
        run_module(
            "src.final_advice_report"
        )

        return

    if command in (
        "/scout",
        "/talentscout",
    ):
        run_module(
            "src.talent_scout_report",
            {
                "SCOUT_FORCE_REPORT": (
                    "yes"
                ),
            },
        )

        return

    if command in (
        "/asta",
        "/repair",
    ):
        run_module(
            "src.repair_auction_report"
        )

        return

    if command in (
        "/simulaasta",
        "/auction",
    ):
        run_module(
            (
                "src."
                "repair_auction_"
                "simulation_report"
            )
        )

        return

    if command == "/trade":
        if not arguments:
            send_long_message(
                trade_usage()
            )

            return

        try:
            give, receive = (
                parse_trade(
                    arguments
                )
            )

        except ValueError as exc:
            send_long_message(
                "\n".join(
                    [
                        "⚠️ <b>TRADE ANALYZER</b>",
                        "",
                        html.escape(
                            str(exc)
                        ),
                        "",
                        trade_usage(),
                    ]
                )
            )

            return

        run_module(
            "src.trade_analysis_report",
            {
                "TRADE_GIVE": give,
                "TRADE_RECEIVE": (
                    receive
                ),
            },
        )

        return

    send_long_message(
        "\n".join(
            [
                "❓ <b>Comando non riconosciuto</b>",
                "",
                (
                    "Scrivi "
                    "<b>/help</b> "
                    "per vedere i comandi."
                ),
            ]
        )
    )


def main():
    command = (
        os.environ.get(
            "TELEGRAM_COMMAND",
            "",
        )
        .strip()
    )

    if not command:
        raise RuntimeError(
            "TELEGRAM_COMMAND "
            "non impostato."
        )

    try:
        execute_command(
            command
        )

    except Exception as exc:
        message = (
            "⚠️ <b>PORCA MADOVBYK AI</b>\n\n"
            "Errore durante l'esecuzione "
            "del comando:\n"
            f"<code>"
            f"{html.escape(str(exc))}"
            f"</code>"
        )

        try:
            send_message(
                message
            )

        except Exception:
            pass

        raise


if __name__ == "__main__":
    main()
