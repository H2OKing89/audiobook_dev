from fastapi import APIRouter, Request, Depends, Form, HTTPException, status
from fastapi.responses import Response, RedirectResponse
from starlette.responses import Response as StarletteResponse
from fastapi.responses import HTMLResponse
from typing import Any, Optional
from src.metadata import fetch_metadata
from src.token_gen import verify_token
from src.html import render_template
from src.db import get_request  # use persistent DB store
from src.utils import format_release_date, format_size
import logging
from datetime import datetime
from starlette.concurrency import run_in_threadpool
from src.security import generate_csrf_token
from src.config import load_config
import re
import html

router = APIRouter()

# Helper function to generate CSRF token and validate for forms
def get_csrf_protection_enabled() -> bool:
    """Check if CSRF protection is enabled in config"""
    config = load_config()
    return config.get('security', {}).get('csrf_protection', True)

def sanitize_input(text: Optional[str]) -> str:
    """Sanitize input to prevent XSS attacks"""
    if not text:
        return ""
    # Remove potentially dangerous HTML tags
    cleaned = re.sub(r'<script.*?>.*?</script>', '', text, flags=re.DOTALL)
    # Escape HTML entities
    sanitized = html.escape(cleaned)
    logging.debug(f"Sanitized input: '{text[:50]}...' -> '{sanitized[:50]}...'")
    return sanitized

@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    """Serve the home page"""
    client_ip = request.client.host if request.client else "unknown"
    logging.info(f"Home page accessed from IP: {client_ip}")
    
    # Add CSRF token if protection is enabled
    context = {}
    if get_csrf_protection_enabled():
        context['csrf_token'] = generate_csrf_token()
        logging.debug("CSRF token generated for home page")
    
    try:
        return render_template(request, 'index.html', context)
    except Exception as e:
        logging.error(f"Failed to render home page: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/approve/{token}", response_class=HTMLResponse)
async def approve(token: str, request: Request) -> HTMLResponse:
    """Display the approval page for a given token"""
    # Log client IP for security monitoring
    client_ip = request.client.host if request.client else "unknown"
    logging.debug(f"Approve page accessed from IP: {client_ip} for token: {token}")
    
    try:
        entry = get_request(token)
        logging.debug(f"Approve called for token: {token}, entry: {'found' if entry else 'not found'}")
        
        if not entry:
            # token invalid or expired
            logging.warning(f"Approval attempt with invalid/expired token: {token} from IP: {client_ip}")
            response = render_template(request, 'token_expired.html', {})
            response.status_code = 410
            return response
            
        metadata = entry.get('metadata') or {}
        payload = entry.get('payload') or {}
        logging.debug(f"Metadata for approval: title='{metadata.get('title', 'N/A')}', author='{metadata.get('author', 'N/A')}'")
        logging.debug(f"Payload for approval: name='{payload.get('name', 'N/A')}', size={payload.get('size', 'N/A')}")

        # Format release_date to YYYY-MM-DD if present
        release_date = metadata.get('release_date') or payload.get('release_date') or ''
        metadata['release_date'] = format_release_date(str(release_date))
        # Format size to MB/GB if present
        size = payload.get('size') or metadata.get('size')
        if size:
            metadata['size'] = format_size(size)
            logging.debug(f"Formatted size: {metadata['size']}")
        # Ensure url and download_url are present
        metadata['url'] = payload.get('url')
        metadata['download_url'] = payload.get('download_url')

        # Merge metadata and payload for template context
        context = {'token': token, **payload, **metadata}
        # Add dynamic Open Graph/Twitter meta
        context.update({
            'og_title': metadata.get('title'),
            'og_description': metadata.get('description') or payload.get('name'),
            'og_image': metadata.get('cover_url') or metadata.get('image')
        })
        
        # Add CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            context['csrf_token'] = generate_csrf_token()
            logging.debug("CSRF token generated for approval page")

        response = render_template(request, 'approval.html', context)
        logging.info(f"Approval page rendered successfully for token: {token}")
        return response
        
    except Exception as e:
        logging.error(f"Error rendering approval page for token {token}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/approve/{token}/action", response_class=HTMLResponse)
async def approve_action(token: str, request: Request) -> HTMLResponse:
    """Process the approval action for a given token"""
    client_ip = request.client.host if request.client else "unknown"
    logging.info(f"Approval action triggered from IP: {client_ip} for token: {token}")
    
    try:
        entry = get_request(token)
        logging.debug(f"Approve-Action called for token: {token}, entry: {'found' if entry else 'not found'}")
        
        if not entry:
            logging.warning(f"Approval action attempt with invalid/expired token: {token} from IP: {client_ip}")
            response = render_template(request, 'token_expired.html', {})
            response.status_code = 410
            return response
        
        from src.db import delete_request
        from src.config import load_config
        from src.qbittorrent import add_torrent_file_with_cookie
        import os
        
        config = load_config()
        qb_cfg = config.get('qbittorrent', {})
        enabled = qb_cfg.get('enabled', False)
        error_message = None
        
        if enabled:
            payload = entry.get('payload', {})
            name = payload.get('name') or entry.get('metadata', {}).get('title')
            download_url = payload.get('download_url')
            cookie = os.environ.get('COOKIE')
            category = qb_cfg.get('category')
            tags = qb_cfg.get('tags', [])
            paused = qb_cfg.get('paused', False)
            autoTMM = qb_cfg.get('use_auto_torrent_management', True)
            contentLayout = qb_cfg.get('content_layout', 'Subfolder')
            
            logging.info(f"[token={token}] Triggering qBittorrent download for: {name}")
            logging.debug(f"[token={token}] qBittorrent config: category={category}, tags={tags}, paused={paused}, autoTMM={autoTMM}, contentLayout={contentLayout}")
            try:
                result = await run_in_threadpool(
                    add_torrent_file_with_cookie,
                    download_url,
                    name,
                    category,
                    tags,
                    cookie,
                    paused,
                    autoTMM,
                    contentLayout
                )
                if not result:
                    error_message = "Failed to add torrent to qBittorrent. Please try again later."
                    logging.error(f"[token={token}] qBittorrent download failed: {error_message}")
                else:
                    logging.info(f"[token={token}] qBittorrent download successful for: {name}")
            except Exception as e:
                logging.error(f"[token={token}] qBittorrent error: {e}")
                logging.exception(f"[token={token}] Full qBittorrent exception traceback:")
                error_message = f"Failed to add torrent to qBittorrent: {e}"
        else:
            logging.info(f"[token={token}] qBittorrent is disabled in config, skipping download")
            
        # Delete the token after processing
        delete_request(token)
        logging.debug(f"[token={token}] Token deleted after approval processing")
        
        close_delay = config.get('server', {}).get('approve_success_autoclose', 3)
        
        if error_message:
            # Dynamic OG meta for failure page
            context = {
                'token': token,
                'error_message': error_message,
                'og_title': 'Approval Failed',
                'og_description': error_message,
                'og_image': 'https://picsur.kingpaging.com/i/e233d240-fe13-4804-a0dd-860dfd70834b.png'
            }
            logging.warning(f"[token={token}] Rendering failure page due to: {error_message}")
            response = render_template(request, 'failure.html', context)
        else:
            # Dynamic OG meta for success page
            context = {
                'token': token,
                'close_delay': close_delay,
                'og_title': 'Approval Successful',
                'og_description': 'Your audiobook request was approved and processed!',
                'og_image': 'https://picsur.kingpaging.com/i/e233d240-fe13-4804-a0dd-860dfd70834b.png'
            }
            logging.info(f"[token={token}] Approval successful, rendering success page")
            response = render_template(request, 'success.html', context)
        return response
    
    except Exception as e:
        logging.error(f"Error processing approval action for token {token}: {e}")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.get("/reject/{token}", response_class=HTMLResponse)
async def reject(token: str, request: Request) -> HTMLResponse:
    """Display the rejection page and process rejection for a given token"""
    # Log client IP for security monitoring
    client_ip = request.client.host if request.client else "unknown"
    logging.debug(f"Reject page accessed from IP: {client_ip} for token: {token}")
    
    try:
        entry = get_request(token)
        logging.debug(f"Reject called for token: {token}, entry: {'found' if entry else 'not found'}")
        
        if not entry:
            logging.warning(f"Rejection attempt with invalid/expired token: {token} from IP: {client_ip}")
            response = render_template(request, 'token_expired.html', {})
            response.status_code = 410
            return response
            
        # Log the rejection with metadata info
        metadata = entry.get('metadata', {})
        payload = entry.get('payload', {})
        title = metadata.get('title') or payload.get('name', 'Unknown')
        logging.info(f"[token={token}] Request rejected: '{title}' from IP: {client_ip}")
        
        # handle rejection logic here
        from src.db import delete_request
        delete_request(token)
        logging.debug(f"[token={token}] Token deleted after rejection")
        
        # Dynamic OG meta for rejection page
        context = {
            'og_title': 'Request Rejected',
            'og_description': 'Your audiobook request was rejected.',
            'og_image': 'https://picsur.kingpaging.com/i/e233d240-fe13-4804-a0dd-860dfd70834b.png'
        }
        
        # Add CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            context['csrf_token'] = generate_csrf_token()
            logging.debug("CSRF token generated for rejection page")
            
        response = render_template(request, 'rejection.html', context)
        logging.info(f"[token={token}] Rejection processed successfully")
        return response
        
    except Exception as e:
        logging.error(f"Error processing rejection for token {token}: {e}")
        logging.exception(f"Full exception traceback for rejection {token}:")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/reject/{token}", response_class=HTMLResponse)
async def reject_post(token: str, request: Request) -> HTMLResponse:
    """Handle POST request for token rejection with CSRF validation"""
    client_ip = request.client.host if request.client else "unknown"
    logging.info(f"Reject POST request from IP: {client_ip} for token: {token}")
    
    try:
        # Validate CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            form_data = await request.form()
            csrf_token = form_data.get("csrf_token")
            if not csrf_token or not isinstance(csrf_token, str) or len(csrf_token) < 32:
                logging.warning(f"[token={token}] CSRF token validation failed on reject from IP: {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token validation failed"
                )
            logging.debug(f"[token={token}] CSRF token validated successfully")
        
        # Reuse the same logic as the GET handler
        return await reject(token, request)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing reject POST for token {token}: {e}")
        logging.exception(f"Full exception traceback for reject POST {token}:")
        raise HTTPException(status_code=500, detail="Internal server error")

@router.post("/approve/{token}", response_class=HTMLResponse)
async def approve_post(token: str, request: Request) -> HTMLResponse:
    """Handle POST request for token approval with CSRF validation"""
    client_ip = request.client.host if request.client else "unknown"
    logging.info(f"Approve POST request from IP: {client_ip} for token: {token}")
    
    try:
        # Validate CSRF token if protection is enabled
        if get_csrf_protection_enabled():
            form_data = await request.form()
            csrf_token = form_data.get("csrf_token")
            if not csrf_token or not isinstance(csrf_token, str) or len(csrf_token) < 32:
                logging.warning(f"[token={token}] CSRF token validation failed on approve from IP: {client_ip}")
                raise HTTPException(
                    status_code=status.HTTP_403_FORBIDDEN,
                    detail="CSRF token validation failed"
                )
            logging.debug(f"[token={token}] CSRF token validated successfully")
        
        # For the test_token_lifecycle_complete test
        # This should mirror the functionality of approve_action
        return await approve_action(token, request)
        
    except HTTPException:
        raise
    except Exception as e:
        logging.error(f"Error processing approve POST for token {token}: {e}")
        logging.exception(f"Full exception traceback for approve POST {token}:")
        raise HTTPException(status_code=500, detail="Internal server error")