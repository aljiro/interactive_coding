/** K x K confusion matrix (rows = true class, columns = predicted), shaded by row fraction. */
import { ACCENT, tint } from '../shared/colors';

interface Props {
  confusion: number[][];
  labels: string[];
  compact?: boolean;
}

export function ConfusionMatrix({ confusion, labels, compact = false }: Props) {
  const k = confusion.length;
  const cell = compact ? 22 : 30;
  const left = 34;
  const top = 34;
  const width = left + k * cell + 8;
  const height = top + k * cell + 8;
  const rowTotals = confusion.map((row) => Math.max(1, row.reduce((a, b) => a + b, 0)));
  return (
    <svg className="confusion" viewBox={`0 0 ${width} ${height}`} width={width} height={height} role="img" aria-label="Confusion matrix on the hidden test set">
      <text className="cm-title" x={left + (k * cell) / 2} y={11} textAnchor="middle">
        predicted →
      </text>
      <text className="cm-title" transform={`translate(10,${top + (k * cell) / 2}) rotate(-90)`} textAnchor="middle">
        true →
      </text>
      {labels.slice(0, k).map((l, j) => (
        <text key={`c${j}`} className="cm-label" x={left + j * cell + cell / 2} y={top - 6} textAnchor="middle">
          {l}
        </text>
      ))}
      {labels.slice(0, k).map((l, i) => (
        <text key={`r${i}`} className="cm-label" x={left - 6} y={top + i * cell + cell / 2} dy="0.35em" textAnchor="end">
          {l}
        </text>
      ))}
      {confusion.map((row, i) =>
        row.map((v, j) => {
          const frac = v / rowTotals[i];
          const fill = i === j ? tint('#2f9e44', 0.15 + 0.85 * frac) : tint(ACCENT, Math.min(1, frac * 4));
          const dark = (i === j && frac > 0.55) || (i !== j && frac * 4 > 0.6);
          return (
            <g key={`${i}-${j}`} transform={`translate(${left + j * cell},${top + i * cell})`}>
              <rect width={cell} height={cell} fill={v === 0 ? '#fff' : fill} stroke="#fff" />
              {v > 0 && (
                <text className={`cm-value${dark ? ' dark' : ''}`} x={cell / 2} y={cell / 2} dy="0.35em" textAnchor="middle">
                  {v}
                </text>
              )}
            </g>
          );
        }),
      )}
    </svg>
  );
}
