import type {
  ChallengeDetail,
  ChallengeSummary,
  DisplayOut,
  JoinResponse,
  LiveSnapshot,
  MeResponse,
  SessionPublic,
  SessionTeacherView,
  SubmissionDisplayOut,
  SubmissionPublic,
} from './types';

export class ApiError extends Error {
  status: number;
  constructor(status: number, detail: string) {
    super(detail);
    this.status = status;
  }
}

async function request<T>(path: string, init: RequestInit = {}): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`/api${path}`, init);
  } catch {
    throw new ApiError(0, 'Cannot reach the server.');
  }
  if (!res.ok) {
    let detail = res.statusText || `HTTP ${res.status}`;
    try {
      const body = await res.json();
      if (typeof body.detail === 'string') detail = body.detail;
      else if (Array.isArray(body.detail)) detail = body.detail.map((d: { msg: string }) => d.msg).join('; ');
    } catch {
      /* non-JSON body */
    }
    throw new ApiError(res.status, detail);
  }
  return (await res.json()) as T;
}

const json = (method: string, body?: unknown, headers: Record<string, string> = {}): RequestInit => ({
  method,
  headers: { 'Content-Type': 'application/json', ...headers },
  body: body === undefined ? undefined : JSON.stringify(body),
});

const participantHeaders = (token: string) => ({ 'X-Participant-Token': token });
const teacherHeaders = (secret: string) => ({ 'X-Teacher-Secret': secret });

export const api = {
  challenges: () => request<ChallengeSummary[]>('/challenges'),
  challenge: (id: string) => request<ChallengeDetail>(`/challenges/${id}`),
  challengeDisplay: (id: string) => request<DisplayOut>(`/challenges/${id}/display`),
  resourceUrl: (challengeId: string, name: string) => `/api/challenges/${challengeId}/resources/${name}`,

  sessionByCode: (code: string) => request<SessionPublic>(`/sessions/by-code/${encodeURIComponent(code)}`),
  session: (id: string) => request<SessionPublic>(`/sessions/${id}`),
  live: (id: string) => request<LiveSnapshot>(`/sessions/${id}/live`),
  join: (join_code: string, display_name: string, student_identifier?: string) =>
    request<JoinResponse>('/sessions/join', json('POST', { join_code, display_name, student_identifier })),
  me: (token: string) => request<MeResponse>('/sessions/me', { headers: participantHeaders(token) }),

  submission: (id: string) => request<SubmissionPublic>(`/submissions/${id}`),
  submissionDisplay: (id: string) => request<SubmissionDisplayOut>(`/submissions/${id}/display`),
  participantSubmissions: (sessionId: string, participantId: string) =>
    request<SubmissionPublic[]>(`/sessions/${sessionId}/submissions?participant_id=${participantId}`),
  upload: (sessionId: string, token: string, file: File) => {
    const form = new FormData();
    form.append('file', file, file.name);
    return request<SubmissionPublic>(`/sessions/${sessionId}/submissions`, {
      method: 'POST',
      headers: participantHeaders(token),
      body: form,
    });
  },

  teacher: {
    verify: (secret: string) => request<{ detail: string }>('/teacher/verify', { headers: teacherHeaders(secret) }),
    sessions: (secret: string) => request<SessionTeacherView[]>('/teacher/sessions', { headers: teacherHeaders(secret) }),
    create: (secret: string, challenge_id: string, name: string, join_code?: string) =>
      request<SessionPublic>('/teacher/sessions', json('POST', { challenge_id, name, join_code: join_code || undefined }, teacherHeaders(secret))),
    update: (secret: string, id: string, patch: Partial<Pick<SessionPublic, 'name' | 'accepting_submissions' | 'scores_hidden' | 'enabled_submission_types'>>) =>
      request<SessionPublic>(`/teacher/sessions/${id}`, json('PATCH', patch, teacherHeaders(secret))),
    reset: (secret: string, id: string) => request<{ detail: string }>(`/teacher/sessions/${id}/reset`, json('POST', undefined, teacherHeaders(secret))),
    delete: (secret: string, id: string) => request<{ detail: string }>(`/teacher/sessions/${id}`, { method: 'DELETE', headers: teacherHeaders(secret) }),
    failures: (secret: string, id: string) => request<SubmissionPublic[]>(`/teacher/sessions/${id}/failures`, { headers: teacherHeaders(secret) }),
  },
};
