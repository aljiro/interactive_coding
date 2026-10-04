import { useCallback, useEffect, useMemo, useState } from 'react';
import { Link, useNavigate } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { useLiveSession } from '../api/live';
import type { ChallengeDetail, DisplayOut, MeResponse, SubmissionDisplayOut } from '../api/types';
import { getVisualization } from '../challenge-visualizations';
import { Markdown } from '../components/Markdown';
import { MetricList } from '../components/MetricList';
import { StatusBadge } from '../components/StatusBadge';
import { TopBar } from '../components/TopBar';
import { UploadControl } from '../components/UploadControl';
import { formatTime, formatValue } from '../lib/format';
import { loadParticipant, saveParticipant } from '../lib/storage';

export function Student() {
  const navigate = useNavigate();
  const stored = useMemo(() => loadParticipant(), []);
  const [me, setMe] = useState<MeResponse | null>(null);
  const [challenge, setChallenge] = useState<ChallengeDetail | null>(null);
  const [display, setDisplay] = useState<DisplayOut | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [latestDisplay, setLatestDisplay] = useState<SubmissionDisplayOut | null>(null);
  const live = useLiveSession(stored?.session_id ?? null);

  const refreshMe = useCallback(async () => {
    if (!stored) return;
    try {
      const m = await api.me(stored.token);
      setMe(m);
      setError(null);
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        saveParticipant(null);
        navigate('/');
        return;
      }
      setError(err instanceof Error ? err.message : 'Failed to load');
    }
  }, [stored, navigate]);

  useEffect(() => {
    if (!stored) {
      navigate('/');
      return;
    }
    refreshMe();
  }, [stored, navigate, refreshMe]);

  useEffect(() => {
    if (!me) return;
    if (!challenge || challenge.id !== me.challenge.id) {
      api.challenge(me.challenge.id).then(setChallenge).catch(() => undefined);
      api.challengeDisplay(me.challenge.id).then(setDisplay).catch(() => undefined);
    }
  }, [me, challenge]);

  // React to our own submission updates and session changes (via SSE).
  const myUpdate = stored ? live.recent[stored.participant_id] : undefined;
  useEffect(() => {
    if (myUpdate) refreshMe();
  }, [myUpdate?.at, myUpdate?.status, refreshMe]); // eslint-disable-line react-hooks/exhaustive-deps
  useEffect(() => {
    if (live.state.session) setMe((m) => (m ? { ...m, session: live.state.session! } : m));
  }, [live.state.session]);
  useEffect(() => {
    if (live.state.deleted) {
      saveParticipant(null);
      navigate('/');
    }
  }, [live.state.deleted, navigate]);

  const latest = me?.submissions[0] ?? null;
  const latestSucceeded = me?.submissions.find((s) => s.status === 'succeeded') ?? null;
  useEffect(() => {
    if (!latestSucceeded) {
      setLatestDisplay(null);
      return;
    }
    api.submissionDisplay(latestSucceeded.id).then(setLatestDisplay).catch(() => setLatestDisplay(null));
  }, [latestSucceeded?.id]); // eslint-disable-line react-hooks/exhaustive-deps

  if (!stored) return null;
  if (!me) {
    return (
      <div className="page">
        <TopBar />
        <main>{error ? <p className="error">{error}</p> : <p className="muted">Loading…</p>}</main>
      </div>
    );
  }

  const { session, participant } = me;
  const plugin = getVisualization(me.challenge.visualization);
  const pending = latest && ['uploaded', 'queued', 'running'].includes(latest.status);
  const enabledTypes = (challenge?.submission_types ?? []).filter((t) => session.enabled_submission_types.includes(t.id));
  const disabledTypes = (challenge?.submission_types ?? []).filter((t) => !session.enabled_submission_types.includes(t.id));
  const leave = () => {
    saveParticipant(null);
    navigate('/');
  };

  return (
    <div className="page student">
      <TopBar title={session.name}>
        <span className="muted small">
          {participant.display_name} · code {session.join_code}
        </span>
        <button className="linklike" onClick={leave}>
          Leave
        </button>
      </TopBar>
      <main className="student-grid">
        <section className="student-side">
          <h2>Your progress</h2>
          <dl className="stats">
            <div>
              <dt>Best {me.challenge.primary_metric.label}</dt>
              <dd>{me.scores_hidden ? 'hidden' : formatValue(participant.best_score, me.challenge.primary_metric.format)}</dd>
            </div>
            <div>
              <dt>Position</dt>
              <dd>{me.scores_hidden ? 'hidden' : participant.rank ? `#${participant.rank}` : '–'}</dd>
            </div>
            <div>
              <dt>Submissions</dt>
              <dd>{participant.n_submissions}</dd>
            </div>
          </dl>

          <h2>Submit</h2>
          {challenge && (
            <UploadControl
              submissionTypes={enabledTypes}
              disabled={!session.accepting_submissions || !!pending || enabledTypes.length === 0}
              disabledReason={
                !session.accepting_submissions
                  ? 'The teacher has paused submissions.'
                  : enabledTypes.length === 0
                    ? 'No submission type is currently enabled.'
                    : pending
                      ? 'Your previous submission is still being evaluated.'
                      : undefined
              }
              onUpload={async (file) => {
                await api.upload(session.id, stored.token, file);
                await refreshMe();
              }}
            />
          )}
          {disabledTypes.length > 0 && (
            <p className="muted small">Currently disabled by the teacher: {disabledTypes.map((t) => t.label).join(', ')}.</p>
          )}

          <h2>Latest submission</h2>
          {latest ? (
            <div className={`latest status-${latest.status}`}>
              <p>
                #{latest.seq_no} · {latest.original_filename} · {formatTime(latest.created_at)} <StatusBadge status={latest.status} />
              </p>
              {pending && <p className="muted">Evaluating… this page updates automatically.</p>}
              {latest.status === 'succeeded' && (
                <MetricList challenge={me.challenge} primaryScore={latest.primary_score} metrics={latest.metrics} hidden={me.scores_hidden} compact />
              )}
              {(latest.status === 'failed' || latest.status === 'timed_out') && (
                <div className="error-box" role="alert">
                  <p>
                    <strong>{latest.error_message}</strong>
                  </p>
                  {latest.error_details.length > 0 && (
                    <ul>
                      {latest.error_details.map((d, i) => (
                        <li key={i}>
                          <code>{d}</code>
                        </li>
                      ))}
                    </ul>
                  )}
                </div>
              )}
            </div>
          ) : (
            <p className="muted">No submissions yet.</p>
          )}
          {plugin.SubmissionPreview && display && latestDisplay && latestSucceeded && (
            <div className="preview">
              <p className="muted small">Your latest evaluated submission (#{latestSucceeded.seq_no})</p>
              <plugin.SubmissionPreview challenge={me.challenge} sessionDisplay={display} display={latestDisplay} />
            </div>
          )}

          {me.submissions.length > 1 && (
            <>
              <h2>History</h2>
              <table className="history">
                <thead>
                  <tr>
                    <th>#</th>
                    <th>Time</th>
                    <th>Status</th>
                    {!me.scores_hidden && <th>{me.challenge.primary_metric.label}</th>}
                  </tr>
                </thead>
                <tbody>
                  {me.submissions.map((s) => (
                    <tr key={s.id}>
                      <td>{s.seq_no}</td>
                      <td>{formatTime(s.created_at)}</td>
                      <td>
                        <StatusBadge status={s.status} />
                      </td>
                      {!me.scores_hidden && <td className="mono">{s.primary_score === null ? '–' : formatValue(s.primary_score, me.challenge.primary_metric.format)}</td>}
                    </tr>
                  ))}
                </tbody>
              </table>
            </>
          )}
        </section>

        <section className="student-main">
          <h1>{me.challenge.title}</h1>
          {challenge ? (
            <>
              <h2>Resources</h2>
              <ul className="resources">
                {challenge.resources
                  .filter((r) => !r.submission_types || r.submission_types.some((t) => session.enabled_submission_types.includes(t)))
                  .map((r) => (
                    <li key={r.name}>
                      <a href={api.resourceUrl(challenge.id, r.name)} download>
                        {r.name}
                      </a>{' '}
                      <span className="muted">— {r.description}</span>
                    </li>
                  ))}
                <li>
                  <a href="/examples/moons_colab.ipynb" download>
                    Starter Colab notebook
                  </a>{' '}
                  <span className="muted">— open in Google Colab (File → Upload notebook)</span>
                </li>
              </ul>
              <Markdown source={challenge.instructions_md} />
              {enabledTypes.length > 0 && (
                <h2>
                  How to submit
                  {enabledTypes.length === 1 ? ` (${enabledTypes[0].label.toLowerCase()} only)` : ''}
                </h2>
              )}
              {enabledTypes.map((t) =>
                challenge.submission_instructions_md[t.id] ? (
                  <Markdown key={t.id} source={challenge.submission_instructions_md[t.id]} />
                ) : null,
              )}
            </>
          ) : (
            <p className="muted">Loading instructions…</p>
          )}
          <p className="muted small">
            <Link to={`/live/${session.id}`}>Open the live view</Link>
          </p>
        </section>
      </main>
    </div>
  );
}
