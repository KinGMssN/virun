"""Allow Groq sightseeing plans in the relational itineraries table."""
from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision = "0002_generated_sightseeing_itineraries"
down_revision = "0001_initial_schema"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.add_column("itineraries", sa.Column("itinerary_type", sa.String(24), server_default="transport", nullable=False))
    op.add_column("itineraries", sa.Column("generated_content", postgresql.JSONB(astext_type=sa.Text()), nullable=True))
    op.add_column("itineraries", sa.Column("duration_days", sa.SmallInteger(), nullable=True))
    op.add_column("itineraries", sa.Column("duration_nights", sa.SmallInteger(), nullable=True))
    op.add_column("itineraries", sa.Column("budget_inr", sa.Numeric(12, 2), nullable=True))
    op.alter_column("itineraries", "trip_request_id", existing_type=sa.Uuid(), nullable=True)
    op.alter_column("itineraries", "total_fare_inr", existing_type=sa.Integer(), nullable=True)
    op.alter_column("itineraries", "duration_minutes", existing_type=sa.Integer(), nullable=True)
    op.drop_constraint("ck_itineraries_itinerary_nonnegative", "itineraries", type_="check")
    op.create_check_constraint(
        "itinerary_nonnegative", "itineraries",
        "(total_fare_inr is null and duration_minutes is null) or (total_fare_inr is not null and duration_minutes is not null and total_fare_inr >= 0 and duration_minutes > 0)",
    )
    op.create_check_constraint("itinerary_type", "itineraries", "itinerary_type in ('transport','sightseeing')")
    op.create_check_constraint("itinerary_duration_days", "itineraries", "duration_days is null or duration_days between 1 and 15")
    op.create_check_constraint("itinerary_duration_nights", "itineraries", "duration_nights is null or duration_nights between 0 and 30")
    op.create_check_constraint("itinerary_budget", "itineraries", "budget_inr is null or budget_inr > 0")


def downgrade() -> None:
    op.drop_constraint("ck_itineraries_itinerary_budget", "itineraries", type_="check")
    op.drop_constraint("ck_itineraries_itinerary_duration_nights", "itineraries", type_="check")
    op.drop_constraint("ck_itineraries_itinerary_duration_days", "itineraries", type_="check")
    op.drop_constraint("ck_itineraries_itinerary_type", "itineraries", type_="check")
    op.drop_constraint("ck_itineraries_itinerary_nonnegative", "itineraries", type_="check")
    op.create_check_constraint("itinerary_nonnegative", "itineraries", "total_fare_inr >= 0 and duration_minutes > 0")
    op.alter_column("itineraries", "trip_request_id", existing_type=sa.Uuid(), nullable=False)
    op.alter_column("itineraries", "total_fare_inr", existing_type=sa.Integer(), nullable=False)
    op.alter_column("itineraries", "duration_minutes", existing_type=sa.Integer(), nullable=False)
    op.drop_column("itineraries", "budget_inr")
    op.drop_column("itineraries", "duration_nights")
    op.drop_column("itineraries", "duration_days")
    op.drop_column("itineraries", "generated_content")
    op.drop_column("itineraries", "itinerary_type")
