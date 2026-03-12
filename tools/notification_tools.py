import os
from langchain_core.tools import tool


@tool
def send_notification(title: str, message: str, urgency: str = "normal") -> str:
    """Send a Windows desktop notification.
    Use for non-voice alerts, background task completions, or reminders.

    Args:
        title:   Notification title
        message: Notification body
        urgency: 'low', 'normal', or 'urgent'
    """
    from win10toast import ToastNotifier

    toaster = ToastNotifier()
    duration = {"low": 3, "normal": 5, "urgent": 10}.get(urgency, 5)
    toaster.show_toast(title, message, duration=duration, threaded=True)
    return f"Notification sent: {title}"


@tool
def send_telegram_message(message: str, chat_id: str = "") -> str:
    """Send a message to your Telegram account via a bot.
    Use for mobile notifications when user is away from the machine.

    Args:
        message: Message to send
        chat_id: Telegram chat ID (defaults to env var TELEGRAM_CHAT_ID)
    """
    import requests
    from dotenv import load_dotenv

    load_dotenv()

    token = os.getenv("TELEGRAM_BOT_TOKEN")
    cid = os.getenv("TELEGRAM_CHAT_ID")

    resp = requests.post(
        f"https://api.telegram.org/bot{token}/sendMessage",
        json={"chat_id": cid, "text": message},
    )
    return "Telegram message sent." if resp.ok else f"Failed: {resp.text}"

NOTIFICATION_TOOLS = [
    send_notification,
    send_telegram_message
]
