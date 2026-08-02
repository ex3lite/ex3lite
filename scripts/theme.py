"""Shared palette + tiny SVG helpers for the ex3lite profile graphics.

Palette and geometry are the single source of truth for every generated asset,
so cards, stats and the heatmap always stay in the same visual system.
"""

MONO = "ui-monospace,SFMono-Regular,Menlo,Consolas,monospace"

THEMES = {
    "dark": {
        "bg": "#05070a", "panel": "#0a0f15", "panel2": "#0f1720", "line": "#1c2833",
        "dim": "#5b7080", "muted": "#8ba0ae", "fg": "#dce8f1",
        "green": "#5ef2a0", "amber": "#f2b45e",
        "cells": ["#0e1620", "#123c2b", "#1b6c49", "#2caa70", "#5ef2a0"],
    },
    "light": {
        "bg": "#fcfdfc", "panel": "#ffffff", "panel2": "#f3f7f5", "line": "#dbe3e2",
        "dim": "#66798a", "muted": "#4a5d6b", "fg": "#08121a",
        "green": "#0b8a58", "amber": "#9d6a08",
        "cells": ["#e9eeec", "#c6ebd7", "#7fd2a8", "#33a276", "#0b8a58"],
    },
}


def esc(s):
    return str(s).replace("&", "&amp;").replace("<", "&lt;").replace(">", "&gt;")


def cw(size):
    """Advance width of one monospace glyph."""
    return size * 0.6


def text(x, y, s, size=13, fill=None, weight=None, anchor=None, ls=None, op=None):
    a = f'<text font-family="{MONO}" x="{x}" y="{y}" font-size="{size}"'
    if fill:
        a += f' fill="{fill}"'
    if weight:
        a += f' font-weight="{weight}"'
    if anchor:
        a += f' text-anchor="{anchor}"'
    if ls:
        a += f' letter-spacing="{ls}"'
    if op is not None:
        a += f' opacity="{op}"'
    return a + f">{esc(s)}</text>"


def rect(x, y, w, h, rx=None, fill=None, stroke=None, op=None):
    a = f'<rect x="{x}" y="{y}" width="{w}" height="{h}"'
    if rx:
        a += f' rx="{rx}"'
    if fill:
        a += f' fill="{fill}"'
    if stroke:
        a += f' stroke="{stroke}" stroke-width="1"'
    if op is not None:
        a += f' opacity="{op}"'
    return a + "/>"


def svg_open(w, h, title):
    return (
        f'<svg xmlns="http://www.w3.org/2000/svg" width="{w}" height="{h}" '
        f'viewBox="0 0 {w} {h}" role="img" aria-label="{esc(title)}">'
        f"<style>text{{white-space:pre}}</style>"
    )


def group(n):
    """1284 -> '1 284' (thin-ish separator that survives every font)."""
    s = str(n)
    out = []
    while len(s) > 3:
        out.insert(0, s[-3:])
        s = s[:-3]
    out.insert(0, s)
    return " ".join(out)
