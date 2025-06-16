from fastapi.templating import Jinja2Templates
from fastapi import Request

# Initialize Jinja2 templates (looks for 'templates/' at project root)
templates = Jinja2Templates(directory="templates")

def render_template(request: Request, template_name: str, context: dict) -> 'TemplateResponse':  # type: ignore
    """
    Renders a Jinja2 template with the provided context, including the request.
    """
    # Inject 'request' into the template context as required by Jinja2Templates
    full_context = {"request": request}
    full_context.update(context or {})
    return templates.TemplateResponse(template_name, full_context)
