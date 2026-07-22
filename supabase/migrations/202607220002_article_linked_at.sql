alter table public.article_stocks
  add column if not exists linked_at timestamptz;

update public.article_stocks
set linked_at = evaluated_at
where linked_at is null;

alter table public.article_stocks
  alter column linked_at set default now(),
  alter column linked_at set not null;

create index if not exists article_stocks_pending_idx
  on public.article_stocks (stock_code, status, linked_at desc);
