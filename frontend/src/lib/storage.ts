/** Lightweight client-side persistence: participant token and teacher secret. */

export interface StoredParticipant {
  token: string;
  participant_id: string;
  session_id: string;
  display_name: string;
}

const PARTICIPANT_KEY = 'dnnls.participant';
const TEACHER_KEY = 'dnnls.teacherSecret';

export function loadParticipant(): StoredParticipant | null {
  try {
    const raw = localStorage.getItem(PARTICIPANT_KEY);
    return raw ? (JSON.parse(raw) as StoredParticipant) : null;
  } catch {
    return null;
  }
}

export function saveParticipant(p: StoredParticipant | null) {
  try {
    if (p) localStorage.setItem(PARTICIPANT_KEY, JSON.stringify(p));
    else localStorage.removeItem(PARTICIPANT_KEY);
  } catch {
    /* storage unavailable */
  }
}

export function loadTeacherSecret(): string {
  try {
    return sessionStorage.getItem(TEACHER_KEY) ?? '';
  } catch {
    return '';
  }
}

export function saveTeacherSecret(secret: string | null) {
  try {
    if (secret) sessionStorage.setItem(TEACHER_KEY, secret);
    else sessionStorage.removeItem(TEACHER_KEY);
  } catch {
    /* storage unavailable */
  }
}
