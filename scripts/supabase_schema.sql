-- Golden Zone dashboard schema
-- Run once in Supabase SQL editor.

create table if not exists setups (
  id           bigint generated always as identity primary key,
  ticker       text not null,
  anchor       text not null check (anchor in ('fixed','pine')),
  date         date not null,
  price        numeric,
  leg_low      numeric,
  leg_high     numeric,
  leg_pct      numeric,
  leg_atr      numeric,
  bars_off_high int,
  retrace      numeric,
  deepest      numeric,
  lvl_382      numeric,
  lvl_500      numeric,
  lvl_618      numeric,
  lvl_786      numeric,
  grade        text,
  score        int,
  align        text,
  b_1d int, b_2d int, b_1w int, b_1m int,
  trend_ok     boolean,
  e21_gt_e50   boolean,
  gt_e200      boolean,
  e50_up       boolean,
  turning      boolean,
  atr_pct      numeric,
  stop         numeric,
  stop_atr     numeric,
  t1           numeric,
  t2           numeric,
  qty          int,
  rr_to_high   numeric,
  pass         boolean,
  created_at   timestamptz not null default now(),
  unique (ticker, anchor, date)
);

create index if not exists setups_date_idx  on setups (date desc);
create index if not exists setups_grade_idx on setups (grade);
create index if not exists setups_pass_idx  on setups (pass);

create table if not exists bars (
  ticker  text not null,
  date    date not null,
  open    numeric,
  high    numeric,
  low     numeric,
  close   numeric,
  volume  bigint,
  primary key (ticker, date)
);

create index if not exists bars_ticker_date_idx on bars (ticker, date desc);

-- Read-only public access (dashboard uses the anon key, never writes)
alter table setups enable row level security;
alter table bars   enable row level security;

create policy "public read setups" on setups for select using (true);
create policy "public read bars"   on bars   for select using (true);

-- Writes only via the service-role key (used by the cron script), so no
-- insert/update policy is needed for anon.
