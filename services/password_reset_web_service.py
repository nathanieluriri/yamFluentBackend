from __future__ import annotations

from fastapi.responses import HTMLResponse

from services.html_template_service import build_html_response, render_template


def render_reset_landing_response(reset_token: str, deep_link: str) -> HTMLResponse:
    content = render_template(
        "password_reset/reset_landing.html",
        {"reset_token": reset_token, "deep_link": deep_link},
    )
    return build_html_response(content)


def render_reset_error_response(message: str, status_code: int = 400) -> HTMLResponse:
    content = render_template("password_reset/reset_error.html", {"message": message})
    return build_html_response(content, status_code=status_code)


def render_reset_success_response() -> HTMLResponse:
    content = render_template("password_reset/reset_success.html", {})
    return build_html_response(content)
