"""
Controller para servir documentacao Markdown como HTML seguro.
"""

import re
from html import escape
from pathlib import Path

from fastapi import HTTPException, status


DOCS_DIR = Path(__file__).resolve().parents[1] / "docs"
ALLOWED_DOCS = {
    "modelo": "modelo.md",
    "company": "company.md",
    "clients": "clients.md",
    "driver": "driver.md",
}


def list_documentation() -> list[dict[str, str]]:
    """Lista documentos disponiveis."""
    return [
        {"key": key, "filename": filename}
        for key, filename in sorted(ALLOWED_DOCS.items())
    ]


def read_markdown_document(doc_key: str) -> tuple[str, str]:
    """Le Markdown permitido por chave, sem aceitar paths arbitrarios."""
    filename = ALLOWED_DOCS.get(doc_key)
    if filename is None:
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Documento nao encontrado",
        )

    path = (DOCS_DIR / filename).resolve()
    if DOCS_DIR.resolve() not in path.parents:
        raise HTTPException(
            status_code=status.HTTP_403_FORBIDDEN,
            detail="Documento invalido",
        )

    if not path.exists():
        raise HTTPException(
            status_code=status.HTTP_404_NOT_FOUND,
            detail="Ficheiro de documentacao nao encontrado",
        )

    return filename, path.read_text(encoding="utf-8")


def markdown_to_safe_html(markdown: str) -> str:
    """Converte um subset simples de Markdown para HTML escapando conteudo."""
    html: list[str] = []
    paragraph: list[str] = []
    list_open = False
    code_open = False
    code_lines: list[str] = []

    def format_inline(text: str) -> str:
        safe = escape(text)
        safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
        safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
        return safe

    def flush_paragraph() -> None:
        nonlocal paragraph
        if paragraph:
            html.append(f"<p>{'<br>'.join(paragraph)}</p>")
            paragraph = []

    def close_list() -> None:
        nonlocal list_open
        if list_open:
            html.append("</ul>")
            list_open = False

    def flush_code() -> None:
        nonlocal code_lines
        code = "\n".join(code_lines)
        html.append(f"<pre><code>{escape(code)}</code></pre>")
        code_lines = []

    for raw_line in markdown.splitlines():
        line = raw_line.rstrip()

        if line.startswith("```"):
            if code_open:
                flush_code()
                code_open = False
            else:
                flush_paragraph()
                close_list()
                code_open = True
                code_lines = []
            continue

        if code_open:
            code_lines.append(line)
            continue

        stripped = line.strip()
        if not stripped:
            flush_paragraph()
            close_list()
            continue

        if stripped.startswith("#"):
            flush_paragraph()
            close_list()
            level = min(len(stripped) - len(stripped.lstrip("#")), 6)
            text = stripped[level:].strip()
            html.append(f"<h{level}>{format_inline(text)}</h{level}>")
            continue

        if stripped.startswith("- "):
            flush_paragraph()
            if not list_open:
                html.append("<ul>")
                list_open = True
            html.append(f"<li>{format_inline(stripped[2:].strip())}</li>")
            continue

        paragraph.append(format_inline(stripped))

    if code_open:
        flush_code()
    flush_paragraph()
    close_list()
    return "\n".join(html)


def render_document_page(title: str, markdown: str) -> str:
    """Renderiza pagina HTML completa para a documentacao."""
    body = markdown_to_safe_html(markdown)
    safe_title = escape(title)
    return f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>{safe_title}</title>
  <style>
    :root {{
      color-scheme: light;
      font-family: Arial, Helvetica, sans-serif;
      line-height: 1.55;
      color: #1f2933;
      background: #f5f7fa;
    }}
    body {{
      margin: 0;
      padding: 32px 16px;
    }}
    main {{
      max-width: 920px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d9e2ec;
      border-radius: 8px;
      padding: 32px;
    }}
    h1, h2, h3, h4, h5, h6 {{
      color: #102a43;
      line-height: 1.25;
      margin: 28px 0 12px;
    }}
    h1 {{
      margin-top: 0;
      font-size: 32px;
    }}
    p, ul {{
      margin: 0 0 16px;
    }}
    li {{
      margin: 6px 0;
    }}
    pre {{
      overflow-x: auto;
      background: #102a43;
      color: #f0f4f8;
      padding: 16px;
      border-radius: 6px;
    }}
    .back-link {{
      display: inline-block;
      margin-bottom: 24px;
      color: #0b63ce;
      text-decoration: none;
      font-weight: 700;
    }}
    .back-link:hover {{
      text-decoration: underline;
    }}
    code {{
      font-family: Consolas, Monaco, monospace;
      font-size: 14px;
    }}
  </style>
</head>
<body>
  <main>
    <a class="back-link" href="/documentation">&larr; Voltar</a>
{body}
  </main>
</body>
</html>"""


def render_documentation_index() -> str:
    """Renderiza pagina inicial com links para os documentos permitidos."""
    items = "\n".join(
        f'<li><a href="/documentation/{escape(item["key"])}">{escape(item["filename"])}</a></li>'
        for item in list_documentation()
    )
    return f"""<!doctype html>
<html lang="pt">
<head>
  <meta charset="utf-8">
  <meta name="viewport" content="width=device-width, initial-scale=1">
  <title>Documentacao CargoLink</title>
  <style>
    body {{
      margin: 0;
      padding: 32px 16px;
      font-family: Arial, Helvetica, sans-serif;
      background: #f5f7fa;
      color: #1f2933;
    }}
    main {{
      max-width: 760px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d9e2ec;
      border-radius: 8px;
      padding: 32px;
    }}
    h1 {{
      margin-top: 0;
      color: #102a43;
    }}
    a {{
      color: #0b63ce;
      text-decoration: none;
      font-weight: 600;
    }}
    a:hover {{
      text-decoration: underline;
    }}
    li {{
      margin: 10px 0;
    }}
  </style>
</head>
<body>
  <main>
    <h1>Documentacao CargoLink</h1>
    <p>Escolha um documento:</p>
    <ul>
{items}
    </ul>
  </main>
</body>
</html>"""
