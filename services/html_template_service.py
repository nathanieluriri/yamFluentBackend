from __future__ import annotations

from pathlib import Path
from string import Template
from typing import Mapping

from fastapi.responses import HTMLResponse

_TEMPLATE_ROOT = Path(__file__).resolve().parents[1] / "html_templates"


def render_template(template_name: str, context: Mapping[str, str]) -> str:
    template_path = _TEMPLATE_ROOT / template_name
    content = template_path.read_text(encoding="utf-8")
    return Template(content).safe_substitute(context)


def build_html_response(content: str, status_code: int = 200) -> HTMLResponse:
    response = HTMLResponse(content=content, status_code=status_code)
    response.headers["Cache-Control"] = "no-store"
    return response
