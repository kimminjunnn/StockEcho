create table if not exists public.historical_events (
  event_id text primary key,
  stock_code text not null references public.stocks(stock_code) on delete cascade,
  topic_id text not null default '',
  event_date date not null,
  name text not null,
  keywords jsonb not null default '[]'::jsonb,
  article_count integer not null check (article_count >= 0),
  source_count integer not null check (source_count >= 0),
  representative_article jsonb not null,
  articles jsonb not null default '[]'::jsonb,
  model_version text not null default '',
  origin text not null check (origin in ('topic_model', 'analysis_snapshot', 'naver_backfill')),
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists historical_events_stock_date_idx
  on public.historical_events (stock_code, event_date desc);

create index if not exists historical_events_date_sources_idx
  on public.historical_events (event_date desc, source_count desc);

create table if not exists public.historical_issue_analyses (
  cache_key text primary key,
  stock_code text not null references public.stocks(stock_code) on delete cascade,
  current_event_id text not null,
  current_event_date date not null,
  request_context jsonb not null,
  status text not null
    check (status in ('processing', 'ready', 'failed')),
  result jsonb,
  error_code text,
  created_at timestamptz not null default now(),
  updated_at timestamptz not null default now()
);

create index if not exists historical_issue_analyses_event_idx
  on public.historical_issue_analyses (stock_code, current_event_id, updated_at desc);

create table if not exists public.market_daily (
  stock_code text not null references public.stocks(stock_code) on delete cascade,
  trading_date date not null,
  close_price numeric(20, 4) not null check (close_price > 0),
  source text not null default 'KIS',
  fetched_at timestamptz not null default now(),
  primary key (stock_code, trading_date)
);

create index if not exists market_daily_stock_date_idx
  on public.market_daily (stock_code, trading_date desc);

alter table public.historical_events enable row level security;
alter table public.historical_issue_analyses enable row level security;
alter table public.market_daily enable row level security;

drop policy if exists "public can read historical events" on public.historical_events;
create policy "public can read historical events"
  on public.historical_events for select to anon, authenticated
  using (true);

drop policy if exists "public can read historical analyses" on public.historical_issue_analyses;
create policy "public can read historical analyses"
  on public.historical_issue_analyses for select to anon, authenticated
  using (status = 'ready');

drop policy if exists "public can read market daily" on public.market_daily;
create policy "public can read market daily"
  on public.market_daily for select to anon, authenticated
  using (true);
