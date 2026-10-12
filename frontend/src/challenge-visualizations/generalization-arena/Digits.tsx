/** Tiny greyscale digit renderers (raw 0..255 pixel rows, row-major). */
import { useEffect, useRef } from 'react';

export interface DigitPixels {
  pixels: number[];
}

interface DigitProps {
  pixels: number[];
  shape: [number, number];
  size?: number;
  title?: string;
}

export function Digit({ pixels, shape, size = 40, title }: DigitProps) {
  const ref = useRef<HTMLCanvasElement>(null);
  const [h, w] = shape;
  useEffect(() => {
    const canvas = ref.current;
    if (!canvas) return;
    const ctx = canvas.getContext('2d');
    if (!ctx) return;
    const img = ctx.createImageData(w, h);
    for (let i = 0; i < w * h; i++) {
      const v = 255 - Math.max(0, Math.min(255, pixels[i] ?? 0));
      img.data[i * 4] = v;
      img.data[i * 4 + 1] = v;
      img.data[i * 4 + 2] = v;
      img.data[i * 4 + 3] = 255;
    }
    ctx.putImageData(img, 0, 0);
  }, [pixels, w, h]);
  return <canvas ref={ref} width={w} height={h} className="digit" style={{ width: size, height: size }} title={title} aria-label={title} />;
}

export interface Mistake extends DigitPixels {
  index: number;
  true: number;
  pred: number;
  confidence: number;
}

export function MistakeStrip({ mistakes, labels, shape, size = 44 }: { mistakes: Mistake[]; labels: string[]; shape: [number, number]; size?: number }) {
  if (!mistakes.length) return <p className="muted small">No mistakes on the hidden test set.</p>;
  return (
    <div className="mistake-strip" role="list" aria-label="Most confident mistakes">
      {mistakes.map((m) => (
        <div className="mistake" key={m.index} role="listitem" title={`#${m.index}: true ${labels[m.true]}, predicted ${labels[m.pred]} (${(m.confidence * 100).toFixed(0)}% confident)`}>
          <Digit pixels={m.pixels} shape={shape} size={size} />
          <div className="mistake-caption">
            <span className="true">{labels[m.true]}</span>
            <span className="arrow">→</span>
            <span className="pred">{labels[m.pred]}</span>
          </div>
        </div>
      ))}
    </div>
  );
}

export function SampleDigits({ digits, labels, shape }: { digits: { label: number; pixels: number[] }[]; labels: string[]; shape: [number, number] }) {
  return (
    <div className="sample-digits" aria-label="Sample training digits">
      {digits.map((d, i) => (
        <Digit key={i} pixels={d.pixels} shape={shape} size={34} title={labels[d.label]} />
      ))}
    </div>
  );
}
