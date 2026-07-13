from __future__ import annotations

import json
from datetime import time
from pathlib import Path

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from models import Center, GymClass, Reservation

BASE_DIR = Path(__file__).resolve().parent

CLASS_SEEDS: list[dict[str, object]] = [
    {
        "id": "yoga-0800",
        "center_id": "gym-1",
        "name": "Yoga",
        "start_time": time(8, 0),
        "spots_total": 10,
        "spots_available": 10,
        "image": "yoga.jpg",
        "icon": "🧘",
        "accent": "violet",
    },
    {
        "id": "spinning-1000",
        "center_id": "gym-2",
        "name": "Spinning",
        "start_time": time(10, 0),
        "spots_total": 6,
        "spots_available": 6,
        "image": "spinning.jpg",
        "icon": "🚴",
        "accent": "amber",
    },
    {
        "id": "pilates-1130",
        "center_id": "gym-3",
        "name": "Pilates",
        "start_time": time(11, 30),
        "spots_total": 8,
        "spots_available": 8,
        "image": "pilates.jpg",
        "icon": "🤸",
        "accent": "teal",
    },
    {
        "id": "fuerza-1730",
        "center_id": "gym-1",
        "name": "Fuerza",
        "start_time": time(17, 30),
        "spots_total": 12,
        "spots_available": 12,
        "image": "fuerza.jpg",
        "icon": "🏋️",
        "accent": "blue",
    },
    {
        "id": "hiit-1900",
        "center_id": "gym-4",
        "name": "HIIT",
        "start_time": time(19, 0),
        "spots_total": 9,
        "spots_available": 9,
        "image": "hiit.jpg",
        "icon": "⚡",
        "accent": "rose",
    },
]


def load_center_seeds() -> list[dict[str, str]]:
    return json.loads(
        (BASE_DIR / "data" / "gimnasios.json").read_text(encoding="utf-8")
    )


def seed_database(session: Session) -> dict[str, int]:
    centers_created = 0
    classes_created = 0

    for data in load_center_seeds():
        center = session.get(Center, data["id"])
        if center is None:
            center = Center(**data)
            session.add(center)
            centers_created += 1
        else:
            center.name = data["name"]
            center.source_name = data.get("source_name")
            center.address = data["address"]
            center.city = data["city"]
            center.is_active = True

    session.flush()

    for data in CLASS_SEEDS:
        gym_class = session.get(GymClass, str(data["id"]))
        if gym_class is None:
            session.add(GymClass(**data))
            classes_created += 1
            continue

        # No reiniciamos spots_available para no borrar reservas ya realizadas.
        gym_class.center_id = str(data["center_id"])
        gym_class.name = str(data["name"])
        gym_class.start_time = data["start_time"]  # type: ignore[assignment]
        gym_class.spots_total = int(data["spots_total"])
        confirmed_reservations = session.scalar(
            select(func.count(Reservation.id)).where(
                Reservation.gym_class_id == gym_class.id,
                Reservation.status == "confirmed",
            )
        ) or 0
        gym_class.spots_available = max(
            gym_class.spots_total - confirmed_reservations, 0
        )
        gym_class.image = str(data["image"])
        gym_class.icon = str(data["icon"])
        gym_class.accent = str(data["accent"])
        gym_class.is_active = True

    session.commit()
    return {
        "centers_created": centers_created,
        "classes_created": classes_created,
    }
