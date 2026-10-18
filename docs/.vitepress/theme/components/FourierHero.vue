<script setup lang="ts">
import { onBeforeUnmount, onMounted, ref } from "vue";

// The italic m of CMU Serif Italic, the initial of Manim and marimo, in font
// units with y pointing up. The scene writes it with rotating vectors, as the
// Fourier example writes its path.
const glyph =
  "M83 288Q83 290 87 305.5Q91 321 99 346Q107 371 115 389Q143 442 187 442Q220 442 243 420.5Q266 399 271 363Q329 442 414 442Q454 442 484 421.5Q514 401 519 354Q579 442 669 442Q712 442 743 418.5Q774 395 774 338Q774 277 713 115Q695 61 695 40Q695 11 717 11Q773 11 810 136Q813 148 815.5 150.5Q818 153 827 153Q842 153 842 143Q842 140 838 125Q834 110 824 86.5Q814 63 800 41.5Q786 20 763.5 4.5Q741 -11 715 -11Q680 -11 659.5 12Q639 35 639 69Q639 91 655 133Q713 299 713 354Q713 420 667 420Q589 420 526 312Q515 293 501 240Q498 229 493 207.5Q488 186 485 175L445 15Q435 -11 409 -11Q395 -11 388 -3Q381 5 381 15Q381 20 384 29L449 289Q458 330 458 354Q458 420 412 420Q334 420 271 312Q260 293 246 240Q244 229 238 207.5Q232 186 230 175L190 15Q180 -11 154 -11Q140 -11 133 -3Q126 5 126 15Q126 20 129 29L204 329Q211 357 211 380Q211 420 185 420Q163 420 147.5 390Q132 360 117 301Q113 285 110.5 281.5Q108 278 98 278Q83 278 83 288Z";

// Frequencies 1, -1, 2, -2, ... up to `order`, in the order 3Blue1Brown
// chains them. The constant term places the glyph at the origin.
const order = 48;
const samples = 1024;
const period = 16;
const curveSteps = 720;
const tail = 0.3;
// The plane spans [-extent, extent] in font units, with a line every unit.
const extent = 600;
const unit = 100;
const planeLines = Array.from({ length: (2 * extent) / unit + 1 }, (_, index) => index * unit - extent);

interface Term {
  frequency: number;
  re: number;
  im: number;
  radius: number;
}

const terms = ref<Term[]>([]);
// Elements the animation updates every frame, outside Vue's reactivity.
const circles: SVGCircleElement[] = [];
const shafts: SVGLineElement[] = [];
const tips: SVGPolygonElement[] = [];
const ghost = ref("");
const trace = ref<SVGPolylineElement>();
const pen = ref<SVGCircleElement>();
const root = ref<SVGSVGElement>();
const written = ref(false);

let curve: [number, number][] = [];
let frame = 0;
let start = 0;
let elapsed = 0;
let visible = false;

const transform = (frequencies: Term[], phase: number): [number, number][] => {
  const points: [number, number][] = [[0, 0]];
  let x = 0;
  let y = 0;
  for (const { frequency, re, im } of frequencies) {
    const angle = 2 * Math.PI * frequency * phase;
    const cos = Math.cos(angle);
    const sin = Math.sin(angle);
    x += re * cos - im * sin;
    y += re * sin + im * cos;
    points.push([x, y]);
  }
  return points;
};

const analyze = (): void => {
  const path = document.createElementNS("http://www.w3.org/2000/svg", "path");
  path.setAttribute("d", glyph);
  const length = path.getTotalLength();
  // Sample by arc length, with y flipped into screen coordinates.
  const points = Array.from({ length: samples }, (_, index) => {
    const { x, y } = path.getPointAtLength((index / samples) * length);
    return [x, -y] as const;
  });
  const center = points.reduce(([sx, sy], [x, y]) => [sx + x / samples, sy + y / samples], [0, 0]);
  const coefficient = (frequency: number): Term => {
    let re = 0;
    let im = 0;
    points.forEach(([x, y], index) => {
      const angle = (-2 * Math.PI * frequency * index) / samples;
      const cos = Math.cos(angle);
      const sin = Math.sin(angle);
      re += (x - center[0]) * cos - (y - center[1]) * sin;
      im += (x - center[0]) * sin + (y - center[1]) * cos;
    });
    re /= samples;
    im /= samples;
    return { frequency, re, im, radius: Math.hypot(re, im) };
  };
  terms.value = Array.from({ length: order }, (_, index) => index + 1).flatMap((n) => [
    coefficient(n),
    coefficient(-n),
  ]);
  curve = Array.from({ length: curveSteps + 1 }, (_, index) => {
    const chain = transform(terms.value, index / curveSteps);
    return chain[chain.length - 1];
  });
  ghost.value = curve.map(([x, y]) => `${x.toFixed(1)},${y.toFixed(1)}`).join(" ");
};

// A vector is a shaft and a triangular tip, sized as Manim sizes its arrows.
const tipLength = (length: number): number => Math.min(0.3 * length, 26);

const draw = (phase: number, first: boolean): void => {
  const chain = transform(terms.value, phase);
  terms.value.forEach((term, index) => {
    const [x0, y0] = chain[index];
    const [x1, y1] = chain[index + 1];
    circles[index]?.setAttribute("cx", x0.toFixed(2));
    circles[index]?.setAttribute("cy", y0.toFixed(2));
    const length = term.radius;
    const size = tipLength(length);
    const ux = length > 0 ? (x1 - x0) / length : 0;
    const uy = length > 0 ? (y1 - y0) / length : 0;
    const bx = x1 - ux * size;
    const by = y1 - uy * size;
    const shaft = shafts[index];
    shaft?.setAttribute("x1", x0.toFixed(2));
    shaft?.setAttribute("y1", y0.toFixed(2));
    shaft?.setAttribute("x2", bx.toFixed(2));
    shaft?.setAttribute("y2", by.toFixed(2));
    const half = size * 0.42;
    tips[index]?.setAttribute(
      "points",
      `${x1.toFixed(2)},${y1.toFixed(2)} ${(bx - uy * half).toFixed(2)},${(by + ux * half).toFixed(2)} ${(bx + uy * half).toFixed(2)},${(by - ux * half).toFixed(2)}`,
    );
  });
  const [px, py] = chain[chain.length - 1];
  pen.value?.setAttribute("cx", px.toFixed(2));
  pen.value?.setAttribute("cy", py.toFixed(2));
  // The first period writes the glyph from its start. Later periods leave it
  // written and trail the pen with the last stretch of the path.
  const end = Math.floor(phase * curveSteps);
  const from = first ? 0 : end - Math.round(tail * curveSteps);
  const points: string[] = [];
  for (let step = from; step <= end; step += 1) {
    const [x, y] = curve[(step + curveSteps) % curveSteps];
    points.push(`${x.toFixed(1)},${y.toFixed(1)}`);
  }
  points.push(`${px.toFixed(1)},${py.toFixed(1)}`);
  trace.value?.setAttribute("points", points.join(" "));
};

const tick = (now: number): void => {
  if (!start) {
    start = now - elapsed;
  }
  elapsed = now - start;
  const cycles = elapsed / 1000 / period;
  const first = cycles < 1;
  if (!first && !written.value) {
    written.value = true;
  }
  draw(cycles % 1, first);
  frame = requestAnimationFrame(tick);
};

const play = (): void => {
  if (!frame && visible && document.visibilityState === "visible") {
    start = 0;
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
  analyze();
  requestAnimationFrame(() => {
    // Readers who ask for reduced motion see the written glyph, still.
    if (matchMedia("(prefers-reduced-motion: reduce)").matches) {
      written.value = true;
      draw(0, false);
      return;
    }
    draw(0, true);
    observer = new IntersectionObserver(([entry]) => {
      visible = entry.isIntersecting;
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
  <svg
    ref="root"
    class="fourier-hero"
    viewBox="-470 -470 940 940"
    role="img"
    aria-label="Rotating vectors, each turning at its own frequency, write an italic m on the complex plane."
  >
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
      <template v-for="position in planeLines" :key="position">
        <line class="fourier-hero__grid" :x1="position" :y1="-extent" :x2="position" :y2="extent" />
        <line class="fourier-hero__grid" :x1="-extent" :y1="position" :x2="extent" :y2="position" />
      </template>
      <line class="fourier-hero__axis" :x1="-extent" y1="0" :x2="extent" y2="0" />
      <line class="fourier-hero__axis" x1="0" :y1="-extent" x2="0" :y2="extent" />
    </g>
    <polyline class="fourier-hero__ghost" :class="{ 'is-written': written }" :points="ghost" />
    <g class="fourier-hero__circles">
      <circle
        v-for="(term, index) in terms"
        :key="term.frequency"
        :ref="(element) => (circles[index] = element as SVGCircleElement)"
        :r="term.radius"
        :style="{ opacity: Math.min(1, term.radius / 40) }"
      />
    </g>
    <polyline ref="trace" class="fourier-hero__trace" />
    <g class="fourier-hero__vectors">
      <template v-for="(term, index) in terms" :key="term.frequency">
        <line :ref="(element) => (shafts[index] = element as SVGLineElement)" />
        <polygon :ref="(element) => (tips[index] = element as SVGPolygonElement)" />
      </template>
    </g>
    <circle ref="pen" class="fourier-hero__pen" r="7" />
  </svg>
</template>

<style scoped>
.fourier-hero {
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

.fourier-hero__grid {
  stroke: var(--mm-plane);
  stroke-width: 1;
}

.fourier-hero__axis {
  stroke: var(--mm-plane-axis);
  stroke-width: 1.25;
}

.fourier-hero__circles circle {
  fill: none;
  stroke: var(--mm-scene);
  stroke-width: 1;
  stroke-opacity: 0.7;
}

.fourier-hero__vectors line {
  stroke: var(--mm-vector);
  stroke-width: 1.5;
  stroke-linecap: round;
}

.fourier-hero__vectors polygon {
  fill: var(--mm-vector);
}

.fourier-hero__ghost {
  fill: none;
  stroke: var(--mm-focus);
  stroke-width: 2;
  stroke-linejoin: round;
  opacity: 0;
  transition: opacity 1.2s ease;
}

.fourier-hero__ghost.is-written {
  opacity: 0.32;
}

.fourier-hero__trace {
  fill: none;
  stroke: var(--mm-focus);
  stroke-width: 3;
  stroke-linecap: round;
  stroke-linejoin: round;
}

.fourier-hero__pen {
  fill: var(--mm-focus);
}
</style>
