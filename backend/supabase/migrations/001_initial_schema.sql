-- 001_initial_schema.sql  (Member 3: transport data for the deterministic planner)
-- !! Coordinate with Member 4 BEFORE running: agree table names and who owns migrations. !!
-- Mirrors app/schemas/transport.py exactly so PostgreSQL can replace the JSON fixtures
-- without changing the planning contract.

create table if not exists public.transport_stops (
  stop_id      text primary key,
  name         text not null,
  city         text,
  aliases      text[] not null default '{}',
  latitude     double precision,
  longitude    double precision,
  data_source  text not null default 'SIMULATED',
  created_at   timestamptz not null default now()
);

create table if not exists public.transport_options (
  option_id            text primary key,
  origin_stop_id       text not null references public.transport_stops(stop_id),
  destination_stop_id  text not null references public.transport_stops(stop_id),
  mode                 text not null check (mode in ('bus','train','metro','flight','cab')),
  departure_at         timestamptz not null,
  arrival_at           timestamptz not null,
  fare_inr             integer not null check (fare_inr >= 0),
  luggage_fee_inr      integer not null default 0 check (luggage_fee_inr >= 0),
  status               text not null check (status in ('available_in_demo','available','cancelled','sold_out')),
  data_source          text not null default 'SIMULATED',
  operator             text,
  seat_type            text check (seat_type in ('sleeper','seater')),
  ac                   boolean,
  reliability_score    numeric(3,2) not null default 0.90 check (reliability_score between 0 and 1),
  origin_lat           double precision,
  origin_lng           double precision,
  destination_lat      double precision,
  destination_lng      double precision,
  created_at           timestamptz not null default now(),
  constraint chk_arrival_after_departure check (arrival_at > departure_at),
  constraint chk_distinct_stops check (origin_stop_id <> destination_stop_id)
);

create index if not exists idx_transport_options_origin    on public.transport_options (origin_stop_id, departure_at);
create index if not exists idx_transport_options_dest      on public.transport_options (destination_stop_id);
create index if not exists idx_transport_options_status    on public.transport_options (status);

-- Read-only access for clients. The backend service-role key bypasses RLS anyway.
alter table public.transport_stops   enable row level security;
alter table public.transport_options enable row level security;

drop policy if exists transport_stops_read   on public.transport_stops;
drop policy if exists transport_options_read on public.transport_options;
create policy transport_stops_read   on public.transport_stops   for select to anon, authenticated using (true);
create policy transport_options_read on public.transport_options for select to anon, authenticated using (true);
