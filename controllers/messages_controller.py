"""
Controller de mensagens — chat por carga.
"""

from fastapi import HTTPException, status
from sqlalchemy import func
from sqlalchemy.orm import Session

from controllers.notifications_controller import create_notification, emit_notification
from controllers.realtime_events import emit_to_rooms
from models.models import Client, Company, Driver, Load, LoadProposal, Message, Trip, User
from schemas.schemas import MessageCreateRequest


def _user_can_access_load_chat(db: Session, user: User, load: Load) -> None:
    """Cliente da carga, motorista com proposta ou motorista da viagem."""
    if user.user_type == "cliente":
        client = db.query(Client).filter(Client.user_id == user.id).first()
        if client and load.client_id == client.id:
            return

    if user.user_type == "motorista":
        driver = db.query(Driver).filter(Driver.user_id == user.id).first()
        if driver is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")

        has_proposal = (
            db.query(LoadProposal)
            .filter(LoadProposal.load_id == load.id, LoadProposal.driver_id == driver.id)
            .first()
        )
        trip = db.query(Trip).filter(Trip.load_id == load.id, Trip.driver_id == driver.id).first()
        if has_proposal or trip:
            return

    if user.user_type == "empresa":
        company = db.query(Company).filter(Company.user_id == user.id).first()
        if company is None:
            raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")

        has_proposal = (
            db.query(LoadProposal)
            .filter(LoadProposal.load_id == load.id, LoadProposal.company_id == company.id)
            .first()
        )
        trip = db.query(Trip).filter(Trip.load_id == load.id, Trip.company_id == company.id).first()
        if has_proposal or trip:
            return

    if user.user_type == "admin":
        return

    raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso a esta conversa")


def count_unread_messages(db: Session, user: User) -> int:
    """Mensagens recebidas e não lidas."""
    return (
        db.query(func.count(Message.id))
        .filter(Message.receiver_id == user.id, Message.read.is_(False))
        .scalar()
        or 0
    )


def list_conversations(db: Session, user: User) -> list[dict]:
    """Resumo por carga das conversas do utilizador."""
    sent_load_ids = db.query(Message.load_id).filter(Message.sender_id == user.id).distinct()
    received_load_ids = (
        db.query(Message.load_id).filter(Message.receiver_id == user.id).distinct()
    )
    load_ids = {row[0] for row in sent_load_ids.all()} | {row[0] for row in received_load_ids.all()}

    summaries: list[dict] = []
    for load_id in load_ids:
        load = db.query(Load).filter(Load.id == load_id).first()
        if load is None:
            continue
        try:
            _user_can_access_load_chat(db, user, load)
        except HTTPException:
            continue

        last_msg = (
            db.query(Message)
            .filter(
                Message.load_id == load_id,
                (Message.sender_id == user.id) | (Message.receiver_id == user.id),
            )
            .order_by(Message.created_at.desc())
            .first()
        )
        if last_msg is None:
            continue

        other_id = (
            last_msg.receiver_id
            if last_msg.sender_id == user.id
            else last_msg.sender_id
        )
        other_user = db.query(User).filter(User.id == other_id).first() if other_id else None

        unread = (
            db.query(func.count(Message.id))
            .filter(
                Message.load_id == load_id,
                Message.receiver_id == user.id,
                Message.read.is_(False),
            )
            .scalar()
            or 0
        )

        summaries.append(
            {
                "load_id": load.id,
                "load_code": load.code,
                "other_user_id": other_user.id if other_user else 0,
                "other_user_name": other_user.name if other_user else "Utilizador",
                "last_message": last_msg.body,
                "last_message_at": last_msg.created_at,
                "unread_count": unread,
            }
        )

    summaries.sort(
        key=lambda item: item["last_message_at"] or item["load_id"],
        reverse=True,
    )
    return summaries


def list_messages_for_load(db: Session, user: User, load_id: int) -> list[Message]:
    """Histórico de mensagens de uma carga."""
    load = db.query(Load).filter(Load.id == load_id).first()
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga não encontrada")
    _user_can_access_load_chat(db, user, load)

    return (
        db.query(Message)
        .filter(
            Message.load_id == load_id,
            (Message.sender_id == user.id) | (Message.receiver_id == user.id),
        )
        .order_by(Message.created_at.asc())
        .all()
    )


def send_message(db: Session, user: User, load_id: int, data: MessageCreateRequest) -> Message:
    """Envia mensagem na conversa da carga."""
    load = db.query(Load).filter(Load.id == load_id).first()
    if load is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Carga não encontrada")
    _user_can_access_load_chat(db, user, load)

    receiver = db.query(User).filter(User.id == data.receiver_id).first()
    if receiver is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Destinatário não encontrado")
    if receiver.id == user.id:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Não pode enviar mensagem para si mesmo",
        )

    message = Message(
        load_id=load_id,
        sender_id=user.id,
        receiver_id=data.receiver_id,
        body=data.body,
        attachment=data.attachment,
    )
    db.add(message)
    notification = create_notification(
        db,
        user_id=receiver.id,
        title="Nova mensagem",
        body=f"{user.name} enviou uma mensagem sobre a carga {load.code}.",
        notification_type="message.created",
        payload={"load_id": load.id, "message_id": None, "sender_id": user.id},
    )
    db.commit()
    db.refresh(message)
    notification.payload = {
        "load_id": load.id,
        "message_id": message.id,
        "sender_id": user.id,
    }
    db.commit()
    db.refresh(notification)
    emit_to_rooms(
        {f"user:{receiver.id}", f"user:{user.id}", f"load:{load.id}"},
        {
            "type": "message.created",
            "load_id": load.id,
            "message": message,
        },
    )
    emit_notification(notification)
    return message


def mark_message_read(db: Session, user: User, message_id: int) -> Message:
    """Marca mensagem recebida como lida."""
    message = db.query(Message).filter(Message.id == message_id).first()
    if message is None:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="Mensagem não encontrada")
    if message.receiver_id != user.id:
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="Sem acesso")
    message.read = True
    db.commit()
    db.refresh(message)
    return message
