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
from models.models import Load, Vehicle


def get_dashboard_stats(db: Session) -> dict:
    """Agrega contagens para os cards do topo do app."""
    now = datetime.now(timezone.utc)
    month_start = now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)

    available_loads = (
        db.query(func.count(Load.id)).filter(Load.status == LOAD_STATUS_AVAILABLE).scalar() or 0
    )

    active_loads = (
        db.query(func.count(Load.id)).filter(Load.status.in_(LOAD_ACTIVE_STATUSES)).scalar() or 0
    )

    completed_this_month = (
        db.query(func.count(Load.id))
        .filter(
            Load.status == LOAD_STATUS_COMPLETED,
            Load.updated_at >= month_start,
        )
        .scalar()
        or 0
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
