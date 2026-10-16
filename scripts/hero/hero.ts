// What the README hero shows, shared by capture.ts, render.ts, and compose.html.

export const themes = ["light", "dark"] as const;
export type Theme = (typeof themes)[number];

// Notebook cells of examples/convolution.py, in notebook order.
export const cells = {
  chart: "distribution_chart",
  controls: "controls",
  distributions: "distributions",
} as const;

// The slider moves in steps of 0.1. The hero drags it from a fair die to one
// biased toward six, so the capture records every step in between.
export const states = {
  fair: { bias: 0 },
  biased: { bias: 0.8 },
} as const;
export type State = keyof typeof states;
export const steps = 9;
export const step = (state: State): number => Math.round(states[state].bias * 10);

export const fps = 25;
// compose.html paints the movie 638 CSS pixels wide, and render.ts paints at
// 1.5 device pixels per CSS pixel.
export const movieWidth = 960;

export interface Shot {
  file: string;
  // CSS pixels in the editor.
  height: number;
  width: number;
}

export interface Manifest {
  cells: Record<
    Theme,
    {
      chart: (Shot & { mean: string })[];
      controls: (Shot & { thumb: { x: number; y: number } })[];
      distributions: Shot;
    }
  >;
  fps: number;
  states: Record<
    State,
    {
      bias: number;
      frames: number;
      // The render's metadata.json.
      movie: { duration: number; fps: number; height: number; width: number };
    }
  >;
}
