"""
Estatísticas do dashboard (ecrã inicial marketplace).
"""

from datetime import datetime, timezone

from sqlalchemy import func
from sqlalchemy.orm import Session

from constants import (
    LOAD_ACTIVE_STATUSES,
    LOAD_STATUS_AVAILABLE,
    LOAD_STATUS_COMPLETED,
)
from controllers.loads_controller import list_related_loads
from models.models import Load, User, Vehicle


def get_dashboard_stats(db: Session, user: User) -> dict:
    """Agrega contagens para os cards do topo do app (escopo do utilizador)."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    if user.user_type == "empresa":
        available_loads = (
            db.query(func.count(Load.id)).filter(Load.status == LOAD_STATUS_AVAILABLE).scalar() or 0
        )
    else:
        available_loads = len(
            list_related_loads(db, user, status_filter=LOAD_STATUS_AVAILABLE)
        )

    related_active = [
        load
        for load in list_related_loads(db, user)
        if load.status in LOAD_ACTIVE_STATUSES
    ]
    active_loads = len(related_active)

    related_completed = list_related_loads(db, user, status_filter=LOAD_STATUS_COMPLETED)
    completed_this_month = sum(
        1 for load in related_completed if load.updated_at and load.updated_at >= month_start
    )

    available_vehicles = (
        db.query(func.count(Vehicle.id)).filter(Vehicle.status == LOAD_STATUS_AVAILABLE).scalar()
        or 0
    )

    return {
        "available_loads": available_loads,
        "active_loads": active_loads,
        "completed_this_month": completed_this_month,
        "available_vehicles": available_vehicles,
    }
