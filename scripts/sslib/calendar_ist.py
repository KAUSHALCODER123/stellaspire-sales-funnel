"""IST calendar decisions: send day, warm-up caps, business-day follow-up timing."""
from datetime import date, datetime, timedelta, timezone

from .config import settings

try:
    from holidays import country_holidays
except ImportError:  # unknown holiday calendar: never send
    country_holidays = None

IST = timezone(timedelta(hours=5, minutes=30), "IST")  # India has no daylight saving; no tz database needed
STEP_DELAYS_DAYS = (0, 3, 4, 5, 7)  # business days after the previous email
WARMUP_CAPS = (5, 10, 15, 20)  # by full weeks since warmup_start_date; week 3 and later = 20
STEPS = 5


def parse_dt(value: str | None, default_now: bool = False) -> datetime | None:
    """ISO text to an aware datetime; a naive value or a bare date is read as IST."""
    if not value:
        return datetime.now(IST) if default_now else None
    dt = datetime.fromisoformat(value)
    return dt.replace(tzinfo=IST) if dt.tzinfo is None else dt


def now_ist(value: str | None = None) -> datetime:
    return parse_dt(value, default_now=True).astimezone(IST)


def non_working_day(day: date) -> str | None:
    """Why no email goes out on this date in India, or None on a working day."""
    if day.weekday() >= 5:
        return "weekend"
    if country_holidays is None:
        return "holidays_package_missing"
    if day in country_holidays("IN", years=day.year):
        return "public_holiday"
    return None


def add_business_days(start: date, n: int) -> date:
    day = start
    while n > 0:
        day += timedelta(days=1)
        if non_working_day(day) is None:
            n -= 1
    return day


def today(inp: dict) -> dict:
    cfg, now = settings(), now_ist(inp.get("now"))
    day, week, reason = now.date(), 0, non_working_day(now.date())
    start = (cfg.get("warmup_start_date") or "").strip()
    if cfg.get("paused"):
        reason = "paused"
    elif reason is None and not start:
        reason = "warmup_start_date_not_set"
    elif reason is None:
        days = (day - date.fromisoformat(start)).days
        if days < 0:
            reason = "before_warmup_start"
        week = days // 7
    ramp = WARMUP_CAPS[min(week, len(WARMUP_CAPS) - 1)]
    total = 0 if reason else min(ramp, int(cfg.get("mailbox_daily_cap", 25)))
    left = max(0, total - int(inp["sent_today"]) - int(inp["drafted_today"]))
    followups = min(int(inp["followups_due"]), left)
    new_cap = left - followups
    pending = int(inp.get("pending_drafts") or 0)
    hold = None
    if reason is None and pending >= total:  # unsent drafts already fill the day: write nothing new
        new_cap = followups = 0
        hold = "drafts_waiting"
    oldest = parse_dt(inp.get("oldest_pending_draft_at"))
    stale = bool(pending and oldest and day > add_business_days(oldest.astimezone(IST).date(), 2))
    budget = 0 if new_cap <= 0 else min(int(cfg.get("max_companies_researched_per_run", 15)),
                                        new_cap * int(cfg.get("companies_per_new_email", 3)))
    return {"send_day": reason is None, "reason": reason, "warmup_week": week, "total_cap": total,
            "new_cap": new_cap, "followup_cap": followups, "paused": bool(cfg.get("paused")),
            "research_budget": budget, "hold_reason": hold, "stale_drafts": stale}


def next_step(inp: dict) -> dict:
    day = now_ist(inp.get("now")).date()
    due, finished = [], []
    for t in inp["threads"]:
        if t["replied"] or t["stopped"]:
            continue
        step = int(t["step"])
        if step >= STEPS:
            finished.append(t["thread_id"])
            continue
        last = parse_dt(t["last_sent_at"]).astimezone(IST).date()
        if day >= add_business_days(last, STEP_DELAYS_DAYS[step]):
            due.append({"thread_id": t["thread_id"], "next_step": step + 1})
    return {"due": due, "finished": finished}
