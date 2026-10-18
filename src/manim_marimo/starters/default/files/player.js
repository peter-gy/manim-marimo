const url = (record, path) => record.files.find((file) => file.path === path)?.url;

for (const host of document.querySelectorAll("marimo-output[render]")) {
  const video = host.querySelector("video");
  const details = host.querySelector(".details");
  if (!video) continue;

  async function show(record) {
    const playing = !video.paused;
    video.poster = url(record, record.preview) ?? "";
    // Studio serves the movie with byte ranges, so the player seeks as it streams.
    video.src = url(record, record.main);
    if (playing) video.play().catch(() => {});
    const response = await fetch(url(record, "metadata.json"));
    if (response.ok && details) {
      const { width, height, fps, duration } = await response.json();
      details.textContent = `${width} × ${height} · ${fps} fps · ${duration.toFixed(1)} seconds`;
    }
  }

  host.addEventListener("marimo-output-ready", (event) => show(event.detail));
  host.addEventListener("marimo-output-updated", (event) => show(event.detail));
  if (host.marimoRender) show(host.marimoRender);

  host.querySelector(".replay")?.addEventListener("click", () => {
    video.currentTime = 0;
    video.play().catch(() => {});
  });
  host.querySelector(".loop")?.addEventListener("change", (event) => {
    video.loop = event.target.checked;
  });
  host.querySelector(".speed")?.addEventListener("change", (event) => {
    video.playbackRate = Number(event.target.value);
  });
}
