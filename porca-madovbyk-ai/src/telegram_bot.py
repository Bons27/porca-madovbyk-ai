import json
import os
import sys
import urllib.parse
import urllib.request


def get_token():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError(
            "TELEGRAM_BOT_TOKEN non configurato."
        )

    return token


def telegram_request(method, data=None):
    token = get_token()

    url = (
        f"https://api.telegram.org/"
        f"bot{token}/{method}"
    )

    if data:
        encoded_data = urllib.parse.urlencode(
            data
        ).encode("utf-8")

        request = urllib.request.Request(
            url,
            data=encoded_data,
        )
    else:
        request = urllib.request.Request(url)

    with urllib.request.urlopen(
        request,
        timeout=20,
    ) as response:
        return json.loads(
            response.read().decode("utf-8")
        )


def discover_chat_id():
    webhook_info = telegram_request(
        "getWebhookInfo"
    )

    webhook_url = (
        webhook_info
        .get("result", {})
        .get("url", "")
    )

    print(
        "Webhook attivo:",
        webhook_url if webhook_url else "NO",
    )

    if webhook_url:
        print("Rimozione webhook...")

        telegram_request(
            "deleteWebhook",
            {
                "drop_pending_updates": "false"
            },
        )

    result = telegram_request(
        "getUpdates"
    )

    updates = result.get("result", [])

    if not updates:
        print("Nessun messaggio trovato.")
        print(
            "Invia un nuovo messaggio al bot "
            "e rilancia il workflow."
        )
        return

    for update in reversed(updates):
        message = (
            update.get("message")
            or update.get("edited_message")
            or update.get("channel_post")
        )

        if not message:
            continue

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if chat_id is not None:
            print(
                f"TELEGRAM_CHAT_ID={chat_id}"
            )
            print(
                "Tipo chat:",
                chat.get(
                    "type",
                    "sconosciuto",
                ),
            )
            return

    print(
        "Aggiornamenti trovati, "
        "ma nessun Chat ID individuato."
    )


def send_message(text):
    chat_id = os.environ.get(
        "TELEGRAM_CHAT_ID"
    )

    if not chat_id:
        raise RuntimeError(
            "TELEGRAM_CHAT_ID non configurato."
        )

    result = telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
            "disable_web_page_preview": "true",
        },
    )

    if not result.get("ok"):
        raise RuntimeError(
            f"Errore Telegram: {result}"
        )

    return result


def send_long_message(
    text,
    max_length=3800,
):
    lines = text.split("\n")

    chunks = []
    current = ""

    for line in lines:
        if current:
            candidate = (
                current + "\n" + line
            )
        else:
            candidate = line

        if len(candidate) > max_length:
            if current:
                chunks.append(current)

            current = line
        else:
            current = candidate

    if current:
        chunks.append(current)

    for chunk in chunks:
        send_message(chunk)


def send_test():
    message = (
        "⚽ <b>Porca MaDovbyk AI</b>\n\n"
        "✅ Collegamento Telegram riuscito.\n"
        "Il tuo agente Fantacalcio è online."
    )

    send_message(message)

    print(
        "Messaggio Telegram "
        "inviato correttamente."
    )


def main():
    if len(sys.argv) < 2:
        print(
            "Comandi disponibili: "
            "discover | send-test"
        )
        return

    command = sys.argv[1]

    if command == "discover":
        discover_chat_id()

    elif command == "send-test":
        send_test()

    else:
        raise ValueError(
            f"Comando sconosciuto: {command}"
        )


if __name__ == "__main__":
    main()
