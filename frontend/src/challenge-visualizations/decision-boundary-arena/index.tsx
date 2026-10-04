import { ClassLegend, DecisionBoundary, type DecisionBoundaryData } from './DecisionBoundary';
import { ScoreBlobs } from './ScoreBlobs';
import type { ArenaProps, SubmissionPreviewProps, VisualizationPlugin } from '../types';

function Arena(props: ArenaProps) {
  const { sessionDisplay, selected, participants, challenge, selectedParticipantId, onSelectParticipant, recent, scoresHidden, reducedMotion, detailPanel } = props;
  const data = sessionDisplay?.data as unknown as DecisionBoundaryData | undefined;
  const probs = (selected.display?.data?.grid_probabilities as number[] | undefined) ?? null;
  const scoreRange = ((data as { score_range?: [number, number] } | undefined)?.score_range ?? [0, 1]) as [number, number];
  const selectedName = participants.find((p) => p.id === selectedParticipantId)?.display_name;

  return (
    <div className="arena dba">
      <section className="dba-main" aria-label="Decision boundary">
        <div className="dba-plot-header">
          <h2>
            {selectedName ? (
              <>
                Decision boundary — <span className="who">{selectedName}</span>
                {selected.submission && <span className="muted"> · submission #{selected.submission.seq_no}</span>}
              </>
            ) : (
              'Two-moons dataset'
            )}
          </h2>
          <ClassLegend labels={(data as { class_labels?: [string, string] } | undefined)?.class_labels} />
        </div>
        <div className={`dba-plot${selected.loading ? ' loading' : ''}`}>
          {data ? <DecisionBoundary data={data} probabilities={probs} /> : <div className="placeholder">Loading dataset…</div>}
        </div>
        {detailPanel}
      </section>
      <section className="dba-cohort" aria-label="Cohort scores">
        <ScoreBlobs
          participants={participants}
          scoreRange={scoreRange}
          scoreLabel={challenge.primary_metric.label}
          scoreFormat={challenge.primary_metric.format}
          selectedId={selectedParticipantId}
          onSelect={onSelectParticipant}
          recent={recent}
          scoresHidden={scoresHidden}
          reducedMotion={reducedMotion}
        />
      </section>
    </div>
  );
}

function SubmissionPreview({ sessionDisplay, display }: SubmissionPreviewProps) {
  const data = sessionDisplay.data as unknown as DecisionBoundaryData;
  const probs = (display.data.grid_probabilities as number[] | undefined) ?? null;
  return <DecisionBoundary data={data} probabilities={probs} compact title="Your decision boundary" />;
}

export const decisionBoundaryArena: VisualizationPlugin = {
  id: 'decision_boundary_arena',
  Arena,
  SubmissionPreview,
};
