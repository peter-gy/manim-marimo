import type { Theme } from "vitepress";
import DefaultTheme from "vitepress/theme-without-fonts";
import { h } from "vue";

import FourierHero from "./components/FourierHero.vue";
import ManimExample from "./components/ManimExample.vue";
import "./fonts.css";
import "./custom.css";

export default {
  extends: DefaultTheme,
  Layout: () => h(DefaultTheme.Layout, null, { "home-hero-image": () => h(FourierHero) }),
  enhanceApp({ app }) {
    app.component("ManimExample", ManimExample);
  },
} satisfies Theme;
