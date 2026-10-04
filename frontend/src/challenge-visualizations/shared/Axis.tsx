import type { ScaleLinear } from 'd3-scale';

interface AxisProps {
  scale: ScaleLinear<number, number>;
  orient: 'bottom' | 'left';
  /** Position of the axis line along the other dimension (y for bottom, x for left). */
  at: number;
  ticks?: number;
  label?: string;
  length: number;
  format?: (v: number) => string;
}

/** Minimal SVG axis (no DOM mutation, so it plays nicely with React). */
export function Axis({ scale, orient, at, ticks = 5, label, length, format }: AxisProps) {
  const values = scale.ticks(ticks);
  const fmt = format ?? ((v: number) => scale.tickFormat(ticks)(v));
  const [r0, r1] = scale.range();
  if (orient === 'bottom') {
    return (
      <g className="axis" transform={`translate(0,${at})`}>
        <line x1={r0} x2={r1} y1={0} y2={0} />
        {values.map((v) => (
          <g key={v} transform={`translate(${scale(v)},0)`}>
            <line y2={5} />
            <text y={18} textAnchor="middle">{fmt(v)}</text>
          </g>
        ))}
        {label && (
          <text className="axis-label" x={(r0 + r1) / 2} y={36} textAnchor="middle">{label}</text>
        )}
      </g>
    );
  }
  return (
    <g className="axis" transform={`translate(${at},0)`}>
      <line y1={r0} y2={r1} x1={0} x2={0} />
      {values.map((v) => (
        <g key={v} transform={`translate(0,${scale(v)})`}>
          <line x2={-5} />
          <text x={-8} dy="0.32em" textAnchor="end">{fmt(v)}</text>
        </g>
      ))}
      {label && (
        <text className="axis-label" transform={`translate(${-44},${length / 2}) rotate(-90)`} textAnchor="middle">
          {label}
        </text>
      )}
    </g>
  );
}
