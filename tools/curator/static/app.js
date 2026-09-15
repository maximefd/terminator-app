"use strict";

(() => {
  const API_HEADERS = { "Content-Type": "application/json", "X-Curator": "1" };
  const FETCH_SIZE = 30;
  const BUFFER_MIN = 10;
  const SWIPE_THRESHOLD = 80;
  const STATS_REFRESH_EVERY = 10;
  const COMBO_MILESTONES = [10, 25, 50, 100, 200, 500];
  const STORAGE = { filters: "curator-filters", badges: "curator-badges", celebrated: "curator-goal-celebrated" };
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const SUGGESTION_LABELS = {
    likely_delete: "Probablement rare",
    review: "À examiner",
    likely_keep: "Probablement courant",
    keep: "Courant",
  };
  const POS_LABELS = {
    NOM: "nom", VER: "verbe", AUX: "auxiliaire", ADJ: "adjectif", ADV: "adverbe", PRE: "préposition",
    CON: "conjonction", ONO: "onomatopée", PRO: "pronom", ART: "article",
  };

  const $ = (id) => document.getElementById(id);
  const state = {
    buffer: [],
    after: -1,
    exhausted: false,
    fetching: null,
    handled: new Set(),
    actionsSinceStats: 0,
    session: 0,
    stats: null,
  };
  let serverChain = Promise.resolve();

  // --- Utilitaires ---

  const display = (card) => card.forms[0] || card.norm.toLowerCase();
  const number = (value) => value.toLocaleString("fr-FR");
  const plural = (count, word) => `${number(count)} ${word}${count > 1 ? "s" : ""}`;
  const localDate = () => {
    const now = new Date();
    return `${now.getFullYear()}-${String(now.getMonth() + 1).padStart(2, "0")}-${String(now.getDate()).padStart(2, "0")}`;
  };

  const storage = {
    get(key, fallback) {
      try {
        const value = localStorage.getItem(key);
        return value === null ? fallback : JSON.parse(value);
      } catch {
        return fallback;
      }
    },
    set(key, value) {
      try {
        localStorage.setItem(key, JSON.stringify(value));
      } catch {
        // Stockage indisponible : sans conséquence
      }
    },
  };

  // --- Notifications : les annonces (badges, objectifs) passent avant les messages courants ---

  const announcements = [];
  let toastTimer = null;
  let announcingUntil = 0;

  function showToast(message, kind, duration) {
    const node = $("toast");
    node.textContent = message;
    node.classList.toggle("error", kind === "error");
    node.classList.toggle("announce", kind === "announce");
    node.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => {
      node.classList.remove("visible");
      if (announcements.length) setTimeout(nextAnnouncement, 250);
    }, duration);
  }

  function nextAnnouncement() {
    const message = announcements.shift();
    if (!message) return;
    announcingUntil = Date.now() + 3000;
    showToast(message, "announce", 3000);
  }

  function announce(message) {
    announcements.push(message);
    if (Date.now() >= announcingUntil) nextAnnouncement();
  }

  function toast(message, isError = false) {
    if (!isError && Date.now() < announcingUntil) return;
    showToast(message, isError ? "error" : "info", isError ? 5000 : 2200);
  }

  function celebrate() {
    if (reducedMotion) return;
    const layer = $("celebration");
    const colors = ["#2563eb", "#16a34a", "#f59e0b", "#dc2626", "#a855f7"];
    for (let i = 0; i < 40; i += 1) {
      const piece = document.createElement("span");
      piece.style.left = `${Math.random() * 100}%`;
      piece.style.background = colors[i % colors.length];
      piece.style.animationDelay = `${Math.random() * 0.4}s`;
      piece.style.setProperty("--drift", `${Math.round((Math.random() - 0.5) * 200)}px`);
      layer.append(piece);
    }
    setTimeout(() => layer.replaceChildren(), 2600);
  }

  // --- API ---

  async function api(path, options = {}) {
    const response = await fetch(path, { credentials: "same-origin", ...options });
    if (response.status === 401) {
      window.location.href = "/login";
      throw new Error("Session expirée.");
    }
    const data = await response.json().catch(() => ({}));
    if (!response.ok) throw new Error(data.error || `Erreur ${response.status}`);
    return data;
  }

  const post = (path, body) => api(path, { method: "POST", headers: API_HEADERS, body: JSON.stringify(body || {}) });

  // Les écritures partent dans l'ordre : une annulation ne passe jamais avant la décision qu'elle annule.
  function enqueue(task) {
    const run = serverChain.then(task);
    serverChain = run.catch(() => {});
    return run;
  }

  // --- Filtres ---

  function filters() {
    const [min, max] = $("filter-length").value.split("-").map(Number);
    return { min, max, suggestion: $("filter-suggestion").value };
  }

  function restoreFilters() {
    const saved = storage.get(STORAGE.filters, {});
    if (saved.length) $("filter-length").value = saved.length;
    if (saved.suggestion !== undefined) $("filter-suggestion").value = saved.suggestion;
  }

  function onFiltersChange() {
    storage.set(STORAGE.filters, { length: $("filter-length").value, suggestion: $("filter-suggestion").value });
    state.buffer = [];
    state.after = -1;
    state.exhausted = false;
    render();
    renderStats();
  }

  // --- File de mots ---

  function fillBuffer() {
    if (state.fetching || state.exhausted) return state.fetching || Promise.resolve();
    const { min, max, suggestion } = filters();
    const params = new URLSearchParams({ after: state.after, limit: FETCH_SIZE, min_length: min, max_length: max });
    if (suggestion) params.set("suggestion", suggestion);
    state.fetching = api(`/api/queue?${params}`)
      .then((data) => {
        state.after = data.next_after;
        const known = new Set(state.buffer.map((card) => card.norm));
        state.buffer.push(...data.cards.filter((card) => !state.handled.has(card.norm) && !known.has(card.norm)));
        if (data.cards.length === 0) state.exhausted = true;
      })
      .catch((error) => toast(error.message, true))
      .finally(() => { state.fetching = null; });
    return state.fetching;
  }

  // --- Carte ---

  function frequencyLabel(zipf) {
    if (zipf === 0) return "absent des corpus";
    if (zipf < 2) return "très rare";
    if (zipf < 3) return "rare";
    if (zipf < 4) return "courant";
    return "très courant";
  }

  function render() {
    const card = state.buffer[0];
    $("card").hidden = !card;
    $("loading").hidden = Boolean(card) || state.exhausted;
    $("empty").hidden = Boolean(card) || !state.exhausted;
    for (const id of ["btn-delete", "btn-keep", "btn-skip", "btn-family"]) $(id).disabled = !card;

    if (!card) {
      if (!state.exhausted) fillBuffer().then(() => { if (state.buffer.length || state.exhausted) render(); });
      return;
    }

    $("card-word").textContent = display(card);
    $("card-forms").textContent = card.forms.length > 1 ? `Aussi : ${card.forms.slice(1).join(", ")}` : "";
    $("card-length").textContent = `${card.length} lettres · ${card.norm}`;
    const badge = $("card-suggestion");
    badge.textContent = SUGGESTION_LABELS[card.suggestion] || card.suggestion;
    badge.dataset.suggestion = card.suggestion;

    const definition = $("card-definition");
    if (card.definition) {
      definition.textContent = card.definition_kind === "inflection" ? `Forme fléchie · ${card.definition}` : card.definition;
      definition.classList.remove("missing");
    } else {
      definition.textContent = "Aucune définition trouvée dans le Wiktionnaire.";
      definition.classList.add("missing");
    }

    $("card-freq-bar").style.width = `${Math.min(card.zipf / 7, 1) * 100}%`;
    $("card-freq-label").textContent = `${frequencyLabel(card.zipf)} (${card.zipf.toFixed(1)})`;
    const pos = card.pos ? card.pos.split(":")[0] : null;
    $("card-pos").textContent = pos ? (POS_LABELS[pos] || card.pos) : "—";
    $("card-lemma").textContent = card.lemma || "—";

    const familySize = card.family_size || 0;
    $("family-count").textContent = familySize > 1 ? `(${familySize} mots)` : "";
    $("btn-family").disabled = familySize <= 1;

    if (state.buffer.length < BUFFER_MIN) fillBuffer();
  }

  // --- Progression ---

  const bandLabel = (length) => (length <= 5 ? "2-5" : length <= 8 ? "6-8" : length <= 11 ? "9-11" : "12+");
  const BANDS = { "2-5": [2, 5], "6-8": [6, 8], "9-11": [9, 11], "12+": [12, 99] };

  function renderStats() {
    const stats = state.stats;
    if (!stats) return;

    $("stat-today").textContent = number(stats.today);
    $("goal").textContent = number(stats.daily_goal);
    $("goal-bar").style.width = `${Math.min(stats.today / stats.daily_goal, 1) * 100}%`;
    $("goal-section").classList.toggle("reached", stats.today >= stats.daily_goal);

    $("stat-streak").textContent = stats.streak_days;
    const atRisk = stats.today === 0 && stats.streak_days > 0;
    $("streak-risk").hidden = !atRisk;
    if (atRisk) {
      $("streak-risk").textContent = `🔥 Triez un mot aujourd'hui pour prolonger votre série de ${plural(stats.streak_days, "jour")}.`;
    }

    const { level } = stats;
    $("level-number").textContent = level.number;
    $("level-title").textContent = level.title;
    const progress = (stats.total_decided - level.current) / (level.next - level.current);
    $("xp-bar").style.width = `${Math.min(Math.max(progress, 0), 1) * 100}%`;

    const unlocked = stats.achievements.filter((a) => a.unlocked).length;
    $("stat-badges").textContent = unlocked;

    const { min, max } = filters();
    const remaining = Object.entries(stats.remaining_by_length)
      .filter(([label]) => BANDS[label] && BANDS[label][0] >= min && BANDS[label][1] <= max)
      .reduce((total, [, count]) => total + count, 0);
    $("stat-remaining").textContent = number(Math.max(remaining, 0));

    if ($("profile-dialog").open) renderProfile();
  }

  function renderProfile() {
    const stats = state.stats;
    if (!stats) return;
    const { level } = stats;
    $("profile-level").textContent = `Niveau ${level.number} · ${level.title}`;
    const left = Math.max(level.next - stats.total_decided, 0);
    $("profile-xp").textContent = `Encore ${plural(left, "mot")} avant le niveau ${level.number + 1}`;
    $("best-streak").textContent = `${plural(stats.best_streak, "jour")}`;
    $("best-day").textContent = plural(stats.best_day, "mot");
    $("total-decided").textContent = number(stats.total_decided);

    const peak = Math.max(1, stats.daily_goal, ...stats.week.map((day) => day.count));
    $("week").replaceChildren(...stats.week.map((day) => {
      const column = document.createElement("div");
      column.className = "day";
      column.title = `${new Date(`${day.date}T12:00:00`).toLocaleDateString("fr-FR", { weekday: "long", day: "numeric", month: "long" })} : ${plural(day.count, "mot")}`;
      const bar = document.createElement("span");
      bar.className = day.count >= stats.daily_goal ? "bar goal-met" : "bar";
      bar.style.height = `${Math.round((day.count / peak) * 100)}%`;
      const label = document.createElement("small");
      label.textContent = new Date(`${day.date}T12:00:00`).toLocaleDateString("fr-FR", { weekday: "narrow" });
      column.append(bar, label);
      return column;
    }));

    const unlocked = stats.achievements.filter((a) => a.unlocked).length;
    $("badge-count").textContent = `${unlocked}/${stats.achievements.length}`;
    $("badges").replaceChildren(...stats.achievements.map((achievement) => {
      const item = document.createElement("li");
      item.className = achievement.unlocked ? "unlocked" : "locked";
      const icon = document.createElement("span");
      icon.className = "badge-icon";
      icon.textContent = achievement.unlocked ? achievement.icon : "🔒";
      const text = document.createElement("span");
      const name = document.createElement("strong");
      name.textContent = achievement.name;
      const description = document.createElement("small");
      description.textContent = achievement.description;
      text.append(name, description);
      item.append(icon, text);
      return item;
    }));
  }

  function announceNewBadges(achievements) {
    const unlocked = achievements.filter((a) => a.unlocked).map((a) => a.id);
    const known = storage.get(STORAGE.badges, null);
    if (known === null) {
      // Premier passage sur cet appareil : on n'annonce pas les badges déjà obtenus
      storage.set(STORAGE.badges, unlocked);
      return;
    }
    const fresh = achievements.filter((a) => a.unlocked && !known.includes(a.id));
    if (!fresh.length) return;
    fresh.forEach((a) => announce(`${a.icon} Nouveau badge : ${a.name}`));
    storage.set(STORAGE.badges, [...new Set([...known, ...unlocked])]);
    celebrate();
  }

  function refreshStats() {
    state.actionsSinceStats = 0;
    return api("/api/stats")
      .then((stats) => {
        const previous = state.stats;
        state.stats = stats;
        if (previous && stats.level.number > previous.level.number) {
          announce(`⬆️ Niveau ${stats.level.number} : ${stats.level.title}`);
          celebrate();
        }
        announceNewBadges(stats.achievements);
        renderStats();
      })
      .catch(() => {});
  }

  // Met à jour la progression tout de suite ; le serveur fait foi et la recalcule régulièrement.
  // `words` : formes normalisées (leur longueur est celle du mot) ; `sign` : +1 décision, -1 annulation.
  // `refresh` : recalculer tout de suite côté serveur (ex. suppression par famille, qui peut débloquer un badge).
  function counted(words, sign, refresh = false) {
    const stats = state.stats;
    let refreshNow = refresh;
    if (stats) {
      const before = { today: stats.today, total: stats.total_decided, session: state.session };
      const delta = sign * words.length;
      stats.today = Math.max(0, stats.today + delta);
      stats.total_decided = Math.max(0, stats.total_decided + delta);
      stats.week[stats.week.length - 1].count = Math.max(0, stats.week[stats.week.length - 1].count + delta);
      for (const word of words) {
        const label = bandLabel(word.length);
        if (label in stats.remaining_by_length) stats.remaining_by_length[label] -= sign;
      }
      state.session = Math.max(0, state.session + delta);

      if (sign > 0) {
        // Une seule annonce, pour le palier le plus haut franchi (une famille peut en franchir plusieurs)
        const reached = COMBO_MILESTONES.filter((m) => before.session < m && state.session >= m).pop();
        if (reached) announce(`🔥 ${reached} mots d'affilée !`);
        if (before.today < stats.daily_goal && stats.today >= stats.daily_goal && storage.get(STORAGE.celebrated) !== localDate()) {
          storage.set(STORAGE.celebrated, localDate());
          announce("🎯 Objectif du jour atteint, bravo !");
          celebrate();
        }
        // Premier mot du jour (la série avance) ou passage de niveau : on recalcule tout de suite
        refreshNow = refreshNow || before.today === 0 || stats.total_decided >= stats.level.next;
      }
      renderStats();
    }
    state.actionsSinceStats += 1;
    if (refreshNow || state.actionsSinceStats >= STATS_REFRESH_EVERY) serverChain.then(refreshStats);
  }

  // --- Actions ---

  function decide(decision) {
    const card = state.buffer.shift();
    if (!card) return;
    state.handled.add(card.norm);
    counted([card.norm], 1);
    render();
    enqueue(() => post("/api/decisions", { words: [card.norm], decision }))
      .then(() => toast(decision === "delete" ? `« ${display(card)} » supprimé` : `« ${display(card)} » gardé`))
      .catch((error) => {
        state.handled.delete(card.norm);
        state.buffer.unshift(card);
        counted([card.norm], -1);
        render();
        toast(error.message, true);
      });
  }

  function skip() {
    const card = state.buffer.shift();
    if (!card) return;
    state.buffer.push(card);
    render();
  }

  function deleteFamily() {
    const card = state.buffer[0];
    if (!card || (card.family_size || 0) <= 1) return;
    enqueue(() => post("/api/decisions/family", { word: card.norm }))
      .then((data) => {
        const removed = new Set(data.words);
        data.words.forEach((word) => state.handled.add(word));
        state.buffer = state.buffer.filter((item) => !removed.has(item.norm));
        counted(data.words, 1, true);
        render();
        toast(`${data.words.length} mots de la famille « ${card.lemma || display(card)} » supprimés · ↓ pour annuler`);
      })
      .catch((error) => toast(error.message, true));
  }

  function undo() {
    enqueue(() => post("/api/undo"))
      .then((data) => {
        if (!data.words.length) {
          toast("Rien à annuler");
          return;
        }
        const restored = new Set(data.words);
        data.words.forEach((word) => state.handled.delete(word));
        state.buffer = [...data.cards, ...state.buffer.filter((item) => !restored.has(item.norm))];
        counted(data.words, -1);
        render();
        toast(`Annulé : ${data.cards.map(display).join(", ")}`);
      })
      .catch((error) => toast(error.message, true));
  }

  // --- Clavier (AZERTY : flèches, Retour arrière, Maj) ---

  document.addEventListener("keydown", (event) => {
    if ($("profile-dialog").open || event.target.closest("select, input, textarea")) return;
    const handlers = {
      ArrowLeft: () => (event.shiftKey ? deleteFamily() : decide("delete")),
      ArrowRight: () => decide("keep"),
      ArrowDown: undo,
      Backspace: undo,
      ArrowUp: skip,
    };
    const handler = handlers[event.key];
    if (!handler) return;
    event.preventDefault();
    if (event.repeat) return; // une touche maintenue ne décide qu'une fois
    handler();
  });

  // --- Glisser sur téléphone ---

  const cardNode = $("card");
  let drag = null;

  cardNode.addEventListener("pointerdown", (event) => {
    if (event.pointerType === "mouse" && event.button !== 0) return;
    drag = { x: event.clientX, id: event.pointerId };
    cardNode.setPointerCapture(event.pointerId);
    cardNode.classList.add("dragging");
  });

  cardNode.addEventListener("pointermove", (event) => {
    if (!drag || event.pointerId !== drag.id) return;
    const dx = event.clientX - drag.x;
    cardNode.style.transform = `translateX(${dx}px) rotate(${dx / 25}deg)`;
    cardNode.dataset.intent = dx > SWIPE_THRESHOLD ? "keep" : dx < -SWIPE_THRESHOLD ? "delete" : "";
  });

  function endDrag(event, allowDecision) {
    if (!drag || event.pointerId !== drag.id) return;
    const dx = event.clientX - drag.x;
    drag = null;
    cardNode.classList.remove("dragging");
    cardNode.style.transform = "";
    cardNode.dataset.intent = "";
    if (!allowDecision) return;
    if (dx > SWIPE_THRESHOLD) decide("keep");
    else if (dx < -SWIPE_THRESHOLD) decide("delete");
  }

  cardNode.addEventListener("pointerup", (event) => endDrag(event, true));
  cardNode.addEventListener("pointercancel", (event) => endDrag(event, false));

  // --- Boutons et démarrage ---

  $("btn-delete").addEventListener("click", () => decide("delete"));
  $("btn-keep").addEventListener("click", () => decide("keep"));
  $("btn-skip").addEventListener("click", skip);
  $("btn-undo").addEventListener("click", undo);
  $("btn-family").addEventListener("click", deleteFamily);
  $("btn-profile").addEventListener("click", () => {
    renderProfile();
    $("profile-dialog").showModal();
  });
  // Un appui en dehors de la fenêtre (sur le fond assombri) la ferme
  $("profile-dialog").addEventListener("click", (event) => {
    if (event.target === $("profile-dialog")) $("profile-dialog").close();
  });
  $("filter-length").addEventListener("change", onFiltersChange);
  $("filter-suggestion").addEventListener("change", onFiltersChange);

  restoreFilters();
  render();
  refreshStats();
})();
