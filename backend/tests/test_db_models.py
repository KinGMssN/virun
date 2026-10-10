from app.db.base import Base
from app.db import models  # noqa: F401 - registers all mapped tables


EXPECTED_TABLES = {
    "profiles", "roles", "profile_roles", "guide_profiles", "guide_languages",
    "guide_profile_languages", "guide_services", "guide_availability", "destinations",
    "attractions", "trip_requests", "itineraries", "itinerary_legs", "bookings",
    "booking_legs", "payments", "reviews", "conversations", "conversation_participants",
    "messages", "trip_events", "transport_stops", "transport_options",
}


def test_sqlalchemy_models_define_all_app_tables_without_owning_supabase_auth():
    public_tables = {name for name, table in Base.metadata.tables.items() if table.schema != "auth"}
    assert public_tables == EXPECTED_TABLES
    assert Base.metadata.tables["auth.users"].info["managed_externally"] is True


def test_relational_integrity_constraints_are_present():
    assert {fk.target_fullname for fk in Base.metadata.tables["profiles"].foreign_keys} == {"auth.users.id"}
    assert any(fk.target_fullname == "profiles.id" for fk in Base.metadata.tables["bookings"].foreign_keys)
    assert any(fk.target_fullname == "transport_stops.stop_id" for fk in Base.metadata.tables["transport_options"].foreign_keys)
    assert any(
        constraint.name.endswith("transport_time_order")
        for constraint in Base.metadata.tables["transport_options"].constraints
    )
