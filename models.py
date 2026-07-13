from __future__ import annotations

from datetime import date, datetime, time

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Time,
    UniqueConstraint,
    func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


class TimestampMixin:
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), server_default=func.now(), onupdate=func.now(), nullable=False
    )


class User(TimestampMixin, Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    full_name: Mapped[str] = mapped_column(String(120), nullable=False)
    email: Mapped[str] = mapped_column(String(255), nullable=False, unique=True, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    reservations: Mapped[list[Reservation]] = relationship(
        back_populates="user", cascade="all, delete-orphan"
    )


class Center(TimestampMixin, Base):
    __tablename__ = "centers"

    id: Mapped[str] = mapped_column(String(36), primary_key=True)
    name: Mapped[str] = mapped_column(String(150), nullable=False, unique=True)
    source_name: Mapped[str | None] = mapped_column(String(80))
    address: Mapped[str] = mapped_column(String(255), nullable=False)
    city: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    classes: Mapped[list[GymClass]] = relationship(
        back_populates="center", cascade="all, delete-orphan"
    )
    reservations: Mapped[list[Reservation]] = relationship(back_populates="center")


class GymClass(TimestampMixin, Base):
    __tablename__ = "gym_classes"
    __table_args__ = (
        CheckConstraint("spots_total >= 0", name="ck_gym_classes_spots_total_nonnegative"),
        CheckConstraint("spots_available >= 0", name="ck_gym_classes_spots_available_nonnegative"),
        CheckConstraint("spots_available <= spots_total", name="ck_gym_classes_spots_within_total"),
        Index("ix_gym_classes_center_name", "center_id", "name"),
    )

    id: Mapped[str] = mapped_column(String(50), primary_key=True)
    center_id: Mapped[str] = mapped_column(
        ForeignKey("centers.id", ondelete="CASCADE"), nullable=False, index=True
    )
    name: Mapped[str] = mapped_column(String(100), nullable=False, index=True)
    start_time: Mapped[time] = mapped_column(Time, nullable=False)
    spots_total: Mapped[int] = mapped_column(Integer, nullable=False)
    spots_available: Mapped[int] = mapped_column(Integer, nullable=False)
    image: Mapped[str] = mapped_column(String(150), nullable=False)
    icon: Mapped[str] = mapped_column(String(20), nullable=False)
    accent: Mapped[str] = mapped_column(String(30), nullable=False)
    is_active: Mapped[bool] = mapped_column(Boolean, nullable=False, default=True, server_default="true")

    center: Mapped[Center] = relationship(back_populates="classes")
    reservations: Mapped[list[Reservation]] = relationship(back_populates="gym_class")


class Reservation(TimestampMixin, Base):
    __tablename__ = "reservations"
    __table_args__ = (
        CheckConstraint(
            "reservation_type IN ('class', 'appointment')",
            name="ck_reservations_type",
        ),
        CheckConstraint(
            "status IN ('confirmed', 'cancelled', 'completed')",
            name="ck_reservations_status",
        ),
        CheckConstraint(
            "(reservation_type = 'class' AND gym_class_id IS NOT NULL "
            "AND professional_id IS NULL) OR "
            "(reservation_type = 'appointment' AND gym_class_id IS NULL "
            "AND professional_id IS NOT NULL AND service IS NOT NULL)",
            name="ck_reservations_payload_by_type",
        ),
        UniqueConstraint(
            "user_id",
            "gym_class_id",
            "reserved_for_date",
            name="uq_reservations_user_class_date",
        ),
        UniqueConstraint(
            "professional_id",
            "reserved_for_date",
            "reserved_for_time",
            name="uq_reservations_professional_slot",
        ),
        Index("ix_reservations_user_date", "user_id", "reserved_for_date"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(
        ForeignKey("users.id", ondelete="CASCADE"), nullable=False, index=True
    )
    center_id: Mapped[str] = mapped_column(
        ForeignKey("centers.id", ondelete="RESTRICT"), nullable=False, index=True
    )
    gym_class_id: Mapped[str | None] = mapped_column(
        ForeignKey("gym_classes.id", ondelete="RESTRICT"), nullable=True, index=True
    )
    professional_id: Mapped[str | None] = mapped_column(String(50), nullable=True, index=True)
    reservation_type: Mapped[str] = mapped_column(String(20), nullable=False)
    service: Mapped[str | None] = mapped_column(String(120), nullable=True)
    reserved_for_date: Mapped[date] = mapped_column(Date, nullable=False)
    reserved_for_time: Mapped[time] = mapped_column(Time, nullable=False)
    status: Mapped[str] = mapped_column(
        String(20), nullable=False, default="confirmed", server_default="confirmed"
    )

    user: Mapped[User] = relationship(back_populates="reservations")
    center: Mapped[Center] = relationship(back_populates="reservations")
    gym_class: Mapped[GymClass | None] = relationship(back_populates="reservations")
