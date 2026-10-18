<script setup lang="ts">
import { withBase } from "vitepress";
import { onBeforeUnmount, onMounted, ref } from "vue";

import { mark, wordmark } from "../brand";

// The hero draws manim-marimo's mark, marimo's looped circle, with the rotating
// vectors the Fourier example computes. It then writes the wordmark below it,
// each contour of each letter traced by its own chain of rotating vectors
// from that contour's Fourier series. The finished word fills in, holds, and
// fades, and the drawing starts again.

// Seconds on the hero's clock.
const timeline = {
  mark: [0.5, 8],
  settle: [8, 9.2],
  word: [8.6, 16.6],
  fill: [16.6, 17.8],
  leave: [22, 23.2],
  loop: 23.6,
} as const;

// Layout in viewBox units: the ring is `unit` wide, and the wordmark
// `wordWidth` wide, centered beneath it.
const unit = 560;
const wordWidth = 820;
const gap = 96;
const steps = 1440;
// Terms per contour: frequencies -pairs..pairs, which reproduce a CMU Serif
// contour closely enough that the exact glyph can take over without a jump.
const pairs = 20;
const samples = 256;

type Point = [number, number];

const chainOf = (terms: [number, number, number][], phase: number, scale: number, origin: Point = [0, 0]): Point[] => {
  const points: Point[] = [origin];
  let [x, y] = origin;
  for (const [k, re, im] of terms) {
    const angle = 2 * Math.PI * k * phase;
    x += (re * Math.cos(angle) - im * Math.sin(angle)) * scale;
    y -= (re * Math.sin(angle) + im * Math.cos(angle)) * scale;
    points.push([x, y]);
  }
  return points;
};

const ring = Array.from({ length: steps + 1 }, (_, index) => chainOf(mark, index / steps, unit).at(-1)!);
const markRadii = mark.map(([, re, im]) => Math.hypot(re, im) * unit);
const ringTop = Math.min(...ring.map(([, y]) => y));
const ringBottom = Math.max(...ring.map(([, y]) => y));

const wordScale = wordWidth / wordmark.width;
const wordTop = ringBottom + gap;
const wordOffset: Point = [-wordWidth / 2, wordTop];
const margin = 36;
const viewBox = [
  -wordWidth / 2 - margin,
  ringTop - margin,
  wordWidth + 2 * margin,
  wordTop + wordmark.height * wordScale - ringTop + 2 * margin,
].map((value) => value.toFixed(1)).join(" ");

interface Contour {
  // Terms in contour units, y pointing up, so chainOf can share one sign
  // convention with the mark.
  terms: [number, number, number][];
  center: Point;
  // Share of the word's writing time, by length.
  start: number;
  end: number;
  outline: Point[];
}

const contours = ref<Contour[]>([]);
const wordPath = wordmark.contours.join("");

// The Fourier series of one contour, sampled at equal arc length.
const analyze = (d: string): Omit<Contour, "start" | "end"> & { length: number } => {
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", d);
  const length = path.getTotalLength();
  const points = Array.from({ length: samples }, (_, index) => {
    const { x, y } = path.getPointAtLength((index / samples) * length);
    return [x, -y] as Point;
  });
  const center = points.reduce<Point>(([sx, sy], [x, y]) => [sx + x / samples, sy + y / samples], [0, 0]);
  const terms: [number, number, number][] = [];
  for (let n = 1; n <= pairs; n += 1) {
    for (const k of [n, -n]) {
      let re = 0;
      let im = 0;
      points.forEach(([x, y], index) => {
        const angle = (-2 * Math.PI * k * index) / samples;
        re += (x - center[0]) * Math.cos(angle) - (y - center[1]) * Math.sin(angle);
        im += (x - center[0]) * Math.sin(angle) + (y - center[1]) * Math.cos(angle);
      });
      terms.push([k, re / samples, im / samples]);
    }
  }
  terms.sort((a, b) => Math.hypot(b[1], b[2]) - Math.hypot(a[1], a[2]));
  const origin: Point = [center[0], -center[1]];
  const outline = Array.from({ length: samples + 1 }, (_, index) => chainOf(terms, index / samples, 1, origin).at(-1)!);
  return { terms, center: origin, outline, length };
};

// Elements the animation updates every frame, outside Vue's reactivity.
const markCircles: SVGCircleElement[] = [];
const markShafts: SVGLineElement[] = [];
const markTips: SVGPolygonElement[] = [];
const wordTraces: SVGPolylineElement[] = [];
// Letter chains show their longest vectors. The rest still move the pen.
const shown = 8;
const letterCircles: SVGCircleElement[] = [];
const letterShafts: SVGLineElement[] = [];
const letterTips: SVGPolygonElement[] = [];
const root = ref<SVGSVGElement>();
const scene = ref<SVGGElement>();
const markTrace = ref<SVGPolylineElement>();
const markPen = ref<SVGCircleElement>();
const markSmall = ref<SVGGElement>();
const letterChain = ref<SVGGElement>();
const letterPen = ref<SVGCircleElement>();
const traces = ref<SVGGElement>();
const fill = ref<SVGPathElement>();

const format = ([x, y]: Point) => `${x.toFixed(1)},${y.toFixed(1)}`;
const clamp = (value: number) => Math.min(Math.max(value, 0), 1);
const progress = (t: number, [from, to]: readonly [number, number]) => clamp((t - from) / (to - from));
// Every motion eases in and out, so the drawing starts and settles gently.
const ease = (t: number): number => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

// A vector is a shaft and a slender tip, sized as Manim sizes arrows. `head`
// caps the tip in the vector's own units.
const vector = (shaft: SVGLineElement | undefined, tip: SVGPolygonElement | undefined, [x0, y0]: Point, [x1, y1]: Point, head: number) => {
  const length = Math.hypot(x1 - x0, y1 - y0) || 1e-6;
  const ux = (x1 - x0) / length;
  const uy = (y1 - y0) / length;
  const size = Math.min(0.3 * length, head);
  const bx = x1 - ux * size;
  const by = y1 - uy * size;
  const half = size * 0.36;
  shaft?.setAttribute("x1", x0.toFixed(2));
  shaft?.setAttribute("y1", y0.toFixed(2));
  shaft?.setAttribute("x2", bx.toFixed(2));
  shaft?.setAttribute("y2", by.toFixed(2));
  tip?.setAttribute(
    "points",
    `${x1.toFixed(2)},${y1.toFixed(2)} ${(bx - uy * half).toFixed(2)},${(by + ux * half).toFixed(2)} ${(bx + uy * half).toFixed(2)},${(by - ux * half).toFixed(2)}`,
  );
};

const drawMark = (t: number): void => {
  const drawn = progress(t, timeline.mark);
  const phase = drawn === 1 ? 1 : ease(drawn);
  const points = chainOf(mark, phase === 1 ? 0 : phase, unit);
  const pen = points.at(-1)!;
  markRadii.forEach((radius, index) => {
    markCircles[index]?.setAttribute("cx", points[index]![0].toFixed(2));
    markCircles[index]?.setAttribute("cy", points[index]![1].toFixed(2));
    // At rest the long vector runs from the center to just short of the pen.
    if (index === 0 && phase === 1) {
      const reach = Math.hypot(...pen);
      vector(markShafts[0], markTips[0], [0, 0], [pen[0] * (1 - 10 / reach), pen[1] * (1 - 10 / reach)], 22);
      return;
    }
    vector(markShafts[index], markTips[index], points[index]!, points[index + 1]!, Math.min(22, 0.3 * radius));
  });
  markTrace.value?.setAttribute("points", [...ring.slice(0, Math.floor(phase * steps) + 1), pen].map(format).join(" "));
  markPen.value?.setAttribute("cx", pen[0].toFixed(2));
  markPen.value?.setAttribute("cy", pen[1].toFixed(2));
  markSmall.value?.setAttribute("opacity", (1 - ease(progress(t, timeline.settle))).toFixed(3));
};

const drawWord = (t: number): void => {
  const written = progress(t, timeline.word);
  let active: { contour: Contour; phase: number } | undefined;
  contours.value.forEach((contour, index) => {
    const local = clamp((written - contour.start) / (contour.end - contour.start));
    const phase = ease(local);
    const end = Math.floor(phase * samples);
    wordTraces[index]?.setAttribute("points", local > 0 ? contour.outline.slice(0, end + 1).map(format).join(" ") : "");
    if (local > 0 && local < 1) {
      active = { contour, phase };
    }
  });
  letterChain.value?.setAttribute("opacity", active ? "1" : "0");
  if (active) {
    const points = chainOf(active.contour.terms, active.phase, 1, active.contour.center);
    for (let index = 0; index < shown; index += 1) {
      const [, re, im] = active.contour.terms[index]!;
      letterCircles[index]?.setAttribute("cx", points[index]![0].toFixed(2));
      letterCircles[index]?.setAttribute("cy", points[index]![1].toFixed(2));
      letterCircles[index]?.setAttribute("r", Math.hypot(re, im).toFixed(2));
      vector(letterShafts[index], letterTips[index], points[index]!, points[index + 1]!, 9 / wordScale);
    }
    const pen = points.at(-1)!;
    letterPen.value?.setAttribute("cx", pen[0].toFixed(2));
    letterPen.value?.setAttribute("cy", pen[1].toFixed(2));
  }
  const filled = ease(progress(t, timeline.fill));
  fill.value?.setAttribute("opacity", filled.toFixed(3));
  traces.value?.setAttribute("opacity", (1 - filled).toFixed(3));
};

const draw = (t: number): void => {
  drawMark(t);
  drawWord(t);
  scene.value?.setAttribute("opacity", (1 - ease(progress(t, timeline.leave))).toFixed(3));
};

// The clock runs only while the hero is on screen and the tab is visible.
let frame = 0;
let clock = 0;
let previous = 0;
let visible = false;

const tick = (now: number): void => {
  clock = (clock + (previous ? (now - previous) / 1000 : 0)) % timeline.loop;
  previous = now;
  draw(clock);
  frame = requestAnimationFrame(tick);
};

const play = (): void => {
  if (!frame && visible && document.visibilityState === "visible") {
    previous = 0;
    frame = requestAnimationFrame(tick);
  }
};

const pause = (): void => {
  cancelAnimationFrame(frame);
  frame = 0;
};

const visibility = (): void => (document.visibilityState === "visible" ? play() : pause());
let observer: IntersectionObserver | undefined;

onMounted(() => {
  const analyzed = wordmark.contours.map(analyze);
  const total = analyzed.reduce((sum, contour) => sum + contour.length, 0);
  let start = 0;
  contours.value = analyzed.map(({ length, ...contour }) => {
    const end = start + length / total;
    const placed = { ...contour, start, end };
    start = end;
    return placed;
  });
  requestAnimationFrame(() => {
    // Readers who ask for reduced motion see the finished mark and word.
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      draw(timeline.fill[1]);
      return;
    }
    draw(0);
    observer = new IntersectionObserver(([entry]) => {
      visible = entry?.isIntersecting ?? false;
      if (visible) {
        play();
      } else {
        pause();
      }
    });
    if (root.value) {
      observer.observe(root.value);
    }
    document.addEventListener("visibilitychange", visibility);
  });
});

onBeforeUnmount(() => {
  pause();
  observer?.disconnect();
  document.removeEventListener("visibilitychange", visibility);
});
</script>

<template>
  <a class="fourier-hero" :href="withBase('/examples/fourier')" aria-label="Fourier drawing: recreate this drawing in a marimo notebook">
    <svg ref="root" :viewBox="viewBox" role="img" aria-label="Rotating vectors draw manim-marimo's mark, marimo's looped circle, and write manim-marimo beneath it.">
      <defs>
        <radialGradient id="fourier-hero-fade">
          <stop offset="0.3" stop-color="#fff" />
          <stop offset="1" stop-color="#fff" stop-opacity="0" />
        </radialGradient>
        <mask id="fourier-hero-plane">
          <rect :x="-unit * 0.62" :y="-unit * 0.62" :width="unit * 1.24" :height="unit * 1.24" fill="url(#fourier-hero-fade)" />
        </mask>
      </defs>
      <g ref="scene">
        <g class="fourier-hero__plane" mask="url(#fourier-hero-plane)">
          <line class="fourier-hero__axis" :x1="-unit * 0.62" y1="0" :x2="unit * 0.62" y2="0" />
          <line class="fourier-hero__axis" x1="0" :y1="-unit * 0.62" x2="0" :y2="unit * 0.62" />
        </g>
        <g ref="markSmall">
          <circle
            v-for="(radius, index) in markRadii"
            :key="`c${index}`"
            :ref="(element) => (markCircles[index] = element as SVGCircleElement)"
            class="fourier-hero__circle"
            :r="radius"
          />
          <template v-for="(_, index) in markRadii.slice(1)" :key="`v${index}`">
            <line :ref="(element) => (markShafts[index + 1] = element as SVGLineElement)" class="fourier-hero__shaft" />
            <polygon :ref="(element) => (markTips[index + 1] = element as SVGPolygonElement)" class="fourier-hero__tip" />
          </template>
        </g>
        <polyline ref="markTrace" class="fourier-hero__ring" />
        <line :ref="(element) => (markShafts[0] = element as SVGLineElement)" class="fourier-hero__shaft is-long" />
        <polygon :ref="(element) => (markTips[0] = element as SVGPolygonElement)" class="fourier-hero__tip is-long" />
        <circle ref="markPen" class="fourier-hero__pen" r="7" />

        <g :transform="`translate(${wordOffset[0]} ${wordOffset[1]}) scale(${wordScale})`">
          <g ref="traces">
            <polyline
              v-for="(_, index) in wordmark.contours"
              :key="index"
              :ref="(element) => (wordTraces[index] = element as SVGPolylineElement)"
              class="fourier-hero__letter"
            />
          </g>
          <path ref="fill" class="fourier-hero__word" :d="wordPath" opacity="0" />
          <g ref="letterChain" opacity="0">
            <template v-for="index in shown" :key="index">
              <circle :ref="(element) => (letterCircles[index - 1] = element as SVGCircleElement)" class="fourier-hero__circle" />
              <line :ref="(element) => (letterShafts[index - 1] = element as SVGLineElement)" class="fourier-hero__shaft" />
              <polygon :ref="(element) => (letterTips[index - 1] = element as SVGPolygonElement)" class="fourier-hero__tip" />
            </template>
            <circle ref="letterPen" class="fourier-hero__pen" :r="3.5 / wordScale" />
          </g>
        </g>
      </g>
    </svg>
  </a>
</template>

<style scoped>
.fourier-hero {
  display: block;
  width: 100%;
}

.fourier-hero svg {
  display: block;
  width: 100%;
  height: auto;
  overflow: visible;
}

.fourier-hero line,
.fourier-hero circle,
.fourier-hero polyline {
  vector-effect: non-scaling-stroke;
}

.fourier-hero__axis {
  stroke: var(--mm-plane-axis);
  stroke-width: 1;
}

.fourier-hero__circle {
  fill: none;
  stroke: var(--mm-scene);
  stroke-width: 1;
  stroke-opacity: 0.28;
}

.fourier-hero__shaft {
  stroke: var(--mm-vector);
  stroke-width: 1;
  stroke-linecap: round;
  stroke-opacity: 0.6;
}

.fourier-hero__tip {
  fill: var(--mm-vector);
  fill-opacity: 0.6;
}

.fourier-hero__shaft.is-long {
  stroke-width: 1.5;
  stroke-opacity: 1;
}

.fourier-hero__tip.is-long {
  fill-opacity: 1;
}

.fourier-hero__ring {
  fill: none;
  stroke: var(--mm-notebook);
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.fourier-hero__letter {
  fill: none;
  stroke: var(--vp-c-text-1);
  stroke-width: 1.25;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.fourier-hero__word {
  fill: var(--vp-c-text-1);
}

.fourier-hero__pen {
  fill: var(--mm-focus);
}

.fourier-hero:focus-visible {
  outline: 2px solid var(--mm-focus);
  outline-offset: 4px;
}
</style>
