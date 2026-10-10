"""Relational schema for Virun. Supabase Auth owns auth.users; this app owns public tables."""
from __future__ import annotations

from datetime import date, datetime, time
from uuid import UUID, uuid4

from sqlalchemy import (
    Boolean, CheckConstraint, Column, Date, DateTime, ForeignKey, Index, Integer,
    Numeric, SmallInteger, String, Text, Time, UniqueConstraint, Uuid,
    Table, func, text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlalchemy.orm import Mapped, mapped_column

from app.db.base import Base

# External Supabase-managed table, included only to resolve the profile FK.
# Migrations must never create, alter, or drop auth.users.
Table("users", Base.metadata, Column("id", Uuid(as_uuid=True), primary_key=True), schema="auth", info={"managed_externally": True})


class UUIDPrimaryKey:
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), primary_key=True, default=uuid4)


class Timestamped:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    updated_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False)


class CreatedAt:
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Profile(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "profiles"
    id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("auth.users.id", ondelete="CASCADE"), primary_key=True)
    display_name: Mapped[str] = mapped_column(String(120), nullable=False)
    phone: Mapped[str | None] = mapped_column(String(32), unique=True)
    avatar_url: Mapped[str | None] = mapped_column(Text)
    locale: Mapped[str] = mapped_column(String(20), server_default="en", nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)


class Role(Base):
    __tablename__ = "roles"
    name: Mapped[str] = mapped_column(String(40), primary_key=True)
    description: Mapped[str | None] = mapped_column(Text)


class ProfileRole(Base):
    __tablename__ = "profile_roles"
    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    role_name: Mapped[str] = mapped_column(ForeignKey("roles.name", ondelete="RESTRICT"), primary_key=True)
    assigned_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    assigned_by: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))


class GuideProfile(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "guide_profiles"
    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), unique=True, nullable=False)
    biography: Mapped[str | None] = mapped_column(Text)
    city: Mapped[str] = mapped_column(String(120), nullable=False)
    verification_status: Mapped[str] = mapped_column(String(24), server_default="unverified", nullable=False)
    is_listed: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)
    __table_args__ = (CheckConstraint("verification_status in ('unverified','pending','verified','rejected')", name="guide_verification_status"),)


class GuideLanguage(Base):
    __tablename__ = "guide_languages"
    code: Mapped[str] = mapped_column(String(16), primary_key=True)
    name: Mapped[str] = mapped_column(String(80), unique=True, nullable=False)


class GuideProfileLanguage(Base):
    __tablename__ = "guide_profile_languages"
    guide_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("guide_profiles.id", ondelete="CASCADE"), primary_key=True)
    language_code: Mapped[str] = mapped_column(ForeignKey("guide_languages.code", ondelete="RESTRICT"), primary_key=True)


class GuideService(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "guide_services"
    guide_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("guide_profiles.id", ondelete="CASCADE"), nullable=False)
    service_type: Mapped[str] = mapped_column(String(60), nullable=False)
    price_inr: Mapped[int | None] = mapped_column(Integer)
    price_unit: Mapped[str | None] = mapped_column(String(24))
    is_active: Mapped[bool] = mapped_column(Boolean, server_default=text("true"), nullable=False)
    __table_args__ = (CheckConstraint("price_inr is null or price_inr >= 0", name="guide_service_price_nonnegative"), UniqueConstraint("guide_profile_id", "service_type"))


class GuideAvailability(UUIDPrimaryKey, Base):
    __tablename__ = "guide_availability"
    guide_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("guide_profiles.id", ondelete="CASCADE"), nullable=False)
    weekday: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    starts_at: Mapped[time] = mapped_column(Time, nullable=False)
    ends_at: Mapped[time] = mapped_column(Time, nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), server_default="Asia/Kolkata", nullable=False)
    valid_from: Mapped[date | None] = mapped_column(Date)
    valid_until: Mapped[date | None] = mapped_column(Date)
    __table_args__ = (CheckConstraint("weekday between 0 and 6", name="availability_weekday"), CheckConstraint("starts_at < ends_at", name="availability_time_order"))


class Destination(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "destinations"
    slug: Mapped[str] = mapped_column(String(120), unique=True, nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    region: Mapped[str | None] = mapped_column(String(120))
    description: Mapped[str | None] = mapped_column(Text)
    data_source: Mapped[str] = mapped_column(String(80), server_default="SAMPLE", nullable=False)
    is_published: Mapped[bool] = mapped_column(Boolean, server_default=text("false"), nullable=False)


class Attraction(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "attractions"
    destination_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("destinations.id", ondelete="CASCADE"), nullable=False)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    description: Mapped[str | None] = mapped_column(Text)
    address: Mapped[str | None] = mapped_column(Text)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    data_source: Mapped[str] = mapped_column(String(80), server_default="SAMPLE", nullable=False)


class TransportStop(Base, CreatedAt):
    __tablename__ = "transport_stops"
    stop_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    name: Mapped[str] = mapped_column(String(160), nullable=False)
    city: Mapped[str | None] = mapped_column(String(120))
    aliases: Mapped[list[str]] = mapped_column(ARRAY(Text), server_default="{}", nullable=False)
    latitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    longitude: Mapped[float | None] = mapped_column(Numeric(9, 6))
    data_source: Mapped[str] = mapped_column(String(80), server_default="SIMULATED", nullable=False)


class TransportOption(Base, CreatedAt):
    __tablename__ = "transport_options"
    option_id: Mapped[str] = mapped_column(String(100), primary_key=True)
    origin_stop_id: Mapped[str] = mapped_column(ForeignKey("transport_stops.stop_id", ondelete="RESTRICT"), nullable=False)
    destination_stop_id: Mapped[str] = mapped_column(ForeignKey("transport_stops.stop_id", ondelete="RESTRICT"), nullable=False)
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fare_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    luggage_fee_inr: Mapped[int] = mapped_column(Integer, server_default="0", nullable=False)
    status: Mapped[str] = mapped_column(String(24), nullable=False)
    data_source: Mapped[str] = mapped_column(String(80), server_default="SIMULATED", nullable=False)
    operator: Mapped[str | None] = mapped_column(String(120))
    seat_type: Mapped[str | None] = mapped_column(String(16))
    ac: Mapped[bool | None] = mapped_column(Boolean)
    reliability_score: Mapped[float] = mapped_column(Numeric(3, 2), server_default="0.90", nullable=False)
    origin_lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    origin_lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    destination_lat: Mapped[float | None] = mapped_column(Numeric(9, 6))
    destination_lng: Mapped[float | None] = mapped_column(Numeric(9, 6))
    __table_args__ = (
        CheckConstraint("mode in ('bus','train','metro','flight','cab')", name="transport_mode"),
        CheckConstraint("status in ('available_in_demo','available','cancelled','sold_out')", name="transport_status"),
        CheckConstraint("fare_inr >= 0 and luggage_fee_inr >= 0", name="transport_nonnegative_fares"),
        CheckConstraint("arrival_at > departure_at", name="transport_time_order"),
        CheckConstraint("origin_stop_id <> destination_stop_id", name="transport_distinct_stops"),
        CheckConstraint("reliability_score between 0 and 1", name="transport_reliability"),
        Index("ix_transport_options_origin_departure", "origin_stop_id", "departure_at"),
        Index("ix_transport_options_destination", "destination_stop_id"),
        Index("ix_transport_options_status", "status"),
    )


class TripRequest(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "trip_requests"
    profile_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))
    origin: Mapped[str] = mapped_column(String(160), nullable=False)
    destination: Mapped[str] = mapped_column(String(160), nullable=False)
    departure_date: Mapped[date] = mapped_column(Date, nullable=False)
    arrival_deadline: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    timezone: Mapped[str] = mapped_column(String(64), server_default="Asia/Kolkata", nullable=False)
    passengers: Mapped[int] = mapped_column(SmallInteger, server_default="1", nullable=False)
    budget_inr: Mapped[int | None] = mapped_column(Integer)
    preferences: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    status: Mapped[str] = mapped_column(String(24), server_default="planned", nullable=False)
    __table_args__ = (CheckConstraint("passengers between 1 and 10", name="trip_passengers"), CheckConstraint("budget_inr is null or budget_inr >= 0", name="trip_budget"))


class Itinerary(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "itineraries"
    # Generated sightseeing plans can exist before a transport TripRequest is saved.
    trip_request_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("trip_requests.id", ondelete="CASCADE"))
    label: Mapped[str] = mapped_column(String(80), nullable=False)
    itinerary_type: Mapped[str] = mapped_column(String(24), server_default="transport", nullable=False)
    generated_content: Mapped[dict | None] = mapped_column(JSONB)
    duration_days: Mapped[int | None] = mapped_column(SmallInteger)
    duration_nights: Mapped[int | None] = mapped_column(SmallInteger)
    budget_inr: Mapped[float | None] = mapped_column(Numeric(12, 2))
    total_fare_inr: Mapped[int | None] = mapped_column(Integer)
    currency: Mapped[str] = mapped_column(String(3), server_default="INR", nullable=False)
    duration_minutes: Mapped[int | None] = mapped_column(Integer)
    data_source: Mapped[str] = mapped_column(String(80), nullable=False)
    __table_args__ = (
        CheckConstraint("(total_fare_inr is null and duration_minutes is null) or (total_fare_inr is not null and duration_minutes is not null and total_fare_inr >= 0 and duration_minutes > 0)", name="itinerary_nonnegative"),
        CheckConstraint("itinerary_type in ('transport','sightseeing')", name="itinerary_type"),
        CheckConstraint("duration_days is null or duration_days between 1 and 15", name="itinerary_duration_days"),
        CheckConstraint("duration_nights is null or duration_nights between 0 and 30", name="itinerary_duration_nights"),
        CheckConstraint("budget_inr is null or budget_inr > 0", name="itinerary_budget"),
    )


class ItineraryLeg(UUIDPrimaryKey, Base):
    __tablename__ = "itinerary_legs"
    itinerary_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("itineraries.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    transport_option_id: Mapped[str | None] = mapped_column(ForeignKey("transport_options.option_id", ondelete="SET NULL"))
    mode: Mapped[str] = mapped_column(String(16), nullable=False)
    origin_name: Mapped[str] = mapped_column(String(160), nullable=False)
    destination_name: Mapped[str] = mapped_column(String(160), nullable=False)
    departure_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    arrival_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    fare_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    __table_args__ = (UniqueConstraint("itinerary_id", "sequence"), CheckConstraint("sequence > 0", name="itinerary_leg_sequence"), CheckConstraint("arrival_at > departure_at", name="itinerary_leg_time_order"))


class Booking(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "bookings"
    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    itinerary_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("itineraries.id", ondelete="RESTRICT"), nullable=False)
    provider: Mapped[str] = mapped_column(String(80), nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(160), unique=True)
    status: Mapped[str] = mapped_column(String(24), server_default="pending", nullable=False)
    total_amount_inr: Mapped[int] = mapped_column(Integer, nullable=False)
    __table_args__ = (CheckConstraint("total_amount_inr >= 0", name="booking_amount"), CheckConstraint("status in ('pending','confirmed','cancelled','failed','refunded')", name="booking_status"))


class BookingLeg(UUIDPrimaryKey, Base):
    __tablename__ = "booking_legs"
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    sequence: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    provider_reference: Mapped[str | None] = mapped_column(String(160))
    status: Mapped[str] = mapped_column(String(24), server_default="pending", nullable=False)
    snapshot: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    __table_args__ = (UniqueConstraint("booking_id", "sequence"),)


class Payment(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "payments"
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id", ondelete="RESTRICT"), nullable=False)
    processor: Mapped[str] = mapped_column(String(80), nullable=False)
    processor_reference: Mapped[str | None] = mapped_column(String(180), unique=True)
    amount_minor: Mapped[int] = mapped_column(Integer, nullable=False)
    currency: Mapped[str] = mapped_column(String(3), server_default="INR", nullable=False)
    status: Mapped[str] = mapped_column(String(24), server_default="created", nullable=False)
    __table_args__ = (CheckConstraint("amount_minor >= 0", name="payment_amount"), CheckConstraint("status in ('created','authorized','captured','failed','refunded')", name="payment_status"))


class Review(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "reviews"
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    reviewer_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    guide_profile_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("guide_profiles.id", ondelete="SET NULL"))
    rating: Mapped[int] = mapped_column(SmallInteger, nullable=False)
    body: Mapped[str | None] = mapped_column(Text)
    __table_args__ = (UniqueConstraint("booking_id", "reviewer_profile_id"), CheckConstraint("rating between 1 and 5", name="review_rating"))


class Conversation(UUIDPrimaryKey, Timestamped, Base):
    __tablename__ = "conversations"
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    __table_args__ = (UniqueConstraint("booking_id"),)


class ConversationParticipant(Base):
    __tablename__ = "conversation_participants"
    conversation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), primary_key=True)
    profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="CASCADE"), primary_key=True)
    joined_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)


class Message(UUIDPrimaryKey, Base):
    __tablename__ = "messages"
    conversation_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("conversations.id", ondelete="CASCADE"), nullable=False)
    sender_profile_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="RESTRICT"), nullable=False)
    body: Mapped[str] = mapped_column(Text, nullable=False)
    sent_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
    read_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True))


class TripEvent(UUIDPrimaryKey, Base):
    __tablename__ = "trip_events"
    booking_id: Mapped[UUID] = mapped_column(Uuid(as_uuid=True), ForeignKey("bookings.id", ondelete="CASCADE"), nullable=False)
    actor_profile_id: Mapped[UUID | None] = mapped_column(Uuid(as_uuid=True), ForeignKey("profiles.id", ondelete="SET NULL"))
    event_type: Mapped[str] = mapped_column(String(40), nullable=False)
    details: Mapped[dict] = mapped_column(JSONB, server_default="{}", nullable=False)
    occurred_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), server_default=func.now(), nullable=False)
