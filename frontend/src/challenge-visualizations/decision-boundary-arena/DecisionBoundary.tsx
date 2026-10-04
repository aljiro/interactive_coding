import { useMemo } from 'react';
import { scaleLinear } from 'd3-scale';
import { Axis } from '../shared/Axis';
import { CLASS_COLORS, probabilityFill } from '../shared/colors';
import { probabilityContours, type GridSpec } from './contours';

export interface DecisionBoundaryData {
  points: { x: number[]; y: number[]; label: number[] };
  grid: GridSpec;
  axis_labels?: [string, string];
  class_labels?: [string, string];
}

interface Props {
  data: DecisionBoundaryData;
  /** Class-1 probabilities on the grid (row-major, x fastest) or null for "no selection". */
  probabilities: number[] | null;
  title?: string;
  compact?: boolean;
}

const MARGIN = { top: 12, right: 14, bottom: 44, left: 54 };
const BAND_THRESHOLDS = [0.1, 0.2, 0.3, 0.4, 0.5, 0.6, 0.7, 0.8, 0.9];

/**
 * Scientific 2-D scatter + probability field + 0.5 decision contour. Rendered with a fixed
 * viewBox whose aspect ratio equals the data aspect ratio, so the SVG scales uniformly.
 */
export function DecisionBoundary({ data, probabilities, title, compact = false }: Props) {
  const { grid, points } = data;
  const dataAspect = (grid.y1 - grid.y0) / (grid.x1 - grid.x0);
  const innerW = 640;
  const innerH = Math.round(innerW * dataAspect);
  const width = innerW + MARGIN.left + MARGIN.right;
  const height = innerH + MARGIN.top + MARGIN.bottom;

  const xScale = useMemo(() => scaleLinear().domain([grid.x0, grid.x1]).range([MARGIN.left, MARGIN.left + innerW]), [grid, innerW]);
  const yScale = useMemo(() => scaleLinear().domain([grid.y0, grid.y1]).range([MARGIN.top + innerH, MARGIN.top]), [grid, innerH]);

  const field = useMemo(() => {
    if (!probabilities || probabilities.length !== grid.nx * grid.ny) return null;
    return probabilityContours(probabilities, grid, xScale, yScale, BAND_THRESHOLDS);
  }, [probabilities, grid, xScale, yScale]);

  const clipId = `clip-${compact ? 'c' : 'f'}`;

  return (
    <svg
      className={`decision-boundary${compact ? ' compact' : ''}`}
      viewBox={`0 0 ${width} ${height}`}
      preserveAspectRatio="xMidYMid meet"
      role="img"
      aria-label={title ?? 'Decision boundary plot'}
    >
      <defs>
        <clipPath id={clipId}>
          <rect x={MARGIN.left} y={MARGIN.top} width={innerW} height={innerH} />
        </clipPath>
      </defs>
      <rect className="plot-bg" x={MARGIN.left} y={MARGIN.top} width={innerW} height={innerH} />
      <g clipPath={`url(#${clipId})`}>
        {field && (
          <g className="field" aria-hidden="true">
            <rect x={MARGIN.left} y={MARGIN.top} width={innerW} height={innerH} fill={probabilityFill(0.05)} />
            {field.bands.map((b) => (
              <path key={b.threshold} d={b.path} fill={probabilityFill(Math.min(0.95, b.threshold + 0.05))} stroke="none" />
            ))}
            <path className="decision-contour" d={field.boundary} />
          </g>
        )}
        <g className="points">
          {points.x.map((x, i) => (
            <circle
              key={i}
              cx={xScale(x)}
              cy={yScale(points.y[i])}
              r={compact ? 2.4 : 3.2}
              fill={CLASS_COLORS[points.label[i]] ?? '#888'}
            />
          ))}
        </g>
      </g>
      <rect className="plot-frame" x={MARGIN.left} y={MARGIN.top} width={innerW} height={innerH} />
      <Axis scale={xScale} orient="bottom" at={MARGIN.top + innerH} label={data.axis_labels?.[0] ?? 'x₁'} length={innerW} />
      <Axis scale={yScale} orient="left" at={MARGIN.left} label={data.axis_labels?.[1] ?? 'x₂'} length={innerH} ticks={6} />
      {!probabilities && !compact && (
        <text className="plot-hint" x={MARGIN.left + innerW / 2} y={MARGIN.top + 24} textAnchor="middle">
          Select a student to show their decision boundary
        </text>
      )}
    </svg>
  );
}

export function ClassLegend({ labels }: { labels?: [string, string] }) {
  return (
    <div className="legend" aria-label="Legend">
      {CLASS_COLORS.map((c, i) => (
        <span key={i} className="legend-item">
          <span className="legend-swatch" style={{ background: c }} /> {labels?.[i] ?? `class ${i}`}
        </span>
      ))}
      <span className="legend-item">
        <span className="legend-line" /> p = 0.5 boundary
      </span>
    </div>
  );
}
