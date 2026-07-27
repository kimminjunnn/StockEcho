alter table public.market_daily
  add column if not exists open_price numeric(20, 4),
  add column if not exists high_price numeric(20, 4),
  add column if not exists low_price numeric(20, 4),
  add column if not exists volume bigint,
  add column if not exists adjusted boolean not null default true;

create table if not exists public.market_index_daily (
  index_code text not null,
  trading_date date not null,
  open_price numeric(20, 4),
  high_price numeric(20, 4),
  low_price numeric(20, 4),
  close_price numeric(20, 4) not null check (close_price > 0),
  volume bigint,
  source text not null default 'KIS',
  fetched_at timestamptz not null default now(),
  primary key (index_code, trading_date)
);

alter table public.historical_events
  add column if not exists detected_at timestamptz,
  add column if not exists feature_cutoff_at timestamptz,
  add column if not exists feature_document_ids jsonb not null default '[]'::jsonb;

alter table public.market_index_daily enable row level security;

drop policy if exists "public can read market index daily"
  on public.market_index_daily;
create policy "public can read market index daily"
  on public.market_index_daily for select to anon, authenticated
  using (true);
