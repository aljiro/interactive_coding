import { STATUS_LABEL } from '../lib/format';
import type { SubmissionStatus } from '../api/types';

export function StatusBadge({ status }: { status: SubmissionStatus | string | null }) {
  if (!status) return null;
  return <span className={`badge status-${status}`}>{STATUS_LABEL[status] ?? status}</span>;
}

export function LiveBadge({ status }: { status: string }) {
  const label = status === 'live' ? 'live' : status === 'reconnecting' ? 'reconnecting…' : status === 'connecting' ? 'connecting…' : status;
  return (
    <span className={`badge live-${status}`} role="status" aria-live="polite">
      <span className="dot" /> {label}
    </span>
  );
}
