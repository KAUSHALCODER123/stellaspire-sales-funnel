"""Auto-pause decision from the last 14 days of mailbox results."""
from .config import settings

MAX_BOUNCE_RATE, MIN_SENDS = 0.03, 20


def health(inp: dict) -> dict:
    sent, bounced = int(inp["sent_14d"]), int(inp["bounced_14d"])
    if settings().get("paused"):
        return {"pause": True, "reason": "paused_in_settings"}
    if int(inp["complaints"]) > 0:
        return {"pause": True, "reason": "spam_complaint"}
    if sent >= MIN_SENDS and bounced / sent > MAX_BOUNCE_RATE:
        return {"pause": True, "reason": f"bounce_rate_{bounced / sent:.1%}"}
    return {"pause": False, "reason": None}
