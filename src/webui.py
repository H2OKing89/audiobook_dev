from fastapi import APIRouter, Request, Depends
from fastapi.responses import HTMLResponse
from src.metadata import fetch_metadata
from src.token_gen import verify_token
from src.html import render_template
from src.db import get_request  # use persistent DB store
from src.utils import format_release_date, format_size
import logging
from datetime import datetime

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request):
    return render_template(request, 'index.html', {})

@router.get("/approve/{token}", response_class=HTMLResponse)
async def approve(token: str, request: Request):
    entry = get_request(token)
    logging.debug(f"Approve called for token: {token}, entry: {entry}")
    if not entry:
        # token invalid or expired
        response = render_template(request, 'token_expired.html', {})
        response.status_code = 410
        return response
    metadata = entry.get('metadata') or {}
    payload = entry.get('payload') or {}
    logging.debug(f"Metadata for approval: {metadata}")
    logging.debug(f"Payload for approval: {payload}")

    # Format release_date to YYYY-MM-DD if present
    release_date = metadata.get('release_date') or payload.get('release_date') or ''
    metadata['release_date'] = format_release_date(str(release_date))
    # Format size to MB/GB if present
    size = payload.get('size') or metadata.get('size')
    if size:
        metadata['size'] = format_size(size)
    # Ensure url and download_url are present
    metadata['url'] = payload.get('url')
    metadata['download_url'] = payload.get('download_url')

    # Merge metadata and payload for template context
    context = {'token': token, **payload, **metadata}

    response = render_template(
        request,
        'approval.html',
        context
    )
    return response

@router.get("/approve/{token}/action", response_class=HTMLResponse)
async def approve_action(token: str, request: Request):
    entry = get_request(token)
    logging.debug(f"Approve-Action called for token: {token}, entry: {entry}")
    if not entry:
        response = render_template(request, 'token_expired.html', {})
        response.status_code = 410
        return response
    # handle approval logic here (e.g., trigger qBittorrent, etc.)
    from src.db import delete_request
    from src.config import load_config
    from src.qbittorrent import add_torrent_file_with_cookie
    import os
    config = load_config()
    qb_cfg = config.get('qbittorrent', {})
    enabled = qb_cfg.get('enabled', False)
    # Only trigger qBittorrent if enabled in config
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
        logging.info(f"Triggering qBittorrent for: {name}")
        add_torrent_file_with_cookie(
            download_url=download_url,
            name=name,
            category=category,
            tags=tags,
            cookie=cookie,
            paused=paused,
            autoTMM=autoTMM,
            contentLayout=contentLayout
        )
    delete_request(token)
    close_delay = config.get('server', {}).get('approve_success_autoclose', 3)
    response = render_template(request, 'success.html', {'token': token, 'close_delay': close_delay})
    return response

@router.get("/reject/{token}", response_class=HTMLResponse)
async def reject(token: str, request: Request):
    entry = get_request(token)
    logging.debug(f"Reject called for token: {token}, entry: {entry}")
    if not entry:
        response = render_template(request, 'token_expired.html', {})
        response.status_code = 410
        return response
    # handle rejection logic here
    logging.info(f"Audiobook with token {token} has been rejected.")
    from src.db import delete_request
    delete_request(token)
    response = render_template(
        request,
        'rejection.html',
        {}
    )
    return response