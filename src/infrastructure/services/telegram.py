import requests
import html


def enviar_telegram(token: str, chat_id: str, texto: str) -> bool:
    url = f"https://api.telegram.org/bot{token}/sendMessage"
    payload = {
        "chat_id": chat_id,
        "text": html.escape(texto),
        "parse_mode": "HTML",
    }
    try:
        r = requests.post(url, data=payload, timeout=10)
        if r.status_code == 200:
            return True
        print(f"Telegram envio falhou. Status: {r.status_code}, resp: {r.text}")
        return False
    except Exception as e:
        print(f"Erro ao chamar Telegram API: {e}")
        return False
