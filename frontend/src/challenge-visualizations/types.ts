/**
 * Visualization plugin contract.
 *
 * A plugin is looked up by the challenge's `visualization` id (same id as the backend
 * VisualizationType). It receives structured display data only - never raw backend objects -
 * and is free to map scores/metrics to any visual encoding it likes. The generic pages
 * (projector, student) own data loading, selection state and the compact leaderboard.
 */
import type { ComponentType, ReactNode } from 'react';
import type { ChallengeSummary, DisplayOut, ParticipantLive, SessionPublic, SubmissionDisplayOut, SubmissionPublic } from '../api/types';
import type { RecentUpdate } from '../api/live';

export interface SelectedSubmission {
  submission: SubmissionPublic | null;
  display: SubmissionDisplayOut | null;
  loading: boolean;
}

export interface ArenaProps {
  session: SessionPublic;
  challenge: ChallengeSummary;
  /** Participants with client-side ranks already assigned. */
  participants: ParticipantLive[];
  /** Static per-challenge display data (from /api/challenges/{id}/display). */
  sessionDisplay: DisplayOut | null;
  selectedParticipantId: string | null;
  selected: SelectedSubmission;
  onSelectParticipant: (participantId: string | null) => void;
  /** participantId -> most recent submission update (for brief highlights). */
  recent: Record<string, RecentUpdate>;
  scoresHidden: boolean;
  reducedMotion: boolean;
  /** Generic detail panel (score, metrics, submission picker) the plugin places where it fits. */
  detailPanel: ReactNode;
}

export interface SubmissionPreviewProps {
  challenge: ChallengeSummary;
  sessionDisplay: DisplayOut;
  display: SubmissionDisplayOut;
}

export interface VisualizationPlugin {
  id: string;
  /** The dominant projector visualization. */
  Arena: ComponentType<ArenaProps>;
  /** Optional small rendering of one submission (student page). */
  SubmissionPreview?: ComponentType<SubmissionPreviewProps>;
}
