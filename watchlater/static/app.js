const $ = (selector) => document.querySelector(selector);
let selectedVideo = null;

async function json(url, options) {
  const response = await fetch(url, options);
  if (!response.ok) {
    let detail = "";
    try {
      const body = await response.json();
      detail = body.detail ? `: ${body.detail}` : "";
    } catch (_) {}
    throw new Error(`The local service could not load this data${detail}`);
  }
  return response.json();
}

function escapeHtml(value) {
  const node = document.createElement("div");
  node.textContent = value;
  return node.innerHTML;
}

async function loadStats() {
  try {
    const stats = await json("/api/stats");
    $("#pending").textContent = stats.pending;
    $("#completed").textContent = stats.completed;
    $("#hours").textContent = (stats.pending_minutes / 60).toFixed(1);
  } catch (_) {
    $("#pending").textContent = "—";
    $("#completed").textContent = "—";
    $("#hours").textContent = "—";
  }
}

async function complete(videoId) {
  await json(`/api/videos/${encodeURIComponent(videoId)}/complete`, {method: "POST"});
  if (selectedVideo?.video_id === videoId) clearPlayer();
  await Promise.all([loadStats(), loadQueue()]);
}

function clearPlayer() {
  selectedVideo = null;
  $("#video-player").src = "";
  $("#video-player").hidden = true;
  $("#player-placeholder").hidden = false;
  $("#now-playing").hidden = true;
}

function selectVideo(item) {
  selectedVideo = item;
  const params = new URLSearchParams({
    autoplay: "1",
    rel: "0",
    modestbranding: "1",
    playsinline: "1",
  });
  $("#video-player").src =
    `https://www.youtube-nocookie.com/embed/${encodeURIComponent(item.video_id)}?${params}`;
  $("#video-player").hidden = false;
  $("#player-placeholder").hidden = true;
  $("#now-playing").hidden = false;
  $("#playing-title").textContent = item.title;
  $("#playing-meta").textContent =
    `${item.channel} · ${item.duration_minutes} min · ${item.category}`;
  $("#viewer").scrollIntoView({behavior: "smooth", block: "center"});
}

async function loadQueue() {
  const minutes = Math.max(1, Number($("#minutes").value) || 25);
  const list = $("#video-list");
  list.innerHTML = '<div class="empty">Building your focused queue…</div>';
  let items;
  try {
    items = await json(`/api/recommendations?minutes=${minutes}&limit=6`);
  } catch (error) {
    list.innerHTML = `
      <div class="empty">
        <strong>We couldn’t build your queue.</strong>
        <p>${escapeHtml(error.message)}. Your videos are still safe.</p>
        <button id="retry-queue">Try again</button>
      </div>`;
    $("#retry-queue").addEventListener("click", loadQueue);
    return;
  }
  if (!items.length) {
    list.innerHTML = '<div class="empty">Your learning inbox is clear.</div>';
    return;
  }
  list.innerHTML = items.map((item, index) => `
    <article class="video">
      <div class="rank">0${index + 1}</div>
      <div>
        <h3>${escapeHtml(item.title)}</h3>
        <div class="meta">${escapeHtml(item.channel)} · ${item.duration_minutes} min · ${escapeHtml(item.category)}</div>
        <div class="reasons">${item.reasons.map(reason => `<span class="pill">${escapeHtml(reason)}</span>`).join("")}</div>
      </div>
      <div class="score">
        <strong>${Math.round(item.score * 100)}</strong><small>MATCH</small>
        <button class="secondary" data-watch="${escapeHtml(item.video_id)}">Watch here</button>
      </div>
    </article>`).join("");
  list.querySelectorAll("[data-watch]").forEach(button => {
    button.addEventListener("click", () => {
      const item = items.find(video => video.video_id === button.dataset.watch);
      if (item) selectVideo(item);
    });
  });
}

$("#refresh").addEventListener("click", loadQueue);
$("#finish-video").addEventListener("click", () => {
  if (selectedVideo) complete(selectedVideo.video_id);
});
Promise.allSettled([loadStats(), loadQueue()]);
