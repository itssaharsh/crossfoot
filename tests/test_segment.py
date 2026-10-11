"""Block and column-line finding on a small ruled image drawn here."""
from PIL import Image, ImageDraw

from crossfoot.segment import find_blocks


def ruled(draw, y, ncols=4, x0=300, colw=100, rows=3, rowh=24):
    x1 = x0 + ncols * colw
    for r in range(rows + 1):
        draw.line([(x0, y + r * rowh), (x1, y + r * rowh)], fill=0, width=2)
    for c in range(ncols + 1):
        draw.line([(x0 + c * colw, y), (x0 + c * colw, y + rows * rowh)], fill=0, width=2)
    draw.text((60, y + 10), "Candidate A", fill=0)


def make():
    im = Image.new("L", (800, 600), 255)
    d = ImageDraw.Draw(im)
    ruled(d, 60)
    ruled(d, 220)
    d.text((60, 560), "Page 1 of 1, footer text", fill=0)
    return im, d


def test_finds_two_blocks_and_ignores_footer():
    im, _ = make()
    blocks = find_blocks(im)
    assert len(blocks) == 2
    assert blocks[0].y0 < 60 < blocks[0].rule_y0 + 2 and blocks[1].y0 > blocks[0].y1


def test_finds_column_lines():
    im, _ = make()
    b = find_blocks(im)[0]
    assert len(b.lines) == 5
    assert [round(x, -1) for x in b.lines] == [300, 400, 500, 600, 700]
    assert not b.blackouts


def test_blacked_out_cell_is_not_a_line():
    im, d = make()
    d.rectangle([(405, 62), (595, 130)], fill=0)
    b = find_blocks(im)[0]
    assert len(b.blackouts) == 1
    assert b.blackouts[0][0] < 420 and b.blackouts[0][1] > 580
