"""Persist a single account type and complete guide profile details."""
from alembic import op
import sqlalchemy as sa

revision = "0003_single_account_roles_and_guide_details"
down_revision = "0002_generated_sightseeing_itineraries"
branch_labels = None
depends_on = None


def upgrade() -> None:
    inspector = sa.inspect(op.get_bind())
    profile_columns = {column["name"] for column in inspector.get_columns("profiles")}
    if "account_type" not in profile_columns:
        op.add_column("profiles", sa.Column("account_type", sa.String(16), server_default="tourist", nullable=False))
    profile_checks = {check["name"] for check in inspector.get_check_constraints("profiles")}
    if "ck_profiles_profile_account_type" not in profile_checks:
        op.create_check_constraint("profile_account_type", "profiles", "account_type in ('tourist','guide')")

    guide_columns = {column["name"] for column in inspector.get_columns("guide_profiles")}
    if "years_experience" not in guide_columns:
        op.add_column("guide_profiles", sa.Column("years_experience", sa.SmallInteger(), server_default="0", nullable=False))
    if "city_knowledge_rating" not in guide_columns:
        op.add_column("guide_profiles", sa.Column("city_knowledge_rating", sa.SmallInteger(), server_default="4", nullable=False))
    guide_checks = {check["name"] for check in inspector.get_check_constraints("guide_profiles")}
    if "ck_guide_profiles_guide_years_experience" not in guide_checks:
        op.create_check_constraint("guide_years_experience", "guide_profiles", "years_experience between 0 and 60")
    if "ck_guide_profiles_guide_city_knowledge_rating" not in guide_checks:
        op.create_check_constraint("guide_city_knowledge_rating", "guide_profiles", "city_knowledge_rating between 1 and 5")


def downgrade() -> None:
    op.drop_constraint("ck_guide_profiles_guide_city_knowledge_rating", "guide_profiles", type_="check")
    op.drop_constraint("ck_guide_profiles_guide_years_experience", "guide_profiles", type_="check")
    op.drop_column("guide_profiles", "city_knowledge_rating")
    op.drop_column("guide_profiles", "years_experience")
    op.drop_constraint("ck_profiles_profile_account_type", "profiles", type_="check")
    op.drop_column("profiles", "account_type")
