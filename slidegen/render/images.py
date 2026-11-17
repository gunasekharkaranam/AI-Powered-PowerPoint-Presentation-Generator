"""Find, download and crop photos safely.

v1 problems fixed:
* Safe search was OFF -> now Openverse (openly licensed images, mature=false).
* Images were stretched to 4.5x3 in -> now center-cropped to the exact box shape.
* No credit was given -> every photo gets a credit line (creator + licence).
* Any URL was downloaded -> size limit, timeout, image content-type only.
"""
from dataclasses import dataclass
import io
import os
import tempfile

from PIL import Image

OPENVERSE = "https://api.openverse.org/v1/images/"
MAX_BYTES = 8_000_000
UA = {"User-Agent": "SlideGen/2.0 (student project)"}


@dataclass
class Photo:
    path: str
    credit: str
    source_url: str = ""


def crop_to_ratio(img: Image.Image, ratio: float) -> Image.Image:
    """Center-crop so width/height == ratio (no stretching)."""
    w, h = img.size
    if w / h > ratio:            # too wide -> cut the sides
        new_w = int(h * ratio)
        left = (w - new_w) // 2
        return img.crop((left, 0, left + new_w, h))
    new_h = int(w / ratio)       # too tall -> cut top and bottom
    top = (h - new_h) // 2
    return img.crop((0, top, w, top + new_h))


def prepare(data: bytes, ratio: float, max_px: int = 1600) -> str:
    img = Image.open(io.BytesIO(data)).convert("RGB")
    img = crop_to_ratio(img, ratio)
    img.thumbnail((max_px, max_px))
    fd, path = tempfile.mkstemp(suffix=".jpg", prefix="slidegen_")
    os.close(fd)
    img.save(path, quality=88)
    return path


def openverse_photo(query: str, ratio: float, session=None):
    """Return a Photo or None. Never raises: a missing photo must not break the deck."""
    import requests
    s = session or requests
    try:
        r = s.get(OPENVERSE, params={"q": query, "page_size": 8, "mature": "false",
                                     "license_type": "all-cc", "aspect_ratio": "wide"},
                  headers=UA, timeout=10)
        r.raise_for_status()
        for item in r.json().get("results", []):
            img = s.get(item["url"], headers=UA, timeout=12, stream=True)
            if img.status_code != 200 or not img.headers.get("content-type", "").startswith("image/"):
                continue
            data = img.raw.read(MAX_BYTES + 1, decode_content=True)
            if len(data) > MAX_BYTES:
                continue
            credit = f'Photo: {item.get("creator") or "unknown"} ({(item.get("license") or "").upper()} '\
                     f'{item.get("license_version") or ""}) via Openverse'
            return Photo(prepare(data, ratio), credit.replace("  ", " "), item.get("foreign_landing_url", ""))
    except Exception:
        return None
    return None
