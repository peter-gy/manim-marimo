<script setup lang="ts">
import { withBase } from "vitepress";
import { computed, onMounted, ref } from "vue";

// One example as its stages: the notebook computes, the scene reads its
// results, Studio renders the movie, and the zero-python export serves the
// page. docs/scripts/build-examples.ts writes the exports under
// public/exports/NAME/, and the default slot holds the scene's source.
const props = defineProps<{
  name: string;
  notebook: string;
  scene: string;
}>();

interface Example {
  inputs: Record<string, unknown>;
  movie: { duration: number; fps: number; height: number; width: number };
  reads: string[];
}

const repository = "https://github.com/peter-gy/marimo-manim/blob/main";
const root = `/exports/${props.name}`;
const file = (path: string): string => path.replace(/^.*\//, "");

const stages = [
  {
    key: "notebook",
    label: "Notebook",
    file: file(props.notebook),
    source: `${repository}/${props.notebook}`,
    open: withBase(`${root}/notebook/index.html`),
    caption: "The notebook computes every result the scene reads.",
  },
  {
    key: "scene",
    label: "Scene",
    file: file(props.scene),
    source: `${repository}/${props.scene}`,
    open: `${repository}/${props.scene}`,
    caption: "The scene reads notebook results by name and choreographs the movie.",
  },
  {
    key: "movie",
    label: "Movie",
    file: "animation.mp4",
    source: `${repository}/${props.scene}`,
    open: withBase(`${root}/render/animation.mp4`),
    caption: "Studio renders the scene with the notebook's current results.",
  },
  {
    key: "page",
    label: "Page",
    file: "index.html",
    source: `${repository}/${props.scene.replace(/[^/]*$/, "index.html")}`,
    open: withBase(`${root}/page/index.html`),
    caption: "The zero-python export prepares one movie per control value. Move the slider.",
  },
] as const;

type Key = (typeof stages)[number]["key"];
const selectedKey = ref<Key>("page");
const selected = computed(() => stages.find(({ key }) => key === selectedKey.value) ?? stages[3]);
const loaded = ref<Record<string, boolean>>({});
// A frame mounts the first time its stage opens and stays mounted, so
// switching stages keeps the page's state and the notebook's scroll position.
const opened = ref<Key[]>(["page"]);
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

// The frames load after mount, so the static build carries no frame sources.
onMounted(async () => {
  mounted.value = true;
  const response = await fetch(withBase(`${root}/example.json`));
  if (response.ok) {
    example.value = (await response.json()) as Example;
  }
});
</script>

<template>
  <figure class="manim-example" :aria-label="`${name} example`">
    <div class="manim-example__rail">
      <nav role="tablist" aria-label="Stages of the example">
        <template v-for="(stage, index) in stages" :key="stage.key">
          <span v-if="index > 0" class="manim-example__arrow" aria-hidden="true">›</span>
          <button
            :id="tabId(stage.key)"
            type="button"
            role="tab"
            :aria-controls="panelId"
            :aria-selected="stage.key === selected.key"
            :tabindex="stage.key === selected.key ? 0 : -1"
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
      <div v-show="selected.key === 'scene'" class="manim-example__source">
        <slot />
      </div>
      <div v-show="selected.key === 'movie'" class="manim-example__movie">
        <div class="manim-example__frame">
          <video
            v-if="mounted && selected.key === 'movie'"
            :src="withBase(`${root}/render/animation.mp4`)"
            :poster="withBase(`${root}/render/poster.png`)"
            controls
            muted
            playsinline
            autoplay
          />
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
  gap: 10px;
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
  font-size: 13px;
  font-weight: 500;
  line-height: 20px;
  text-decoration: underline 1px transparent;
  text-underline-offset: 7px;
}

.manim-example__rail button:hover {
  color: var(--vp-c-text-1);
}

.manim-example__rail button[aria-selected="true"] {
  color: var(--vp-c-text-1);
  text-decoration-color: currentColor;
}

.manim-example__arrow {
  color: var(--vp-c-text-3);
  font-size: 13px;
  line-height: 20px;
  opacity: 0.6;
}

.manim-example__open {
  display: inline-flex;
  flex: 0 0 auto;
  align-items: center;
  gap: 4px;
  color: var(--vp-c-text-3);
  font-size: 12px;
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
  border-radius: 6px;
  background: var(--vp-c-bg);
}

.manim-example__viewport iframe {
  display: block;
  width: 100%;
  height: 100%;
  border: 0;
}

.manim-example__loading {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  background: var(--vp-c-bg);
  color: var(--vp-c-text-3);
  font-size: 13px;
}

/* The scene's code block fills the viewport and scrolls inside it. */
.manim-example__source {
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
  border-radius: 4px;
}

.manim-example__movie dl {
  display: grid;
  flex: 0 0 auto;
  gap: 8px;
  margin: 0;
  font-size: 13px;
  line-height: 20px;
}

.manim-example__movie dl > div {
  display: grid;
  grid-template-columns: 112px minmax(0, 1fr);
  gap: 16px;
}

.manim-example__movie dt {
  color: var(--vp-c-text-3);
}

.manim-example__movie dd {
  display: flex;
  flex-wrap: wrap;
  gap: 4px 16px;
  margin: 0;
  color: var(--vp-c-text-1);
  font-variant-numeric: tabular-nums;
}

.manim-example__movie code {
  padding: 0;
  background: transparent;
  color: var(--vp-c-text-1);
  font-size: 12.5px;
}

figcaption {
  display: flex;
  align-items: baseline;
  justify-content: space-between;
  gap: 24px;
  padding-top: 12px;
  color: var(--vp-c-text-2);
  font-size: 13px;
  line-height: 20px;
}

figcaption a {
  flex: 0 0 auto;
  color: var(--vp-c-text-3);
  font-family: var(--vp-font-family-mono);
  font-size: 12px;
  text-decoration: none;
}

figcaption a:hover {
  color: var(--vp-c-text-1);
}

@media (max-width: 640px) {
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
