"""Finds blocks and column lines on a ruled page from the image itself. No model.

A block is a band of ink separated from the next by blank rows. A band counts as a block only if it holds a
long horizontal rule, which leaves out the footer, the signature and scanner specks. Inside a block, the column
lines are columns of dark pixels that run the height of the ruled rows; a dark run wider than a line is a
blacked-out region, reported separately.
"""
from __future__ import annotations

from dataclasses import dataclass, field

import numpy as np
from PIL import Image

DARK = 110          # grey level below which a pixel is ink
MIN_GAP = 8         # blank rows that separate two blocks, in pixels at 200 dpi
RULE_FRACTION = 0.5 # share of the table width a row must cover to count as a rule
LINE_FRACTION = 0.6 # share of the ruled height a column must cover to count as a line
GRAND_DROP = 24     # pixels added below a block so the grand total is inside the crop
MAX_LINE_WIDTH = 7  # a darker run wider than this is a blackout, not a line


@dataclass
class Block:
    y0: int
    y1: int
    x0: int
    x1: int
    rule_y0: int
    rule_y1: int
    lines: list = field(default_factory=list)   # x centres of column lines
    blackouts: list = field(default_factory=list)  # (x0, x1) of dark regions wider than a line

    @property
    def box(self) -> tuple[int, int, int, int]:
        return (self.x0, self.y0, self.x1, self.y1)


def _runs(mask: np.ndarray) -> list[tuple[int, int]]:
    """Inclusive (start, end) of each run of True."""
    idx = np.flatnonzero(mask)
    if idx.size == 0:
        return []
    cuts = np.flatnonzero(np.diff(idx) > 1)
    starts = np.r_[idx[0], idx[cuts + 1]]
    ends = np.r_[idx[cuts], idx[-1]]
    return list(zip(starts.tolist(), ends.tolist()))


def find_blocks(image, *, pad: int = 6) -> list[Block]:
    im = image if isinstance(image, Image.Image) else Image.open(image)
    g = np.asarray(im.convert("L"))
    h, w = g.shape
    xl, xr = int(0.04 * w), int(0.98 * w)
    dark = g[:, xl:xr] < DARK
    # the thick bar under the TOTAL column runs down into the next block's gap, so band ink ignores the right edge
    ink = dark[:, :int(0.88 * w) - xl].sum(axis=1) >= 2
    # merge bands whose gap is below MIN_GAP
    bands: list[list[int]] = []
    for s, e in _runs(ink):
        if bands and s - bands[-1][1] <= MIN_GAP:
            bands[-1][1] = e
        else:
            bands.append([s, e])
    rule_rows = dark[:, int(0.08 * w):].mean(axis=1) >= RULE_FRACTION
    blocks = []
    for s, e in bands:
        rr = np.flatnonzero(rule_rows[s:e + 1])
        if rr.size == 0 or e - s < 20:
            continue
        r0, r1 = s + int(rr[0]), s + int(rr[-1])
        b = Block(max(0, s - pad), min(h - 1, e + pad), xl, xr, r0, r1)
        _column_lines(dark, b, xl)
        blocks.append(b)
    # the grand total hangs below the small totals at the far right, outside the band-finding range
    for b, nxt in zip(blocks, blocks[1:] + [None]):
        b.y1 = min(h - 1, b.y1 + GRAND_DROP, (nxt.y0 + 12) if nxt else h - 1)
    return blocks


def _column_lines(dark: np.ndarray, b: Block, xl: int) -> None:
    band = dark[b.rule_y0:b.rule_y1 + 1]
    if band.shape[0] < 4:
        return
    cover = band.mean(axis=0) >= LINE_FRACTION
    for s, e in _runs(cover):
        if e - s + 1 <= MAX_LINE_WIDTH:
            b.lines.append(xl + (s + e) // 2)
        else:
            b.blackouts.append((xl + s, xl + e))
