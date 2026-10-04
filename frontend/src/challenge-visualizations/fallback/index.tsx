/**
 * Generic fallback used when no plugin is registered for a challenge's visualization id.
 * Shows participants ordered by rank with their primary score - deliberately plain.
 */
import type { ArenaProps, VisualizationPlugin } from '../types';
import { formatValue } from '../../lib/format';

function Arena({ participants, challenge, selectedParticipantId, onSelectParticipant, scoresHidden, detailPanel, selected }: ArenaProps) {
  const ranked = [...participants].sort((a, b) => (a.rank ?? 1e9) - (b.rank ?? 1e9));
  return (
    <div className="arena fallback">
      <section className="fallback-list">
        <h2>{challenge.title}</h2>
        <p className="muted">
          No visualization plugin is registered for <code>{challenge.visualization}</code>. Showing scores only.
        </p>
        <ol>
          {ranked.map((p) => (
            <li key={p.id}>
              <button className={`linklike${p.id === selectedParticipantId ? ' selected' : ''}`} onClick={() => onSelectParticipant(p.id)}>
                {p.display_name}
              </button>{' '}
              {!scoresHidden && p.best_score !== null && <span className="mono">{formatValue(p.best_score, challenge.primary_metric.format)}</span>}
            </li>
          ))}
        </ol>
        {selected.display && <pre className="json">{JSON.stringify(selected.display.data, null, 2)}</pre>}
      </section>
      <section>{detailPanel}</section>
    </div>
  );
}

export const fallbackVisualization: VisualizationPlugin = { id: '__fallback__', Arena };
