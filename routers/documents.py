"""
Rotas de documentos do utilizador.
"""

from fastapi import APIRouter, Depends
from sqlalchemy.orm import Session

from constants import DOCUMENT_TYPES
from controllers.documents_controller import (
    create_document,
    delete_document,
    get_document,
    list_my_documents,
)
from database import get_db
from deps import get_current_user
from models.models import User
from schemas.schemas import DocumentCreateRequest, DocumentResponse, DocumentTypeItem

router = APIRouter()


@router.get("/types", response_model=list[DocumentTypeItem])
def list_document_types():
    """Catálogo de tipos (BI, carta, licença, etc.)."""
    return [DocumentTypeItem(**item) for item in DOCUMENT_TYPES]


@router.get("/me", response_model=list[DocumentResponse])
def list_mine(
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Lista documentos do utilizador autenticado."""
    return list_my_documents(db, current_user)


@router.post("/me", response_model=DocumentResponse, status_code=201)
def upload(
    data: DocumentCreateRequest,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Regista documento (enviar ficheiro ao storage e passar file_url)."""
    return create_document(db, current_user, data)


@router.get("/me/{document_id}", response_model=DocumentResponse)
def get_one(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Detalhe de um documento."""
    return get_document(db, current_user, document_id)


@router.delete("/me/{document_id}", status_code=204)
def remove(
    document_id: int,
    current_user: User = Depends(get_current_user),
    db: Session = Depends(get_db),
):
    """Remove documento."""
    delete_document(db, current_user, document_id)
