from typing import Any

from fastapi import Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates

from src.config import load_config
from src.logging_setup import get_logger


# Initialize Jinja2 templates (looks for 'templates/' at project root)
templates = Jinja2Templates(directory="templates")

log = get_logger(__name__)


def get_config() -> dict[str, Any]:
    """Template helper to access config in templates

    Returns empty dict on config load failure to prevent template errors.
    """
    try:
        return load_config()
    except Exception as e:
        log.exception("template.config.load_failed", error=str(e))
        # Return empty dict to prevent template rendering errors
        return {}


# Add config to Jinja2 globals
templates.env.globals["get_config"] = get_config


def render_template(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """
    Renders a Jinja2 template with the provided context, including the request.
    """
    try:
        # Inject 'request' into the template context as required by Jinja2Templates
        full_context = {"request": request}
        full_context.update(context or {})

        log.debug("template.rendering", template=template_name, context_keys=list(full_context.keys()))
        response = templates.TemplateResponse(request, template_name, full_context)
        log.debug("template.render_success", template=template_name)
        return response

    except Exception as e:
        log.error("template.render_failed", template=template_name, error=str(e))
        log.exception("template.render_exception", template=template_name)
        raise
