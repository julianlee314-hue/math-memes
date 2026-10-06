/* Mathera Memes Wall */
(function () {
  const LS_KEY = "math-memes-v1";
  const gallery = document.getElementById("gallery");
  const empty = document.getElementById("empty");
  const qInput = document.getElementById("q");
  const nsfwToggle = document.getElementById("show-nsfw");
  const favsOnly = document.getElementById("favs-only");
  const chips = document.getElementById("chips");
  const statShown = document.getElementById("stat-shown");
  const statTotal = document.getElementById("stat-total");
  const dialog = document.getElementById("lightbox");
  const lbImg = document.getElementById("lb-img");
  const lbTitle = document.getElementById("lb-title");
  const lbCredit = document.getElementById("lb-credit");
  const lbReddit = document.getElementById("lb-reddit");
  const lbFav = document.getElementById("lb-fav");

  let memes = [];
  let view = [];
  let idx = 0;
  let activeTag = "";

  function loadFavs() {
    try {
      const raw = localStorage.getItem(LS_KEY);
      const data = raw ? JSON.parse(raw) : {};
      return new Set(data.favourites || []);
    } catch {
      return new Set();
    }
  }
  function saveFavs(set) {
    localStorage.setItem(LS_KEY, JSON.stringify({ favourites: [...set] }));
  }
  let favs = loadFavs();

  function fmtScore(n) {
    if (n >= 1000) return (n / 1000).toFixed(n >= 10000 ? 0 : 1).replace(/\.0$/, "") + "k";
    return String(n);
  }

  function permalink(m) {
    if (m.credit && m.credit.permalink) {
      const p = m.credit.permalink;
      return p.startsWith("http") ? p : "https://www.reddit.com" + p;
    }
    return "https://www.reddit.com/r/mathmemes/comments/" + m.id + "/";
  }

  function renderChips(tags) {
    chips.innerHTML = "";
    const all = document.createElement("button");
    all.type = "button";
    all.className = "chip";
    all.textContent = "All";
    all.setAttribute("aria-pressed", activeTag ? "false" : "true");
    all.addEventListener("click", () => {
      activeTag = "";
      apply();
      renderChips(tags);
    });
    chips.appendChild(all);
    tags.slice(0, 12).forEach((t) => {
      const b = document.createElement("button");
      b.type = "button";
      b.className = "chip";
      b.textContent = t;
      b.setAttribute("aria-pressed", activeTag === t ? "true" : "false");
      b.addEventListener("click", () => {
        activeTag = activeTag === t ? "" : t;
        apply();
        renderChips(tags);
      });
      chips.appendChild(b);
    });
  }

  function tile(m) {
    const a = document.createElement("a");
    a.className = "meme-tile" + (m.nsfw ? " nsfw" : "");
    a.href = "#" + m.id;
    a.dataset.id = m.id;
    const isPersonal = m.source === "personal" || (m.tags || []).includes("personal") || m.score == null;
    const scoreHtml = isPersonal
      ? '<span class="score personal-badge" title="Personal upload">personal</span>'
      : '<span class="score" title="Reddit score">▲ ' + fmtScore(m.score || 0) + "</span>";
    a.innerHTML =
      scoreHtml +
      '<button type="button" class="fav" aria-label="Favourite" aria-pressed="' +
      (favs.has(m.id) ? "true" : "false") +
      '">' +
      (favs.has(m.id) ? "★" : "☆") +
      "</button>" +
      "<figure><img src=\"" +
      (m.thumb || m.image) +
      '" alt="' +
      escapeAttr(m.alt || m.title) +
      '" loading="lazy" width="' +
      (m.w || "") +
      '" height="' +
      (m.h || "") +
      '" /></figure>' +
      '<div class="tile-body"><h2>' +
      escapeHtml(m.title) +
      '</h2><p class="meta"><span>' +
      (isPersonal
        ? escapeHtml((m.credit && m.credit.author) || "Julius (personal)")
        : "u/" + escapeHtml((m.credit && m.credit.author) || "unknown")) +
      "</span>" +
      (m.nsfw ? "<span>NSFW</span>" : "") +
      "</p></div>" +
      (m.nsfw ? '<span class="nsfw-badge">NSFW</span>' : "");
    a.querySelector(".fav").addEventListener("click", (e) => {
      e.preventDefault();
      e.stopPropagation();
      if (favs.has(m.id)) favs.delete(m.id);
      else favs.add(m.id);
      saveFavs(favs);
      apply();
    });
    a.addEventListener("click", (e) => {
      if (e.target.closest(".fav")) return;
      e.preventDefault();
      openAt(view.findIndex((x) => x.id === m.id));
    });
    return a;
  }

  function escapeHtml(s) {
    return String(s || "")
      .replace(/&/g, "&amp;")
      .replace(/</g, "&lt;")
      .replace(/>/g, "&gt;");
  }
  function escapeAttr(s) {
    return escapeHtml(s).replace(/"/g, "&quot;");
  }

  function apply() {
    const q = (qInput.value || "").trim().toLowerCase();
    const showNsfw = nsfwToggle.checked;
    const onlyFav = favsOnly.checked;
    view = memes.filter((m) => {
      if (!showNsfw && m.nsfw) return false;
      if (onlyFav && !favs.has(m.id)) return false;
      if (activeTag && !(m.tags || []).includes(activeTag)) return false;
      if (!q) return true;
      const hay = (
        m.title +
        " " +
        ((m.credit && m.credit.author) || "") +
        " " +
        (m.tags || []).join(" ")
      ).toLowerCase();
      return hay.includes(q);
    });
    gallery.innerHTML = "";
    view.forEach((m) => gallery.appendChild(tile(m)));
    empty.classList.toggle("hidden", view.length > 0);
    statShown.textContent = String(view.length);
    statTotal.textContent = String(memes.length);
  }

  function openAt(i) {
    if (i < 0 || i >= view.length) return;
    idx = i;
    const m = view[idx];
    lbImg.src = m.image;
    lbImg.alt = m.alt || m.title;
    lbTitle.textContent = m.title;
    const isPersonal = m.source === "personal" || (m.tags || []).includes("personal") || m.score == null;
    lbCredit.innerHTML = isPersonal
      ? "Personal upload · " + escapeHtml((m.credit && m.credit.author) || "Julius") +
        (m.nsfw ? " · <strong>NSFW</strong>" : "")
      : "▲ " +
        fmtScore(m.score || 0) +
        " · u/" +
        escapeHtml((m.credit && m.credit.author) || "unknown") +
        (m.nsfw ? " · <strong>NSFW</strong>" : "");
    if (isPersonal) {
      lbReddit.style.display = "none";
    } else {
      lbReddit.style.display = "";
      lbReddit.href = permalink(m);
    }
    lbFav.textContent = favs.has(m.id) ? "Unfavourite" : "Favourite";
    history.replaceState(null, "", "#" + m.id);
    if (!dialog.open) dialog.showModal();
  }

  function closeLb() {
    dialog.close();
    history.replaceState(null, "", location.pathname + location.search);
  }

  document.getElementById("lb-close").addEventListener("click", closeLb);
  document.getElementById("lb-close2").addEventListener("click", closeLb);
  document.getElementById("lb-prev").addEventListener("click", () => openAt(idx - 1));
  document.getElementById("lb-next").addEventListener("click", () => openAt(idx + 1));
  lbFav.addEventListener("click", () => {
    const m = view[idx];
    if (!m) return;
    if (favs.has(m.id)) favs.delete(m.id);
    else favs.add(m.id);
    saveFavs(favs);
    lbFav.textContent = favs.has(m.id) ? "Unfavourite" : "Favourite";
    apply();
  });
  dialog.addEventListener("click", (e) => {
    if (e.target === dialog) closeLb();
  });
  window.addEventListener("keydown", (e) => {
    if (!dialog.open) return;
    if (e.key === "Escape") closeLb();
    if (e.key === "ArrowLeft") openAt(idx - 1);
    if (e.key === "ArrowRight") openAt(idx + 1);
  });

  qInput.addEventListener("input", apply);
  nsfwToggle.addEventListener("change", apply);
  favsOnly.addEventListener("change", apply);

  fetch("data/memes.json")
    .then((r) => r.json())
    .then((data) => {
      memes = (Array.isArray(data) ? data : data.memes || []).slice();
      memes.sort((a, b) => {
        const sa = a.score == null ? -1 : a.score;
        const sb = b.score == null ? -1 : b.score;
        if (sb !== sa) return sb - sa;
        return String(a.id).localeCompare(String(b.id));
      });
      const tagCount = {};
      memes.forEach((m) =>
        (m.tags || []).forEach((t) => {
          tagCount[t] = (tagCount[t] || 0) + 1;
        })
      );
      const tags = Object.keys(tagCount).sort((a, b) => tagCount[b] - tagCount[a]);
      renderChips(tags);
      apply();
      const hash = location.hash.replace(/^#/, "");
      if (hash) {
        const i = view.findIndex((m) => m.id === hash);
        if (i >= 0) openAt(i);
        else {
          const j = memes.findIndex((m) => m.id === hash);
          if (j >= 0 && memes[j].nsfw) {
            nsfwToggle.checked = true;
            apply();
            const k = view.findIndex((m) => m.id === hash);
            if (k >= 0) openAt(k);
          }
        }
      }
    })
    .catch((err) => {
      empty.textContent = "Could not load data/memes.json: " + err;
      empty.classList.remove("hidden");
    });
})();
