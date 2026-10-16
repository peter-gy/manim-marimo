import { defineConfig } from "vitepress";
import llmstxt from "vitepress-plugin-llms";

const repository = "https://github.com/peter-gy/marimo-manim";
const site = new URL("https://peter-gy.github.io/marimo-manim/");
const description =
  "Manim animations of marimo notebook results, rendered as marimo-studio views.";

// GitHub Pages serves the site beneath the repository name. The workflow
// passes that prefix, and local builds serve from the root.
const base = process.env.BASE_PATH ? `${process.env.BASE_PATH.replace(/\/$/, "")}/` : "/";

export default defineConfig({
  title: "marimo-manim",
  description,
  base,
  lang: "en-US",
  cleanUrls: true,
  lastUpdated: true,
  sitemap: { hostname: site.href },
  head: [
    ["link", { rel: "icon", type: "image/svg+xml", href: `${base}logo.svg` }],
    ["meta", { property: "og:type", content: "website" }],
    ["meta", { property: "og:title", content: "marimo-manim" }],
    ["meta", { property: "og:description", content: description }],
    ["meta", { property: "og:image", content: new URL("media/fourier.png", site).href }],
  ],
  themeConfig: {
    logo: "/logo.svg",
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
          { text: "Fourier drawing", link: "/examples/fourier" },
          { text: "Convolution of dice", link: "/examples/convolution" },
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
  vite: {
    plugins: [llmstxt({ domain: site.origin, excludeIndexPage: false })],
  },
});
