"""Shop logo management. Uploads are validated, stored in a managed folder
(app_data/logos) so later file moves never break printing, and embedded as
base64 data URIs at render time. A missing logo never crashes rendering."""
import base64
import os

from app.logging_setup import log

BASE_DIR = os.path.dirname(os.path.dirname(os.path.dirname(__file__)))
LOGO_DIR = os.path.join(BASE_DIR, "app_data", "logos")
LOGO_FILENAME = "shop-logo"

MAX_BYTES = 2 * 1024 * 1024

# ext -> (mime, magic-byte prefixes)
ALLOWED = {
    ".png": ("image/png", [b"\x89PNG\r\n\x1a\n"]),
    ".jpg": ("image/jpeg", [b"\xff\xd8\xff"]),
    ".jpeg": ("image/jpeg", [b"\xff\xd8\xff"]),
    ".svg": ("image/svg+xml", [b"<svg", b"<?xml"]),
}


def logo_path_for_ext(ext: str) -> str:
    return os.path.join(LOGO_DIR, LOGO_FILENAME + ext)


def current_logo_path() -> str | None:
    for ext in ALLOWED:
        p = logo_path_for_ext(ext)
        if os.path.isfile(p):
            return p
    return None


def validate_upload(filename: str, content: bytes) -> tuple[str, str]:
    """Returns (ext, error). error == '' means valid."""
    ext = os.path.splitext(filename or "")[1].lower()
    if ext not in ALLOWED:
        return "", "Logo must be a PNG, JPG or SVG image."
    if len(content) > MAX_BYTES:
        return "", "Logo is too large (max 2 MB)."
    if not content:
        return "", "Uploaded file is empty."
    mime, magics = ALLOWED[ext]
    head = content.lstrip()[:5].lower() if ext == ".svg" else content[:8]
    if not any(head.startswith(m) for m in magics):
        return "", "File content does not look like a valid image."
    return ext, ""


def save_upload(filename: str, content: bytes) -> tuple[str, str]:
    """Validates + stores the logo, removing any previous format. Returns (path, error)."""
    ext, err = validate_upload(filename, content)
    if err:
        return "", err
    try:
        os.makedirs(LOGO_DIR, exist_ok=True)
        for old_ext in ALLOWED:
            old = logo_path_for_ext(old_ext)
            if old_ext != ext and os.path.isfile(old):
                os.remove(old)
        path = logo_path_for_ext(ext)
        with open(path, "wb") as f:
            f.write(content)
        log.info("logo saved: %s (%s bytes)", path, len(content))
        return path, ""
    except OSError as exc:
        log.error("logo save failed: %s", exc)
        return "", "Could not save the logo. Please try again."


def delete_logo() -> None:
    for ext in ALLOWED:
        p = logo_path_for_ext(ext)
        try:
            if os.path.isfile(p):
                os.remove(p)
        except OSError as exc:
            log.error("logo delete failed: %s", exc)


def _flatten_to_rgb(raw: bytes) -> tuple[bytes, str] | tuple[None, None]:
    """PNG/JPG bytes -> opaque RGB PNG bytes (or (None, None) on failure).

    Transparent pixels become WHITE. Without this, renderers print the
    transparent area as solid BLACK (the black-square logo bug on thermal).
    """
    import io

    from PIL import Image

    try:
        img = Image.open(io.BytesIO(raw))
        if img.mode in ("RGBA", "LA") or (img.mode == "P" and "transparency" in img.info):
            bg = Image.new("RGB", img.size, (255, 255, 255))
            alpha = img.convert("RGBA").split()[-1]
            bg.paste(img.convert("RGB"), mask=alpha)
            img = bg
        else:
            img = img.convert("RGB")
        out = io.BytesIO()
        img.save(out, format="PNG")
        return out.getvalue(), "image/png"
    except Exception as exc:
        log.error("logo flatten failed: %s", exc)
        return None, None


def load_data_uri(path: str | None) -> str | None:
    """Base64 data URI for embedding in SVG, or None when unavailable.

    Raster images are flattened onto white first — transparency would
    otherwise print as a solid black square on thermal printers.
    """
    if not path or not os.path.isfile(path):
        return None
    try:
        if os.path.getsize(path) > MAX_BYTES:
            return None
        ext = os.path.splitext(path)[1].lower()
        with open(path, "rb") as f:
            raw = f.read()
        if ext in (".png", ".jpg", ".jpeg"):
            flat, mime = _flatten_to_rgb(raw)
            if flat is not None:
                raw, mime = flat, mime
            else:
                # Unreadable image: keep original bytes (old behaviour) so a
                # weird-but-valid file still has a chance to print.
                mime = ALLOWED.get(ext, ("image/png", []))[0]
        else:
            mime = ALLOWED.get(ext, ("image/png", []))[0]
        b64 = base64.b64encode(raw).decode("ascii")
        return f"data:{mime};base64,{b64}"
    except OSError as exc:
        log.error("logo read failed: %s", exc)
        return None
