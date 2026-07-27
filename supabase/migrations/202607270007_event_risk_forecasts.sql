create table if not exists public.event_risk_forecasts (
  event_id text not null,
  stock_code text not null references public.stocks(stock_code) on delete cascade,
  horizon text not null check (horizon in ('d1', 'd5', 'd20')),
  as_of timestamptz not null,
  stale_after timestamptz not null,
  status text not null check (status in ('available', 'unavailable')),
  confidence text not null
    check (confidence in ('high', 'medium', 'low', 'insufficient')),
  model_version text not null,
  dataset_version text not null,
  result jsonb not null,
  evidence_event_ids jsonb not null default '[]'::jsonb,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now(),
  primary key (event_id, horizon, model_version, dataset_version)
);

create index if not exists event_risk_forecasts_stock_latest_idx
  on public.event_risk_forecasts (stock_code, as_of desc);

alter table public.event_risk_forecasts enable row level security;

drop policy if exists "public can read event risk forecasts"
  on public.event_risk_forecasts;
create policy "public can read event risk forecasts"
  on public.event_risk_forecasts for select to anon, authenticated
  using (true);
