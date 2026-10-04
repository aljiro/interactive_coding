import { useCallback, useEffect, useMemo, useState } from 'react';
import { useParams } from 'react-router-dom';
import { api } from '../api/client';
import { useLiveSession } from '../api/live';
import type { DisplayOut, SubmissionDisplayOut, SubmissionPublic } from '../api/types';
import { getVisualization } from '../challenge-visualizations';
import { Leaderboard } from '../components/Leaderboard';
import { LiveBadge } from '../components/StatusBadge';
import { SubmissionDetail } from '../components/SubmissionDetail';
import { useReducedMotion } from '../lib/hooks';

/**
 * Projector / teacher live view. Generic: loads the snapshot + SSE stream, manages selection,
 * and delegates all drawing to the challenge's visualization plugin.
 *
 * Selection rule: clicking a student selects their *best* submission; when "follow latest" is
 * on, a newly evaluated submission selects that student and that submission.
 */
export function Projector() {
  const { sessionId = '' } = useParams();
  const { state, status, error, recent } = useLiveSession(sessionId);
  const reducedMotion = useReducedMotion();
  const [display, setDisplay] = useState<DisplayOut | null>(null);
  const [selectedId, setSelectedId] = useState<string | null>(null);
  const [submission, setSubmission] = useState<SubmissionPublic | null>(null);
  const [subDisplay, setSubDisplay] = useState<SubmissionDisplayOut | null>(null);
  const [history, setHistory] = useState<SubmissionPublic[]>([]);
  const [loading, setLoading] = useState(false);
  const [followLatest, setFollowLatest] = useState(true);
  const [showTable, setShowTable] = useState(false);

  const challengeId = state.challenge?.id;
  useEffect(() => {
    if (challengeId) api.challengeDisplay(challengeId).then(setDisplay).catch(() => setDisplay(null));
  }, [challengeId]);

  const loadSubmission = useCallback(async (submissionId: string | null) => {
    if (!submissionId) {
      setSubmission(null);
      setSubDisplay(null);
      return;
    }
    setLoading(true);
    try {
      const [s, d] = await Promise.all([api.submission(submissionId), api.submissionDisplay(submissionId).catch(() => null)]);
      setSubmission(s);
      setSubDisplay(d);
    } finally {
      setLoading(false);
    }
  }, []);

  const participants = state.participants;
  const selected = useMemo(() => participants.find((p) => p.id === selectedId) ?? null, [participants, selectedId]);

  const selectParticipant = useCallback(
    (id: string | null, submissionId?: string | null) => {
      setSelectedId(id);
      const p = participants.find((x) => x.id === id);
      const target = submissionId ?? p?.best_submission_id ?? null;
      loadSubmission(target);
      if (id) api.participantSubmissions(sessionId, id).then(setHistory).catch(() => setHistory([]));
      else setHistory([]);
    },
    [participants, loadSubmission, sessionId],
  );

  // Follow the most recent successful evaluation.
  const last = state.lastSubmission;
  useEffect(() => {
    if (!last || last.status !== 'succeeded') return;
    if (followLatest || last.participant_id === selectedId) {
      setSelectedId(last.participant_id);
      loadSubmission(last.id);
      api.participantSubmissions(sessionId, last.participant_id).then(setHistory).catch(() => undefined);
    }
  }, [last?.id, last?.status]); // eslint-disable-line react-hooks/exhaustive-deps

  // Selected participant vanished (reset) -> clear selection.
  useEffect(() => {
    if (selectedId && !participants.some((p) => p.id === selectedId)) selectParticipant(null);
  }, [participants, selectedId, selectParticipant]);

  if (error) {
    return (
      <div className="page projector">
        <main className="centered">
          <p className="error">{error}</p>
        </main>
      </div>
    );
  }
  if (!state.session || !state.challenge) {
    return (
      <div className="page projector">
        <main className="centered">
          <p className="muted">Connecting…</p>
        </main>
      </div>
    );
  }
  if (state.deleted) {
    return (
      <div className="page projector">
        <main className="centered">
          <p className="muted">This session has been deleted.</p>
        </main>
      </div>
    );
  }

  const { session, challenge } = state;
  const plugin = getVisualization(challenge.visualization);
  const scoresHidden = session.scores_hidden;
  const joinUrl = `${window.location.host}`;

  const detailPanel = (
    <SubmissionDetail
      challenge={challenge}
      participant={selected}
      submission={submission}
      history={history}
      onPick={(id) => loadSubmission(id)}
      scoresHidden={scoresHidden}
      loading={loading}
    />
  );

  return (
    <div className="page projector">
      <header className="projector-bar">
        <div className="projector-title">
          <h1>{session.name}</h1>
          <span className="muted">{challenge.title}</span>
        </div>
        <div className="join-hint" aria-label="How to join">
          <span className="muted small">join at</span> <span className="mono">{joinUrl}</span>
          <span className="muted small">code</span> <span className="join-code">{session.join_code}</span>
        </div>
        <div className="projector-status">
          {!session.accepting_submissions && <span className="badge paused">submissions paused</span>}
          {scoresHidden && <span className="badge">scores hidden</span>}
          <span className="muted small">{participants.length} joined</span>
          <LiveBadge status={status} />
          <label className="small toggle">
            <input type="checkbox" checked={followLatest} onChange={(e) => setFollowLatest(e.target.checked)} /> follow latest
          </label>
          <button className="linklike small" onClick={() => setShowTable((v) => !v)} aria-expanded={showTable}>
            {showTable ? 'hide table' : 'table'}
          </button>
        </div>
      </header>
      <main className="projector-main">
        <plugin.Arena
          session={session}
          challenge={challenge}
          participants={participants}
          sessionDisplay={display}
          selectedParticipantId={selectedId}
          selected={{ submission, display: subDisplay, loading }}
          onSelectParticipant={(id) => selectParticipant(id)}
          recent={recent}
          scoresHidden={scoresHidden}
          reducedMotion={reducedMotion}
          detailPanel={detailPanel}
        />
        {showTable && (
          <aside className="table-drawer" aria-label="Leaderboard">
            <Leaderboard participants={participants} challenge={challenge} selectedId={selectedId} onSelect={(id) => selectParticipant(id)} scoresHidden={scoresHidden} />
          </aside>
        )}
      </main>
    </div>
  );
}
