<script setup lang="ts">
import { withBase } from "vitepress";
import { computed, onMounted, ref } from "vue";

// One example's movie, as Studio rendered it for the zero-python export that
// docs/scripts/build-examples.ts writes under public/exports/NAME/. Pausing
// the movie traces each shape to the notebook result it shows.
const props = defineProps<{
  name: string;
  notebook: string;
  scene: string;
}>();

// A traced shape of the movie: [x, y, width, height, start, end, reads, label,
// path, line], in fractions of the frame and seconds. Poster shapes have no
// times.
type Source = [string | null, number | null];
type MovieRegion = [number, number, number, number, number, number | null, string[], string | null, ...Source];
type PosterRegion = [number, number, number, number, string[], string | null, ...Source];

interface Example {
  inputs: Record<string, unknown>;
  movie: { duration: number; fps: number; height: number; width: number };
  reads: string[];
  trace?: {
    cells: Record<string, string>;
    values: Record<string, unknown>;
    movie: MovieRegion[];
    poster: PosterRegion[];
  };
}

interface Shape {
  box: [number, number, number, number];
  reads: string[];
  label: string | null;
  path: string | null;
  line: number | null;
}

const repository = "https://github.com/peter-gy/manim-marimo/blob/main";
const root = `/exports/${props.name}`;
const file = (path: string): string => path.replace(/^.*\//, "");
const sceneUrl = (line?: number | null) => `${repository}/${props.scene}${line ? `#L${line}` : ""}`;

const links = [
  { label: "Notebook", href: withBase(`${root}/notebook/index.html`) },
  { label: file(props.scene), href: sceneUrl() },
  { label: "Exported page", href: withBase(`${root}/page/index.html`) },
];

const example = ref<Example>();
const video = ref<HTMLVideoElement>();
const frame = ref<HTMLElement>();
const paused = ref(true);
const hovered = ref<Shape>();
const pointer = ref({ x: 0, y: 0 });
const touched = ref(false);

const shapesAt = (time: number, ended: boolean): Shape[] => {
  const trace = example.value?.trace;
  if (!trace) {
    return [];
  }
  if (ended && trace.poster.length > 0) {
    return trace.poster.map(([x, y, width, height, reads, label, path, line]) => ({
      box: [x, y, width, height],
      reads,
      label,
      path,
      line,
    }));
  }
  return trace.movie
    .filter(([, , , , start, end]) => start <= time + 1e-3 && (end === null || time < end))
    .map(([x, y, width, height, , , reads, label, path, line]) => ({
      box: [x, y, width, height],
      reads,
      label,
      path,
      line,
    }));
};

const shapeUnder = (clientX: number, clientY: number): Shape | undefined => {
  const element = video.value;
  if (!element || !paused.value) {
    return undefined;
  }
  const bounds = element.getBoundingClientRect();
  const x = (clientX - bounds.left) / bounds.width;
  const y = (clientY - bounds.top) / bounds.height;
  // The browser's controls cover the bottom of the picture.
  if (x < 0 || x > 1 || y < 0 || clientY > bounds.bottom - 48) {
    return undefined;
  }
  const ended = element.ended || element.currentTime >= element.duration - 0.05;
  let found: Shape | undefined;
  for (const shape of shapesAt(element.currentTime, ended)) {
    const [left, top, width, height] = shape.box;
    if (x >= left && x <= left + width && y >= top && y <= top + height) {
      if (!found || width * height < found.box[2] * found.box[3]) {
        found = shape;
      }
    }
  }
  return found;
};

let last: { x: number; y: number } | undefined;

const point = (clientX: number, clientY: number): void => {
  last = { x: clientX, y: clientY };
  hovered.value = shapeUnder(clientX, clientY);
  const bounds = frame.value?.getBoundingClientRect();
  if (bounds) {
    pointer.value = { x: clientX - bounds.left, y: clientY - bounds.top };
  }
};

const hover = (event: PointerEvent): void => {
  if (event.pointerType !== "touch") {
    point(event.clientX, event.clientY);
  }
};

// After a seek the shapes under a still pointer change.
const seeked = (): void => {
  if (last && !touched.value) {
    point(last.x, last.y);
  }
};

const targetOf = (read: string): string | undefined =>
  Object.keys({ ...example.value?.trace?.cells, ...example.value?.trace?.values })
    .filter((target) => read === target || read.startsWith(`${target}.`) || read.startsWith(`${target}[`))
    .sort((a, b) => b.length - a.length)[0];

// Resolve the steps a read adds to its target, such as [17] in people[17].
const valueOf = (read: string): unknown => {
  const target = targetOf(read);
  const values = example.value?.trace?.values ?? {};
  if (target === undefined || !(target in values)) {
    return undefined;
  }
  let value: unknown = values[target];
  for (const [, field, index, quoted] of read.slice(target.length).matchAll(/\.([A-Za-z]\w*)|\[(\d+)\]|\[("(?:[^"\\]|\\.)*")\]/g)) {
    const key = field ?? (index !== undefined ? Number(index) : JSON.parse(quoted));
    if (value === null || typeof value !== "object") {
      return undefined;
    }
    value = (value as Record<string | number, unknown>)[key];
  }
  return value;
};

const format = (value: unknown): string => {
  const text = JSON.stringify(value, (_, item) =>
    typeof item === "number" && !Number.isInteger(item) ? Number(item.toFixed(3)) : item,
  );
  if (text === undefined) {
    return "";
  }
  const spaced = text.replace(/"(\w+)":/g, "$1: ").replace(/,(?=\S)/g, ", ");
  return spaced.length > 96 ? `${spaced.slice(0, 95)}…` : spaced;
};

const card = computed(() => {
  const shape = hovered.value;
  if (!shape) {
    return undefined;
  }
  // The most specific read, such as people[17] beside city_size, shows its value.
  const read = [...shape.reads].sort((a, b) => b.length - a.length)[0] ?? "";
  const target = targetOf(read);
  return {
    reads: shape.reads.slice(0, 3).join(" · "),
    more: Math.max(shape.reads.length - 3, 0),
    value: format(valueOf(read)),
    cell: target ? example.value?.trace?.cells[target] : undefined,
    file: shape.path ? file(shape.path) : file(props.scene),
    line: shape.line,
  };
});

const outline = computed(() => {
  const shape = hovered.value;
  const element = video.value;
  const container = frame.value;
  if (!shape || !element || !container) {
    return undefined;
  }
  const outer = container.getBoundingClientRect();
  const inner = element.getBoundingClientRect();
  const [x, y, w, h] = shape.box;
  return {
    left: `${inner.left - outer.left + x * inner.width - 3}px`,
    top: `${inner.top - outer.top + y * inner.height - 3}px`,
    width: `${w * inner.width + 6}px`,
    height: `${h * inner.height + 6}px`,
  };
});

// The card keeps clear of the frame's edges on narrow screens.
const cardPosition = computed(() => {
  const { x, y } = pointer.value;
  const width = frame.value?.clientWidth ?? 0;
  const height = frame.value?.clientHeight ?? 0;
  const left = Math.min(Math.max(x + 14, 8), Math.max(width - 288, 8));
  return y > height / 2 ? { left: `${left}px`, bottom: `${height - y + 14}px` } : { left: `${left}px`, top: `${y + 14}px` };
});

// A click on a shape opens the line of the scene that drew it. On a touch
// screen the first tap shows the shape, and a second tap on it follows it.
const follow = (event: PointerEvent | MouseEvent): void => {
  const shape = shapeUnder(event.clientX, event.clientY);
  if (!shape) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  const shown = hovered.value;
  const same = shown?.line === shape.line && shown?.box.join() === shape.box.join();
  if ("pointerType" in event && event.pointerType === "touch" && !same) {
    touched.value = true;
    point(event.clientX, event.clientY);
    return;
  }
  if (shape.line && (!shape.path || shape.path === file(props.scene))) {
    window.open(sceneUrl(shape.line), "_blank", "noopener");
  }
};

const details = computed(() => {
  const movie = example.value?.movie;
  if (!movie) {
    return "";
  }
  const inputs = Object.entries(example.value?.inputs ?? {})
    .map(([name, value]) => `${name} = ${String(value)}`)
    .join(", ");
  return [inputs, `${movie.width} × ${movie.height}`, `${movie.duration.toFixed(1)} s`].filter(Boolean).join(" · ");
});

onMounted(async () => {
  try {
    const response = await fetch(withBase(`${root}/example.json`));
    if (response.ok) {
      example.value = (await response.json()) as Example;
    }
  } catch {
    // The movie plays without its traced shapes.
  }
});
</script>

<template>
  <figure class="manim-example" :aria-label="`${name} example`">
    <div
      ref="frame"
      class="manim-example__frame"
      @pointermove="hover"
      @pointerleave="touched || (hovered = undefined)"
      @click.capture="follow"
    >
      <video
        ref="video"
        :src="withBase(`${root}/render/animation.mp4`)"
        :poster="withBase(`${root}/render/poster.png`)"
        :class="{ 'is-tracing': hovered }"
        controls
        muted
        playsinline
        preload="metadata"
        @seeked="seeked"
        @play="(paused = false), (hovered = undefined), (touched = false)"
        @pause="paused = true"
      />
      <div v-if="outline" class="manim-example__outline" :style="outline" aria-hidden="true" />
      <div v-if="card" class="manim-example__card" :style="cardPosition" aria-hidden="true">
        <code class="manim-example__read">{{ card.reads }}</code>
        <span v-if="card.more > 0" class="manim-example__muted">and {{ card.more }} more</span>
        <code v-if="card.value" class="manim-example__value">{{ card.value }}</code>
        <span class="manim-example__muted">
          <template v-if="card.cell">cell {{ card.cell }} · </template>
          <template v-if="card.line">{{ card.file }} line {{ card.line }}</template>
        </span>
      </div>
    </div>
    <figcaption>
      <p v-if="example" class="manim-example__reads">
        <code v-for="read in example.reads" :key="read">{{ read }}</code>
      </p>
      <p class="manim-example__meta">
        <span>{{ details }}</span>
        <span class="manim-example__links">
          <a v-for="link in links" :key="link.label" :href="link.href" target="_blank" rel="noopener noreferrer">{{ link.label }}</a>
        </span>
      </p>
    </figcaption>
  </figure>
</template>

<style scoped>
.manim-example {
  margin: 28px 0 36px;
}

.manim-example__frame {
  position: relative;
}

.manim-example__frame video {
  display: block;
  width: 100%;
  aspect-ratio: 16 / 9;
  background: var(--manim-scene-bg);
}

.manim-example__frame video.is-tracing {
  cursor: pointer;
}

/* The shape under the pointer gets Manim's SurroundingRectangle: yellow,
   square, and clear of the shape. */
.manim-example__outline {
  position: absolute;
  border: 2px solid var(--mm-focus);
  pointer-events: none;
}

.manim-example__card {
  position: absolute;
  z-index: 1;
  display: grid;
  gap: 2px;
  width: max-content;
  max-width: 280px;
  padding: 9px 11px;
  border: 1px solid var(--vp-c-border);
  border-radius: 2px;
  background: var(--vp-c-bg-elv);
  pointer-events: none;
}

.manim-example__card code {
  padding: 0;
  background: transparent;
  font-size: 13px;
  line-height: 18px;
  overflow-wrap: anywhere;
}

.manim-example__read {
  color: var(--mm-notebook);
}

.manim-example__value {
  color: var(--vp-c-text-2);
}

.manim-example__muted {
  color: var(--vp-c-text-3);
  font-size: 13px;
  line-height: 18px;
}

figcaption {
  display: grid;
  gap: 6px;
  padding-top: 12px;
}

figcaption p {
  margin: 0;
  line-height: 1.5;
}

.manim-example__reads {
  display: flex;
  flex-wrap: wrap;
  gap: 2px 14px;
}

.manim-example__reads code {
  padding: 0;
  background: transparent;
  color: var(--mm-notebook);
  font-size: 13.5px;
}

.manim-example__meta {
  display: flex;
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 4px 20px;
  color: var(--vp-c-text-3);
  font-size: 14px;
}

.manim-example__links {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  font-family: var(--mm-font-ui);
}

.manim-example__links a {
  color: var(--vp-c-text-2);
  text-decoration: none;
}

.manim-example__links a::after {
  content: " ↗";
  color: var(--vp-c-text-3);
}

.manim-example__links a:hover {
  color: var(--vp-c-brand-1);
}

.manim-example a:focus-visible {
  outline: 2px solid var(--mm-focus);
  outline-offset: 3px;
}
</style>
