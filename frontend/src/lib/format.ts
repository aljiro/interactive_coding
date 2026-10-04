import type { MetricSpec } from '../api/types';

/** Format a metric value according to a MetricSpec format string (".3f", "d", "%"). */
export function formatValue(value: unknown, format = '.3f'): string {
  if (value === null || value === undefined) return '–';
  if (typeof value !== 'number') return String(value);
  if (format === 'd') return Math.round(value).toString();
  if (format === '%') return `${(value * 100).toFixed(1)}%`;
  const m = /^\.(\d+)f$/.exec(format);
  if (m) return value.toFixed(Number(m[1]));
  return value.toPrecision(4);
}

export function formatMetric(spec: MetricSpec | undefined, value: unknown): string {
  return formatValue(value, spec?.format ?? '.3f');
}

export function formatTime(iso: string | null | undefined): string {
  if (!iso) return '–';
  const d = new Date(iso);
  return d.toLocaleTimeString([], { hour: '2-digit', minute: '2-digit', second: '2-digit' });
}

export function formatBytes(n: number): string {
  if (n < 1024) return `${n} B`;
  if (n < 1024 * 1024) return `${(n / 1024).toFixed(1)} KB`;
  return `${(n / 1024 / 1024).toFixed(1)} MB`;
}

export const STATUS_LABEL: Record<string, string> = {
  uploaded: 'uploaded',
  queued: 'queued',
  running: 'evaluating…',
  succeeded: 'evaluated',
  failed: 'failed',
  timed_out: 'timed out',
};
