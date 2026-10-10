-- Virun application schema for Supabase SQL Editor.
-- Run this entire file in one execution. Supabase Auth owns auth.users.
-- Private tables have RLS enabled without policies (deny by default).

BEGIN;

CREATE TABLE IF NOT EXISTS public.profiles (
  id uuid PRIMARY KEY REFERENCES auth.users(id) ON DELETE CASCADE,
  display_name varchar(120) NOT NULL,
  phone varchar(32) UNIQUE,
  avatar_url text,
  locale varchar(20) NOT NULL DEFAULT 'en',
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.roles (
  name varchar(40) PRIMARY KEY,
  description text
);

CREATE TABLE IF NOT EXISTS public.profile_roles (
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  role_name varchar(40) NOT NULL REFERENCES public.roles(name) ON DELETE RESTRICT,
  assigned_at timestamptz NOT NULL DEFAULT now(),
  assigned_by uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  PRIMARY KEY (profile_id, role_name)
);

CREATE TABLE IF NOT EXISTS public.guide_profiles (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid NOT NULL UNIQUE REFERENCES public.profiles(id) ON DELETE CASCADE,
  biography text,
  city varchar(120) NOT NULL,
  verification_status varchar(24) NOT NULL DEFAULT 'unverified'
    CONSTRAINT ck_guide_profiles_guide_verification_status CHECK (verification_status IN ('unverified','pending','verified','rejected')),
  is_listed boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.guide_languages (
  code varchar(16) PRIMARY KEY,
  name varchar(80) NOT NULL UNIQUE
);

CREATE TABLE IF NOT EXISTS public.guide_profile_languages (
  guide_profile_id uuid NOT NULL REFERENCES public.guide_profiles(id) ON DELETE CASCADE,
  language_code varchar(16) NOT NULL REFERENCES public.guide_languages(code) ON DELETE RESTRICT,
  PRIMARY KEY (guide_profile_id, language_code)
);

CREATE TABLE IF NOT EXISTS public.guide_services (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  guide_profile_id uuid NOT NULL REFERENCES public.guide_profiles(id) ON DELETE CASCADE,
  service_type varchar(60) NOT NULL,
  price_inr integer CONSTRAINT ck_guide_services_guide_service_price_nonnegative CHECK (price_inr IS NULL OR price_inr >= 0),
  price_unit varchar(24),
  is_active boolean NOT NULL DEFAULT true,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_guide_services_guide_profile_id UNIQUE (guide_profile_id, service_type)
);

CREATE TABLE IF NOT EXISTS public.guide_availability (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  guide_profile_id uuid NOT NULL REFERENCES public.guide_profiles(id) ON DELETE CASCADE,
  weekday smallint NOT NULL CONSTRAINT ck_guide_availability_availability_weekday CHECK (weekday BETWEEN 0 AND 6),
  starts_at time NOT NULL,
  ends_at time NOT NULL CONSTRAINT ck_guide_availability_availability_time_order CHECK (starts_at < ends_at),
  timezone varchar(64) NOT NULL DEFAULT 'Asia/Kolkata',
  valid_from date,
  valid_until date
);

CREATE TABLE IF NOT EXISTS public.destinations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  slug varchar(120) NOT NULL UNIQUE,
  name varchar(160) NOT NULL,
  region varchar(120),
  description text,
  data_source varchar(80) NOT NULL DEFAULT 'SAMPLE',
  is_published boolean NOT NULL DEFAULT false,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.attractions (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  destination_id uuid NOT NULL REFERENCES public.destinations(id) ON DELETE CASCADE,
  name varchar(160) NOT NULL,
  description text,
  address text,
  latitude numeric(9,6),
  longitude numeric(9,6),
  data_source varchar(80) NOT NULL DEFAULT 'SAMPLE',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.transport_stops (
  stop_id varchar(100) PRIMARY KEY,
  name varchar(160) NOT NULL,
  city varchar(120),
  aliases text[] NOT NULL DEFAULT '{}',
  latitude numeric(9,6),
  longitude numeric(9,6),
  data_source varchar(80) NOT NULL DEFAULT 'SIMULATED',
  created_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.transport_options (
  option_id varchar(100) PRIMARY KEY,
  origin_stop_id varchar(100) NOT NULL REFERENCES public.transport_stops(stop_id) ON DELETE RESTRICT,
  destination_stop_id varchar(100) NOT NULL REFERENCES public.transport_stops(stop_id) ON DELETE RESTRICT,
  mode varchar(16) NOT NULL CONSTRAINT ck_transport_options_transport_mode CHECK (mode IN ('bus','train','metro','flight','cab')),
  departure_at timestamptz NOT NULL,
  arrival_at timestamptz NOT NULL,
  fare_inr integer NOT NULL,
  luggage_fee_inr integer NOT NULL DEFAULT 0,
  status varchar(24) NOT NULL,
  data_source varchar(80) NOT NULL DEFAULT 'SIMULATED',
  operator varchar(120),
  seat_type varchar(16),
  ac boolean,
  reliability_score numeric(3,2) NOT NULL DEFAULT 0.90,
  origin_lat numeric(9,6),
  origin_lng numeric(9,6),
  destination_lat numeric(9,6),
  destination_lng numeric(9,6),
  created_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_transport_options_transport_status CHECK (status IN ('available_in_demo','available','cancelled','sold_out')),
  CONSTRAINT ck_transport_options_transport_nonnegative_fares CHECK (fare_inr >= 0 AND luggage_fee_inr >= 0),
  CONSTRAINT ck_transport_options_transport_time_order CHECK (arrival_at > departure_at),
  CONSTRAINT ck_transport_options_transport_distinct_stops CHECK (origin_stop_id <> destination_stop_id),
  CONSTRAINT ck_transport_options_transport_reliability CHECK (reliability_score BETWEEN 0 AND 1)
);

CREATE INDEX IF NOT EXISTS ix_transport_options_origin_departure ON public.transport_options (origin_stop_id, departure_at);
CREATE INDEX IF NOT EXISTS ix_transport_options_destination ON public.transport_options (destination_stop_id);
CREATE INDEX IF NOT EXISTS ix_transport_options_status ON public.transport_options (status);

CREATE TABLE IF NOT EXISTS public.trip_requests (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  origin varchar(160) NOT NULL,
  destination varchar(160) NOT NULL,
  departure_date date NOT NULL,
  arrival_deadline timestamptz NOT NULL,
  timezone varchar(64) NOT NULL DEFAULT 'Asia/Kolkata',
  passengers smallint NOT NULL DEFAULT 1 CONSTRAINT ck_trip_requests_trip_passengers CHECK (passengers BETWEEN 1 AND 10),
  budget_inr integer CONSTRAINT ck_trip_requests_trip_budget CHECK (budget_inr IS NULL OR budget_inr >= 0),
  preferences jsonb NOT NULL DEFAULT '{}'::jsonb,
  status varchar(24) NOT NULL DEFAULT 'planned',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.itineraries (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  trip_request_id uuid NOT NULL REFERENCES public.trip_requests(id) ON DELETE CASCADE,
  label varchar(80) NOT NULL,
  total_fare_inr integer NOT NULL,
  currency varchar(3) NOT NULL DEFAULT 'INR',
  duration_minutes integer NOT NULL,
  data_source varchar(80) NOT NULL,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_itineraries_itinerary_nonnegative CHECK (total_fare_inr >= 0 AND duration_minutes > 0)
);

CREATE TABLE IF NOT EXISTS public.itinerary_legs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  itinerary_id uuid NOT NULL REFERENCES public.itineraries(id) ON DELETE CASCADE,
  sequence smallint NOT NULL,
  transport_option_id varchar(100) REFERENCES public.transport_options(option_id) ON DELETE SET NULL,
  mode varchar(16) NOT NULL,
  origin_name varchar(160) NOT NULL,
  destination_name varchar(160) NOT NULL,
  departure_at timestamptz NOT NULL,
  arrival_at timestamptz NOT NULL,
  fare_inr integer NOT NULL,
  snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT uq_itinerary_legs_itinerary_id UNIQUE (itinerary_id, sequence),
  CONSTRAINT ck_itinerary_legs_itinerary_leg_sequence CHECK (sequence > 0),
  CONSTRAINT ck_itinerary_legs_itinerary_leg_time_order CHECK (arrival_at > departure_at)
);

CREATE TABLE IF NOT EXISTS public.bookings (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
  itinerary_id uuid NOT NULL REFERENCES public.itineraries(id) ON DELETE RESTRICT,
  provider varchar(80) NOT NULL,
  provider_reference varchar(160) UNIQUE,
  status varchar(24) NOT NULL DEFAULT 'pending',
  total_amount_inr integer NOT NULL CONSTRAINT ck_bookings_booking_amount CHECK (total_amount_inr >= 0),
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_bookings_booking_status CHECK (status IN ('pending','confirmed','cancelled','failed','refunded'))
);

CREATE TABLE IF NOT EXISTS public.booking_legs (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
  sequence smallint NOT NULL,
  provider_reference varchar(160),
  status varchar(24) NOT NULL DEFAULT 'pending',
  snapshot jsonb NOT NULL DEFAULT '{}'::jsonb,
  CONSTRAINT uq_booking_legs_booking_id UNIQUE (booking_id, sequence)
);

CREATE TABLE IF NOT EXISTS public.payments (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES public.bookings(id) ON DELETE RESTRICT,
  processor varchar(80) NOT NULL,
  processor_reference varchar(180) UNIQUE,
  amount_minor integer NOT NULL CONSTRAINT ck_payments_payment_amount CHECK (amount_minor >= 0),
  currency varchar(3) NOT NULL DEFAULT 'INR',
  status varchar(24) NOT NULL DEFAULT 'created',
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT ck_payments_payment_status CHECK (status IN ('created','authorized','captured','failed','refunded'))
);

CREATE TABLE IF NOT EXISTS public.reviews (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
  reviewer_profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
  guide_profile_id uuid REFERENCES public.guide_profiles(id) ON DELETE SET NULL,
  rating smallint NOT NULL CONSTRAINT ck_reviews_review_rating CHECK (rating BETWEEN 1 AND 5),
  body text,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now(),
  CONSTRAINT uq_reviews_booking_id UNIQUE (booking_id, reviewer_profile_id)
);

CREATE TABLE IF NOT EXISTS public.conversations (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL UNIQUE REFERENCES public.bookings(id) ON DELETE CASCADE,
  created_at timestamptz NOT NULL DEFAULT now(),
  updated_at timestamptz NOT NULL DEFAULT now()
);

CREATE TABLE IF NOT EXISTS public.conversation_participants (
  conversation_id uuid NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
  profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE CASCADE,
  joined_at timestamptz NOT NULL DEFAULT now(),
  PRIMARY KEY (conversation_id, profile_id)
);

CREATE TABLE IF NOT EXISTS public.messages (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  conversation_id uuid NOT NULL REFERENCES public.conversations(id) ON DELETE CASCADE,
  sender_profile_id uuid NOT NULL REFERENCES public.profiles(id) ON DELETE RESTRICT,
  body text NOT NULL,
  sent_at timestamptz NOT NULL DEFAULT now(),
  read_at timestamptz
);

CREATE TABLE IF NOT EXISTS public.trip_events (
  id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
  booking_id uuid NOT NULL REFERENCES public.bookings(id) ON DELETE CASCADE,
  actor_profile_id uuid REFERENCES public.profiles(id) ON DELETE SET NULL,
  event_type varchar(40) NOT NULL,
  details jsonb NOT NULL DEFAULT '{}'::jsonb,
  occurred_at timestamptz NOT NULL DEFAULT now()
);

ALTER TABLE public.profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.profile_roles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guide_profiles ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guide_languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guide_profile_languages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guide_services ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.guide_availability ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.destinations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.attractions ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trip_requests ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.itineraries ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.itinerary_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.bookings ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.booking_legs ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.payments ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.reviews ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversations ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.conversation_participants ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.messages ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.trip_events ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transport_stops ENABLE ROW LEVEL SECURITY;
ALTER TABLE public.transport_options ENABLE ROW LEVEL SECURITY;

DROP POLICY IF EXISTS transport_stops_read ON public.transport_stops;
CREATE POLICY transport_stops_read ON public.transport_stops FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS transport_options_read ON public.transport_options;
CREATE POLICY transport_options_read ON public.transport_options FOR SELECT TO anon, authenticated USING (true);
DROP POLICY IF EXISTS destinations_public_read ON public.destinations;
CREATE POLICY destinations_public_read ON public.destinations FOR SELECT TO anon, authenticated USING (is_published);
DROP POLICY IF EXISTS attractions_public_read ON public.attractions;
CREATE POLICY attractions_public_read ON public.attractions FOR SELECT TO anon, authenticated USING (
  EXISTS (SELECT 1 FROM public.destinations d WHERE d.id = destination_id AND d.is_published)
);

COMMIT;
