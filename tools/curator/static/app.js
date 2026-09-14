"use strict";

(() => {
  const API_HEADERS = { "Content-Type": "application/json", "X-Curator": "1" };
  const FETCH_SIZE = 30;
  const BUFFER_MIN = 10;
  const SWIPE_THRESHOLD = 80;
  const STATS_REFRESH_EVERY = 20;

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
    stats: null,
  };
  let serverChain = Promise.resolve();

  // --- Utilitaires ---

  const display = (card) => card.forms[0] || card.norm.toLowerCase();

  function toast(message, isError = false) {
    const node = $("toast");
    node.textContent = message;
    node.classList.toggle("error", isError);
    node.classList.add("visible");
    clearTimeout(toast.timer);
    toast.timer = setTimeout(() => node.classList.remove("visible"), isError ? 5000 : 2500);
  }

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
    try {
      const saved = JSON.parse(localStorage.getItem("curator-filters") || "{}");
      if (saved.length) $("filter-length").value = saved.length;
      if (saved.suggestion !== undefined) $("filter-suggestion").value = saved.suggestion;
    } catch {
      // Pas de stockage local : filtres par défaut
    }
  }

  function onFiltersChange() {
    try {
      localStorage.setItem("curator-filters", JSON.stringify({
        length: $("filter-length").value, suggestion: $("filter-suggestion").value,
      }));
    } catch {
      // Ignoré
    }
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

  // --- Affichage ---

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
      if (!state.exhausted) fillBuffer().then(() => { if (state.buffer.length) render(); else if (state.exhausted) render(); });
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

  function renderStats() {
    const stats = state.stats;
    if (!stats) return;
    $("stat-today").textContent = stats.today;
    $("stat-streak").textContent = stats.streak_days;
    const { min, max } = filters();
    const bands = { "2-5": [2, 5], "6-8": [6, 8], "9-11": [9, 11], "12+": [12, 99] };
    const remaining = Object.entries(stats.remaining_by_length)
      .filter(([label]) => bands[label] && bands[label][0] >= min && bands[label][1] <= max)
      .reduce((total, [, count]) => total + count, 0);
    $("stat-remaining").textContent = remaining.toLocaleString("fr-FR");
  }

  function refreshStats() {
    state.actionsSinceStats = 0;
    return api("/api/stats").then((stats) => { state.stats = stats; renderStats(); }).catch(() => {});
  }

  const bandLabel = (length) => (length <= 5 ? "2-5" : length <= 8 ? "6-8" : length <= 11 ? "9-11" : "12+");

  // Met à jour les compteurs tout de suite ; le serveur les recalcule régulièrement.
  // `words` : formes normalisées (leur longueur est celle du mot) ; `sign` : +1 décision, -1 annulation.
  function counted(words, sign) {
    if (state.stats) {
      state.stats.today = Math.max(0, state.stats.today + sign * words.length);
      for (const word of words) {
        const label = bandLabel(word.length);
        if (label in state.stats.remaining_by_length) state.stats.remaining_by_length[label] -= sign;
      }
      renderStats();
    }
    state.actionsSinceStats += 1;
    if (state.actionsSinceStats >= STATS_REFRESH_EVERY) serverChain.then(refreshStats);
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
        counted(data.words, 1);
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
    if (event.target.closest("select, input, textarea")) return;
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
  $("filter-length").addEventListener("change", onFiltersChange);
  $("filter-suggestion").addEventListener("change", onFiltersChange);

  restoreFilters();
  render();
  refreshStats();
})();
