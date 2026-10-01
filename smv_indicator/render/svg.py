"""Rendu SVG autonome (aucune dépendance) pour vérifier visuellement les événements.

Police demandée : Lora. Elle est déclarée dans le SVG ; elle ne s'affiche que si elle est
installée sur la machine qui ouvre le fichier (aucune police n'est embarquée).
"""
from __future__ import annotations

from html import escape

from smv.types import Bar

from .primitives import build

PALETTE = {
    "bg": "#FAF9F5", "fg": "#141413", "grid": "#E8E6DC", "muted": "#87867F",
    "up": "#5E7D5B", "down": "#C15F3C",
    "liq_intact": "#141413", "liq_clean": "#B0AEA5", "liq_taken": "#D4D2C8",
    "bos_bull": "#3B6E8F", "bos_bear": "#C15F3C",
    "demand": "#5E7D5B", "supply": "#C15F3C", "breaker": "#8A6FA8", "range": "#87867F",
    "imbalance": "#D9B44A", "fail": "#C15F3C", "idm": "#3B6E8F", "sweep": "#141413",
    "eq": "#8A6FA8", "odf": "#5E7D5B",
}


DEFAULT_LAYERS = frozenset({"demand", "supply", "range", "liq_intact", "liq_clean", "bos_bull",
                            "bos_bear", "fail", "idm", "sweep", "eq", "odf", "imbalance"})


def render(bars: list[Bar], events, start: int = 0, end: int | None = None,
           width: int = 1600, height: int = 800, title: str = "SMV",
           layers: frozenset = DEFAULT_LAYERS, lookback: int = 150) -> str:
    """`layers` : styles affichés (ajouter "breaker", "liq_taken" pour tout voir) ;
    `lookback` : n'affiche que les objets ancrés au plus `lookback` bougies avant la fenêtre."""
    end = len(bars) - 1 if end is None else min(end, len(bars) - 1)
    view = bars[start:end + 1]
    prims = build([e for e in events if e.confirm_index <= end], end)

    def keep(style: str, x0: int, x1: int) -> bool:
        return style.split("_dec")[0] in layers and x0 >= start - lookback and x1 >= start

    prims = {
        "boxes": [b for b in prims["boxes"] if keep(b.style, b.x0, b.x1)],
        "segments": [s for s in prims["segments"] if keep(s.style, s.x0, s.x1)],
        "markers": [m for m in prims["markers"] if m.style in layers],
    }
    pad_l, pad_r, pad_t, pad_b = 10, 70, 34, 24
    lo = min(b.low for b in view)
    hi = max(b.high for b in view)
    span = (hi - lo) or 1.0
    lo -= span * 0.04
    hi += span * 0.04
    n = len(view)
    cw = (width - pad_l - pad_r) / max(n, 1)

    def X(i: float) -> float:
        return pad_l + (i - start + 0.5) * cw

    def Y(p: float) -> float:
        p = min(max(p, lo), hi)  # les objets hors de l'échelle sont coupés au bord
        return pad_t + (hi - p) / (hi - lo) * (height - pad_t - pad_b)

    def clip(x0: int, x1: int) -> tuple[int, int] | None:
        if x1 < start or x0 > end:
            return None
        return max(x0, start), min(x1, end)

    font = "font-family=\"Lora, serif\""
    out = [f'<svg xmlns="http://www.w3.org/2000/svg" width="{width}" height="{height}" '
           f'viewBox="0 0 {width} {height}">',
           f'<rect width="100%" height="100%" fill="{PALETTE["bg"]}"/>',
           f'<text x="{pad_l}" y="20" {font} font-size="15" fill="{PALETTE["fg"]}">{escape(title)}</text>']
    for k in range(6):
        p = lo + (hi - lo) * k / 5
        out.append(f'<line x1="{pad_l}" x2="{width - pad_r}" y1="{Y(p):.1f}" y2="{Y(p):.1f}" '
                   f'stroke="{PALETTE["grid"]}" stroke-width="1"/>')
        out.append(f'<text x="{width - pad_r + 4}" y="{Y(p) + 4:.1f}" {font} font-size="11" '
                   f'fill="{PALETTE["muted"]}">{p:.5g}</text>')
    for bx in prims["boxes"]:
        c = clip(bx.x0, bx.x1)
        if c is None:
            continue
        col = PALETTE.get(bx.style.split("_")[0], PALETTE["muted"])
        dec = bx.style.endswith("_dec")
        y0, y1 = sorted((Y(bx.y0), Y(bx.y1)))
        out.append(f'<rect x="{X(c[0]) - cw / 2:.1f}" y="{y0:.1f}" width="{(c[1] - c[0] + 1) * cw:.1f}" '
                   f'height="{max(y1 - y0, 1):.1f}" fill="{col}" fill-opacity="{0.22 if dec else 0.12}" '
                   f'stroke="{col}" stroke-opacity="0.6" stroke-width="{1.5 if dec else 0.8}">'
                   f'<title>{escape(bx.style)} {escape(str(bx.meta))}</title></rect>')
        if bx.label:
            out.append(f'<text x="{X(c[0]) - cw / 2 + 2:.1f}" y="{y0 + 11:.1f}" {font} font-size="10" '
                       f'fill="{col}">{escape(bx.label)}</text>')
    for b in view:
        col = PALETTE["up"] if b.close >= b.open else PALETTE["down"]
        x = X(b.index)
        out.append(f'<line x1="{x:.1f}" x2="{x:.1f}" y1="{Y(b.high):.1f}" y2="{Y(b.low):.1f}" stroke="{col}"/>')
        top, bot = Y(max(b.open, b.close)), Y(min(b.open, b.close))
        out.append(f'<rect x="{x - cw * 0.35:.1f}" y="{top:.1f}" width="{cw * 0.7:.1f}" '
                   f'height="{max(bot - top, 0.8):.1f}" fill="{col}"/>')
    for s in prims["segments"]:
        c = clip(s.x0, s.x1)
        if c is None:
            continue
        col = PALETTE.get(s.style, PALETTE["muted"])
        dash = ' stroke-dasharray="4 3"' if s.style in ("liq_clean", "liq_taken") else ""
        w = 1.6 if s.style.startswith("bos") else 0.9
        out.append(f'<line x1="{X(c[0]):.1f}" x2="{X(c[1]):.1f}" y1="{Y(s.y):.1f}" y2="{Y(s.y):.1f}" '
                   f'stroke="{col}" stroke-width="{w}"{dash}><title>{escape(s.style)} '
                   f'{escape(str(s.meta))}</title></line>')
        if s.label:
            out.append(f'<text x="{X(c[1]) + 2:.1f}" y="{Y(s.y) - 2:.1f}" {font} font-size="10" '
                       f'fill="{col}">{escape(s.label)}</text>')
    for m in prims["markers"]:
        if not start <= m.x <= end:
            continue
        col = PALETTE.get(m.style, PALETTE["fg"])
        out.append(f'<circle cx="{X(m.x):.1f}" cy="{Y(m.y):.1f}" r="3" fill="none" stroke="{col}"/>')
        out.append(f'<text x="{X(m.x) + 4:.1f}" y="{Y(m.y) - 4:.1f}" {font} font-size="10" '
                   f'fill="{col}">{escape(m.label)}</text>')
    out.append("</svg>")
    return "\n".join(out)
