from fastapi.templating import Jinja2Templates
from fastapi import Request
from fastapi.responses import HTMLResponse
import logging

# Initialize Jinja2 templates (looks for 'templates/' at project root)
templates = Jinja2Templates(directory="templates")

def render_template(request: Request, template_name: str, context: dict) -> HTMLResponse:
    """
    Renders a Jinja2 template with the provided context, including the request.
    """
    try:
        # Inject 'request' into the template context as required by Jinja2Templates
        full_context = {"request": request}
        full_context.update(context or {})
        
        logging.debug(f"Rendering template: {template_name} with context keys: {list(full_context.keys())}")
        response = templates.TemplateResponse(request, template_name, full_context)
        logging.debug(f"Template {template_name} rendered successfully")
        return response
        
    except Exception as e:
        logging.error(f"Failed to render template {template_name}: {e}")
        logging.exception(f"Full template rendering exception for {template_name}:")
        raise
