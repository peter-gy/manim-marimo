<script setup lang="ts">
import { withBase } from "vitepress";
import { computed, nextTick, onBeforeUnmount, onMounted, ref } from "vue";

// One example as its stages: the notebook computes, the scene reads its
// results, Studio renders the movie, and the zero-python export serves the
// page. docs/scripts/build-examples.ts writes the exports under
// public/exports/NAME/, and the default slot holds the scene's source.
const props = withDefaults(
  defineProps<{
    name: string;
    notebook: string;
    scene: string;
    stage?: "notebook" | "scene" | "movie" | "page";
  }>(),
  { stage: "page" },
);

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

const stages = [
  {
    key: "notebook",
    label: "Notebook",
    color: "var(--mm-notebook)",
    file: file(props.notebook),
    source: `${repository}/${props.notebook}`,
    open: withBase(`${root}/notebook/index.html`),
    caption: "The notebook computes every result the scene reads.",
  },
  {
    key: "scene",
    label: "Scene",
    color: "var(--mm-scene)",
    file: file(props.scene),
    source: `${repository}/${props.scene}`,
    open: `${repository}/${props.scene}`,
    caption: "The scene reads notebook results by name and choreographs the movie.",
  },
  {
    key: "movie",
    label: "Movie",
    color: "var(--mm-focus)",
    file: "animation.mp4",
    source: `${repository}/${props.scene}`,
    open: withBase(`${root}/render/animation.mp4`),
    caption: "Pause the movie and point at a shape to see the notebook result it shows. Click it to open the line that drew it.",
  },
  {
    key: "page",
    label: "Page",
    color: "var(--vp-c-text-1)",
    file: "index.html",
    source: `${repository}/${props.scene.replace(/[^/]*$/, "index.html")}`,
    open: withBase(`${root}/page/index.html`),
    caption: "The zero-python export prepares one movie per control value. Change a control.",
  },
] as const;

type Key = (typeof stages)[number]["key"];
const selectedKey = ref<Key>(props.stage);
const selected = computed(() => stages.find(({ key }) => key === selectedKey.value) ?? stages[3]);
const loaded = ref<Record<string, boolean>>({});
// A frame mounts the first time its stage opens and stays mounted, so
// switching stages keeps the page's state and the notebook's scroll position.
const opened = ref<Key[]>([props.stage]);
const frames = computed(() =>
  stages.filter(({ key }) => (key === "notebook" || key === "page") && opened.value.includes(key)),
);
const example = ref<Example>();
const mounted = ref(false);

const tabId = (key: string): string => `manim-example-${props.name}-${key}`;
const panelId = `manim-example-${props.name}-panel`;

const select = (key: Key): void => {
  selectedKey.value = key;
  if (!opened.value.includes(key)) {
    opened.value.push(key);
  }
};

const selectFromKeyboard = (event: KeyboardEvent, key: Key): void => {
  const index = stages.findIndex((stage) => stage.key === key);
  const next = {
    ArrowLeft: (index - 1 + stages.length) % stages.length,
    ArrowRight: (index + 1) % stages.length,
    Home: 0,
    End: stages.length - 1,
  }[event.key];
  if (next === undefined) {
    return;
  }
  event.preventDefault();
  select(stages[next].key);
  requestAnimationFrame(() => document.getElementById(tabId(stages[next].key))?.focus());
};

const seconds = (value: number): string => `${value.toFixed(1)} s`;
const inputs = computed(() =>
  Object.entries(example.value?.inputs ?? {})
    .map(([name, value]) => `${name} = ${String(value)}`)
    .join(", "),
);

// Tracing: while the movie is paused, the shape under the pointer shows the
// notebook results it reads, the cell that computed them, and the scene line
// that drew it, as Lens does in Studio's preview.
const video = ref<HTMLVideoElement>();
const stageElement = ref<HTMLElement>();
const source = ref<HTMLElement>();
const paused = ref(true);
const screen = ref({ left: 0, top: 0, width: 0, height: 0 });
const hovered = ref<Shape>();
const pointer = ref({ x: 0, y: 0 });

const traced = computed(() => (example.value?.trace?.movie.length ?? 0) + (example.value?.trace?.poster.length ?? 0));

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

const measure = (): void => {
  const element = video.value;
  const container = stageElement.value;
  if (!element || !container || !element.videoWidth) {
    return;
  }
  const outer = container.getBoundingClientRect();
  const inner = element.getBoundingClientRect();
  // The element keeps the movie's aspect ratio, so the picture fills it.
  screen.value = { left: inner.left - outer.left, top: inner.top - outer.top, width: inner.width, height: inner.height };
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
  measure();
  last = { x: clientX, y: clientY };
  hovered.value = shapeUnder(clientX, clientY);
  const container = stageElement.value?.getBoundingClientRect();
  if (container) {
    pointer.value = { x: clientX - container.left, y: clientY - container.top };
  }
};

const hover = (event: PointerEvent): void => {
  if (event.pointerType !== "touch") {
    point(event.clientX, event.clientY);
  }
};

// After a seek the shapes under a still pointer change.
const seeked = (): void => {
  if (last) {
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
    label: shape.label,
  };
});

const outline = computed(() => {
  const shape = hovered.value;
  if (!shape) {
    return undefined;
  }
  const { left, top, width, height } = screen.value;
  const [x, y, w, h] = shape.box;
  return {
    left: `${left + x * width - 3}px`,
    top: `${top + y * height - 3}px`,
    width: `${w * width + 6}px`,
    height: `${h * height + 6}px`,
  };
});

const cardPosition = computed(() => {
  const { x, y } = pointer.value;
  const container = stageElement.value;
  const right = container ? container.clientWidth - x < 340 : false;
  return right ? { right: `${(container?.clientWidth ?? 0) - x + 14}px`, top: `${y + 14}px` } : { left: `${x + 14}px`, top: `${y + 14}px` };
});

// A click on a shape opens the scene at the line that drew it. On a touch
// screen the first tap shows the shape, and a second tap on it follows it.
const follow = async (event: PointerEvent | MouseEvent): Promise<void> => {
  const shape = shapeUnder(event.clientX, event.clientY);
  if (!shape?.line) {
    return;
  }
  event.preventDefault();
  event.stopPropagation();
  const shown = hovered.value;
  const same = shown?.line === shape.line && shown?.box.join() === shape.box.join();
  if ("pointerType" in event && event.pointerType === "touch" && !same) {
    point(event.clientX, event.clientY);
    return;
  }
  if (shape.path && shape.path !== file(props.scene)) {
    return;
  }
  select("scene");
  await nextTick();
  const container = source.value;
  const line = container?.querySelectorAll<HTMLElement>("code .line")[shape.line - 1];
  if (!container || !line) {
    return;
  }
  for (const marked of container.querySelectorAll(".manim-example__traced")) {
    marked.classList.remove("manim-example__traced");
  }
  line.classList.add("manim-example__traced");
  container.scrollTop = line.offsetTop - container.clientHeight / 3;
};

let resize: ResizeObserver | undefined;

// The frames load after mount, so the static build carries no frame sources.
onMounted(async () => {
  mounted.value = true;
  resize = new ResizeObserver(measure);
  if (stageElement.value) {
    resize.observe(stageElement.value);
  }
  try {
    const response = await fetch(withBase(`${root}/example.json`));
    if (response.ok) {
      example.value = (await response.json()) as Example;
    }
  } catch {
    // The movie plays without its traced shapes.
  }
});

onBeforeUnmount(() => resize?.disconnect());
</script>

<template>
  <figure class="manim-example" :aria-label="`${name} example`">
    <div class="manim-example__rail">
      <nav role="tablist" aria-label="Stages of the example">
        <template v-for="(stage, index) in stages" :key="stage.key">
          <svg v-if="index > 0" class="manim-example__arrow" viewBox="0 0 18 8" aria-hidden="true">
            <path d="M0 4h15M12 1l3 3-3 3" fill="none" stroke="currentColor" stroke-width="1" />
          </svg>
          <button
            :id="tabId(stage.key)"
            type="button"
            role="tab"
            :aria-controls="panelId"
            :aria-selected="stage.key === selected.key"
            :tabindex="stage.key === selected.key ? 0 : -1"
            :style="{ '--stage-color': stage.color }"
            @click="select(stage.key)"
            @keydown="selectFromKeyboard($event, stage.key)"
          >
            {{ stage.label }}
          </button>
        </template>
      </nav>
      <a class="manim-example__open" :href="selected.open" target="_blank" rel="noopener noreferrer">
        Open
        <svg viewBox="0 0 12 12" aria-hidden="true">
          <path d="M4.5 2.5h5v5M9.5 2.5 3 9" fill="none" stroke="currentColor" stroke-width="1.2" />
        </svg>
      </a>
    </div>

    <div :id="panelId" class="manim-example__viewport" role="tabpanel" :aria-labelledby="tabId(selected.key)">
      <template v-if="mounted">
        <iframe
          v-for="stage in frames"
          v-show="stage.key === selected.key"
          :key="stage.key"
          :src="stage.open"
          :title="`${stage.label}: ${stage.file}`"
          loading="eager"
          allow="fullscreen"
          allowfullscreen
          @load="loaded[stage.key] = true"
        />
      </template>
      <div v-show="selected.key === 'scene'" ref="source" class="manim-example__source">
        <slot />
      </div>
      <div v-show="selected.key === 'movie'" class="manim-example__movie">
        <div
          ref="stageElement"
          class="manim-example__frame"
          @pointermove="hover"
          @pointerleave="hovered = undefined"
          @click.capture="follow"
        >
          <video
            v-if="mounted && selected.key === 'movie'"
            ref="video"
            :src="withBase(`${root}/render/animation.mp4`)"
            :poster="withBase(`${root}/render/poster.png`)"
            :class="{ 'manim-example__tracing': hovered }"
            controls
            muted
            playsinline
            autoplay
            @loadedmetadata="measure"
            @seeked="seeked"
            @play="(paused = false), (hovered = undefined)"
            @pause="paused = true"
          />
          <div v-if="outline" class="manim-example__outline" :style="outline" aria-hidden="true" />
          <div v-if="card" class="manim-example__card" :style="cardPosition" aria-hidden="true">
            <code class="manim-example__read">{{ card.reads }}</code>
            <span v-if="card.more > 0" class="manim-example__more">and {{ card.more }} more</span>
            <code v-if="card.value" class="manim-example__value">{{ card.value }}</code>
            <span class="manim-example__origin">
              <template v-if="card.cell">cell <strong>{{ card.cell }}</strong> · </template>
              <template v-if="card.line">{{ card.file }} line {{ card.line }}</template>
              <template v-if="card.label"> · {{ card.label }}</template>
            </span>
          </div>
        </div>
        <dl v-if="example">
          <div>
            <dt>Rendered with</dt>
            <dd>{{ inputs }}</dd>
          </div>
          <div>
            <dt>Reads</dt>
            <dd>
              <code v-for="read in example.reads" :key="read">{{ read }}</code>
            </dd>
          </div>
          <div>
            <dt>Movie</dt>
            <dd>
              {{ example.movie.width }} × {{ example.movie.height }} · {{ example.movie.fps }} fps ·
              {{ seconds(example.movie.duration) }}
            </dd>
          </div>
          <div v-if="traced">
            <dt>Traced</dt>
            <dd>{{ traced.toLocaleString("en") }} shape regions, each naming the notebook result it shows</dd>
          </div>
        </dl>
      </div>
      <div
        v-if="(selected.key === 'notebook' || selected.key === 'page') && !loaded[selected.key]"
        class="manim-example__loading"
        role="status"
      >
        Loading
      </div>
    </div>

    <figcaption>
      <span>{{ selected.caption }}</span>
      <a :href="selected.source" target="_blank" rel="noopener noreferrer">{{ selected.file }}</a>
    </figcaption>
  </figure>
</template>

<style scoped>
.manim-example {
  margin: 32px 0 40px;
}

.manim-example__rail {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding-bottom: 12px;
}

.manim-example__rail nav {
  display: flex;
  align-items: center;
  gap: 12px;
  min-width: 0;
  overflow-x: auto;
  scrollbar-width: none;
}

.manim-example__rail button {
  flex: 0 0 auto;
  padding: 4px 0;
  border: 0;
  background: transparent;
  color: var(--vp-c-text-3);
  cursor: pointer;
  font: inherit;
  font-size: 16px;
  font-weight: 400;
  line-height: 22px;
  text-decoration: underline 1.5px transparent;
  text-underline-offset: 7px;
}

.manim-example__rail button:hover {
  color: var(--vp-c-text-1);
}

.manim-example__rail button[aria-selected="true"] {
  color: var(--vp-c-text-1);
  text-decoration-color: var(--stage-color);
}

.manim-example__arrow {
  flex: 0 0 auto;
  width: 18px;
  height: 8px;
  color: var(--vp-c-text-3);
  opacity: 0.7;
}

.manim-example__open {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
  color: var(--vp-c-text-3);
  font-size: 15px;
  text-decoration: none;
}

.manim-example__open:hover {
  color: var(--vp-c-text-1);
}

.manim-example__open svg {
  width: 11px;
  height: 11px;
}

.manim-example button:focus-visible,
.manim-example a:focus-visible {
  outline: 2px solid var(--vp-c-brand-1);
  outline-offset: 3px;
  border-radius: 2px;
}

.manim-example__viewport {
  position: relative;
  height: clamp(520px, calc(100dvh - var(--vp-nav-height) - 220px), 780px);
  overflow: hidden;
  border: 1px solid var(--vp-c-divider);
  border-radius: 2px;
  background: var(--vp-c-bg);
}

/* The exports follow prefers-color-scheme, which a frame's color-scheme sets
   for the document inside it. */
.manim-example__viewport iframe {
  color-scheme: light;
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}

.dark .manim-example__viewport iframe {
  color-scheme: dark;
}

.manim-example__loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-3);
  font-size: 16px;
  font-style: italic;
}

/* The scene's code block fills the viewport and scrolls inside it. */
.manim-example__source {
  position: relative;
  height: 100%;
  overflow: auto;
  background: var(--vp-code-block-bg);
}

.manim-example__source :deep(div[class*="language-"]) {
  margin: 0 !important;
  border: 0 !important;
  border-radius: 0 !important;
}

.manim-example__source :deep(pre) {
  padding: 20px 0 !important;
}

.manim-example__source :deep(.manim-example__traced) {
  display: inline-block;
  width: 100%;
  background: color-mix(in srgb, var(--mm-focus) 16%, transparent);
  box-shadow: inset 2px 0 var(--mm-focus);
}

.manim-example__movie {
  display: flex;
  flex-direction: column;
  gap: 24px;
  height: 100%;
  padding: 28px;
  box-sizing: border-box;
  overflow: auto;
}

/* The movie keeps its own frame: it scales to fit the space above the
   details without letterboxing. */
.manim-example__frame {
  position: relative;
  display: flex;
  flex: 1 1 auto;
  min-height: 0;
  align-items: center;
  justify-content: center;
}

.manim-example__frame video {
  display: block;
  width: auto;
  height: auto;
  max-width: 100%;
  max-height: 100%;
}

.manim-example__frame video.manim-example__tracing {
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
  gap: 3px;
  max-width: 320px;
  padding: 10px 12px;
  border: 1px solid var(--vp-c-border);
  border-radius: 2px;
  background: var(--vp-c-bg-elv);
  pointer-events: none;
}

.manim-example__card code {
  padding: 0;
  background: transparent;
  font-size: 13.5px;
  line-height: 19px;
  overflow-wrap: anywhere;
}

.manim-example__read {
  color: var(--mm-notebook);
  font-weight: 700;
}

.manim-example__value {
  color: var(--vp-c-text-2);
}

.manim-example__more,
.manim-example__origin {
  color: var(--vp-c-text-3);
  font-size: 14px;
  line-height: 19px;
}

.manim-example__origin strong {
  color: var(--vp-c-text-2);
  font-weight: 500;
}

.manim-example__movie dl {
  display: grid;
  flex: 0 0 auto;
  gap: 8px;
  margin: 0;
  font-size: 15px;
  line-height: 22px;
}

.manim-example__movie dl > div {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 16px;
}

.manim-example__movie dt {
  color: var(--vp-c-text-3);
  font-style: italic;
}

.manim-example__movie dd {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 0;
  color: var(--vp-c-text-1);
  font-variant-numeric: tabular-nums;
}

.manim-example__movie dd code {
  padding: 0;
  background: transparent;
  color: var(--mm-notebook);
  font-size: 14px;
}

figcaption {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 24px;
  padding-top: 12px;
  color: var(--vp-c-text-2);
  font-size: 16px;
  line-height: 24px;
}

figcaption a {
  flex: 0 0 auto;
  color: var(--vp-c-text-3);
  font-family: var(--vp-font-family-mono);
  font-size: 14px;
  text-decoration: none;
}

figcaption a:hover {
  color: var(--vp-c-text-1);
}

@media (max-width: 640px) {
  /* Four equal tabs keep their places as the selection moves. */
  .manim-example__rail {
    flex-wrap: wrap;
    row-gap: 4px;
  }

  .manim-example__rail nav {
    display: grid;
    flex: 1 1 100%;
    grid-template-columns: repeat(4, minmax(0, 1fr));
    gap: 0;
    overflow: visible;
  }

  .manim-example__arrow {
    display: none;
  }

  .manim-example__rail button {
    padding: 6px 0;
    text-align: center;
  }

  .manim-example__open {
    margin-left: auto;
    font-size: 14px;
  }

  /* The movie sits at the top of its panel, above its details. */
  .manim-example__frame {
    flex: 0 0 auto;
  }

  .manim-example__viewport {
    height: clamp(460px, calc(100dvh - var(--vp-nav-height) - 180px), 680px);
  }

  .manim-example__movie {
    padding: 16px;
  }

  .manim-example__movie dl > div {
    grid-template-columns: 1fr;
    gap: 2px;
  }

  figcaption {
    flex-direction: column;
    gap: 4px;
  }
}
</style>
