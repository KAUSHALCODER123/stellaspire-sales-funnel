#!/usr/bin/env python3
"""Export leads and the blocklist from the old sales engine's database (read-only) into config/.

Writes:
  config/already-contacted.csv  people the old engine actually emailed (or stopped), plus its suppressions
  config/imported-leads.json    leads with a fresh role waiting to be emailed, and verified contacts with no role yet

Needs gcloud access to the stellaspire VM. Run it once more on the day the old engine is shut down for good.
imported-leads.json holds personal data: it goes into the plugin zip, never into git.
"""
import base64
import csv
import json
import pathlib
import subprocess
import sys

CONFIG = pathlib.Path(__file__).resolve().parents[1] / "config"
GCLOUD = ["gcloud", "compute", "ssh", "stellaspire", "--project", "gen-lang-client-0184664335", "--zone", "asia-south1-a"]

WAITING = """select coalesce(json_agg(t), '[]'::json) from (
 select co.segment, co.name company, co.normalized_domain domain, co.headquarters_city city, co.industry,
        c.full_name, c.job_title title, lower(trim(c.work_email)) email, c.email_status, c.country, c.professional_profile_url linkedin,
        s.role_title, s.role_url, j.source_posted_at, j.raw_metadata->>'hiring_basis' hiring_basis
 from outreach_sequences s join contacts c on c.id=s.contact_id join companies co on co.id=s.company_id
 left join job_observations j on j.company_id=s.company_id and j.external_id=s.role_external_id and j.url=s.role_url
 where s.status='drafted' and s.pushed_at is null and not coalesce(c.do_not_contact,false) order by s.created_at) t;"""
NO_ROLE = """select coalesce(json_agg(t), '[]'::json) from (
 select co.segment, co.name company, co.normalized_domain domain, co.headquarters_city city, co.industry,
        c.full_name, c.job_title title, lower(trim(c.work_email)) email, c.email_status, c.country, c.professional_profile_url linkedin
 from contacts c join companies co on co.id=c.company_id
 where not exists (select 1 from outreach_sequences s where s.contact_id=c.id)
   and c.email_status='verified' and not coalesce(c.do_not_contact,false)) t;"""
BLOCKED = """select coalesce(json_agg(t), '[]'::json) from (
 select lower(trim(c.work_email)) email, lower(co.normalized_domain) domain,
        to_char(coalesce(s.pushed_at, s.created_at) at time zone 'Asia/Kolkata','YYYY-MM-DD') last_contacted,
        'live_engine_' || s.status source
 from outreach_sequences s join contacts c on c.id=s.contact_id join companies co on co.id=s.company_id
 where s.pushed_at is not null or s.status in ('active','stopped','completed')
 union all
 select lower(trim(email)), split_part(lower(trim(email)),'@',2), to_char(created_at at time zone 'Asia/Kolkata','YYYY-MM-DD'), 'suppressed_' || reason
 from suppressions) t;"""


def query(sql: str) -> list[dict]:
    b64 = base64.b64encode(sql.encode()).decode()
    remote = f"echo {b64} | base64 -d | sudo docker exec -i stellaspire-db-1 sh -c 'psql -U $POSTGRES_USER -d $POSTGRES_DB -t -A'"
    out = subprocess.run(GCLOUD + ["--command", remote], capture_output=True, text=True, shell=sys.platform == "win32")
    text = "\n".join(l for l in out.stdout.splitlines() if not l.startswith("WARNING")).strip()
    try:
        return json.loads(text)
    except ValueError:
        sys.exit(f"Export failed, nothing written.\n{out.stderr[-300:]}")


def person(r: dict) -> dict:
    return {"company": {"name": r["company"], "domain": r["domain"], "city": r["city"], "industry": r["industry"]},
            "segment": r["segment"],
            "contact": {"full_name": r["full_name"], "title": r["title"], "email": r["email"], "email_status": r["email_status"],
                        "country": r["country"], "linkedin_url": r["linkedin"]}}


def main() -> None:
    waiting, no_role, blocked = query(WAITING), query(NO_ROLE), query(BLOCKED)
    leads = [{**person(r), "role": {"title": r["role_title"], "url": r["role_url"], "posted_at": r["source_posted_at"],
                                    "on_employer_board": r["hiring_basis"] == "board"}} for r in waiting]
    data = {"exported_on": __import__("datetime").date.today().isoformat(), "leads": leads,
            "contacts_without_role": [person(r) for r in no_role]}
    (CONFIG / "imported-leads.json").write_text(json.dumps(data, ensure_ascii=False, indent=1) + "\n", encoding="utf-8")
    with open(CONFIG / "already-contacted.csv", "w", newline="", encoding="utf-8") as f:
        w = csv.writer(f, lineterminator="\n")
        w.writerow(["email", "domain", "last_contacted", "source"])
        for r in sorted(blocked, key=lambda r: r["email"]):
            w.writerow([r["email"], r["domain"], r["last_contacted"], r["source"]])
    print(f"{len(leads)} leads with a role, {len(no_role)} contacts without one, {len(blocked)} blocked")


if __name__ == "__main__":
    main()
