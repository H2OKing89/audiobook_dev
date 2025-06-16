from fastapi import APIRouter, Request, Depends
from fastapi.responses import Response
from starlette.responses import Response as StarletteResponse
from fastapi.responses import HTMLResponse
from typing import Any
from src.metadata import fetch_metadata
from src.token_gen import verify_token
from src.html import render_template
from src.db import get_request  # use persistent DB store
from src.utils import format_release_date, format_size
import logging
from datetime import datetime
from starlette.concurrency import run_in_threadpool

router = APIRouter()

@router.get("/", response_class=HTMLResponse)
async def home(request: Request) -> HTMLResponse:
    return render_template(request, 'index.html', {})

@router.get("/approve/{token}", response_class=HTMLResponse)
async def approve(token: str, request: Request) -> HTMLResponse:
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
    # Add dynamic Open Graph/Twitter meta
    context.update({
        'og_title': metadata.get('title'),
        'og_description': metadata.get('description') or payload.get('name'),
        'og_image': metadata.get('cover_url') or metadata.get('image')
    })

    response = render_template(
        request,
        'approval.html',
        context
    )
    return response

@router.get("/approve/{token}/action", response_class=HTMLResponse)
async def approve_action(token: str, request: Request) -> HTMLResponse:
    entry = get_request(token)
    logging.debug(f"Approve-Action called for token: {token}, entry: {entry}")
    if not entry:
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
        logging.info(f"Triggering qBittorrent for: {name}")
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
        except Exception as e:
            logging.error(f"qBittorrent error: {e}")
            error_message = f"Failed to add torrent to qBittorrent: {e}"
    delete_request(token)
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
        response = render_template(request, 'success.html', context)
    return response

@router.get("/reject/{token}", response_class=HTMLResponse)
async def reject(token: str, request: Request) -> HTMLResponse:
    entry = get_request(token)
    logging.debug(f"Reject called for token: {token}, entry: {entry}")
    if not entry:
        response = render_template(request, 'token_expired.html', {})
        response.status_code = 410
        return response
    # handle rejection logic here
    from src.db import delete_request
    delete_request(token)
    # Dynamic OG meta for rejection page
    context = {
        'og_title': 'Request Rejected',
        'og_description': 'Your audiobook request was rejected.',
        'og_image': 'https://picsur.kingpaging.com/i/e233d240-fe13-4804-a0dd-860dfd70834b.png'
    }
    response = render_template(request, 'rejection.html', context)
    return response