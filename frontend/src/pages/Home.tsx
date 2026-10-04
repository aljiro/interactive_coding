import { useEffect, useState } from 'react';
import { Link, useNavigate, useParams, useSearchParams } from 'react-router-dom';
import { api, ApiError } from '../api/client';
import { TopBar } from '../components/TopBar';
import { loadParticipant, saveParticipant } from '../lib/storage';

export function Home() {
  const navigate = useNavigate();
  const params = useParams();
  const [search] = useSearchParams();
  const [code, setCode] = useState((params.code ?? search.get('code') ?? '').toUpperCase());
  const [name, setName] = useState('');
  const [error, setError] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const existing = loadParticipant();
  const [sessionName, setSessionName] = useState<string | null>(null);

  useEffect(() => {
    if (code.length < 4) {
      setSessionName(null);
      return;
    }
    let cancelled = false;
    api
      .sessionByCode(code)
      .then((s) => !cancelled && setSessionName(`${s.name} — ${s.challenge_title}`))
      .catch(() => !cancelled && setSessionName(null));
    return () => {
      cancelled = true;
    };
  }, [code]);

  const join = async (e: React.FormEvent) => {
    e.preventDefault();
    setBusy(true);
    setError(null);
    try {
      const res = await api.join(code.trim(), name.trim());
      saveParticipant({ token: res.token, participant_id: res.participant.id, session_id: res.session.id, display_name: res.participant.display_name });
      navigate('/student');
    } catch (err) {
      setError(err instanceof ApiError ? err.message : 'Could not join');
    } finally {
      setBusy(false);
    }
  };

  return (
    <div className="page narrow">
      <TopBar>
        <Link to="/teacher">Teacher</Link>
      </TopBar>
      <main>
        <h1>Join a session</h1>
        <p className="muted">Train in Colab, then submit your artifact here. Your teacher shows the join code on the projector.</p>
        {existing && (
          <p className="notice">
            You are already joined as <strong>{existing.display_name}</strong>. <Link to="/student">Continue to your session</Link> or join again below.
          </p>
        )}
        <form className="join-form" onSubmit={join}>
          <label>
            Join code
            <input value={code} onChange={(e) => setCode(e.target.value.toUpperCase())} autoCapitalize="characters" autoComplete="off" required minLength={4} maxLength={12} placeholder="e.g. DEMO" />
          </label>
          {sessionName && <p className="small muted">Session: {sessionName}</p>}
          <label>
            Display name
            <input value={name} onChange={(e) => setName(e.target.value)} required maxLength={60} placeholder="Shown on the projector" />
          </label>
          <button className="primary" type="submit" disabled={busy || code.length < 4 || !name.trim()}>
            {busy ? 'Joining…' : 'Join'}
          </button>
          {error && <p className="error" role="alert">{error}</p>}
        </form>
      </main>
    </div>
  );
}
