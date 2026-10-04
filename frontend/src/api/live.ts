/**
 * useLiveSession: snapshot + Server-Sent Events, kept generic for every challenge.
 *
 * The hook knows nothing about how scores are displayed; it just maintains the list of
 * participants and remembers which of them changed recently (for subtle highlights).
 */
import { useCallback, useEffect, useReducer, useRef, useState } from 'react';
import { api, ApiError } from './client';
import type { ChallengeSummary, LiveSnapshot, ParticipantLive, SessionEvent, SessionPublic, SubmissionPublic } from './types';

export type ConnectionStatus = 'connecting' | 'live' | 'reconnecting' | 'error' | 'closed';

export interface RecentUpdate {
  at: number; // Date.now()
  improved: boolean;
  status: SubmissionPublic['status'];
}

export interface LiveState {
  session: SessionPublic | null;
  challenge: ChallengeSummary | null;
  participants: ParticipantLive[];
  lastEventId: number;
  deleted: boolean;
  lastSubmission: SubmissionPublic | null;
}

type Action =
  | { type: 'snapshot'; snapshot: LiveSnapshot }
  | { type: 'event'; event: SessionEvent; id: number };

export function rankParticipants(parts: ParticipantLive[], higherIsBetter: boolean): ParticipantLive[] {
  const scored = parts.filter((p) => p.best_score !== null);
  scored.sort((a, b) => {
    const d = higherIsBetter ? b.best_score! - a.best_score! : a.best_score! - b.best_score!;
    return d !== 0 ? d : (a.best_at ?? '').localeCompare(b.best_at ?? '');
  });
  const rank = new Map(scored.map((p, i) => [p.id, i + 1]));
  return parts.map((p) => ({ ...p, rank: rank.get(p.id) ?? null }));
}

function reducer(state: LiveState, action: Action): LiveState {
  switch (action.type) {
    case 'snapshot': {
      const { session, challenge, participants, last_event_id } = action.snapshot;
      return {
        ...state,
        session,
        challenge,
        participants: rankParticipants(participants, challenge.primary_metric.higher_is_better),
        lastEventId: last_event_id,
        deleted: false,
      };
    }
    case 'event': {
      const ev = action.event;
      const hib = state.challenge?.primary_metric.higher_is_better ?? true;
      const next = { ...state, lastEventId: Math.max(state.lastEventId, action.id) };
      switch (ev.type) {
        case 'participant_joined': {
          const p = ev.payload.participant;
          if (state.participants.some((x) => x.id === p.id)) return next;
          return { ...next, participants: rankParticipants([...state.participants, p], hib) };
        }
        case 'submission_updated': {
          const p = ev.payload.participant;
          const exists = state.participants.some((x) => x.id === p.id);
          const parts = exists ? state.participants.map((x) => (x.id === p.id ? p : x)) : [...state.participants, p];
          return { ...next, participants: rankParticipants(parts, hib), lastSubmission: ev.payload.submission };
        }
        case 'session_updated':
          return { ...next, session: ev.payload.session };
        case 'session_deleted':
          return { ...next, deleted: true };
        default:
          return next;
      }
    }
  }
}

const EVENT_TYPES: SessionEvent['type'][] = ['participant_joined', 'submission_updated', 'session_updated', 'session_reset', 'session_deleted'];

export function useLiveSession(sessionId: string | null) {
  const [state, dispatch] = useReducer(reducer, {
    session: null,
    challenge: null,
    participants: [],
    lastEventId: 0,
    deleted: false,
    lastSubmission: null,
  });
  const [status, setStatus] = useState<ConnectionStatus>('connecting');
  const [error, setError] = useState<string | null>(null);
  const [recent, setRecent] = useState<Record<string, RecentUpdate>>({});
  const lastIdRef = useRef(0);
  const [generation, setGeneration] = useState(0);

  const refresh = useCallback(() => setGeneration((g) => g + 1), []);

  useEffect(() => {
    if (!sessionId) return;
    let es: EventSource | null = null;
    let cancelled = false;

    (async () => {
      try {
        const snap = await api.live(sessionId);
        if (cancelled) return;
        dispatch({ type: 'snapshot', snapshot: snap });
        lastIdRef.current = snap.last_event_id;
        setError(null);
      } catch (e) {
        if (cancelled) return;
        setError(e instanceof ApiError ? e.message : 'Failed to load session');
        setStatus('error');
        return;
      }
      es = new EventSource(`/api/sessions/${sessionId}/events?after=${lastIdRef.current}`);
      es.onopen = () => setStatus('live');
      es.onerror = () => setStatus((s) => (s === 'closed' ? s : 'reconnecting'));
      for (const type of EVENT_TYPES) {
        es.addEventListener(type, (raw) => {
          const msg = raw as MessageEvent<string>;
          const id = Number(msg.lastEventId) || 0;
          if (id && id <= lastIdRef.current) return; // duplicate after reconnect
          if (id) lastIdRef.current = id;
          let payload: unknown = {};
          try {
            payload = JSON.parse(msg.data);
          } catch {
            return;
          }
          const event = { type, payload } as SessionEvent;
          if (event.type === 'session_reset') {
            refresh();
            return;
          }
          if (event.type === 'submission_updated') {
            const { participant, submission } = event.payload;
            setRecent((r) => ({ ...r, [participant.id]: { at: Date.now(), improved: !!participant.improved, status: submission.status } }));
          }
          dispatch({ type: 'event', event, id });
          if (event.type === 'session_deleted') {
            es?.close();
            setStatus('closed');
          }
        });
      }
    })();

    return () => {
      cancelled = true;
      es?.close();
    };
  }, [sessionId, generation, refresh]);

  return { state, status, error, recent, refresh };
}
