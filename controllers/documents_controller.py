"""
Controller de documentos do utilizador (BI, carta, etc.).
"""

from fastapi import HTTPException, status
from sqlalchemy.orm import Session

from constants import (
    DOCUMENT_STATUS_APPROVED,
    DOCUMENT_STATUS_PENDING,
    DOCUMENT_STATUS_REJECTED,
    DOCUMENT_TYPE_IDS,
)
from models.models import Company, Document, User
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


def _require_admin(user: User) -> None:
    if user.user_type != "admin":
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Acesso permitido apenas para admin",
        )


def _recompute_company_verified(db: Session, company: Company) -> None:
    """
    Recalcula verified com base nos documentos do utilizador da empresa.

    Regra simples:
    - empresa fica verified apenas se TODOS os documentos estiverem 'aprovado'
    - se existir pelo menos um 'pendente' ou 'rejeitado', verified = False
    """

    docs = db.query(Document).filter(Document.user_id == company.user_id).all()
    if not docs:
        company.verified = False
        # user.verified: relationship via back_populates, mas aqui fazemos query direta para não depender de lazy-loading.
        db.query(User).filter(User.id == company.user_id).update({"verified": False})
        db.commit()
        return

    all_approved = all(doc.status == DOCUMENT_STATUS_APPROVED for doc in docs)
    verified = bool(all_approved)
    company.verified = verified
    db.query(User).filter(User.id == company.user_id).update({"verified": verified})
    db.commit()


def list_company_documents_admin(
    db: Session, admin_user: User, company_id: int, status_filter: str | None = None
) -> list[Document]:
    """Lista documentos de uma empresa (visão admin)."""
    _require_admin(admin_user)

    company = db.query(Company).filter(Company.id == company_id).first()
    if company is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Empresa nao encontrada",
        )

    query = db.query(Document).filter(Document.user_id == company.user_id)
    if status_filter:
        query = query.filter(Document.status == status_filter)

    return query.order_by(Document.created_at.desc()).all()


def approve_company_document_admin(
    db: Session, admin_user: User, document_id: int
) -> Document:
    """Aprova um documento e atualiza verified da empresa (se for documento de empresa)."""
    _require_admin(admin_user)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento nao encontrado",
        )

    doc.status = DOCUMENT_STATUS_APPROVED
    db.commit()
    db.refresh(doc)

    if doc.user and doc.user.user_type == "empresa" and doc.user.company:
        _recompute_company_verified(db, doc.user.company)

    return doc


def reject_company_document_admin(
    db: Session, admin_user: User, document_id: int
) -> Document:
    """Rejeita um documento e atualiza verified da empresa (se for documento de empresa)."""
    _require_admin(admin_user)

    doc = db.query(Document).filter(Document.id == document_id).first()
    if doc is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento nao encontrado",
        )

    doc.status = DOCUMENT_STATUS_REJECTED
    db.commit()
    db.refresh(doc)

    if doc.user and doc.user.user_type == "empresa" and doc.user.company:
        _recompute_company_verified(db, doc.user.company)

    return doc
