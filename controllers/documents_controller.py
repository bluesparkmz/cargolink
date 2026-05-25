"""
Controller de documentos do utilizador (BI, carta, etc.).
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from constants import DOCUMENT_STATUS_PENDING, DOCUMENT_TYPE_IDS
from models.models import Document, User
from schemas.schemas import DocumentCreateRequest


def list_my_documents(db: Session, user: User) -> list[Document]:
    """Lista documentos do utilizador autenticado."""
    return (
        db.query(Document)
        .filter(Document.user_id == user.id)
        .order_by(Document.created_at.desc())
        .all()
    )


def get_document(db: Session, user: User, document_id: int) -> Document:
    """Detalhe de um documento próprio."""
    doc = (
        db.query(Document)
        .filter(Document.id == document_id, Document.user_id == user.id)
        .first()
    )
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento não encontrado",
        )
    return doc


def create_document(db: Session, user: User, data: DocumentCreateRequest) -> Document:
    """Regista novo documento (URL após upload no storage/CDN)."""
    if data.document_type not in DOCUMENT_TYPE_IDS:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail=f"Tipo inválido. Use: {', '.join(sorted(DOCUMENT_TYPE_IDS))}",
        )

    doc = Document(
        user_id=user.id,
        document_type=data.document_type,
        file_url=data.file_url.strip(),
        notes=data.notes,
        status=DOCUMENT_STATUS_PENDING,
    )
    db.add(doc)
    db.commit()
    db.refresh(doc)
    return doc


def delete_document(db: Session, user: User, document_id: int) -> None:
    """Remove documento do utilizador."""
    doc = get_document(db, user, document_id)
    db.delete(doc)
    db.commit()
