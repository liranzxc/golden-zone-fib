# Golden Zone Dashboard

Next.js (App Router) dashboard, read-only, backed by Supabase. A cron job
runs the scanner and writes; the site only selects.

## 1. Supabase

1. Create a project.
2. Run `scripts/supabase_schema.sql` in the SQL editor — creates `setups`
   and `bars`, with RLS restricted to public `select`.
3. Grab the project URL, `anon` key, and `service_role` key.

## 2. Cron script

```
pip install -r scripts/requirements.txt
export SUPABASE_URL=https://xxxx.supabase.co
export SUPABASE_SECRET_KEY=sb_secret_...        # elevated key — bypasses RLS, backend only
python scripts/golden_zone_scan.py --supabase --out ''
```

`--out ''` skips the local CSV; drop it if you still want one too.
`--bars-keep 180` (default) controls how much OHLCV history is stored per
ticker for the charts — raise it if you want the candlestick view to scroll
further back.

Schedule it once a day after the close, e.g. a GitHub Actions cron job or
`crontab -e`:

```
0 22 * * 1-5 SUPABASE_URL=... SUPABASE_SECRET_KEY=... /usr/bin/python3 /path/to/golden_zone_scan.py --supabase --out ''
```

## 3. Frontend

```
cp .env.local.example .env.local   # fill in SUPABASE_URL / SUPABASE_PUBLISHABLE_KEY
npm install
npm run dev
```

- `app/page.tsx` — dashboard: reads filters from the URL, queries `setups`
  for the latest `date`, batch-fetches `bars` for the visible tickers.
- `components/Sidebar.tsx` — anchor / grade / retracement-zone filters,
  written to the URL so the page stays a server component.
- `components/CandleChart.tsx` — `lightweight-charts` candlesticks + dashed
  price lines for `lvl_382/500/618/786` and the leg high/low.
- `components/NavBar.tsx` — top nav (Dashboard / Watchlist / About — the
  latter two are stubs, wire them up as needed).

Deploy as-is to Vercel; set `SUPABASE_URL` and `SUPABASE_PUBLISHABLE_KEY`
there too — `SUPABASE_SECRET_KEY` is only used by the cron script and
should never be set on the Vercel project. `SUPABASE_JWKS_URL` isn't used
by this app (it's for verifying user JWTs, which this read-only dashboard
doesn't do) — safe to leave unset.
# golden-zone-fib
