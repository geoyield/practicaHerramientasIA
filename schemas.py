from __future__ import annotations

from datetime import date
from typing import Literal

from pydantic import BaseModel, EmailStr, Field


class EnrollmentRequest(BaseModel):
    class_id: str
    member_name: str = Field(min_length=2, max_length=120)
    email: EmailStr


class AppointmentRequest(BaseModel):
    professional_id: str
    gym_id: str
    member_name: str = Field(min_length=2, max_length=120)
    email: EmailStr
    service: Literal["Entrenamiento personal", "Consulta con dietista"]
    appointment_date: date
    appointment_time: str = Field(pattern=r"^([01]\d|2[0-3]):[0-5]\d$")


class ChatRequest(BaseModel):
    message: str = Field(min_length=1, max_length=600)
