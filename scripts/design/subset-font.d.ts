declare module "subset-font" {
  export default function subsetFont(
    source: Uint8Array,
    text: string,
    options?: { targetFormat?: "sfnt" | "truetype" | "woff" | "woff2"; preserveNameIds?: number[] },
  ): Promise<Uint8Array>;
}
