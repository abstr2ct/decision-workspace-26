"""Typography, palette, and vector artwork for the submission PDFs."""

import math
from pathlib import Path

from reportlab.lib.colors import HexColor, linearlyInterpolatedColor
from reportlab.pdfbase import pdfmetrics
from reportlab.pdfbase.ttfonts import TTFont


PAGE = '#130B24'
PANEL = '#211435'
PANEL_ALT = '#281740'
FEATURE = '#3A2058'
TEXT = '#F4EDFF'
MUTED = '#CCBEDD'
EDGE = '#523B6A'
PINK = '#FF9CD9'
LILAC = '#CCADFF'
CORAL = '#FFC0C6'
BRIGHT = '#FFF9FF'


def register_fonts(folder: Path):
    """Use the display set when supplied, with system faces as a build fallback."""
    display_set = {
        'UI': 'Manrope-Regular.ttf', 'UIB': 'Manrope-Bold.ttf',
        'UIL': 'Manrope-Medium.ttf', 'Display': 'Unbounded-SemiBold.ttf',
    }
    system_set = {'UI': 'segoeui.ttf', 'UIB': 'segoeuib.ttf',
                  'UIL': 'segoeuil.ttf', 'Display': 'segoeuib.ttf'}
    faces = display_set if all((folder / file).is_file() for file in display_set.values()) else system_set
    mono = folder / 'consola.ttf'
    for name, file in faces.items():
        pdfmetrics.registerFont(TTFont(name, str(folder / file)))
    pdfmetrics.registerFont(TTFont('Mono', str(mono if mono.is_file() else Path('C:/Windows/Fonts/consola.ttf'))))
    for regular in ('UI', 'UIL'):
        pdfmetrics.registerFontFamily(regular, normal=regular, bold='UIB', italic=regular, boldItalic='UIB')


def _diamond(canvas, x, y, radius, color):
    path = canvas.beginPath()
    path.moveTo(x, y + radius)
    path.lineTo(x + radius, y)
    path.lineTo(x, y - radius)
    path.lineTo(x - radius, y)
    path.close()
    canvas.setFillColor(HexColor(color))
    canvas.drawPath(path, fill=1, stroke=0)


def _ribbon(canvas, cx, cy, rx, ry, phase, amount):
    dark = HexColor('#2B1449')
    lit = HexColor('#E04FAE')
    canvas.setLineWidth(.38 + amount * .16)
    for index in range(37):
        offset = index / 36
        path = canvas.beginPath()
        for step in range(131):
            t = -.92 + step * .034
            a = t + phase + offset * .92
            x = cx + (rx + offset * rx * .32) * math.cos(a) + rx * .33 * math.sin(2*t + offset*2.7)
            y = cy + (ry - offset * ry * .29) * math.sin(a) + ry * .38 * math.cos(2*t - offset*3.9)
            (path.moveTo if step == 0 else path.lineTo)(x, y)
        shimmer = (.18 + .82 * math.sin(math.pi * offset)**2) * amount
        canvas.setStrokeColor(linearlyInterpolatedColor(dark, lit, 0, 1, shimmer))
        canvas.drawPath(path)


def page_art(canvas, width, height, page, cover=False, compact=False):
    """Paint cropped folds and registration marks outside the reading area."""
    canvas.saveState()
    canvas.setFillColor(HexColor(PAGE))
    canvas.rect(0, 0, width, height, fill=1, stroke=0)
    if cover:
        canvas.saveState()
        if compact:
            canvas.translate(width * .31, height * .55)
            canvas.scale(.69, .45)
        center_x, center_y = width - 20, height - 222
        canvas.setLineWidth(.6)
        canvas.setStrokeColor(HexColor('#432659'))
        for radius in (97, 151, 207):
            canvas.circle(center_x, center_y, radius, fill=0, stroke=1)
        _ribbon(canvas, center_x + 13, center_y, 181, 139, .62, .64 if compact else 1)
        _ribbon(canvas, center_x + 64, center_y - 82, 148, 84, 1.28, .40 if compact else .62)
        for x, y, radius, color in [(width-106,height-108,5,PINK), (width-62,height-344,3,LILAC),
                                     (width-216,height-288,3,LILAC), (width-135,height-410,4,PINK)]:
            _diamond(canvas, x, y, radius, color)
        canvas.restoreState()
    else:
        _ribbon(canvas, width + 3, height - 41, 112, 77, .4 + .13 * (page % 4), .27)
        _diamond(canvas, width - 51, height - 40, 3.5, PINK)
        _diamond(canvas, width - 35, height - 57, 2.2, LILAC)
    canvas.setFillColor(HexColor(PINK))
    canvas.rect(45, height - 28, 19 if cover else 10, 1.5, fill=1, stroke=0)
    canvas.setFillColor(HexColor(LILAC))
    canvas.rect(68 if cover else 59, height - 28, 3, 1.5, fill=1, stroke=0)
    canvas.restoreState()
