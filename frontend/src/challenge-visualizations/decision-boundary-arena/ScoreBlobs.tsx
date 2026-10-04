/**
 * Cohort view: every participant is a labelled blob whose vertical position encodes the
 * primary score. Horizontal position carries NO meaning - it is produced by a force layout
 * purely so labels do not overlap.
 */
import { useEffect, useMemo, useRef, useState } from 'react';
import { forceCollide, forceSimulation, forceX, forceY, type Simulation, type SimulationNodeDatum } from 'd3-force';
import { scaleLinear } from 'd3-scale';
import type { ParticipantLive } from '../../api/types';
import type { RecentUpdate } from '../../api/live';
import { useElementSize, useTick } from '../../lib/hooks';
import { formatValue } from '../../lib/format';
import { Axis } from '../shared/Axis';

interface Node extends SimulationNodeDatum {
  id: string;
  score: number;
  r: number;
  ty: number;
}

interface Props {
  participants: ParticipantLive[];
  scoreRange: [number, number];
  scoreLabel: string;
  scoreFormat: string;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  recent: Record<string, RecentUpdate>;
  scoresHidden: boolean;
  reducedMotion: boolean;
}

const MARGIN = { top: 28, right: 20, bottom: 16, left: 56 };
const WAITING_H = 64;
const BLOB_R = 13;
const HIGHLIGHT_MS = 2500;

function hash(s: string): number {
  let h = 2166136261;
  for (let i = 0; i < s.length; i++) h = Math.imul(h ^ s.charCodeAt(i), 16777619);
  return (h >>> 0) / 4294967295;
}

export function ScoreBlobs({ participants, scoreRange, scoreLabel, scoreFormat, selectedId, onSelect, recent, scoresHidden, reducedMotion }: Props) {
  const { ref, width, height } = useElementSize<HTMLDivElement>();
  const scored = useMemo(() => participants.filter((p) => p.best_score !== null), [participants]);
  const waiting = useMemo(() => participants.filter((p) => p.best_score === null), [participants]);
  useTick(500, Object.keys(recent).length > 0);

  const plotTop = MARGIN.top;
  const plotBottom = Math.max(plotTop + 60, height - MARGIN.bottom - (waiting.length ? WAITING_H : 0));
  const cx = MARGIN.left + (width - MARGIN.left - MARGIN.right) / 2;

  const yScale = useMemo(() => {
    const minScore = scored.length ? Math.min(...scored.map((p) => p.best_score!)) : scoreRange[0];
    const lo = Math.min(scoreRange[0], Math.floor((minScore - 0.02) * 20) / 20);
    return scaleLinear().domain([lo, scoreRange[1]]).range([plotBottom, plotTop]).clamp(true);
  }, [scored, scoreRange, plotBottom, plotTop]);

  const simRef = useRef<Simulation<Node, undefined> | null>(null);
  const nodesRef = useRef<Map<string, Node>>(new Map());
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

  useEffect(() => {
    if (!width || !height) return;
    const xMin = MARGIN.left + BLOB_R + 4;
    const xMax = width - MARGIN.right - BLOB_R - 4;
    const nodes: Node[] = scored.map((p) => {
      const ty = yScale(p.best_score!);
      const labelW = Math.max(BLOB_R * 2, p.display_name.length * 6.5 + 8);
      let n = nodesRef.current.get(p.id);
      if (!n) {
        n = { id: p.id, score: p.best_score!, r: labelW / 2, ty, x: xMin + hash(p.id) * (xMax - xMin), y: ty };
        nodesRef.current.set(p.id, n);
      }
      n.score = p.best_score!;
      n.ty = ty;
      n.r = Math.max(BLOB_R + 4, Math.min(labelW / 2, 46));
      return n;
    });
    for (const id of Array.from(nodesRef.current.keys())) if (!scored.some((p) => p.id === id)) nodesRef.current.delete(id);

    const publish = () => {
      const pos: Record<string, { x: number; y: number }> = {};
      for (const n of nodes) {
        n.x = Math.max(xMin, Math.min(xMax, n.x ?? cx));
        pos[n.id] = { x: n.x, y: n.y ?? n.ty };
      }
      setPositions(pos);
    };

    let sim = simRef.current;
    if (!sim) {
      sim = forceSimulation<Node>().alphaDecay(0.035).velocityDecay(0.35);
      simRef.current = sim;
    }
    sim
      .nodes(nodes)
      .force('y', forceY<Node>((d) => d.ty).strength(0.9))
      .force('x', forceX<Node>(cx).strength(0.02))
      .force('collide', forceCollide<Node>((d) => d.r + 2).strength(0.9).iterations(2))
      .on('tick', reducedMotion ? null : publish);

    if (reducedMotion) {
      sim.stop();
      sim.alpha(1);
      for (let i = 0; i < 250; i++) sim.tick();
      publish();
    } else {
      sim.alpha(0.7).restart();
    }
    return () => {
      sim?.on('tick', null);
    };
  }, [scored, yScale, width, height, cx, reducedMotion]);

  useEffect(() => () => {
    simRef.current?.stop();
  }, []);

  const now = Date.now();
  const ticks = Math.max(3, Math.min(11, Math.round((plotBottom - plotTop) / 60)));

  return (
    <div className="score-blobs" ref={ref}>
      {width > 0 && height > 0 && (
        <svg width={width} height={height} role="group" aria-label={`Participants by ${scoreLabel}`}>
          <Axis scale={yScale} orient="left" at={MARGIN.left} ticks={ticks} length={plotBottom - plotTop} format={(v) => (scoresHidden ? '' : formatValue(v, scoreFormat === 'd' ? 'd' : '.2f'))} />
          <text className="axis-title" x={MARGIN.left} y={plotTop - 12}>
            {scoreLabel} ↑
          </text>
          <text className="axis-note" x={width - MARGIN.right} y={plotTop - 12} textAnchor="end">
            horizontal position has no meaning
          </text>
          {scored.map((p) => {
            const pos = positions[p.id];
            if (!pos) return null;
            const upd = recent[p.id];
            const fresh = upd && now - upd.at < HIGHLIGHT_MS && upd.status === 'succeeded';
            const selected = p.id === selectedId;
            const cls = ['blob', selected ? 'selected' : '', fresh ? (upd.improved ? 'fresh improved' : 'fresh') : '', reducedMotion ? 'static' : ''].join(' ').trim();
            const label = p.display_name.length > 16 ? p.display_name.slice(0, 15) + '…' : p.display_name;
            return (
              <g
                key={p.id}
                className={cls}
                transform={`translate(${pos.x.toFixed(1)},${pos.y.toFixed(1)})`}
                tabIndex={0}
                role="button"
                aria-pressed={selected}
                aria-label={`${p.display_name}${scoresHidden ? '' : `, ${scoreLabel} ${formatValue(p.best_score, scoreFormat)}`}`}
                onClick={() => onSelect(selected ? null : p.id)}
                onKeyDown={(e) => {
                  if (e.key === 'Enter' || e.key === ' ') {
                    e.preventDefault();
                    onSelect(selected ? null : p.id);
                  }
                }}
              >
                {fresh && <circle className="pulse" r={BLOB_R} />}
                <circle className="body" r={BLOB_R} />
                {p.rank && !scoresHidden && (
                  <text className="rank" dy="0.35em" textAnchor="middle">{p.rank}</text>
                )}
                <text className="name" y={BLOB_R + 13} textAnchor="middle">{label}</text>
                {!scoresHidden && (
                  <text className="score" y={BLOB_R + 25} textAnchor="middle">{formatValue(p.best_score, scoreFormat)}</text>
                )}
              </g>
            );
          })}
          {waiting.length > 0 && (
            <g className="waiting" transform={`translate(0,${plotBottom + 22})`}>
              <text className="axis-note" x={MARGIN.left} y={0}>
                no evaluated submission yet
              </text>
              {waiting.map((p, i) => {
                const perRow = Math.max(1, Math.floor((width - MARGIN.left - MARGIN.right) / 92));
                const x = MARGIN.left + 20 + (i % perRow) * 92;
                const y = 20 + Math.floor(i / perRow) * 22;
                const upd = recent[p.id];
                const pending = p.latest_status && ['uploaded', 'queued', 'running'].includes(p.latest_status);
                const failed = p.latest_status === 'failed' || p.latest_status === 'timed_out';
                return (
                  <g
                    key={p.id}
                    className={`blob waiting-blob${pending ? ' pending' : ''}${failed ? ' failed' : ''}${upd && now - upd.at < HIGHLIGHT_MS ? ' fresh' : ''}`}
                    transform={`translate(${x},${y})`}
                  >
                    <circle className="body" r={6} />
                    <text className="name" x={10} dy="0.35em">
                      {p.display_name.length > 12 ? p.display_name.slice(0, 11) + '…' : p.display_name}
                    </text>
                  </g>
                );
              })}
            </g>
          )}
        </svg>
      )}
    </div>
  );
}
