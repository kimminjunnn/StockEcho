create extension if not exists vector with schema extensions;

alter table public.historical_events
  add column if not exists esg_classification jsonb,
  add column if not exists event_embedding extensions.vector(768),
  add column if not exists embedding_model text,
  add column if not exists embedding_text_hash text;

create index if not exists historical_events_event_embedding_hnsw_idx
  on public.historical_events
  using hnsw (event_embedding extensions.vector_cosine_ops);
