// The pencil loop: one closed path round a box, slightly irregular like a hand-drawn loop. The shape is fixed
// (nothing random) and scaled to the box; it starts at the top left and runs clockwise, so drawing it on from the
// start reads as a pencil going round. Units are whatever the box is in; `air` is the clear space on every side.
const N = 28, START = -Math.PI * 0.75, SQUARE = 4;

export function loopPath(box, air) {
  const cx = (box[0] + box[2]) / 2, cy = (box[1] + box[3]) / 2;
  const a = (box[2] - box[0]) / 2 + air, b = (box[3] - box[1]) / 2 + air;
  const pts = [];
  for (let i = 0; i <= N; i++) {
    const th = START + (i / N) * Math.PI * 2, c = Math.cos(th), s = Math.sin(th);
    const r = Math.pow(Math.pow(Math.abs(c) / a, SQUARE) + Math.pow(Math.abs(s) / b, SQUARE), -1 / SQUARE);
    // never inside the superellipse (the air is a minimum), drifting out a little as the pencil goes round
    const k = 1 + 0.025 * (1 + Math.sin(2 * th + 1)) + 0.02 * (1 + Math.sin(3 * th + 0.5)) + 0.04 * (i / N);
    pts.push([cx + c * r * k, cy + s * r * k]);
  }
  // a Catmull-Rom spline through the points, as cubic Beziers
  const f = n => n.toFixed(2);
  let d = `M${f(pts[0][0])} ${f(pts[0][1])}`;
  for (let i = 0; i < pts.length - 1; i++) {
    const p0 = pts[Math.max(0, i - 1)], p1 = pts[i], p2 = pts[i + 1], p3 = pts[Math.min(pts.length - 1, i + 2)];
    d += `C${f(p1[0] + (p2[0] - p0[0]) / 6)} ${f(p1[1] + (p2[1] - p0[1]) / 6)} ${f(p2[0] - (p3[0] - p1[0]) / 6)} ${f(p2[1] - (p3[1] - p1[1]) / 6)} ${f(p2[0])} ${f(p2[1])}`;
  }
  return d + 'Z';
}

// with no ink box: the cell's own box as a rounded rectangle, from the top left, clockwise
export function boxPath(box, r = 4) {
  const [x0, y0, x1, y1] = box, k = Math.min(r, (x1 - x0) / 2, (y1 - y0) / 2);
  return `M${x0 + k} ${y0}H${x1 - k}Q${x1} ${y0} ${x1} ${y0 + k}V${y1 - k}Q${x1} ${y1} ${x1 - k} ${y1}H${x0 + k}` +
         `Q${x0} ${y1} ${x0} ${y1 - k}V${y0 + k}Q${x0} ${y0} ${x0 + k} ${y0}Z`;
}
