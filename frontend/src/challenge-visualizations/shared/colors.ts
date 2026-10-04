/** Restrained scientific palette shared by visualizations. */
export const CLASS_COLORS = ['#2f6db5', '#e0782f']; // class 0 (blue), class 1 (orange)
export const INK = '#1f2933';
export const MUTED = '#6b7280';
export const ACCENT = '#0b7285';
export const IMPROVED = '#2f9e44';

function hex(c: string): [number, number, number] {
  const n = parseInt(c.slice(1), 16);
  return [(n >> 16) & 255, (n >> 8) & 255, n & 255];
}

/** Mix colour `c` with white: t=0 -> white, t=1 -> c. */
export function tint(c: string, t: number): string {
  const [r, g, b] = hex(c);
  const m = (v: number) => Math.round(255 + (v - 255) * t);
  return `rgb(${m(r)}, ${m(g)}, ${m(b)})`;
}

/** Diverging fill for a class-1 probability: light blue (0) - white (0.5) - light orange (1). */
export function probabilityFill(p: number, maxTint = 0.45): string {
  if (p < 0.5) return tint(CLASS_COLORS[0], ((0.5 - p) / 0.5) * maxTint);
  return tint(CLASS_COLORS[1], ((p - 0.5) / 0.5) * maxTint);
}
