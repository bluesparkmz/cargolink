"""
Controller de notificações in-app.
"""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from models.models import Notification, User


def list_notifications(
    db: Session,
    user: User,
    *,
    unread_only: bool = False,
    limit: int = 50,
    offset: int = 0,
) -> list[Notification]:
    """Lista notificações do utilizador."""
    query = db.query(Notification).filter(Notification.user_id == user.id)
    if unread_only:
        query = query.filter(Notification.read.is_(False))
    return query.order_by(Notification.created_at.desc()).offset(offset).limit(limit).all()


def count_unread(db: Session, user: User) -> int:
    """Total de notificações não lidas."""
    return (
        db.query(func.count(Notification.id))
        .filter(Notification.user_id == user.id, Notification.read.is_(False))
        .scalar()
        or 0
    )


def mark_notification_read(db: Session, user: User, notification_id: int) -> Notification:
    """Marca uma notificação como lida."""
    notification = (
        db.query(Notification)
        .filter(Notification.id == notification_id, Notification.user_id == user.id)
        .first()
    )
    if notification is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Notificação não encontrada",
        )
    notification.read = True
    db.commit()
    db.refresh(notification)
    return notification


def mark_all_read(db: Session, user: User) -> int:
    """Marca todas como lidas; devolve quantidade atualizada."""
    updated = (
        db.query(Notification)
        .filter(Notification.user_id == user.id, Notification.read.is_(False))
        .update({Notification.read: True}, synchronize_session=False)
    )
    db.commit()
    return updated
