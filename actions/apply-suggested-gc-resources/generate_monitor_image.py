#!/usr/bin/env python3
"""Generate monitor preview image using Playwright"""

import asyncio
from playwright.async_api import async_playwright


async def generate_monitor_image(monitor: dict, output_path: str = 'monitor-preview.png') -> str:
    """Generate a PNG image of the monitor preview with GroundCover styling."""
    
    # Extract monitor details
    title = monitor.get('title', 'Monitor')
    description = monitor['display']['description']
    severity = monitor.get('severity', 'Unknown')
    monitor_type = monitor.get('measurementType', 'state').title()
    
    queries = monitor['model'].get('queries', [])
    query_expr = queries[0]['expression'] if queries else 'N/A'
    
    thresholds = monitor['model'].get('thresholds', [])
    threshold_value = thresholds[0]['values'][0] if thresholds else 0
    threshold_op = thresholds[0].get('operator', 'gt') if thresholds else 'gt'
    operator_symbol = {'gt': '>', 'gte': '>=', 'lt': '<', 'lte': '<=', 'eq': '=='}.get(threshold_op, '>')
    
    eval_interval = monitor['evaluationInterval']['interval']
    pending_for = monitor['evaluationInterval']['pendingFor']
    
    # Build styled HTML with exact GroundCover look
    html_content = f"""
    <!DOCTYPE html>
    <html>
    <head>
        <meta charset="UTF-8">
        <style>
            body {{
                margin: 0;
                padding: 20px;
                background: #ffffff;
                font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', 'Noto Sans', Helvetica, Arial, sans-serif;
            }}
            .monitor-card {{
                border: 1px solid #d0d7de;
                border-radius: 6px;
                padding: 20px;
                background: #ffffff;
                color: #1f2328;
                width: 800px;
            }}
            .header {{
                display: flex;
                align-items: center;
                gap: 10px;
                margin-bottom: 20px;
            }}
            .title {{
                margin: 0;
                font-size: 20px;
                font-weight: 600;
                color: #1f2328;
            }}
            .badge {{
                background: #d1242f;
                color: #ffffff;
                padding: 2px 10px;
                border-radius: 3px;
                font-size: 13px;
                font-weight: 500;
            }}
            .metadata {{
                display: flex;
                gap: 24px;
                margin-bottom: 24px;
                font-size: 14px;
                color: #656d76;
            }}
            .metadata-item {{
                font-weight: 400;
            }}
            .metadata-value {{
                color: #1f2328;
                font-weight: 400;
            }}
            .metadata-value.severity {{
                font-weight: 600;
            }}
            .section {{
                margin-bottom: 24px;
            }}
            .section-title {{
                margin-bottom: 8px;
                font-size: 14px;
                font-weight: 600;
                color: #1f2328;
            }}
            .section-content {{
                font-size: 14px;
                color: #656d76;
                line-height: 1.5;
            }}
            .code-block {{
                background: #f6f8fa;
                padding: 14px;
                border-radius: 6px;
                border: 1px solid #d0d7de;
                overflow-x: auto;
                font-size: 12px;
                font-family: ui-monospace, SFMono-Regular, 'SF Mono', Menlo, Consolas, 'Liberation Mono', 'Courier New', monospace;
                margin: 0;
                color: #1f2328;
                line-height: 1.6;
                white-space: pre-wrap;
                word-break: break-all;
            }}
            .info-box {{
                background: #f6f8fa;
                padding: 16px;
                border-radius: 6px;
                border: 1px solid #d0d7de;
                font-size: 14px;
                color: #1f2328;
            }}
            .info-row {{
                margin-bottom: 6px;
            }}
            .info-row:last-child {{
                margin-bottom: 0;
            }}
            .info-label {{
                font-weight: 600;
            }}
            hr {{
                margin: 20px 0;
                border: none;
                border-top: 1px solid #d0d7de;
            }}
            .footer {{
                text-align: center;
                color: #656d76;
                font-size: 14px;
            }}
            .footer-code {{
                background: #f6f8fa;
                padding: 3px 6px;
                border-radius: 3px;
                font-size: 12px;
                color: #1f2328;
                border: 1px solid #d0d7de;
                font-family: ui-monospace, SFMono-Regular, monospace;
            }}
        </style>
    </head>
    <body>
        <div class="monitor-card">
            <div class="header">
                <h2 class="title">{title}</h2>
                <span class="badge">Alerting</span>
            </div>
            
            <div class="metadata">
                <div class="metadata-item">Monitor type: <span class="metadata-value">{monitor_type}</span></div>
                <div class="metadata-item">Severity: <span class="metadata-value severity">{severity}</span></div>
            </div>
            
            <div class="section">
                <div class="section-title">Description</div>
                <div class="section-content">{description}</div>
            </div>
            
            <div class="section">
                <div class="section-title">Query</div>
                <div class="code-block">{query_expr}</div>
            </div>
            
            <div class="info-box">
                <div class="info-row"><span class="info-label">Threshold:</span> {operator_symbol} {threshold_value}</div>
                <div class="info-row"><span class="info-label">Evaluation Interval:</span> {eval_interval}</div>
                <div class="info-row"><span class="info-label">Pending For:</span> {pending_for}</div>
            </div>
            
            <hr>
            
            <div class="footer">
                Reply with <span class="footer-code">/create-monitor</span> to create it.
            </div>
        </div>
    </body>
    </html>
    """
    
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=True)
        page = await browser.new_page(viewport={'width': 900, 'height': 1200})
        await page.set_content(html_content)
        
        # Wait for fonts to load
        await page.wait_for_timeout(500)
        
        # Take screenshot of just the card
        card = await page.query_selector('.monitor-card')
        await card.screenshot(path=output_path)
        
        await browser.close()
    
    return output_path


def generate_monitor_image_sync(monitor: dict, output_path: str = 'monitor-preview.png') -> str:
    """Synchronous wrapper for generate_monitor_image."""
    return asyncio.run(generate_monitor_image(monitor, output_path))

