<script setup lang="ts">
import { withBase } from "vitepress";
import { onBeforeUnmount, onMounted, ref } from "vue";

import { terms } from "../mark";

// The hero draws manim-marimo's mark: marimo's looped circle, written by the
// rotating vectors the Fourier example computes. One turn of the vectors
// draws the whole ring, and the drawing comes to rest on the mark itself.
const unit = 760;
const duration = 12;
const delay = 0.6;
const steps = 1440;
const extent = 600;

const chain = (phase: number): [number, number][] => {
  const points: [number, number][] = [[0, 0]];
  let x = 0;
  let y = 0;
  for (const [k, re, im] of terms) {
    const angle = 2 * Math.PI * k * phase;
    x += (re * Math.cos(angle) - im * Math.sin(angle)) * unit;
    y -= (re * Math.sin(angle) + im * Math.cos(angle)) * unit;
    points.push([x, y]);
  }
  return points;
};
const ring = Array.from({ length: steps + 1 }, (_, index) => chain(index / steps).at(-1)!);
const radii = terms.map(([, re, im]) => Math.hypot(re, im) * unit);

// Elements the animation updates every frame, outside Vue's reactivity.
const circles: SVGCircleElement[] = [];
const shafts: SVGLineElement[] = [];
const tips: SVGPolygonElement[] = [];
const root = ref<SVGSVGElement>();
// At rest the drawing becomes the mark: the ring, one vector from the center
// to the pen, and the pen.
const resting = ref(false);
const trace = ref<SVGPolylineElement>();
const dot = ref<SVGCircleElement>();

const format = ([x, y]: [number, number]) => `${x.toFixed(1)},${y.toFixed(1)}`;

const draw = (phase: number): void => {
  const points = chain(phase === 1 ? 0 : phase);
  const pen = points.at(-1)!;
  radii.forEach((radius, index) => {
    // The resting vector runs from the center to just short of the pen.
    const rest = phase === 1 && index === 0;
    const [x0, y0] = rest ? [0, 0] : points[index]!;
    const reach = Math.hypot(pen[0], pen[1]);
    const [x1, y1] = rest ? [pen[0] * (1 - 12 / reach), pen[1] * (1 - 12 / reach)] : points[index + 1]!;
    if (rest) {
      radius = Math.hypot(x1, y1);
    }
    circles[index]?.setAttribute("cx", x0.toFixed(2));
    circles[index]?.setAttribute("cy", y0.toFixed(2));
    // A vector is a shaft and a slender tip, sized as Manim sizes arrows.
    const ux = (x1 - x0) / radius;
    const uy = (y1 - y0) / radius;
    const size = Math.min(0.3 * radius, 24);
    const bx = x1 - ux * size;
    const by = y1 - uy * size;
    const half = size * 0.36;
    shafts[index]?.setAttribute("x1", x0.toFixed(2));
    shafts[index]?.setAttribute("y1", y0.toFixed(2));
    shafts[index]?.setAttribute("x2", bx.toFixed(2));
    shafts[index]?.setAttribute("y2", by.toFixed(2));
    tips[index]?.setAttribute(
      "points",
      `${x1.toFixed(2)},${y1.toFixed(2)} ${(bx - uy * half).toFixed(2)},${(by + ux * half).toFixed(2)} ${(bx + uy * half).toFixed(2)},${(by - ux * half).toFixed(2)}`,
    );
  });
  const end = Math.floor(phase * steps);
  trace.value?.setAttribute("points", [...ring.slice(0, end + 1), pen].map(format).join(" "));
  dot.value?.setAttribute("cx", pen[0].toFixed(2));
  dot.value?.setAttribute("cy", pen[1].toFixed(2));
  resting.value = phase === 1;
};

let frame = 0;
let start = 0;
let observer: IntersectionObserver | undefined;

// The pen eases in and out, so the drawing starts and settles gently.
const ease = (t: number): number => (t < 0.5 ? 4 * t * t * t : 1 - (-2 * t + 2) ** 3 / 2);

const tick = (now: number): void => {
  start ||= now;
  const t = Math.min(Math.max((now - start) / 1000 - delay, 0) / duration, 1);
  const phase = t === 1 ? 1 : ease(t);
  draw(phase);
  frame = phase < 1 ? requestAnimationFrame(tick) : 0;
};

onMounted(() => {
  // Readers who ask for reduced motion see the finished mark.
  if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
    draw(1);
    return;
  }
  draw(0);
  // The drawing starts when the hero comes into view.
  observer = new IntersectionObserver(([entry]) => {
    if (entry?.isIntersecting && !start) {
      frame = requestAnimationFrame(tick);
      observer?.disconnect();
    }
  });
  if (root.value) {
    observer.observe(root.value);
  }
});

onBeforeUnmount(() => {
  cancelAnimationFrame(frame);
  observer?.disconnect();
});
</script>

<template>
  <a class="fourier-hero" :href="withBase('/examples/fourier')" aria-label="Fourier drawing: recreate this drawing in a marimo notebook">
    <svg ref="root" :class="{ 'is-resting': resting }" viewBox="-470 -470 940 940" role="img" aria-label="Five rotating vectors draw manim-marimo's mark, marimo's looped circle, on the complex plane.">
      <defs>
        <radialGradient id="fourier-hero-fade">
          <stop offset="0.35" stop-color="#fff" />
          <stop offset="1" stop-color="#fff" stop-opacity="0" />
        </radialGradient>
        <mask id="fourier-hero-plane">
          <rect x="-600" y="-600" width="1200" height="1200" fill="url(#fourier-hero-fade)" />
        </mask>
      </defs>
      <g class="fourier-hero__plane" mask="url(#fourier-hero-plane)">
        <line class="fourier-hero__axis" :x1="-extent" y1="0" :x2="extent" y2="0" />
        <line class="fourier-hero__axis" x1="0" :y1="-extent" x2="0" :y2="extent" />
      </g>
      <g class="fourier-hero__circles">
        <circle
          v-for="(radius, index) in radii"
          :key="index"
          :ref="(element) => (circles[index] = element as SVGCircleElement)"
          :class="{ 'is-small': index > 0 }"
          :r="radius"
          :style="{ opacity: Math.min(1, radius / 40) }"
        />
      </g>
      <polyline ref="trace" class="fourier-hero__trace" />
      <g class="fourier-hero__vectors">
        <template v-for="(radius, index) in radii" :key="index">
          <line :ref="(element) => (shafts[index] = element as SVGLineElement)" :class="{ 'is-long': index === 0, 'is-small': index > 0 }" />
          <polygon :ref="(element) => (tips[index] = element as SVGPolygonElement)" :class="{ 'is-small': index > 0 }" />
        </template>
      </g>
      <circle ref="dot" class="fourier-hero__pen" r="8" />
    </svg>
  </a>
</template>

<style scoped>
.fourier-hero {
  display: block;
  width: 100%;
  height: 100%;
}

.fourier-hero svg {
  display: block;
  width: 100%;
  height: 100%;
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

.fourier-hero__circles circle {
  fill: none;
  stroke: var(--mm-scene);
  stroke-width: 1;
  stroke-opacity: 0.28;
}

.fourier-hero__vectors line {
  stroke: var(--mm-vector);
  stroke-width: 1;
  stroke-linecap: round;
  stroke-opacity: 0.6;
}

.fourier-hero__vectors line.is-long {
  stroke-width: 1.5;
  stroke-opacity: 1;
}

.fourier-hero__vectors polygon.is-small {
  fill-opacity: 0.6;
}

.fourier-hero__vectors polygon {
  fill: var(--mm-vector);
}

.fourier-hero__trace {
  fill: none;
  stroke: var(--mm-notebook);
  stroke-width: 1.75;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.fourier-hero__pen {
  fill: var(--mm-focus);
}

.fourier-hero__circles circle,
.fourier-hero__vectors .is-small {
  transition: opacity 1.6s ease;
}

.is-resting .fourier-hero__circles circle,
.is-resting .fourier-hero__vectors .is-small {
  opacity: 0 !important;
}

.fourier-hero:focus-visible {
  outline: 2px solid var(--mm-focus);
  outline-offset: 4px;
}
</style>
