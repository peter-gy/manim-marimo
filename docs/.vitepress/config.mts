import subsetFont from "subset-font";
import type { Plugin } from "vite";
import { defineConfig } from "vitepress";
import llmstxt from "vitepress-plugin-llms";

const repository = "https://github.com/peter-gy/manim-marimo";
const site = new URL("https://peter-gy.github.io/manim-marimo/");
const description =
  "Manim animations of marimo notebook results, rendered as marimo-studio views.";

// GitHub Pages serves the site beneath the repository name. The workflow
// passes that prefix, and local builds serve from the root.
const base = process.env.BASE_PATH ? `${process.env.BASE_PATH.replace(/\/$/, "")}/` : "/";

// Code reads in ManimGL's palette, with one role per color in both themes.
const manimTheme = (
  name: string,
  type: "light" | "dark",
  ink: Record<"text" | "comment" | "keyword" | "function" | "string" | "number" | "type" | "builtin" | "property", string>,
) => ({
  name,
  type,
  colors: { "editor.background": "#00000000", "editor.foreground": ink.text },
  tokenColors: [
    { scope: "comment", settings: { foreground: ink.comment } },
    { scope: ["keyword", "storage", "keyword.operator.logical", "keyword.operator.new"], settings: { foreground: ink.keyword } },
    { scope: ["keyword.operator", "punctuation"], settings: { foreground: ink.text } },
    { scope: "punctuation.definition.comment", settings: { foreground: ink.comment } },
    { scope: ["string", "string punctuation"], settings: { foreground: ink.string } },
    // Shell arguments are unquoted strings, and read as plain text.
    { scope: "string.unquoted", settings: { foreground: ink.text } },
    { scope: ["constant.numeric", "constant.character"], settings: { foreground: ink.number } },
    { scope: ["constant.language", "support.function.builtin", "variable.language"], settings: { foreground: ink.builtin } },
    { scope: ["entity.name.function", "meta.function-call.generic", "support.function"], settings: { foreground: ink.function } },
    { scope: ["entity.name.type", "entity.name.class", "support.class", "support.type"], settings: { foreground: ink.type } },
    { scope: ["variable.other.property", "entity.other.attribute-name", "meta.attribute"], settings: { foreground: ink.property } },
    { scope: ["entity.name.tag", "markup.heading"], settings: { foreground: ink.keyword } },
    { scope: ["variable.parameter", "meta.function.parameters"], settings: { foreground: ink.text } },
  ],
});

const manimDark = manimTheme("manim-dark", "dark", {
  text: "#ececec",
  comment: "#9aa1a9",
  keyword: "#58c4dd",
  function: "#f4d345",
  string: "#a6cf8c",
  number: "#f0ac5f",
  type: "#5cd0b3",
  builtin: "#b189c6",
  property: "#9cdceb",
});

const manimLight = manimTheme("manim-light", "light", {
  text: "#16191d",
  comment: "#69717a",
  keyword: "#1c758a",
  function: "#8b4513",
  string: "#4f7a3a",
  number: "#a8561f",
  type: "#2f7f6a",
  builtin: "#644172",
  property: "#155f70",
});

// The CMU faces cover Cyrillic, IPA, and most of Unicode's math. The build
// keeps Latin, punctuation, Greek, arrows, and math operators, which cuts
// each face to a fraction of its size.
const glyphs = [
  [0x20, 0x7e],
  [0xa0, 0x17f],
  [0x2c6, 0x2dd],
  [0x391, 0x3c9],
  [0x2000, 0x206f],
  [0x2190, 0x21ff],
  [0x2200, 0x22ff],
]
  .flatMap(([start, end]) => Array.from({ length: end - start + 1 }, (_, index) => String.fromCodePoint(start + index)))
  .join("");

const subsetComputerModern = (): Plugin => ({
  name: "subset-computer-modern",
  apply: "build",
  async generateBundle(_, bundle) {
    for (const file of Object.values(bundle)) {
      if (file.type === "asset" && /\/cmu-[\w-]+\.[\w-]+\.woff2$/.test(file.fileName)) {
        file.source = await subsetFont(Buffer.from(file.source), glyphs, { targetFormat: "woff2" });
      }
    }
  },
});

export default defineConfig({
  title: "manim-marimo",
  description,
  base,
  lang: "en-US",
  appearance: "dark",
  cleanUrls: true,
  lastUpdated: true,
  sitemap: { hostname: site.href },
  head: [
    ["link", { rel: "icon", type: "image/svg+xml", href: `${base}favicon.svg` }],
    ["link", { rel: "apple-touch-icon", href: `${base}apple-touch-icon.png` }],
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:title", content: "manim-marimo" }],
    ["meta", { property: "og:description", content: description }],
    ["meta", { property: "og:image", content: new URL("brand/manim-marimo-og.png", site).href }],
    ["meta", { property: "og:image:width", content: "2400" }],
    ["meta", { property: "og:image:height", content: "1260" }],
    [
      "meta",
      {
        property: "og:image:alt",
        content: "Animate marimo notebooks with Manim: rotating vectors draw manim-marimo's mark, marimo's looped circle.",
      },
    ],
    ["meta", { name: "twitter:card", content: "summary_large_image" }],
  ],
  // Preload the faces the first screen sets: body text and code.
  transformHead({ assets }) {
    return assets
      .filter((file) => /cmu-(serif-500-roman|bright-500-roman|typewriter-text-500-roman)\.[\w-]+\.woff2$/.test(file))
      .map((href) => ["link", { rel: "preload", href, as: "font", type: "font/woff2", crossorigin: "" }]);
  },
  themeConfig: {
    logo: { light: "/brand/manim-marimo-icon-light.svg", dark: "/brand/manim-marimo-icon-dark.svg", alt: "" },
    nav: [
      { text: "Guide", link: "/guide/getting-started" },
      { text: "Examples", link: "/examples/" },
      { text: "Reference", link: "/reference/python-api" },
      { text: "marimo-studio", link: "https://marimo-team.github.io/marimo-studio/" },
    ],
    sidebar: [
      {
        text: "Guide",
        items: [
          { text: "Getting started", link: "/guide/getting-started" },
          { text: "Scenes and notebook results", link: "/guide/scenes" },
          { text: "Pages and players", link: "/guide/pages" },
          { text: "Author with agents", link: "/guide/agents" },
          { text: "Run and export", link: "/guide/run-and-export" },
          { text: "Troubleshooting", link: "/guide/troubleshooting" },
        ],
      },
      {
        text: "Examples",
        items: [
          { text: "Overview", link: "/examples/" },
          { text: "A notebook is a dataflow graph", link: "/examples/dataflow" },
          { text: "Fourier drawing", link: "/examples/fourier" },
          { text: "Convolution of dice", link: "/examples/convolution" },
          { text: "Simulating an epidemic", link: "/examples/epidemic" },
        ],
      },
      {
        text: "Reference",
        items: [
          { text: "Python API", link: "/reference/python-api" },
          { text: "View provider", link: "/reference/provider" },
        ],
      },
    ],
    outline: [2, 3],
    notFound: { title: "Page not found", linkText: "Take me home" },
    search: { provider: "local" },
    editLink: {
      pattern: `${repository}/edit/main/docs/:path`,
      text: "Edit this page on GitHub",
    },
    socialLinks: [{ icon: "github", link: repository }],
    footer: {
      message:
        'A view provider for <a href="https://marimo-team.github.io/marimo-studio/">marimo-studio</a>, rendering with <a href="https://github.com/3b1b/manim">ManimGL</a>.',
      copyright: "Apache License 2.0",
    },
  },
  markdown: {
    theme: { light: manimLight, dark: manimDark },
  },
  vite: {
    plugins: [subsetComputerModern(), llmstxt({ domain: site.origin, excludeIndexPage: false })],
  },
});
