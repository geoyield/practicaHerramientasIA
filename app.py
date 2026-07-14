from __future__ import annotations

from datetime import date, datetime, time, timedelta
from pathlib import Path

from fastapi import Depends, FastAPI, HTTPException, Query, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select, text
from sqlalchemy.exc import IntegrityError, SQLAlchemyError
from sqlalchemy.orm import Session, joinedload

from database import get_db
from models import Center, GymClass, Reservation, User
from schemas import AppointmentRequest, ChatRequest, EnrollmentRequest

BASE_DIR = Path(__file__).resolve().parent
STATIC_DIR = BASE_DIR / "static"
TEMPLATES_DIR = BASE_DIR / "templates"

app = FastAPI(
    title="Ponte Cachas Portal",
    description="Portal con PostgreSQL y SQLAlchemy para centros, usuarios, clases y reservas.",
    version="0.3.2",
)
app.mount("/static", StaticFiles(directory=STATIC_DIR), name="static")
templates = Jinja2Templates(directory=TEMPLATES_DIR)

TRAINERS: list[dict[str, str]] = [
    {
        "id": "Marvin",
        "name": "Marvin Bernal",
        "role": "Entrenador",
        "specialty": "Spinning y Funcional",
        "image": "victor.jpg",
        "status": "Disponible",
        "greeting": "¡Hola! Soy Víctor. Puedo ayudarte a ganar fuerza con una progresión segura y realista.",
    },
    {
        "id": "manuel",
        "name": "Manuel Yerbes",
        "role": "Entrenador",
        "specialty": "Gimnasio",
        "image": "manuel.jpg",
        "status": "Disponible",
        "greeting": "¡Hola! Soy Manuel. Cuéntame tu objetivo y diseñamos un plan sostenible para alcanzarlo.",
    },
    {
        "id": "enmanuel",
        "name": "Enmanuel Alejandro",
        "role": "Entrenador",
        "specialty": "Piscina y HITT",
        "image": "enmanuel.jpg",
        "status": "Disponible",
        "greeting": "¡Hola! Soy Enmanuel. Puedo ayudarte con piscina, técnica y HITT.",
    },
    {
        "id": "claudi",
        "name": "Claudi Berenguer",
        "role": "Entrenador",
        "specialty": "Crossfit y Halterofilia",
        "image": "claudi.jpg",
        "status": "Disponible",
        "greeting": "¡Hola! Soy Claudi. Te voy a ayudar con crossfit y halterofilia.",
    },
]


def center_to_dict(center: Center) -> dict[str, object]:
    return {
        "id": center.id,
        "name": center.name,
        "source_name": center.source_name,
        "address": center.address,
        "city": center.city,
        "is_active": center.is_active,
    }


def class_to_dict(gym_class: GymClass) -> dict[str, object]:
    return {
        "id": gym_class.id,
        "name": gym_class.name,
        "time": gym_class.start_time.strftime("%H:%M"),
        "spots": gym_class.spots_available,
        "spots_total": gym_class.spots_total,
        "image": gym_class.image,
        "icon": gym_class.icon,
        "accent": gym_class.accent,
        "gym_id": gym_class.center.id,
        "gym": gym_class.center.name,
        "gym_address": gym_class.center.address,
    }


def reservation_to_dict(reservation: Reservation) -> dict[str, object]:
    payload: dict[str, object] = {
        "id": reservation.id,
        "reservation_type": reservation.reservation_type,
        "status": reservation.status,
        "user_id": reservation.user_id,
        "member_name": reservation.user.full_name,
        "email": reservation.user.email,
        "gym_id": reservation.center_id,
        "gym": reservation.center.name,
        "gym_address": reservation.center.address,
        "date": reservation.reserved_for_date.isoformat(),
        "time": reservation.reserved_for_time.strftime("%H:%M"),
        "created_at": reservation.created_at.isoformat(),
    }
    if reservation.gym_class is not None:
        payload.update(
            {
                "class_id": reservation.gym_class.id,
                "class_name": reservation.gym_class.name,
            }
        )
    else:
        trainer = next(
            (item for item in TRAINERS if item["id"] == reservation.professional_id),
            None,
        )
        payload.update(
            {
                "professional_id": reservation.professional_id,
                "professional_name": trainer["name"] if trainer else reservation.professional_id,
                "service": reservation.service,
            }
        )
    return payload


def get_or_create_user(db: Session, *, full_name: str, email: str) -> User:
    normalized_email = email.strip().lower()
    user = db.scalar(select(User).where(func.lower(User.email) == normalized_email))
    if user is None:
        user = User(full_name=full_name.strip(), email=normalized_email)
        db.add(user)
        db.flush()
    elif user.full_name != full_name.strip():
        user.full_name = full_name.strip()
    return user


def find_trainer(trainer_id: str) -> dict[str, str]:
    trainer = next((item for item in TRAINERS if item["id"] == trainer_id), None)
    if trainer is None:
        raise HTTPException(status_code=404, detail="Profesional no encontrado")
    return trainer


def build_chat_reply(trainer: dict[str, str], message: str) -> str:
    content = message.lower()
    if any(word in content for word in ("hola", "buenas", "hey")):
        return trainer["greeting"]
    if any(word in content for word in ("precio", "cuánto", "cuanto", "coste")):
        return "La primera valoración se muestra como una reserva de demostración. En producción consultaríamos tarifas y tu plan activo."
    if any(word in content for word in ("horario", "hora", "disponible", "reserva")):
        return "Tengo huecos de demostración por la mañana y por la tarde. Pulsa “Reservar sesión” para elegir centro, fecha y hora."
    replies = {
        "carlos": "Para mejorar fuerza empezaría revisando tu experiencia, técnica y número de días disponibles. ¿Cuántos días entrenas ahora?",
        "laura": "Para perder grasa sin perder energía conviene combinar fuerza, pasos diarios y una pauta sostenible. ¿Qué te cuesta más mantener?",
        "miguel": "Podemos trabajar movilidad con una rutina breve y específica. ¿Notas más limitación en cadera, hombros o espalda?",
        "andrea": "Para orientarte bien necesito conocer tu objetivo, horarios, preferencias y posibles restricciones alimentarias. ¿Qué te gustaría mejorar primero?",
    }
    return replies[trainer["id"]]


def build_upcoming(classes: list[GymClass]) -> list[dict[str, str]]:
    weekdays = ["Lun", "Mar", "Mié", "Jue", "Vie", "Sáb", "Dom"]
    months = ["ENE", "FEB", "MAR", "ABR", "MAY", "JUN", "JUL", "AGO", "SEP", "OCT", "NOV", "DIC"]
    offsets = (0, 1, 3)
    upcoming: list[dict[str, str]] = []
    for index, gym_class in enumerate(classes[:3]):
        class_date = date.today() + timedelta(days=offsets[index])
        upcoming.append(
            {
                "day": f"{class_date.day:02d}",
                "month": months[class_date.month - 1],
                "title": gym_class.name,
                "time": (
                    f"{weekdays[class_date.weekday()]}, {class_date.day:02d}/{class_date.month:02d} "
                    f"· {gym_class.start_time.strftime('%H:%M')}"
                ),
                "gym": gym_class.center.name,
            }
        )
    return upcoming


@app.get("/", response_class=HTMLResponse)
def home(request: Request, db: Session = Depends(get_db)):
    centers = list(
        db.scalars(select(Center).where(Center.is_active.is_(True)).order_by(Center.name))
    )
    class_models = list(
        db.scalars(
            select(GymClass)
            .options(joinedload(GymClass.center))
            .where(GymClass.is_active.is_(True))
            .order_by(GymClass.start_time)
        )
    )
    if not centers:
        raise HTTPException(
            status_code=503,
            detail="La base de datos no tiene centros. Ejecuta: uv run python -m scripts.seed_db",
        )
    return templates.TemplateResponse(
        request=request,
        name="index.html",
        context={
            "gyms": [center_to_dict(center) for center in centers],
            "classes": [class_to_dict(item) for item in class_models],
            "trainers": TRAINERS,
            "upcoming": build_upcoming(class_models),
            "today_label": date.today().strftime("%d/%m/%Y"),
        },
    )


@app.get("/api/centers")
def get_centers(db: Session = Depends(get_db)):
    centers = db.scalars(select(Center).order_by(Center.name)).all()
    return {"centers": [center_to_dict(center) for center in centers]}


@app.get("/api/gyms", include_in_schema=False)
def get_gyms_compatibility(db: Session = Depends(get_db)):
    centers = db.scalars(select(Center).order_by(Center.name)).all()
    return {"gyms": [center_to_dict(center) for center in centers]}


@app.get("/api/classes")
def get_classes(
    center_id: str | None = Query(default=None),
    activity: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    statement = (
        select(GymClass)
        .options(joinedload(GymClass.center))
        .where(GymClass.is_active.is_(True))
        .order_by(GymClass.start_time)
    )
    if center_id:
        statement = statement.where(GymClass.center_id == center_id)
    if activity:
        statement = statement.where(func.lower(GymClass.name) == activity.lower())
    classes = db.scalars(statement).all()
    return {"classes": [class_to_dict(item) for item in classes]}


@app.post("/api/classes/enroll", status_code=201)
def enroll(payload: EnrollmentRequest, db: Session = Depends(get_db)):
    try:
        gym_class = db.scalar(
            select(GymClass)
            .where(GymClass.id == payload.class_id, GymClass.is_active.is_(True))
            .with_for_update()
        )
        if gym_class is None:
            raise HTTPException(status_code=404, detail="Clase no encontrada")
        if gym_class.spots_available <= 0:
            raise HTTPException(status_code=409, detail="No quedan plazas disponibles")

        user = get_or_create_user(
            db,
            full_name=payload.member_name,
            email=str(payload.email),
        )
        reservation_date = date.today()
        duplicate = db.scalar(
            select(Reservation.id).where(
                Reservation.user_id == user.id,
                Reservation.gym_class_id == gym_class.id,
                Reservation.reserved_for_date == reservation_date,
                Reservation.status == "confirmed",
            )
        )
        if duplicate is not None:
            raise HTTPException(status_code=409, detail="Ya estás inscrito en esta clase")

        gym_class.spots_available -= 1
        reservation = Reservation(
            user_id=user.id,
            center_id=gym_class.center_id,
            gym_class_id=gym_class.id,
            reservation_type="class",
            reserved_for_date=reservation_date,
            reserved_for_time=gym_class.start_time,
            status="confirmed",
        )
        db.add(reservation)
        db.commit()

        saved = db.scalar(
            select(Reservation)
            .options(
                joinedload(Reservation.user),
                joinedload(Reservation.center),
                joinedload(Reservation.gym_class),
            )
            .where(Reservation.id == reservation.id)
        )
        assert saved is not None
        return {
            "ok": True,
            "message": (
                f"Inscripción confirmada para {saved.gym_class.name} a las "
                f"{saved.reserved_for_time.strftime('%H:%M')} en {saved.center.name}."
            ),
            "remaining_spots": gym_class.spots_available,
            "enrollment": reservation_to_dict(saved),
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="La inscripción ya existe") from error


@app.post("/api/appointments", status_code=201)
def create_appointment(payload: AppointmentRequest, db: Session = Depends(get_db)):
    trainer = find_trainer(payload.professional_id)
    if payload.service == "Consulta con dietista" and trainer["role"] != "Dietista":
        raise HTTPException(status_code=422, detail="Selecciona un dietista para esta consulta")
    if payload.service == "Entrenamiento personal" and trainer["role"] == "Dietista":
        raise HTTPException(status_code=422, detail="Selecciona un entrenador para esta sesión")

    center = db.get(Center, payload.gym_id)
    if center is None or not center.is_active:
        raise HTTPException(status_code=404, detail="Centro no encontrado")

    appointment_time = time.fromisoformat(payload.appointment_time)
    if payload.appointment_date < date.today():
        raise HTTPException(status_code=422, detail="La fecha no puede estar en el pasado")

    try:
        user = get_or_create_user(
            db,
            full_name=payload.member_name,
            email=str(payload.email),
        )
        conflict = db.scalar(
            select(Reservation.id).where(
                Reservation.professional_id == payload.professional_id,
                Reservation.reserved_for_date == payload.appointment_date,
                Reservation.reserved_for_time == appointment_time,
                Reservation.status == "confirmed",
            )
        )
        if conflict is not None:
            raise HTTPException(
                status_code=409,
                detail="El profesional ya tiene una reserva en ese horario",
            )

        reservation = Reservation(
            user_id=user.id,
            center_id=center.id,
            professional_id=trainer["id"],
            reservation_type="appointment",
            service=payload.service,
            reserved_for_date=payload.appointment_date,
            reserved_for_time=appointment_time,
            status="confirmed",
        )
        db.add(reservation)
        db.commit()

        saved = db.scalar(
            select(Reservation)
            .options(joinedload(Reservation.user), joinedload(Reservation.center))
            .where(Reservation.id == reservation.id)
        )
        assert saved is not None
        return {
            "ok": True,
            "message": (
                f"Reserva confirmada con {trainer['name']} el "
                f"{saved.reserved_for_date.isoformat()} a las "
                f"{saved.reserved_for_time.strftime('%H:%M')} en {saved.center.name}."
            ),
            "appointment": reservation_to_dict(saved),
        }
    except HTTPException:
        db.rollback()
        raise
    except IntegrityError as error:
        db.rollback()
        raise HTTPException(status_code=409, detail="No se pudo crear la reserva") from error


@app.get("/api/reservations")
def get_reservations(
    email: str | None = Query(default=None),
    db: Session = Depends(get_db),
):
    statement = (
        select(Reservation)
        .options(
            joinedload(Reservation.user),
            joinedload(Reservation.center),
            joinedload(Reservation.gym_class),
        )
        .order_by(Reservation.reserved_for_date, Reservation.reserved_for_time)
    )
    if email:
        statement = statement.join(Reservation.user).where(
            func.lower(User.email) == email.strip().lower()
        )
    reservations = db.scalars(statement).unique().all()
    return {"reservations": [reservation_to_dict(item) for item in reservations]}


@app.post("/api/chat/{trainer_id}")
def chat(trainer_id: str, payload: ChatRequest):
    trainer = find_trainer(trainer_id)
    return {
        "trainer_id": trainer["id"],
        "trainer_name": trainer["name"],
        "reply": build_chat_reply(trainer, payload.message),
    }


@app.get("/api/demo-state")
def demo_state(db: Session = Depends(get_db)):
    reservations = db.scalars(
        select(Reservation)
        .options(
            joinedload(Reservation.user),
            joinedload(Reservation.center),
            joinedload(Reservation.gym_class),
        )
        .order_by(Reservation.id)
    ).unique().all()
    serialized = [reservation_to_dict(item) for item in reservations]
    return {
        "enrollments": [item for item in serialized if item["reservation_type"] == "class"],
        "appointments": [item for item in serialized if item["reservation_type"] == "appointment"],
    }


@app.get("/health")
def health(db: Session = Depends(get_db)):
    try:
        db.execute(text("SELECT 1"))
        return {"status": "ok", "database": "connected", "timestamp": datetime.now().isoformat()}
    except SQLAlchemyError as error:
        raise HTTPException(status_code=503, detail="Base de datos no disponible") from error
