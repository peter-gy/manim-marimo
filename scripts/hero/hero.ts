// What the README hero shows, shared by capture.ts, render.ts, and compose.html.

export const themes = ["light", "dark"] as const;
export type Theme = (typeof themes)[number];

// Cells of examples/dataflow.py the hero shows, in notebook order.
export const cells = {
  controls: "controls",
  cascade: "cascade",
  summary: "summary",
} as const;

// The radio choices the hero moves between. Each is one prepared movie.
export const states = ["noise", "degree"] as const;
export type State = (typeof states)[number];

export const fps = 25;
// compose.html paints the movie 680 CSS pixels wide, and render.ts paints at
// 1.5 device pixels per CSS pixel.
export const movieWidth = 1020;

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
      cascade: Shot;
      // The controls cell with each choice selected, and where each choice's
      // label sits within the cell.
      controls: Record<State, Shot>;
      choices: Record<State, { x: number; y: number }>;
      summary: Record<State, Shot>;
    }
  >;
  fps: number;
  states: Record<
    State,
    {
      frames: number;
      // The render's metadata.json.
      movie: { duration: number; fps: number; height: number; width: number };
    }
  >;
}
