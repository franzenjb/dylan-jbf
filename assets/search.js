(function () {
  const DATA = new URL("index.json", document.querySelector('script[src*="search.js"]').src).href;
  let index = null;

  function norm(s) { return (s || "").toString().toLowerCase(); }

  function score(item, q) {
    const hay = norm([item.text, item.song, item.title, item.album, item.name, item.year, (item.tags || []).join(" ")].join(" "));
    if (!q) return 0;
    if (hay.includes(q)) return q.length + (norm(item.text || item.title || item.name).startsWith(q) ? 5 : 0);
    return q.split(/\s+/).every((p) => hay.includes(p)) ? q.length - 1 : -1;
  }

  function rel(path) {
    const here = location.pathname;
    if (here.endsWith("/") && here !== "/") return "../" + path;
    if (/\/(quotes|songs|albums|subjects)\//.test(here)) return "../" + path;
    return path;
  }

  async function load() {
    if (index) return index;
    const r = await fetch(DATA);
    index = await r.json();
    return index;
  }

  function render(q, mount, status) {
    const data = index;
    q = norm(q).trim();
    if (!q) {
      if (status) status.textContent = "Type a word, a song, a year, or a subject.";
      mount.innerHTML = "";
      return;
    }
    const quotes = data.quotes.map((x) => ({ ...x, _s: score(x, q), kind: "quote" })).filter((x) => x._s >= 0);
    const songs = data.songs.map((x) => ({ ...x, _s: score(x, q), kind: "song" })).filter((x) => x._s >= 0);
    const subjects = data.subjects.map((x) => ({ ...x, _s: score(x, q), kind: "subject" })).filter((x) => x._s >= 0);
    quotes.sort((a, b) => b._s - a._s);
    songs.sort((a, b) => b._s - a._s || b.n - a.n);
    subjects.sort((a, b) => b._s - a._s);
    const n = quotes.length + songs.length + subjects.length;
    if (status) status.textContent = n ? `${n} matches for “${q}”.` : `No matches for “${q}”.`;
    let html = "";
    quotes.slice(0, 40).forEach((x) => {
      html += `<article class="search-hit"><p class="qtext"><a href="${rel("quotes/" + x.id + ".html")}">${escapeHtml(x.text)}</a></p><p class="meta"><a href="${rel("songs/" + x.song_slug + ".html")}">${escapeHtml(x.song)}</a> · ${escapeHtml(x.album || "")} ${x.year || ""}</p></article>`;
    });
    songs.slice(0, 20).forEach((x) => {
      html += `<article class="search-hit"><p><a href="${rel("songs/" + x.slug + ".html")}">${escapeHtml(x.title)}</a></p><p class="meta">${escapeHtml(x.album || "")} ${x.year || ""} ${x.n ? " · " + x.n + " cited" : ""}</p></article>`;
    });
    subjects.slice(0, 12).forEach((x) => {
      html += `<article class="search-hit"><p><a href="${rel("subjects/" + x.slug + ".html")}">${escapeHtml(x.name)}</a> <span class="meta">${x.n} lines</span></p></article>`;
    });
    mount.innerHTML = html;
  }

  function escapeHtml(s) {
    return (s || "").replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c]));
  }

  function wireHeader() {
    document.querySelectorAll(".site-head .find").forEach((form) => {
      const input = form.querySelector("input");
      form.addEventListener("submit", (e) => {
        e.preventDefault();
        const dest = new URL(rel("search.html"), location.href);
        dest.searchParams.set("q", input.value.trim());
        location.href = dest.toString();
      });
    });
  }

  window.DylanSearch = {
    async page() {
      await load();
      const params = new URLSearchParams(location.search);
      const q = params.get("q") || "";
      const input = document.querySelector(".site-head input[type=search]");
      if (input && q) input.value = q;
      const mount = document.getElementById("search-results");
      const status = document.getElementById("search-status");
      render(q, mount, status);
      if (input) {
        input.addEventListener("input", () => {
          const dest = new URL(location.href);
          if (input.value.trim()) dest.searchParams.set("q", input.value.trim());
          else dest.searchParams.delete("q");
          history.replaceState(null, "", dest);
          render(input.value, mount, status);
        });
        input.focus();
      }
    },
  };

  document.addEventListener("DOMContentLoaded", wireHeader);
})();
