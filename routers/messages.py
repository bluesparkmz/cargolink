"""
Rotas de mensagens — chat por carga.
"""

from fastapi import APIRouter, Depends, Query
from sqlalchemy.orm import Session

from controllers.messages_controller import (
    count_unread_messages,
    list_conversations,
    list_messages_for_load,
    mark_message_read,
    send_message,
)
from database import get_db
from deps import get_current_user
from models.models import User
from schemas.schemas import (
    ConversationSummary,
    MessageCreateRequest,
    MessageResponse,
    MessagesSummaryResponse,
)

router = APIRouter()


@router.get("/summary", response_model=MessagesSummaryResponse)
def messages_summary(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Total de mensagens não lidas (badge da tab Mensagens)."""
    return MessagesSummaryResponse(unread_count=count_unread_messages(db, current_user))


@router.get("", response_model=list[ConversationSummary])
def list_conversations_route(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista conversas agrupadas por carga."""
    return list_conversations(db, current_user)


@router.get("/loads/{load_id}", response_model=list[MessageResponse])
def get_load_messages(
    load_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Histórico de mensagens de uma carga."""
    return list_messages_for_load(db, current_user, load_id)


@router.post("/loads/{load_id}", response_model=MessageResponse, status_code=201)
def post_message(
    load_id: int,
    data: MessageCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Envia mensagem na conversa da carga."""
    return send_message(db, current_user, load_id, data)


@router.patch("/{message_id}/read", response_model=MessageResponse)
def read_message(
    message_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Marca mensagem recebida como lida."""
    return mark_message_read(db, current_user, message_id)
