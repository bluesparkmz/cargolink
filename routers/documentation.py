"""
Rotas seguras para ler documentacao Markdown como HTML.
"""

from fastapi import APIRouter, Depends
from fastapi.responses import HTMLResponse

from controllers.docs_controller import (
    read_markdown_document,
    render_documentation_index,
    render_document_page,
)

router = APIRouter()


@router.get("", response_class=HTMLResponse)
def list_docs():
    """Pagina HTML com documentos Markdown disponiveis."""
    return HTMLResponse(render_documentation_index())


@router.get("/{doc_key}", response_class=HTMLResponse)
def get_doc_html(doc_key: str):
    """Renderiza documento Markdown permitido como HTML seguro."""
    filename, markdown = read_markdown_document(doc_key)
    return HTMLResponse(render_document_page(filename, markdown))
