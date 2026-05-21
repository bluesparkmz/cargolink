"""
Rotas de notificações in-app.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from controllers.notifications_controller import (
    count_unread,
    list_notifications,
    mark_all_read,
    mark_notification_read,
)
from database import get_db
from deps import get_current_user
from models import User
from schemas import NotificationResponse, UnreadCountResponse

router = APIRouter()


@router.get("", response_model=list[NotificationResponse])
def list_all(
    unread_only: bool = Query(False),
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista notificações do utilizador."""
    return list_notifications(
        db, current_user, unread_only=unread_only, limit=limit, offset=offset
    )


@router.get("/unread-count", response_model=UnreadCountResponse)
def unread_count(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Badge do sino de notificações."""
    return UnreadCountResponse(count=count_unread(db, current_user))


@router.patch("/read-all")
def read_all(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca todas as notificações como lidas."""
    updated = mark_all_read(db, current_user)
    return {"updated": updated}


@router.patch("/{notification_id}/read", response_model=NotificationResponse)
def read_one(
    notification_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca uma notificação como lida."""
    return mark_notification_read(db, current_user, notification_id)
