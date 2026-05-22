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
    code_language = ""

    def format_inline(text: str) -> str:
        safe = escape(text)
        safe = re.sub(r"`([^`]+)`", r"<code>\1</code>", safe)
        safe = re.sub(r"\*\*([^*]+)\*\*", r"<strong>\1</strong>", safe)
        return safe

    def detect_code_language(code: str, language: str) -> str:
        if language:
            return language.lower()
        stripped = code.lstrip()
        if stripped.startswith("{") or stripped.startswith("["):
            return "json"
        if re.match(r"^(GET|POST|PATCH|DELETE|PUT)\s+/", stripped):
            return "http"
        return "text"

    def highlight_code(code: str, language: str) -> str:
        lang = detect_code_language(code, language)
        safe = escape(code, quote=False)

        if lang == "json":
            safe = re.sub(
                r'("(?:\\.|[^"\\])*")(?=\s*:)',
                r'<span class="tok-key">\1</span>',
                safe,
            )
            safe = re.sub(
                r'(:\s*)("(?:\\.|[^"\\])*")',
                r'\1<span class="tok-string">\2</span>',
                safe,
            )
            safe = re.sub(r"\b(true|false|null)\b", r'<span class="tok-bool">\1</span>', safe)
            safe = re.sub(r"\b(-?\d+(?:\.\d+)?)\b", r'<span class="tok-number">\1</span>', safe)
            return safe

        if lang == "http":
            safe = re.sub(
                r"\b(GET|POST|PATCH|DELETE|PUT)\b",
                r'<span class="tok-method">\1</span>',
                safe,
            )
            safe = re.sub(r"(/[\w/{}/?.=&:-]*)", r'<span class="tok-path">\1</span>', safe)
            return safe

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
        highlighted = highlight_code(code, code_language)
        html.append(f'<pre><code class="language-{escape(code_language or "text")}">{highlighted}</code></pre>')
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
                code_language = line[3:].strip()
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
      border: 1px solid #243b53;
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
    p code, li code {{
      background: #e6f6ff;
      color: #0b4f71;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.92em;
    }}
    pre code {{
      background: transparent;
      color: inherit;
      padding: 0;
      border-radius: 0;
    }}
    .tok-key {{
      color: #7dd3fc;
    }}
    .tok-string {{
      color: #bef264;
    }}
    .tok-number {{
      color: #fbbf24;
    }}
    .tok-bool {{
      color: #f0abfc;
    }}
    .tok-method {{
      color: #fbbf24;
      font-weight: 700;
    }}
    .tok-path {{
      color: #93c5fd;
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
    """Renderiza pagina inicial com introducao e documentacao geral."""
    _, markdown = read_markdown_document("modelo")
    body = markdown_to_safe_html(markdown)
    cards = "\n".join(
        f"""
        <a class="doc-card" href="/documentation/{escape(key)}">
          <span>{escape(title)}</span>
          <small>{escape(description)}</small>
        </a>"""
        for key, title, description in (
            ("company", "Empresa", "Frota, motoristas, propostas e viagens."),
            ("clients", "Cliente", "Cargas, propostas recebidas, tracking e entrega."),
            ("driver", "Motorista", "Viagens atribuidas, GPS, paragens e chegada."),
        )
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
      line-height: 1.55;
    }}
    main {{
      max-width: 980px;
      margin: 0 auto;
      background: #ffffff;
      border: 1px solid #d9e2ec;
      border-radius: 8px;
      padding: 32px;
    }}
    .hero {{
      border-bottom: 1px solid #d9e2ec;
      margin-bottom: 28px;
      padding-bottom: 24px;
    }}
    .hero-label {{
      color: #f59e0b;
      font-weight: 800;
      text-transform: uppercase;
      font-size: 12px;
      letter-spacing: 0.08em;
      margin-bottom: 10px;
    }}
    h1, h2, h3, h4, h5, h6 {{
      margin-top: 0;
      color: #102a43;
      line-height: 1.25;
    }}
    h1 {{
      font-size: 34px;
      margin-bottom: 12px;
    }}
    h2 {{
      margin: 32px 0 12px;
    }}
    p, ul {{
      margin: 0 0 16px;
    }}
    .hero p {{
      max-width: 780px;
      font-size: 18px;
    }}
    .doc-grid {{
      display: grid;
      grid-template-columns: repeat(3, minmax(0, 1fr));
      gap: 14px;
      margin: 22px 0 6px;
    }}
    .doc-card {{
      display: block;
      border: 1px solid #d9e2ec;
      border-radius: 8px;
      padding: 16px;
      background: #f8fafc;
    }}
    .doc-card span {{
      display: block;
      color: #102a43;
      font-size: 18px;
      font-weight: 800;
      margin-bottom: 6px;
    }}
    .doc-card small {{
      display: block;
      color: #52606d;
      font-size: 14px;
      line-height: 1.4;
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
    pre {{
      overflow-x: auto;
      background: #102a43;
      color: #f0f4f8;
      padding: 16px;
      border-radius: 6px;
      border: 1px solid #243b53;
    }}
    code {{
      font-family: Consolas, Monaco, monospace;
      font-size: 14px;
    }}
    p code, li code {{
      background: #e6f6ff;
      color: #0b4f71;
      padding: 2px 6px;
      border-radius: 4px;
      font-size: 0.92em;
    }}
    pre code {{
      background: transparent;
      color: inherit;
      padding: 0;
      border-radius: 0;
    }}
    .tok-key {{
      color: #7dd3fc;
    }}
    .tok-string {{
      color: #bef264;
    }}
    .tok-number {{
      color: #fbbf24;
    }}
    .tok-bool {{
      color: #f0abfc;
    }}
    .tok-method {{
      color: #fbbf24;
      font-weight: 700;
    }}
    .tok-path {{
      color: #93c5fd;
    }}
    @media (max-width: 760px) {{
      main {{
        padding: 22px;
      }}
      .doc-grid {{
        grid-template-columns: 1fr;
      }}
      h1 {{
        font-size: 28px;
      }}
    }}
  </style>
</head>
<body>
  <main>
    <section class="hero">
      <div class="hero-label">Documentacao do backend</div>
      <h1>CargoLink</h1>
      <p>
        Plataforma para ligar clientes que precisam transportar cargas a empresas
        transportadoras com frota e motoristas, com propostas, viagens, tracking
        e confirmacao de entrega.
      </p>
      <div class="doc-grid">
{cards}
      </div>
    </section>
{body}
  </main>
</body>
</html>"""
