"""
Estatísticas do perfil do cliente (ecrã Perfil).
"""

from sqlalchemy import func
from sqlalchemy.orm import Session

from constants import (
    LOAD_ACTIVE_STATUSES,
    LOAD_STATUS_CANCELLED,
    LOAD_STATUS_COMPLETED,
)
from controllers.clients_controller import get_my_client
from models import Load, Rating, User


def get_client_stats(db: Session, user: User) -> dict:
    """Contagens para os cards Minhas atividades."""
    client = get_my_client(db, user)

    published_count = (
        db.query(func.count(Load.id))
        .filter(Load.client_id == client.id, Load.status != LOAD_STATUS_CANCELLED)
        .scalar()
        or 0
    )

    in_progress_count = (
        db.query(func.count(Load.id))
        .filter(Load.client_id == client.id, Load.status.in_(LOAD_ACTIVE_STATUSES))
        .scalar()
        or 0
    )

    completed_count = (
        db.query(func.count(Load.id))
        .filter(Load.client_id == client.id, Load.status == LOAD_STATUS_COMPLETED)
        .scalar()
        or 0
    )

    avg, count = (
        db.query(func.avg(Rating.score), func.count(Rating.id))
        .filter(Rating.rated_user_id == user.id, Rating.score.isnot(None))
        .first()
    ) or (None, 0)

    return {
        "published_count": published_count,
        "in_progress_count": in_progress_count,
        "completed_count": completed_count,
        "average_rating": round(float(avg), 1) if avg is not None else None,
        "rating_count": int(count or 0),
    }
