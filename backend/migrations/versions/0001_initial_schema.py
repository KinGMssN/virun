"""Create the Virun relational schema from SQLAlchemy metadata.

Revision ID: 0001_initial_schema
Revises:
"""
from alembic import op

from app.db.base import Base
from app.db import models  # noqa: F401 - registers models on Base.metadata

revision = "0001_initial_schema"
down_revision = None
branch_labels = None
depends_on = None


def upgrade() -> None:
    # Existing transport tables from the legacy SQL migration are left intact;
    # create_all creates any missing tables and never alters existing data.
    managed_tables = [table for table in Base.metadata.sorted_tables if table.schema != "auth"]
    Base.metadata.create_all(bind=op.get_bind(), tables=managed_tables, checkfirst=True)
    for table in (
        "profiles", "roles", "profile_roles", "guide_profiles", "guide_languages",
        "guide_profile_languages", "guide_services", "guide_availability",
        "destinations", "attractions", "trip_requests", "itineraries",
        "itinerary_legs", "bookings", "booking_legs", "payments", "reviews",
        "conversations", "conversation_participants", "messages", "trip_events",
        "transport_stops", "transport_options",
    ):
        op.execute(f'ALTER TABLE public."{table}" ENABLE ROW LEVEL SECURITY')

    # Public catalog and timetable reads only. Private app tables have RLS enabled
    # with no policies yet, so PostgREST access is denied until auth flows/policies
    # are implemented and reviewed.
    op.execute("""
        DO $$ BEGIN
          IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='transport_stops' AND policyname='transport_stops_read') THEN
            CREATE POLICY transport_stops_read ON public.transport_stops FOR SELECT TO anon, authenticated USING (true);
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='transport_options' AND policyname='transport_options_read') THEN
            CREATE POLICY transport_options_read ON public.transport_options FOR SELECT TO anon, authenticated USING (true);
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='destinations' AND policyname='destinations_public_read') THEN
            CREATE POLICY destinations_public_read ON public.destinations FOR SELECT TO anon, authenticated USING (is_published);
          END IF;
          IF NOT EXISTS (SELECT 1 FROM pg_policies WHERE schemaname='public' AND tablename='attractions' AND policyname='attractions_public_read') THEN
            CREATE POLICY attractions_public_read ON public.attractions FOR SELECT TO anon, authenticated USING (
              EXISTS (SELECT 1 FROM public.destinations d WHERE d.id = destination_id AND d.is_published)
            );
          END IF;
        END $$;
    """)


def downgrade() -> None:
    # Preserve the pre-existing planner tables during rollback.
    Base.metadata.drop_all(
        bind=op.get_bind(),
        tables=[table for table in reversed(Base.metadata.sorted_tables)
                if table.schema != "auth" and table.name not in {"transport_stops", "transport_options"}],
        checkfirst=True,
    )
