#!/usr/bin/env bash
# Refresh config/already-contacted.csv from the old sales engine's database (read-only).
# Run weekly until the old server is shut down, then commit the CSV so the plugin picks it up.
set -euo pipefail
cd "$(dirname "$0")/.."
OUT=config/already-contacted.csv
TMP=$(mktemp)
gcloud compute ssh stellaspire --project gen-lang-client-0184664335 --zone asia-south1-a --command '
sudo docker exec stellaspire-db-1 sh -c "psql -U \$POSTGRES_USER -d \$POSTGRES_DB -A -F, -t -c \"
select lower(trim(c.work_email)), lower(co.normalized_domain),
       to_char(coalesce(max(s.pushed_at), max(s.created_at)) at time zone '"'"'Asia/Kolkata'"'"', '"'"'YYYY-MM-DD'"'"'),
       '"'"'live_engine_'"'"' || string_agg(distinct s.status, '"'"'+'"'"')
from outreach_sequences s join contacts c on c.id = s.contact_id join companies co on co.id = s.company_id
where c.work_email is not null group by 1, 2
union all
select lower(trim(email)), split_part(lower(trim(email)), '"'"'@'"'"', 2),
       to_char(created_at at time zone '"'"'Asia/Kolkata'"'"', '"'"'YYYY-MM-DD'"'"'), '"'"'suppressed_'"'"' || reason
from suppressions order by 1\""' 2>/dev/null | grep -v '^$' > "$TMP"
[ -s "$TMP" ] || { echo "Export returned nothing; keeping the old file." >&2; rm -f "$TMP"; exit 1; }
{ echo "email,domain,last_contacted,source"; cat "$TMP"; } > "$OUT"
rm -f "$TMP"
echo "Wrote $(($(wc -l < "$OUT") - 1)) rows to $OUT"
