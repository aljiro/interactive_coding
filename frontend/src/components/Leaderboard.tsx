import type { ChallengeSummary, ParticipantLive } from '../api/types';
import { formatTime, formatValue } from '../lib/format';

interface Props {
  participants: ParticipantLive[];
  challenge: ChallengeSummary;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  scoresHidden: boolean;
}

/** Compact, accessible table - a secondary view next to the challenge visualization. */
export function Leaderboard({ participants, challenge, selectedId, onSelect, scoresHidden }: Props) {
  const rows = [...participants].sort((a, b) => (a.rank ?? 1e9) - (b.rank ?? 1e9) || a.display_name.localeCompare(b.display_name));
  const secondary = challenge.secondary_metrics.slice(0, 2);
  return (
    <table className="leaderboard">
      <thead>
        <tr>
          <th scope="col">#</th>
          <th scope="col">Student</th>
          {!scoresHidden && <th scope="col">{challenge.primary_metric.label}</th>}
          {!scoresHidden && secondary.map((m) => <th scope="col" key={m.key}>{m.label}</th>)}
          <th scope="col">Subs</th>
          <th scope="col">Latest</th>
        </tr>
      </thead>
      <tbody>
        {rows.map((p) => (
          <tr
            key={p.id}
            className={p.id === selectedId ? 'selected' : ''}
            onClick={() => onSelect(p.id === selectedId ? null : p.id)}
            tabIndex={0}
            onKeyDown={(e) => e.key === 'Enter' && onSelect(p.id)}
          >
            <td>{scoresHidden ? '' : (p.rank ?? '–')}</td>
            <td>{p.display_name}</td>
            {!scoresHidden && <td className="mono">{p.best_score === null ? '–' : formatValue(p.best_score, challenge.primary_metric.format)}</td>}
            {!scoresHidden && secondary.map((m) => <td className="mono" key={m.key}>{p.best_metrics ? formatValue(p.best_metrics[m.key], m.format) : '–'}</td>)}
            <td className="mono">{p.n_submissions}</td>
            <td className="muted">{p.latest_status ?? '–'} {p.latest_at ? formatTime(p.latest_at) : ''}</td>
          </tr>
        ))}
        {rows.length === 0 && (
          <tr>
            <td colSpan={6} className="muted">Nobody has joined yet.</td>
          </tr>
        )}
      </tbody>
    </table>
  );
}
