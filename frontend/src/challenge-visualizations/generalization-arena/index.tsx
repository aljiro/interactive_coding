import { ConfusionMatrix } from './ConfusionMatrix';
import { GapScatter } from './GapScatter';
import { MistakeStrip, SampleDigits, type Mistake } from './Digits';
import type { ArenaProps, SubmissionPreviewProps, VisualizationPlugin } from '../types';
import { formatValue } from '../../lib/format';

interface GeneralizationData {
  class_labels: string[];
  image_shape: [number, number];
  n_train: number;
  n_test: number;
  score_range?: [number, number];
  sample_digits: { label: number; pixels: number[] }[];
}

interface SubmissionData {
  test_accuracy: number;
  train_accuracy?: number;
  confusion: number[][];
  per_class_accuracy: number[];
  mistakes: Mistake[];
}

function Arena(props: ArenaProps) {
  const { sessionDisplay, selected, participants, challenge, selectedParticipantId, onSelectParticipant, recent, scoresHidden, reducedMotion, detailPanel } = props;
  const data = sessionDisplay?.data as unknown as GeneralizationData | undefined;
  const sub = (selected.display?.data as unknown as SubmissionData | undefined) ?? null;
  const labels: string[] = data?.class_labels ?? [];
  const shape: [number, number] = data?.image_shape ?? [28, 28];
  const scoreRange: [number, number] = data?.score_range ?? [0, 1];
  const selectedName = participants.find((p) => p.id === selectedParticipantId)?.display_name;
  const trainLabel = challenge.secondary_metrics.find((m) => m.key === 'train_accuracy')?.label ?? 'training accuracy';

  return (
    <div className="arena dba gza">
      <section className="dba-main" aria-label="Training versus hidden-test accuracy">
        <div className="dba-plot-header">
          <h2>Does it generalise?</h2>
          <span className="muted small">
            {data ? `${data.n_train} training digits · ${data.n_test} hidden test digits` : ''}
          </span>
        </div>
        <GapScatter
          participants={participants}
          scoreRange={scoreRange}
          xLabel={trainLabel}
          yLabel={challenge.primary_metric.label}
          scoreFormat={challenge.primary_metric.format}
          selectedId={selectedParticipantId}
          onSelect={onSelectParticipant}
          recent={recent}
          scoresHidden={scoresHidden}
          reducedMotion={reducedMotion}
        />
        {detailPanel}
      </section>
      <section className={`gza-side${selected.loading ? ' loading' : ''}`} aria-label="Selected submission">
        {selectedName && sub ? (
          <>
            <h2>
              <span className="who">{selectedName}</span>
              {selected.submission && <span className="muted"> · submission #{selected.submission.seq_no}</span>}
            </h2>
            {!scoresHidden && (
              <p className="gza-summary">
                hidden test <strong>{formatValue(sub.test_accuracy, challenge.primary_metric.format)}</strong>
                {typeof sub.train_accuracy === 'number' && (
                  <>
                    {' '}· training <strong>{formatValue(sub.train_accuracy, challenge.primary_metric.format)}</strong>
                    {' '}· gap <strong>{formatValue(sub.train_accuracy - sub.test_accuracy, challenge.primary_metric.format)}</strong>
                  </>
                )}
              </p>
            )}
            <ConfusionMatrix confusion={sub.confusion} labels={labels} />
            <h3>Most confident mistakes on the hidden set</h3>
            <MistakeStrip mistakes={sub.mistakes} labels={labels} shape={shape} />
          </>
        ) : (
          <>
            <h2>Small-data MNIST</h2>
            {data ? <SampleDigits digits={data.sample_digits} labels={labels} shape={shape} /> : <div className="placeholder">Loading dataset…</div>}
            <p className="muted small">
              Click a name to see that model's confusion matrix and its most confident mistakes on the hidden test digits.
            </p>
          </>
        )}
      </section>
    </div>
  );
}

function SubmissionPreview({ sessionDisplay, display, challenge }: SubmissionPreviewProps) {
  const data = sessionDisplay.data as unknown as GeneralizationData;
  const sub = display.data as unknown as SubmissionData;
  if (!sub?.confusion) return null;
  return (
    <div className="gza-preview">
      {typeof sub.train_accuracy === 'number' && (
        <p className="small">
          training <strong>{formatValue(sub.train_accuracy, challenge.primary_metric.format)}</strong> · hidden test{' '}
          <strong>{formatValue(sub.test_accuracy, challenge.primary_metric.format)}</strong> · gap{' '}
          <strong>{formatValue(sub.train_accuracy - sub.test_accuracy, challenge.primary_metric.format)}</strong>
        </p>
      )}
      <ConfusionMatrix confusion={sub.confusion} labels={data.class_labels} compact />
      <MistakeStrip mistakes={sub.mistakes} labels={data.class_labels} shape={data.image_shape} size={36} />
    </div>
  );
}

export const generalizationArena: VisualizationPlugin = {
  id: 'generalization_arena',
  Arena,
  SubmissionPreview,
};
