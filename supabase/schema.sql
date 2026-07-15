create extension if not exists pgcrypto;

create table if not exists public.observations (
    id uuid primary key default gen_random_uuid(),
    indicator_code text not null,
    period date not null,
    value double precision not null,
    unit text not null,
    source text not null,
    source_url text not null default '',
    frequency text not null check (frequency in ('daily', 'weekly', 'monthly', 'quarterly', 'annual')),
    data_type text not null default 'fact' check (data_type in ('fact', 'forecast')),
    published_at timestamptz,
    fetched_at timestamptz not null default now(),
    quality_status text not null default 'valid' check (quality_status in ('valid', 'warning', 'invalid')),
    created_at timestamptz not null default now(),
    updated_at timestamptz not null default now(),
    unique (indicator_code, period, source, data_type)
);

create index if not exists observations_indicator_period_idx
    on public.observations (indicator_code, period desc);

create table if not exists public.ingestion_runs (
    id uuid primary key default gen_random_uuid(),
    started_at timestamptz not null default now(),
    finished_at timestamptz,
    status text not null check (status in ('running', 'success', 'partial', 'failed')),
    trigger_type text not null check (trigger_type in ('manual', 'schedule', 'migration')),
    records_received integer not null default 0,
    error_message text
);

create table if not exists public.reports (
    id uuid primary key default gen_random_uuid(),
    report_date date not null,
    created_at timestamptz not null default now(),
    storage_path text not null,
    status text not null default 'ready'
);

create or replace function public.set_updated_at()
returns trigger
language plpgsql
as $$
begin
    new.updated_at = now();
    return new;
end;
$$;

drop trigger if exists observations_set_updated_at on public.observations;
create trigger observations_set_updated_at
before update on public.observations
for each row execute function public.set_updated_at();

alter table public.observations enable row level security;
alter table public.ingestion_runs enable row level security;
alter table public.reports enable row level security;

-- Policies are intentionally absent: only the server-side service_role key can access data.
-- Never expose SUPABASE_SERVICE_ROLE_KEY in browser code or commit it to Git.
