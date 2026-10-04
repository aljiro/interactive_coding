import type { ChallengeSummary, ParticipantLive, SubmissionPublic } from '../api/types';
import { formatTime } from '../lib/format';
import { MetricList } from './MetricList';
import { StatusBadge } from './StatusBadge';

interface Props {
  challenge: ChallengeSummary;
  participant: ParticipantLive | null;
  submission: SubmissionPublic | null;
  history: SubmissionPublic[];
  onPick: (submissionId: string) => void;
  scoresHidden: boolean;
  loading: boolean;
}

/** Generic detail panel: who is selected, which submission, metrics, picker for history. */
export function SubmissionDetail({ challenge, participant, submission, history, onPick, scoresHidden, loading }: Props) {
  if (!participant) {
    return (
      <div className="detail-panel empty">
        <p className="muted">Click a student to see their submission. Clicking selects their best submission; newer ones can be picked below.</p>
      </div>
    );
  }
  const succeeded = history.filter((s) => s.status === 'succeeded');
  return (
    <div className="detail-panel" aria-live="polite">
      <div className="detail-head">
        <h3>
          {participant.display_name}
          {participant.rank && !scoresHidden && <span className="muted"> · rank {participant.rank}</span>}
        </h3>
        <span className="muted small">
          {participant.n_submissions} submission{participant.n_submissions === 1 ? '' : 's'}
          {participant.latest_status && participant.latest_status !== 'succeeded' && (
            <>
              {' '}· latest <StatusBadge status={participant.latest_status} />
            </>
          )}
        </span>
      </div>
      {submission ? (
        <>
          <MetricList challenge={challenge} primaryScore={submission.primary_score} metrics={submission.metrics} hidden={scoresHidden} compact />
          <p className="muted small">
            Submission #{submission.seq_no} · {submission.submission_type.replace('_', ' ')} · {formatTime(submission.finished_at ?? submission.created_at)}
            {submission.id === participant.best_submission_id ? ' · best' : ''}
          </p>
        </>
      ) : (
        <p className="muted">{loading ? 'Loading…' : 'No evaluated submission yet.'}</p>
      )}
      {succeeded.length > 1 && (
        <label className="small picker">
          Show submission{' '}
          <select value={submission?.id ?? ''} onChange={(e) => onPick(e.target.value)}>
            {succeeded.map((s) => (
              <option key={s.id} value={s.id}>
                #{s.seq_no} · {formatTime(s.finished_at)}
                {scoresHidden || s.primary_score === null ? '' : ` · ${s.primary_score.toFixed(3)}`}
                {s.id === participant.best_submission_id ? ' (best)' : ''}
              </option>
            ))}
          </select>
        </label>
      )}
    </div>
  );
}
