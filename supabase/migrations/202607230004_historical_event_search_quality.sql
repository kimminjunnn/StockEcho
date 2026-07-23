alter table public.historical_events
  add column if not exists topic_name text not null default '',
  add column if not exists topic_keywords jsonb not null default '[]'::jsonb,
  add column if not exists event_category text not null default '사업·전략',
  add column if not exists impact_direction text not null default 'unknown'
    check (
      impact_direction in (
        'positive', 'negative', 'neutral', 'mixed', 'unknown'
      )
    );

create index if not exists historical_events_updated_at_idx
  on public.historical_events (updated_at desc);
