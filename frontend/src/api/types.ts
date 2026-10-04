// Mirrors backend/app/schemas/api.py

export interface MetricSpec {
  key: string;
  label: string;
  higher_is_better: boolean;
  format: string;
  description: string;
}

export interface SubmissionTypeInfo {
  id: string;
  label: string;
  accepted_extensions: string[];
  description: string;
}

export interface ChallengeSummary {
  id: string;
  title: string;
  short_description: string;
  submission_type: string;
  evaluator: string;
  visualization: string;
  primary_metric: MetricSpec;
  secondary_metrics: MetricSpec[];
  /** Every adapter the challenge allows; a session may enable only a subset. */
  submission_types: SubmissionTypeInfo[];
}

export interface ResourceInfo {
  name: string;
  description: string;
  content_type: string;
  /** Adapter ids this file is for; null = relevant for every submission type. */
  submission_types: string[] | null;
}

export interface ChallengeDetail extends ChallengeSummary {
  instructions_md: string;
  /** Per-submission-type instructions, keyed by adapter id. */
  submission_instructions_md: Record<string, string>;
  resources: ResourceInfo[];
  visualization_config: Record<string, unknown>;
}

export interface SessionPublic {
  id: string;
  name: string;
  challenge_id: string;
  challenge_title: string;
  join_code: string;
  accepting_submissions: boolean;
  scores_hidden: boolean;
  /** Adapter ids students may currently use (teacher-controlled subset). */
  enabled_submission_types: string[];
  created_at: string | null;
}

export interface SessionTeacherView extends SessionPublic {
  n_participants: number;
  n_submissions: number;
}

export type SubmissionStatus = 'uploaded' | 'queued' | 'running' | 'succeeded' | 'failed' | 'timed_out';

export interface ParticipantLive {
  id: string;
  display_name: string;
  joined_at: string | null;
  n_submissions: number;
  n_succeeded: number;
  best_score: number | null;
  best_metrics: Record<string, unknown> | null;
  best_submission_id: string | null;
  best_at: string | null;
  latest_submission_id: string | null;
  latest_status: SubmissionStatus | null;
  latest_at: string | null;
  latest_score: number | null;
  rank: number | null;
  improved?: boolean | null;
}

export interface SubmissionPublic {
  id: string;
  session_id: string;
  participant_id: string;
  seq_no: number;
  status: SubmissionStatus;
  submission_type: string;
  original_filename: string;
  size_bytes: number;
  created_at: string | null;
  started_at: string | null;
  finished_at: string | null;
  error_message: string | null;
  error_details: string[];
  primary_score: number | null;
  metrics: Record<string, unknown> | null;
}

export interface LiveSnapshot {
  session: SessionPublic;
  challenge: ChallengeSummary;
  participants: ParticipantLive[];
  last_event_id: number;
}

export interface MeResponse {
  participant: ParticipantLive;
  session: SessionPublic;
  challenge: ChallengeSummary;
  submissions: SubmissionPublic[];
  scores_hidden: boolean;
}

export interface JoinResponse {
  token: string;
  participant: ParticipantLive;
  session: SessionPublic;
}

export interface DisplayOut {
  visualization: string;
  config: Record<string, unknown>;
  data: Record<string, unknown>;
}

export interface SubmissionDisplayOut {
  submission_id: string;
  participant_id: string;
  visualization: string;
  data: Record<string, unknown>;
}

// SSE payloads
export type SessionEvent =
  | { type: 'participant_joined'; payload: { participant: ParticipantLive } }
  | { type: 'submission_updated'; payload: { submission: SubmissionPublic; participant: ParticipantLive } }
  | { type: 'session_updated'; payload: { session: SessionPublic } }
  | { type: 'session_reset'; payload: Record<string, never> }
  | { type: 'session_deleted'; payload: Record<string, never> };
