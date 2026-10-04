import { contours as d3contours } from 'd3-contour';
import type { ScaleLinear } from 'd3-scale';

export interface GridSpec {
  nx: number;
  ny: number;
  x0: number;
  x1: number;
  y0: number;
  y1: number;
}

/** Convert a d3-contour MultiPolygon (grid index space) to an SVG path in pixel space. */
function toPath(
  geometry: GeoJSON.MultiPolygon,
  grid: GridSpec,
  xScale: ScaleLinear<number, number>,
  yScale: ScaleLinear<number, number>,
): string {
  // d3-contour treats value i as occupying cell [i, i+1); its centre is at i + 0.5.
  const dx = (grid.x1 - grid.x0) / (grid.nx - 1);
  const dy = (grid.y1 - grid.y0) / (grid.ny - 1);
  const px = (gx: number) => xScale(grid.x0 + (gx - 0.5) * dx);
  const py = (gy: number) => yScale(grid.y0 + (gy - 0.5) * dy);
  let d = '';
  for (const polygon of geometry.coordinates) {
    for (const ring of polygon) {
      d += ring.map(([gx, gy], i) => `${i ? 'L' : 'M'}${px(gx).toFixed(1)},${py(gy).toFixed(1)}`).join('') + 'Z';
    }
  }
  return d;
}

export interface ContourBand {
  threshold: number;
  path: string;
}

/** Filled probability bands (regions where p >= threshold) and the decision contour. */
export function probabilityContours(
  values: number[],
  grid: GridSpec,
  xScale: ScaleLinear<number, number>,
  yScale: ScaleLinear<number, number>,
  thresholds: number[],
  decision = 0.5,
): { bands: ContourBand[]; boundary: string } {
  const gen = d3contours().size([grid.nx, grid.ny]).smooth(true);
  const bands = gen.thresholds(thresholds)(values).map((c) => ({ threshold: c.value, path: toPath(c, grid, xScale, yScale) }));
  const [b] = gen.thresholds([decision])(values);
  return { bands, boundary: b ? toPath(b, grid, xScale, yScale) : '' };
}
