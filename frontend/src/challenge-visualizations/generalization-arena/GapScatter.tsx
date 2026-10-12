/**
 * Cohort view: one labelled blob per participant at (training accuracy, hidden-test accuracy)
 * of their best submission. Both axes share one domain so the diagonal y = x is meaningful:
 * the further below it a blob sits, the more that model overfits.
 *
 * A light force layout only nudges overlapping blobs apart; positions stay close to the data.
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
  tx: number;
  ty: number;
  r: number;
}

interface Props {
  participants: ParticipantLive[];
  scoreRange: [number, number];
  xLabel: string;
  yLabel: string;
  scoreFormat: string;
  selectedId: string | null;
  onSelect: (id: string | null) => void;
  recent: Record<string, RecentUpdate>;
  scoresHidden: boolean;
  reducedMotion: boolean;
}

const MARGIN = { top: 30, right: 24, bottom: 48, left: 60 };
const WAITING_H = 56;
const BLOB_R = 12;
const HIGHLIGHT_MS = 2500;

export function trainAccuracy(p: ParticipantLive): number | null {
  const v = p.best_metrics?.train_accuracy;
  return typeof v === 'number' ? v : null;
}

export function GapScatter({ participants, scoreRange, xLabel, yLabel, scoreFormat, selectedId, onSelect, recent, scoresHidden, reducedMotion }: Props) {
  const { ref, width, height } = useElementSize<HTMLDivElement>();
  const scored = useMemo(() => participants.filter((p) => p.best_score !== null), [participants]);
  const waiting = useMemo(() => participants.filter((p) => p.best_score === null), [participants]);
  useTick(500, Object.keys(recent).length > 0);

  const plotTop = MARGIN.top;
  const plotBottom = Math.max(plotTop + 80, height - MARGIN.bottom - (waiting.length ? WAITING_H : 0));
  const plotLeft = MARGIN.left;
  const plotRight = Math.max(plotLeft + 80, width - MARGIN.right);

  const domain = useMemo<[number, number]>(() => {
    const values = scored.flatMap((p) => [p.best_score!, trainAccuracy(p) ?? p.best_score!]);
    const minV = values.length ? Math.min(...values) : scoreRange[0];
    const lo = Math.max(0, Math.min(scoreRange[0] + 0.5, Math.floor((minV - 0.03) * 20) / 20));
    return [lo, scoreRange[1]];
  }, [scored, scoreRange]);

  const xScale = useMemo(() => scaleLinear().domain(domain).range([plotLeft, plotRight]).clamp(true), [domain, plotLeft, plotRight]);
  const yScale = useMemo(() => scaleLinear().domain(domain).range([plotBottom, plotTop]).clamp(true), [domain, plotBottom, plotTop]);

  const simRef = useRef<Simulation<Node, undefined> | null>(null);
  const nodesRef = useRef<Map<string, Node>>(new Map());
  const [positions, setPositions] = useState<Record<string, { x: number; y: number }>>({});

  useEffect(() => {
    if (!width || !height) return;
    const nodes: Node[] = scored.map((p) => {
      const tx = xScale(trainAccuracy(p) ?? p.best_score!);
      const ty = yScale(p.best_score!);
      let n = nodesRef.current.get(p.id);
      if (!n) {
        n = { id: p.id, tx, ty, r: BLOB_R, x: tx, y: ty };
        nodesRef.current.set(p.id, n);
      }
      n.tx = tx;
      n.ty = ty;
      return n;
    });
    for (const id of Array.from(nodesRef.current.keys())) if (!scored.some((p) => p.id === id)) nodesRef.current.delete(id);

    const publish = () => {
      const pos: Record<string, { x: number; y: number }> = {};
      for (const n of nodes) {
        n.x = Math.max(plotLeft + BLOB_R, Math.min(plotRight - BLOB_R, n.x ?? n.tx));
        n.y = Math.max(plotTop + BLOB_R, Math.min(plotBottom - BLOB_R, n.y ?? n.ty));
        pos[n.id] = { x: n.x, y: n.y };
      }
      setPositions(pos);
    };

    let sim = simRef.current;
    if (!sim) {
      sim = forceSimulation<Node>().alphaDecay(0.05).velocityDecay(0.4);
      simRef.current = sim;
    }
    sim
      .nodes(nodes)
      .force('x', forceX<Node>((d) => d.tx).strength(0.6))
      .force('y', forceY<Node>((d) => d.ty).strength(0.6))
      .force('collide', forceCollide<Node>((d) => d.r + 3).strength(0.7).iterations(2))
      .on('tick', reducedMotion ? null : publish);

    if (reducedMotion) {
      sim.stop();
      sim.alpha(1);
      for (let i = 0; i < 200; i++) sim.tick();
      publish();
    } else {
      sim.alpha(0.6).restart();
    }
    return () => {
      sim?.on('tick', null);
    };
  }, [scored, xScale, yScale, width, height, plotLeft, plotRight, plotTop, plotBottom, reducedMotion]);

  useEffect(() => () => {
    simRef.current?.stop();
  }, []);

  const now = Date.now();
  const ticks = Math.max(3, Math.min(10, Math.round((plotBottom - plotTop) / 60)));
  const fmt = (v: number) => (scoresHidden ? '' : formatValue(v, '.2f'));
  const d0 = domain[0];
  const d1 = domain[1];

  return (
    <div className="gap-scatter" ref={ref}>
      {width > 0 && height > 0 && (
        <svg width={width} height={height} role="group" aria-label={`Participants by ${xLabel} and ${yLabel}`}>
          <polygon
            className="overfit-region"
            points={`${xScale(d0)},${yScale(d0)} ${xScale(d1)},${yScale(d1)} ${xScale(d1)},${yScale(d0)}`}
          />
          <line className="diagonal" x1={xScale(d0)} y1={yScale(d0)} x2={xScale(d1)} y2={yScale(d1)} />
          <text className="axis-note" x={xScale(d1) - 6} y={yScale(d0) - 8} textAnchor="end">
            below the diagonal = overfitting
          </text>
          <text className="axis-note" x={xScale(d0) + 6} y={yScale(d1) + 14} textAnchor="start">
            train = test
          </text>
          <Axis scale={yScale} orient="left" at={plotLeft} ticks={ticks} length={plotBottom - plotTop} format={fmt} />
          <Axis scale={xScale} orient="bottom" at={plotBottom} ticks={ticks} length={plotRight - plotLeft} format={fmt} label={xLabel} />
          <text className="axis-title" x={plotLeft} y={plotTop - 12}>
            {yLabel} ↑
          </text>
          {scored.map((p) => {
            const pos = positions[p.id];
            if (!pos) return null;
            const upd = recent[p.id];
            const fresh = upd && now - upd.at < HIGHLIGHT_MS && upd.status === 'succeeded';
            const selected = p.id === selectedId;
            const cls = ['blob', selected ? 'selected' : '', fresh ? (upd.improved ? 'fresh improved' : 'fresh') : '', reducedMotion ? 'static' : ''].join(' ').trim();
            const label = p.display_name.length > 16 ? p.display_name.slice(0, 15) + '…' : p.display_name;
            const tr = trainAccuracy(p);
            const aria = scoresHidden
              ? p.display_name
              : `${p.display_name}, ${yLabel} ${formatValue(p.best_score, scoreFormat)}${tr !== null ? `, ${xLabel} ${formatValue(tr, scoreFormat)}` : ''}`;
            return (
              <g
                key={p.id}
                className={cls}
                transform={`translate(${pos.x.toFixed(1)},${pos.y.toFixed(1)})`}
                tabIndex={0}
                role="button"
                aria-pressed={selected}
                aria-label={aria}
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
            <g className="waiting" transform={`translate(0,${plotBottom + 40})`}>
              <text className="axis-note" x={plotLeft} y={0}>
                no evaluated submission yet
              </text>
              {waiting.map((p, i) => {
                const perRow = Math.max(1, Math.floor((plotRight - plotLeft) / 92));
                const x = plotLeft + 20 + (i % perRow) * 92;
                const y = 18 + Math.floor(i / perRow) * 20;
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
