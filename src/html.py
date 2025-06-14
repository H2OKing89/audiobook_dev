from fastapi.templating import Jinja2Templates
from fastapi import Request

# Initialize Jinja2 templates (looks for 'templates/' at project root)
templates = Jinja2Templates(directory="templates")

def render_template(request: Request, template_name: str, context: dict):
    """
    Renders a Jinja2 template with the provided context.
    """
    return templates.TemplateResponse(request, template_name, context)
