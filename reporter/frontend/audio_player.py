import html
import json

import streamlit.components.v1 as components


def render_audio_player(
    audio_url: str,
    segments: list[dict[str, str | int]],
    language: str,
    selected_date: str,
) -> None:
    """Render an audio player with a transcript synchronized to TTS timings."""
    if not segments:
        components.html(
            "<p>No timed transcript is available for this recording.</p>",
            height=80,
        )
        return

    safe_audio_url = json.dumps(audio_url).replace("<", "\\u003c")
    safe_segments = json.dumps(segments, ensure_ascii=False).replace("<", "\\u003c")
    is_german = language == "german"
    language_label = "Deutsch" if is_german else "Türkçe"
    player_title = "Nachrichten des Tages" if is_german else "Günün haberleri"
    player_subtitle = (
        "Der gesprochene Satz wird hervorgehoben"
        if is_german
        else "Cümleler sesle eşzamanlı olarak vurgulanır"
    )
    language_label = html.escape(language_label)
    player_title = html.escape(player_title)
    player_subtitle = html.escape(player_subtitle)
    date_label = html.escape(selected_date)

    player_html = """
<!doctype html>
<html lang="__HTML_LANGUAGE__">
<head>
<meta charset="utf-8">
<meta name="viewport" content="width=device-width, initial-scale=1">
<style>
  :root { color-scheme: dark; font-family: Inter, ui-sans-serif, system-ui, sans-serif; }
  * { box-sizing: border-box; }
  body { margin: 0; background: #101115; color: #f7f7f8; }
  .player { min-height: 650px; padding: 30px clamp(18px, 5vw, 64px) 24px; border: 1px solid #28292e; border-radius: 24px; background: radial-gradient(ellipse at 85% 0%, #543c7a 0, #252035 38%, #17181d 76%); display: flex; flex-direction: column; }
  header { display: flex; justify-content: space-between; align-items: center; gap: 16px; padding-bottom: 26px; }
  .brand { font-size: 12px; letter-spacing: .16em; text-transform: uppercase; color: #c7b3f1; font-weight: 700; }
  .meta { color: #c6c3cc; font-size: 13px; text-align: right; }
  h1 { margin: 0 0 5px; font-size: clamp(25px, 4vw, 38px); letter-spacing: -.04em; }
  .subtitle { color: #bbb8c2; font-size: 14px; }
  .current { min-height: 132px; display: flex; align-items: center; padding: 18px 0 20px; }
  .current p { margin: 0; max-width: 1000px; font-size: clamp(27px, 5vw, 48px); line-height: 1.12; letter-spacing: -.035em; font-weight: 750; }
  .transcript { flex: 1; min-height: 155px; max-height: 235px; overflow-y: auto; padding: 15px 18px; border-radius: 16px; background: rgb(10 10 13 / 32%); scrollbar-color: #777083 transparent; }
  .line { padding: 8px 0; color: #b8b5bf; line-height: 1.5; font-size: 16px; transition: color .2s ease, opacity .2s ease; }
  .line.active { color: #fff; font-weight: 700; }
  .controls { padding-top: 20px; }
  .seek { width: 100%; accent-color: #c4a3ff; cursor: pointer; }
  .times { display: flex; justify-content: space-between; color: #c3bfcb; font-size: 12px; margin-top: 3px; font-variant-numeric: tabular-nums; }
  .buttons { display: flex; align-items: center; justify-content: center; gap: 13px; padding-top: 13px; }
  button { border: 0; border-radius: 999px; padding: 10px 14px; color: #f4f0fa; background: rgb(255 255 255 / 12%); font-size: 13px; cursor: pointer; }
  button:hover { background: rgb(255 255 255 / 20%); }
  button:focus-visible, input:focus-visible { outline: 2px solid #d2b6ff; outline-offset: 3px; }
  #toggle { width: 58px; height: 58px; padding: 0; color: #20152f; background: #f4edff; font-size: 14px; font-weight: 800; }
  #toggle:hover { background: #e4d4ff; }
  #status { min-height: 18px; padding-top: 8px; text-align: center; color: #ffcfca; font-size: 12px; }
  @media (max-width: 560px) {
    .player { min-height: 620px; padding: 22px 17px 18px; border-radius: 18px; }
    header { padding-bottom: 15px; }
    .current { min-height: 150px; }
    .transcript { max-height: 190px; }
    .line { font-size: 15px; }
    .buttons { gap: 8px; }
    button { padding: 9px 11px; }
  }
</style>
</head>
<body>
<main class="player">
  <header>
    <div>
      <div class="brand">Daily News · Listen</div>
      <h1>__PLAYER_TITLE__</h1>
      <div class="subtitle">__PLAYER_SUBTITLE__</div>
    </div>
    <div class="meta"><div>__LANGUAGE_LABEL__</div><div>__DATE_LABEL__</div></div>
  </header>
  <section class="current" aria-live="polite" aria-atomic="true">
    <p id="current-line">Hazırlanıyor…</p>
  </section>
  <section class="transcript" id="transcript" aria-label="Timed transcript"></section>
  <section class="controls" aria-label="Audio controls">
    <input class="seek" id="seek" type="range" min="0" max="0" value="0" step="0.1" aria-label="Seek">
    <div class="times"><span id="elapsed">0:00</span><span id="duration">0:00</span></div>
    <div class="buttons">
      <button id="previous" type="button" aria-label="Previous sentence">«</button>
      <button id="back" type="button" aria-label="Back 15 seconds">−15s</button>
      <button id="toggle" type="button" aria-label="Play">PLAY</button>
      <button id="forward" type="button" aria-label="Forward 15 seconds">+15s</button>
      <button id="next" type="button" aria-label="Next sentence">»</button>
    </div>
    <div id="status" role="status"></div>
  </section>
</main>
<audio id="audio" preload="metadata"></audio>
<script>
const audioUrl = __AUDIO_URL__;
const segments = __SEGMENTS__;
const audio = document.getElementById("audio");
const seek = document.getElementById("seek");
const toggle = document.getElementById("toggle");
const transcript = document.getElementById("transcript");
const currentLine = document.getElementById("current-line");
const elapsed = document.getElementById("elapsed");
const duration = document.getElementById("duration");
const status = document.getElementById("status");
let activeIndex = -1;
let seeking = false;
const lineNodes = segments.map((segment, index) => {
  const line = document.createElement("div");
  line.className = "line";
  line.textContent = segment.text;
  line.dataset.index = String(index);
  line.addEventListener("click", () => {
    audio.currentTime = segment.start_ms / 1000;
    audio.play().catch(showPlaybackError);
  });
  transcript.appendChild(line);
  return line;
});

function formatTime(seconds) {
  if (!Number.isFinite(seconds)) return "0:00";
  const total = Math.max(0, Math.floor(seconds));
  return `${Math.floor(total / 60)}:${String(total % 60).padStart(2, "0")}`;
}

function findSegment(timeMs) {
  let low = 0;
  let high = segments.length - 1;
  while (low <= high) {
    const middle = Math.floor((low + high) / 2);
    const segment = segments[middle];
    if (timeMs < segment.start_ms) high = middle - 1;
    else if (timeMs >= segment.end_ms) low = middle + 1;
    else return middle;
  }
  return -1;
}

function updateTranscript() {
  const nextIndex = findSegment(audio.currentTime * 1000);
  if (nextIndex === activeIndex) return;
  if (activeIndex >= 0) lineNodes[activeIndex].classList.remove("active");
  activeIndex = nextIndex;
  if (activeIndex >= 0) {
    const segment = segments[activeIndex];
    lineNodes[activeIndex].classList.add("active");
    currentLine.textContent = segment.text;
    lineNodes[activeIndex].scrollIntoView({ block: "nearest", behavior: "smooth" });
  } else if (audio.currentTime === 0) {
    currentLine.textContent = segments[0].text;
  }
}

function syncControls() {
  elapsed.textContent = formatTime(audio.currentTime);
  if (Number.isFinite(audio.duration)) {
    duration.textContent = formatTime(audio.duration);
    seek.max = String(audio.duration);
    if (!seeking) seek.value = String(audio.currentTime);
  }
  updateTranscript();
}

function showPlaybackError() {
  status.textContent = "Ses başlatılamadı. Lütfen tekrar deneyin.";
}

audio.src = audioUrl;
audio.addEventListener("loadedmetadata", syncControls);
audio.addEventListener("timeupdate", syncControls);
audio.addEventListener("durationchange", syncControls);
audio.addEventListener("play", () => {
  toggle.textContent = "PAUSE";
  toggle.setAttribute("aria-label", "Pause");
  status.textContent = "";
});
audio.addEventListener("pause", () => {
  toggle.textContent = "PLAY";
  toggle.setAttribute("aria-label", "Play");
});
audio.addEventListener("ended", () => {
  toggle.textContent = "PLAY";
  toggle.setAttribute("aria-label", "Play");
});
audio.addEventListener("error", () => {
  status.textContent = "Ses yüklenemedi. Bağlantı süresi dolmuş olabilir; tarihi tekrar seçip yeniden deneyin.";
});
toggle.addEventListener("click", () => {
  if (audio.paused) audio.play().catch(showPlaybackError);
  else audio.pause();
});
seek.addEventListener("input", () => {
  seeking = true;
  audio.currentTime = Number(seek.value);
  elapsed.textContent = formatTime(audio.currentTime);
  updateTranscript();
});
seek.addEventListener("change", () => { seeking = false; });
document.getElementById("back").addEventListener("click", () => {
  audio.currentTime = Math.max(0, audio.currentTime - 15);
});
document.getElementById("forward").addEventListener("click", () => {
  audio.currentTime = Math.min(audio.duration || 0, audio.currentTime + 15);
});
document.getElementById("previous").addEventListener("click", () => {
  const index = Math.max(0, activeIndex - 1);
  audio.currentTime = segments[index].start_ms / 1000;
});
document.getElementById("next").addEventListener("click", () => {
  const index = Math.min(segments.length - 1, activeIndex + 1);
  audio.currentTime = segments[index].start_ms / 1000;
});
currentLine.textContent = segments[0].text;
</script>
</body>
</html>
"""
    player_html = (
        player_html        .replace("__HTML_LANGUAGE__", "de" if is_german else "tr")
        .replace("__LANGUAGE_LABEL__", language_label)
        .replace("__PLAYER_TITLE__", player_title)
        .replace("__PLAYER_SUBTITLE__", player_subtitle)
        .replace("__DATE_LABEL__", date_label)
        .replace("__AUDIO_URL__", safe_audio_url)
        .replace("__SEGMENTS__", safe_segments)
    )
    components.html(player_html, height=700, scrolling=False)
