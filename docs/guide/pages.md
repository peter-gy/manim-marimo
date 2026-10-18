---
title: Pages and players
description: Show one or more scenes on a view page, with a custom player and native notebook cells.
---

# Pages and players

`index.html` is an ordinary page. Each render host on it names a scene file,
and Studio renders that scene for the reader:

```html
<marimo-output render="scene.py">
  <video controls playsinline preload="metadata"></video>
</marimo-output>
<marimo-cell name="controls"></marimo-cell>
```

`<marimo-cell name="controls">` places the notebook cell called `controls`
with its live widgets. Moving a slider there runs the notebook, and every scene
that reads an affected value renders again. Studio's
[projections reference](https://marimo-team.github.io/marimo-studio/reference/projections)
describes cell and output hosts.

## Several scenes on one page

Add a scene file and a host for it. The
[Fourier example](../examples/fourier.md) shows the vector animation and a
spectrum side by side:

```html
<marimo-output render="scene.py" aria-label="Rotating vectors">...</marimo-output>
<marimo-output render="spectrum.py" aria-label="Spectrum">...</marimo-output>
```

Each scene renders on its own, from the results it reads. A host for a missing
scene file reports `manim-scene-missing` at the host's line.

## What a render publishes

| File            | Contents                                    |
| --------------- | ------------------------------------------- |
| `animation.mp4` | The movie, H.264 with `faststart` for streaming |
| `poster.png`    | The last frame, shown before playback       |
| `metadata.json` | `duration`, `fps`, `width`, and `height`    |

Studio serves the movie with byte ranges, so the player seeks while it streams.
The host's toolbar holds a **Download** link for the movie.

## The player

Markup inside a host replaces Studio's stock video player, and the page fills
it from the host's render record. The starter's `player.js` drives every host
on the page:

```js
const url = (record, path) => record.files.find((file) => file.path === path)?.url;

for (const host of document.querySelectorAll("marimo-output[render]")) {
  const video = host.querySelector("video");
  const show = (record) => {
    video.poster = url(record, record.preview) ?? "";
    video.src = url(record, record.main);
  };
  host.addEventListener("marimo-output-ready", (event) => show(event.detail));
  host.addEventListener("marimo-output-updated", (event) => show(event.detail));
  if (host.marimoRender) show(host.marimoRender);
}
```

The starter's full player also keeps playing when a new movie arrives during
playback, and adds replay, looping, and playback speed. Remove the markup
inside a host to use Studio's stock player.

## Render states

A host keeps its last movie on screen while the next one renders.

| `data-state` | The host                                             |
| ------------ | ---------------------------------------------------- |
| `loading`    | Waits for its first movie                            |
| `stale`      | Shows the previous movie while a new one renders     |
| `ready`      | Shows the movie for the current notebook results     |
| `error`      | Shows the last movie with the error and its scene line |

Style the states from page CSS. The starter dims a stale movie:

```css
marimo-output[data-state="stale"] video {
  opacity: 0.6;
  transition: opacity 0.2s;
}
```

`host.marimoRender.absent` lists reads that rendered at their defaults, and the
toolbar notes them as `Showing the default for <target>.`

## Quality

Set `quality` in `view.toml`:

```toml
schema = 1
provider = "manim-marimo/manim"

[options]
quality = "draft"
```

| Quality      | Resolution  | Frames per second |
| ------------ | ----------- | ----------------- |
| `draft`      | 640 × 360   | 15                |
| `preview`    | 960 × 540   | 24                |
| `production` | 1920 × 1080 | 30                |

Without `quality`, Studio Preview renders at `preview` and run mode and export
render at `production`.

## Page assets

Put images and fonts beneath `public/` and reference them from `index.html`.
The build publishes the page, its CSS and JavaScript, and `public/`. Scenes and
their helper modules stay private to the render.
