import { useCallback, useEffect, useState } from 'react';
import { Link } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import type { ChallengeSummary, SessionTeacherView, SubmissionPublic } from '../api/types';
import { StatusBadge } from '../components/StatusBadge';
import { TopBar } from '../components/TopBar';
import { formatTime } from '../lib/format';
import { loadTeacherSecret, saveTeacherSecret } from '../lib/storage';

export function Teacher() {
  const [secret, setSecret] = useState(loadTeacherSecret());
  const [verified, setVerified] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [challenges, setChallenges] = useState<ChallengeSummary[]>([]);
  const [sessions, setSessions] = useState<SessionTeacherView[]>([]);
  const [newChallenge, setNewChallenge] = useState('');
  const [newName, setNewName] = useState('');
  const [newCode, setNewCode] = useState('');
  const [failures, setFailures] = useState<Record<string, SubmissionPublic[]>>({});

  const load = useCallback(async () => {
    const [c, s] = await Promise.all([api.challenges(), api.teacher.sessions(secret)]);
    setChallenges(c);
    setSessions(s);
    if (!newChallenge && c.length) setNewChallenge(c[0].id);
  }, [secret, newChallenge]);

  useEffect(() => {
    if (!secret) return;
    api.teacher
      .verify(secret)
      .then(() => {
        setVerified(true);
        saveTeacherSecret(secret);
        setError(null);
        return load();
      })
      .catch((e) => {
        setVerified(false);
        setError(e instanceof ApiError && e.status === 401 ? 'Wrong teacher secret.' : e.message);
      });
  }, [secret, load]);

  useEffect(() => {
    if (!verified) return;
    const id = setInterval(() => load().catch(() => undefined), 5000);
    return () => clearInterval(id);
  }, [verified, load]);

  const run = async (fn: () => Promise<unknown>) => {
    try {
      await fn();
      await load();
      setError(null);
    } catch (e) {
      setError(e instanceof Error ? e.message : 'Request failed');
    }
  };

  if (!verified) {
    return (
      <div className="page narrow">
        <TopBar title="Teacher" />
        <main>
          <h1>Teacher sign-in</h1>
          <form
            className="join-form"
            onSubmit={(e) => {
              e.preventDefault();
              setSecret((e.currentTarget.elements.namedItem('secret') as HTMLInputElement).value);
            }}
          >
            <label>
              Teacher secret (TEACHER_SECRET in .env)
              <input name="secret" type="password" defaultValue={secret} autoComplete="current-password" />
            </label>
            <button className="primary" type="submit">
              Sign in
            </button>
            {error && <p className="error">{error}</p>}
          </form>
        </main>
      </div>
    );
  }

  return (
    <div className="page teacher">
      <TopBar title="Teacher">
        <button
          className="linklike"
          onClick={() => {
            saveTeacherSecret(null);
            setSecret('');
            setVerified(false);
          }}
        >
          Sign out
        </button>
      </TopBar>
      <main>
        {error && <p className="error" role="alert">{error}</p>}
        <section>
          <h2>New session</h2>
          <form
            className="inline-form"
            onSubmit={(e) => {
              e.preventDefault();
              run(() => api.teacher.create(secret, newChallenge, newName, newCode.trim() || undefined)).then(() => {
                setNewName('');
                setNewCode('');
              });
            }}
          >
            <label>
              Challenge
              <select value={newChallenge} onChange={(e) => setNewChallenge(e.target.value)}>
                {challenges.map((c) => (
                  <option key={c.id} value={c.id}>
                    {c.title}
                  </option>
                ))}
              </select>
            </label>
            <label>
              Session name
              <input value={newName} onChange={(e) => setNewName(e.target.value)} placeholder="e.g. DNNLS week 3, group A" />
            </label>
            <label>
              Join code (optional)
              <input value={newCode} onChange={(e) => setNewCode(e.target.value.toUpperCase())} placeholder="auto" maxLength={12} />
            </label>
            <button className="primary" type="submit" disabled={!newChallenge}>
              Create
            </button>
          </form>
          <p className="muted small">
            Available challenges: {challenges.map((c) => `${c.title} (${c.submission_type} → ${c.evaluator} → ${c.visualization})`).join('; ')}
          </p>
        </section>

        <section>
          <h2>Sessions</h2>
          {sessions.length === 0 && <p className="muted">No sessions yet.</p>}
          <ul className="session-list">
            {sessions.map((s) => (
              <li key={s.id} className="session-card">
                <div className="session-head">
                  <div>
                    <strong>{s.name}</strong> <span className="muted">· {s.challenge_title}</span>
                    <div className="muted small">
                      created {s.created_at ? new Date(s.created_at).toLocaleString() : ''} · {s.n_participants} participants · {s.n_submissions} submissions
                    </div>
                  </div>
                  <div className="join-code big">{s.join_code}</div>
                </div>
                <div className="session-actions">
                  <Link className="button" to={`/live/${s.id}`} target="_blank" rel="noreferrer">
                    Open projector view ↗
                  </Link>
                  <Link className="button" to={`/join/${s.join_code}`} target="_blank" rel="noreferrer">
                    Student join link ↗
                  </Link>
                  <button onClick={() => run(() => api.teacher.update(secret, s.id, { accepting_submissions: !s.accepting_submissions }))}>
                    {s.accepting_submissions ? 'Stop accepting submissions' : 'Start accepting submissions'}
                  </button>
                  <button onClick={() => run(() => api.teacher.update(secret, s.id, { scores_hidden: !s.scores_hidden }))}>
                    {s.scores_hidden ? 'Show scores' : 'Hide scores'}
                  </button>
                  {(challenges.find((c) => c.id === s.challenge_id)?.submission_types ?? []).map((t) => {
                    const on = s.enabled_submission_types.includes(t.id);
                    const next = on ? s.enabled_submission_types.filter((x) => x !== t.id) : [...s.enabled_submission_types, t.id];
                    return (
                      <button
                        key={t.id}
                        className={on ? 'toggle-on' : 'toggle-off'}
                        aria-pressed={on}
                        title={`${t.label}: ${t.accepted_extensions.join(', ')}. ${next.length === 0 ? 'At least one type must stay enabled.' : ''}`}
                        disabled={next.length === 0}
                        onClick={() => run(() => api.teacher.update(secret, s.id, { enabled_submission_types: next }))}
                      >
                        {t.label.replace(' (ZIP)', '')}: {on ? 'on' : 'off'}
                      </button>
                    );
                  })}
                  <button
                    onClick={() =>
                      run(async () => {
                        const f = await api.teacher.failures(secret, s.id);
                        setFailures((m) => ({ ...m, [s.id]: f }));
                      })
                    }
                  >
                    Show failures
                  </button>
                  <button
                    className="danger"
                    onClick={() => window.confirm(`Reset "${s.name}"? All participants and submissions are removed; the join code stays.`) && run(() => api.teacher.reset(secret, s.id))}
                  >
                    Reset
                  </button>
                  <button
                    className="danger"
                    onClick={() => window.confirm(`Delete "${s.name}" permanently?`) && run(() => api.teacher.delete(secret, s.id))}
                  >
                    Delete
                  </button>
                </div>
                <div className="muted small">
                  {s.accepting_submissions ? 'accepting submissions' : 'submissions paused'} · scores {s.scores_hidden ? 'hidden' : 'visible'} · enabled types:{' '}
                  {s.enabled_submission_types.join(', ')}
                </div>
                {failures[s.id] && (
                  <div className="failures">
                    <h3>Failed submissions ({failures[s.id].length})</h3>
                    {failures[s.id].length === 0 && <p className="muted small">None.</p>}
                    {failures[s.id].map((f) => (
                      <details key={f.id}>
                        <summary>
                          <StatusBadge status={f.status} /> {formatTime(f.created_at)} · {f.original_filename} · {f.error_message}
                        </summary>
                        <ul>
                          {f.error_details.map((d, i) => (
                            <li key={i}>
                              <code>{d}</code>
                            </li>
                          ))}
                        </ul>
                      </details>
                    ))}
                  </div>
                )}
              </li>
            ))}
          </ul>
        </section>
        <p className="muted small">
          API documentation: <a href="/api/docs">/api/docs</a>
        </p>
      </main>
    </div>
  );
}
