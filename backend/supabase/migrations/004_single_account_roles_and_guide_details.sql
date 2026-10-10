-- Keep Supabase SQL Editor deployments aligned with Alembic revision 0003.
BEGIN;

ALTER TABLE public.profiles
  ADD COLUMN IF NOT EXISTS account_type varchar(16) NOT NULL DEFAULT 'tourist';

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'public.profiles'::regclass
      AND conname = 'ck_profiles_profile_account_type'
  ) THEN
    ALTER TABLE public.profiles
      ADD CONSTRAINT ck_profiles_profile_account_type
      CHECK (account_type IN ('tourist', 'guide'));
  END IF;
END;
$$;

ALTER TABLE public.guide_profiles
  ADD COLUMN IF NOT EXISTS years_experience smallint NOT NULL DEFAULT 0,
  ADD COLUMN IF NOT EXISTS city_knowledge_rating smallint NOT NULL DEFAULT 4;

DO $$
BEGIN
  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'public.guide_profiles'::regclass
      AND conname = 'ck_guide_profiles_guide_years_experience'
  ) THEN
    ALTER TABLE public.guide_profiles
      ADD CONSTRAINT ck_guide_profiles_guide_years_experience
      CHECK (years_experience BETWEEN 0 AND 60);
  END IF;

  IF NOT EXISTS (
    SELECT 1
    FROM pg_constraint
    WHERE conrelid = 'public.guide_profiles'::regclass
      AND conname = 'ck_guide_profiles_guide_city_knowledge_rating'
  ) THEN
    ALTER TABLE public.guide_profiles
      ADD CONSTRAINT ck_guide_profiles_guide_city_knowledge_rating
      CHECK (city_knowledge_rating BETWEEN 1 AND 5);
  END IF;
END;
$$;

COMMIT;
