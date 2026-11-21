"""Shared offline styling for HTML exports."""

import base64
from functools import lru_cache
from pathlib import Path


ASSETS = Path(__file__).with_name('assets')


@lru_cache(maxsize=1)
def styles():
    """Embed local assets so a single exported file can be opened offline."""
    fonts = (
        ('Manrope', 'Manrope.woff2', '400 800'),
        ('Unbounded', 'Unbounded.woff2', '650'),
    )
    faces = []
    for family, filename, weight in fonts:
        source = base64.b64encode((ASSETS / filename).read_bytes()).decode('ascii')
        faces.append(f"@font-face{{font-family:{family};font-style:normal;font-weight:{weight};"
                     f"font-display:swap;src:url(data:font/woff2;base64,{source}) format('woff2')}}")
    return '\n'.join(faces) + '\n' + (ASSETS / 'report.css').read_text(encoding='utf-8')
