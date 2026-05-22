"""
Rotas seguras para ler documentacao Markdown como HTML.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from controllers.docs_controller import (
    list_documentation,
    read_markdown_document,
    render_document_page,
)
from deps import get_current_user
from models import User

router = APIRouter()


@router.get("")
def list_docs(current_user: User = Depends(get_current_user)):
    """Lista documentos Markdown disponiveis para leitura."""
    return {"documents": list_documentation()}


@router.get("/{doc_key}", response_class=HTMLResponse)
def get_doc_html(
    doc_key: str,
    current_user: User = Depends(get_current_user),
):
    """Renderiza documento Markdown permitido como HTML seguro."""
    filename, markdown = read_markdown_document(doc_key)
    return HTMLResponse(render_document_page(filename, markdown))
