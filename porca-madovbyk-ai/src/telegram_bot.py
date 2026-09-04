import json
import os
import sys
import urllib.parse
import urllib.request


def get_token():
    token = os.environ.get("TELEGRAM_BOT_TOKEN")

    if not token:
        raise RuntimeError("TELEGRAM_BOT_TOKEN non configurato.")

    return token


def telegram_request(method, data=None):
    token = get_token()
    url = f"https://api.telegram.org/bot{token}/{method}"

    if data:
        encoded_data = urllib.parse.urlencode(data).encode("utf-8")
        request = urllib.request.Request(url, data=encoded_data)
    else:
        request = urllib.request.Request(url)

    with urllib.request.urlopen(request, timeout=20) as response:
        return json.loads(response.read().decode("utf-8"))


def discover_chat_id():
    result = telegram_request("getUpdates")

    updates = result.get("result", [])

    if not updates:
        print("Nessun messaggio trovato.")
        print("Apri il bot su Telegram, premi Start e inviagli un messaggio.")
        return

    for update in reversed(updates):
        message = update.get("message") or update.get("edited_message")

        if not message:
            continue

        chat = message.get("chat", {})
        chat_id = chat.get("id")

        if chat_id is not None:
            print(f"TELEGRAM_CHAT_ID={chat_id}")
            print(f"Tipo chat: {chat.get('type', 'sconosciuto')}")
            return

    print("Non è stato possibile individuare il Chat ID.")


def send_test():
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID non configurato.")

    message = (
        "⚽ Porca MaDovbyk AI\n\n"
        "✅ Collegamento Telegram riuscito.\n"
        "Il tuo agente Fantacalcio è online."
    )

    result = telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": message,
        },
    )

    if result.get("ok"):
        print("Messaggio Telegram inviato correttamente.")
    else:
        raise RuntimeError(f"Errore Telegram: {result}")

def send_message(text):
    chat_id = os.environ.get("TELEGRAM_CHAT_ID")

    if not chat_id:
        raise RuntimeError("TELEGRAM_CHAT_ID non configurato.")

    result = telegram_request(
        "sendMessage",
        {
            "chat_id": chat_id,
            "text": text,
            "parse_mode": "HTML",
        },
    )

    if not result.get("ok"):
        raise RuntimeError(f"Errore Telegram: {result}")

    return result
if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usa: discover oppure send-test")
        sys.exit(1)

    command = sys.argv[1]

    if command == "discover":
        discover_chat_id()
    elif command == "send-test":
        send_test()
    else:
        raise ValueError(f"Comando sconosciuto: {command}")
