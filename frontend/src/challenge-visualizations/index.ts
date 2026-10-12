import { decisionBoundaryArena } from './decision-boundary-arena';
import { fallbackVisualization } from './fallback';
import { generalizationArena } from './generalization-arena';
import type { VisualizationPlugin } from './types';

const plugins: Record<string, VisualizationPlugin> = {
  [decisionBoundaryArena.id]: decisionBoundaryArena,
  [generalizationArena.id]: generalizationArena,
};

/** Register an additional plugin at runtime (e.g. from a new challenge module). */
export function registerVisualization(plugin: VisualizationPlugin) {
  plugins[plugin.id] = plugin;
}

export function getVisualization(id: string | null | undefined): VisualizationPlugin {
  return (id && plugins[id]) || fallbackVisualization;
}

export type { ArenaProps, SubmissionPreviewProps, VisualizationPlugin } from './types';
