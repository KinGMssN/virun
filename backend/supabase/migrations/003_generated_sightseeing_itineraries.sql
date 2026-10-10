-- Stores Groq-generated sightseeing plans in public.itineraries.
ALTER TABLE public.itineraries
  ADD COLUMN IF NOT EXISTS itinerary_type varchar(24) NOT NULL DEFAULT 'transport',
  ADD COLUMN IF NOT EXISTS generated_content jsonb,
  ADD COLUMN IF NOT EXISTS duration_days smallint,
  ADD COLUMN IF NOT EXISTS duration_nights smallint,
  ADD COLUMN IF NOT EXISTS budget_inr numeric(12,2);

ALTER TABLE public.itineraries ALTER COLUMN trip_request_id DROP NOT NULL;
ALTER TABLE public.itineraries ALTER COLUMN total_fare_inr DROP NOT NULL;
ALTER TABLE public.itineraries ALTER COLUMN duration_minutes DROP NOT NULL;
ALTER TABLE public.itineraries DROP CONSTRAINT IF EXISTS ck_itineraries_itinerary_nonnegative;
ALTER TABLE public.itineraries ADD CONSTRAINT ck_itineraries_itinerary_nonnegative CHECK (
  (total_fare_inr IS NULL AND duration_minutes IS NULL)
  OR (total_fare_inr IS NOT NULL AND duration_minutes IS NOT NULL
      AND total_fare_inr >= 0 AND duration_minutes > 0)
);
ALTER TABLE public.itineraries ADD CONSTRAINT ck_itineraries_itinerary_type CHECK (itinerary_type IN ('transport','sightseeing'));
ALTER TABLE public.itineraries ADD CONSTRAINT ck_itineraries_itinerary_duration_days CHECK (duration_days IS NULL OR duration_days BETWEEN 1 AND 15);
ALTER TABLE public.itineraries ADD CONSTRAINT ck_itineraries_itinerary_duration_nights CHECK (duration_nights IS NULL OR duration_nights BETWEEN 0 AND 30);
ALTER TABLE public.itineraries ADD CONSTRAINT ck_itineraries_itinerary_budget CHECK (budget_inr IS NULL OR budget_inr > 0);
