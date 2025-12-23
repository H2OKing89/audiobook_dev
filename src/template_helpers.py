from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse
from src.config import load_config
import logging
from typing import Any

# Initialize Jinja2 templates (looks for 'templates/' at project root)
templates = Jinja2Templates(directory="templates")

logger = logging.getLogger(__name__)

def get_config() -> dict[str, Any]:
    """Template helper to access config in templates
    
    Returns empty dict on config load failure to prevent template errors.
    """
    try:
        return load_config()
    except Exception as e:
        logger.exception("Failed to load configuration in template helper: %s", e)
        # Return empty dict to prevent template rendering errors
        return {}

# Add config to Jinja2 globals
templates.env.globals['get_config'] = get_config

def render_template(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """
    Renders a Jinja2 template with the provided context, including the request.
    """
    try:
        # Inject 'request' into the template context as required by Jinja2Templates
        full_context = {"request": request}
        full_context.update(context or {})
        
        logger.debug("Rendering template: %s with context keys: %s", template_name, list(full_context.keys()))
        response = templates.TemplateResponse(request, template_name, full_context)
        logger.debug("Template %s rendered successfully", template_name)
        return response
        
    except Exception as e:
        logger.error("Failed to render template %s: %s", template_name, e)
        logger.exception("Full template rendering exception for %s:", template_name)
        raise
