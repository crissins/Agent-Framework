# agents/qr_agent.py
"""
Standalone QR Code generation agent.

Generates QR codes from URLs, text, or any data string.
Outputs base64-encoded PNG data-URIs and/or saves files to disk.
"""
import base64
import logging
from io import BytesIO
from pathlib import Path
from typing import Optional

import qrcode
from qrcode.constants import ERROR_CORRECT_H, ERROR_CORRECT_M
from PIL import Image

logger = logging.getLogger(__name__)


# ── Configuration ─────────────────────────────────────────────────────────
QR_DEFAULTS = {
    "version": 1,
    "box_size": 10,
    "border": 2,
    "fill_color": "black",
    "back_color": "white",
    "error_correction": ERROR_CORRECT_M,
}


def generate_qr_code(
    data: str,
    *,
    box_size: int = 10,
    border: int = 2,
    fill_color: str = "black",
    back_color: str = "white",
    error_correction: int = ERROR_CORRECT_M,
    logo_path: Optional[str] = None,
) -> str:
    """
    Generate a QR code and return it as a base64 data-URI PNG string.

    Args:
        data: The content to encode (URL, text, etc.)
        box_size: Size of each box/module in pixels
        border: Border width in modules
        fill_color: QR module color
        back_color: Background color
        error_correction: Error correction level (use ERROR_CORRECT_H for logo overlay)
        logo_path: Optional path to a logo image to overlay in center

    Returns:
        Base64 data-URI string (data:image/png;base64,...) or empty string on failure
    """
    try:
        # Use higher error correction when embedding a logo
        if logo_path:
            error_correction = ERROR_CORRECT_H

        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGBA")

        # Overlay logo if provided
        if logo_path and Path(logo_path).exists():
            try:
                logo = Image.open(logo_path).convert("RGBA")
                # Logo should be ~25% of QR size
                qr_w, qr_h = img.size
                logo_max = min(qr_w, qr_h) // 4
                logo.thumbnail((logo_max, logo_max), Image.LANCZOS)
                logo_w, logo_h = logo.size
                pos = ((qr_w - logo_w) // 2, (qr_h - logo_h) // 2)
                img.paste(logo, pos, logo)
            except Exception as e:
                logger.warning(f"Failed to overlay logo on QR: {e}")

        buf = BytesIO()
        img.save(buf, format="PNG")
        b64 = base64.b64encode(buf.getvalue()).decode()
        return f"data:image/png;base64,{b64}"

    except Exception as e:
        logger.error(f"QR code generation failed for '{data[:80]}': {e}")
        return ""


def save_qr_code(
    data: str,
    output_path: str,
    *,
    box_size: int = 10,
    border: int = 2,
    fill_color: str = "black",
    back_color: str = "white",
    logo_path: Optional[str] = None,
) -> Optional[str]:
    """
    Generate a QR code and save it to a file.

    Args:
        data: The content to encode
        output_path: File path to save the PNG
        box_size: Size of each box/module in pixels
        border: Border width in modules
        fill_color: QR module color
        back_color: Background color
        logo_path: Optional path to a logo image to overlay

    Returns:
        The output file path on success, None on failure
    """
    try:
        error_correction = ERROR_CORRECT_H if logo_path else ERROR_CORRECT_M
        qr = qrcode.QRCode(
            version=1,
            error_correction=error_correction,
            box_size=box_size,
            border=border,
        )
        qr.add_data(data)
        qr.make(fit=True)
        img = qr.make_image(fill_color=fill_color, back_color=back_color).convert("RGBA")

        if logo_path and Path(logo_path).exists():
            try:
                logo = Image.open(logo_path).convert("RGBA")
                qr_w, qr_h = img.size
                logo_max = min(qr_w, qr_h) // 4
                logo.thumbnail((logo_max, logo_max), Image.LANCZOS)
                logo_w, logo_h = logo.size
                pos = ((qr_w - logo_w) // 2, (qr_h - logo_h) // 2)
                img.paste(logo, pos, logo)
            except Exception as e:
                logger.warning(f"Failed to overlay logo on QR: {e}")

        Path(output_path).parent.mkdir(parents=True, exist_ok=True)
        img.save(output_path, format="PNG")
        logger.info(f"✅ QR code saved: {output_path}")
        return output_path

    except Exception as e:
        logger.error(f"QR code save failed: {e}")
        return None


def generate_qr_batch(items: list[dict]) -> list[dict]:
    """
    Generate QR codes for a batch of items.

    Args:
        items: List of dicts with at least a 'data' key.
               Optional keys: 'label', 'fill_color', 'back_color'

    Returns:
        List of dicts with original data plus 'qr_data_uri' key
    """
    results = []
    for item in items:
        data = item.get("data", "")
        if not data:
            continue
        qr_uri = generate_qr_code(
            data,
            fill_color=item.get("fill_color", "black"),
            back_color=item.get("back_color", "white"),
        )
        results.append({
            **item,
            "qr_data_uri": qr_uri,
        })
    return results
