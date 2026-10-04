import type { ChallengeSummary } from '../api/types';
import { formatMetric, formatValue } from '../lib/format';

interface Props {
  challenge: ChallengeSummary;
  primaryScore: number | null;
  metrics: Record<string, unknown> | null;
  hidden?: boolean;
  compact?: boolean;
}

/** Primary score + secondary metrics as a definition list. */
export function MetricList({ challenge, primaryScore, metrics, hidden = false, compact = false }: Props) {
  if (hidden) return <p className="muted">Scores are hidden by the teacher.</p>;
  const pm = challenge.primary_metric;
  return (
    <dl className={`metrics${compact ? ' compact' : ''}`}>
      <div className="metric primary">
        <dt>{pm.label}</dt>
        <dd>{formatValue(primaryScore, pm.format)}</dd>
      </div>
      {challenge.secondary_metrics.map((m) => (
        <div className="metric" key={m.key}>
          <dt>{m.label}</dt>
          <dd>{formatMetric(m, metrics?.[m.key])}</dd>
        </div>
      ))}
    </dl>
  );
}
