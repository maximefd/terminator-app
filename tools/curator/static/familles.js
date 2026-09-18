"use strict";

(() => {
  const API_HEADERS = { "Content-Type": "application/json", "X-Curator": "1" };
  const FETCH_SIZE = 10;
  const BUFFER_MIN = 3;
  const STORAGE_FILTER = "curator-families-filter";

  const POS_LABELS = {
    NOM: "nom", VER: "verbe", AUX: "auxiliaire", ADJ: "adjectif", ADV: "adverbe", PRE: "préposition",
    CON: "conjonction", ONO: "onomatopée", PRO: "pronom", ART: "article",
  };

  const $ = (id) => document.getElementById(id);
  const state = { buffer: [], after: -1, exhausted: false, fetching: null, handled: new Set(), decided: 0, open: null };
  let serverChain = Promise.resolve();

  // --- Utilitaires ---

  const number = (value) => value.toLocaleString("fr-FR");
  const plural = (count, word) => `${number(count)} ${word}${count > 1 ? "s" : ""}`;

  function element(tag, className, text) {
    const node = document.createElement(tag);
    if (className) node.className = className;
    if (text) node.textContent = text;
    return node;
  }

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

  let toastTimer = null;
  function toast(message, isError = false) {
    const node = $("toast");
    node.textContent = message;
    node.classList.toggle("error", isError);
    node.classList.add("visible");
    clearTimeout(toastTimer);
    toastTimer = setTimeout(() => node.classList.remove("visible"), isError ? 5000 : 2600);
  }

  async function api(path, options = {}) {
    let response;
    try {
      response = await fetch(path, { credentials: "same-origin", ...options });
    } catch {
      // Erreur réseau (« Failed to fetch ») : curateur arrêté, redémarré ou Wi-Fi coupé
      throw new Error("Curateur injoignable : vérifiez qu'il tourne (make curator-bg) et la connexion, puis réessayez.");
    }
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

  // --- File des familles ---

  function filters() {
    const [min, max] = $("filter-length").value.split("-").map(Number);
    return { min, max };
  }

  function fillBuffer() {
    if (state.fetching || state.exhausted) return state.fetching || Promise.resolve();
    const { min, max } = filters();
    const params = new URLSearchParams({ after: state.after, limit: FETCH_SIZE, min_length: min, max_length: max });
    state.fetching = api(`/api/families?${params}`)
      .then((data) => {
        state.after = data.next_after;
        const known = new Set(state.buffer.map((card) => card.family));
        state.buffer.push(...data.families.filter((card) => !state.handled.has(card.family) && !known.has(card.family)));
        if (data.families.length === 0) state.exhausted = true;
      })
      .catch((error) => toast(error.message, true))
      .finally(() => { state.fetching = null; });
    return state.fetching;
  }

  function frequencyLabel(zipf) {
    if (zipf === 0) return "absent des corpus";
    if (zipf < 2) return "très rare";
    if (zipf < 3) return "rare";
    if (zipf < 4) return "courant";
    return "très courant";
  }

  // --- Une forme de la famille, triable seule ---

  function formNode(card, form) {
    const item = element("li", "form");
    if (form.protected) item.classList.add("protected");
    if (form.decided) item.classList.add("decided");

    const head = element("button", "form-head");
    head.type = "button";
    head.append(element("span", "form-text", form.form));
    if (form.protected) head.append(element("small", "muted", "mot courant, gardé d'office"));
    else if (form.decided) head.append(element("small", "muted", "déjà décidé"));
    else head.append(element("small", "muted", `${form.length} lettres`));
    head.addEventListener("click", () => {
      state.open = state.open === form.norm ? null : form.norm;
      render();
    });
    item.append(head);

    if (state.open === form.norm) {
      const details = element("div", "form-details");
      details.append(element("p", "form-definition", form.definition || "Aucune définition trouvée dans le Wiktionnaire."));
      if (!form.protected && !form.decided) {
        const actions = element("div", "form-actions");
        const remove = element("button", "danger small", "Supprimer ce mot");
        remove.type = "button";
        remove.addEventListener("click", () => decideOne(card, form, "delete"));
        const keep = element("button", "success small", "Garder ce mot");
        keep.type = "button";
        keep.addEventListener("click", () => decideOne(card, form, "keep"));
        actions.append(remove, keep);
        details.append(actions);
      }
      item.append(details);
    }
    return item;
  }

  function render() {
    const card = state.buffer[0];
    $("card").hidden = !card;
    $("loading").hidden = Boolean(card) || state.exhausted;
    $("empty").hidden = Boolean(card) || !state.exhausted;
    for (const id of ["btn-delete", "btn-keep", "btn-skip"]) $(id).disabled = !card;
    $("stat-position").textContent = state.decided ? plural(state.decided, "décidée") : "—";

    if (!card) {
      if (!state.exhausted) fillBuffer().then(() => { if (state.buffer.length || state.exhausted) render(); });
      return;
    }

    $("card-lemma").textContent = card.lemma;
    $("card-count").textContent = `${plural(card.pending_count, "forme")} à trier`;
    $("card-total").textContent = `${plural(card.total_forms, "forme")} en tout`;

    const definition = $("card-definition");
    if (card.definition) {
      definition.textContent = card.definition;
      definition.classList.remove("missing");
    } else {
      definition.textContent = "Aucune définition trouvée dans le Wiktionnaire.";
      definition.classList.add("missing");
    }

    $("card-freq-bar").style.width = `${Math.min(card.zipf / 7, 1) * 100}%`;
    $("card-freq-label").textContent = `${frequencyLabel(card.zipf)} (${card.zipf.toFixed(1)})`;
    const pos = card.pos ? card.pos.split(":")[0] : null;
    $("card-pos").textContent = pos ? (POS_LABELS[pos] || card.pos) : "—";

    $("card-forms").replaceChildren(...card.forms.map((form) => formNode(card, form)));
    const hidden = card.total_forms - card.forms.length;
    $("card-more").hidden = hidden <= 0;
    if (hidden > 0) $("card-more").textContent = `… et ${plural(hidden, "autre forme")}.`;

    if (state.buffer.length < BUFFER_MIN) fillBuffer();
  }

  // --- Actions ---

  function decideOne(card, form, decision) {
    form.decided = true;
    card.pending = card.pending.filter((norm) => norm !== form.norm);
    card.pending_count = card.pending.length;
    state.open = null;
    // Une famille vidée forme par forme n'a plus lieu d'être affichée
    if (!card.pending_count) {
      state.buffer.shift();
      state.handled.add(card.family);
    }
    render();
    enqueue(() => post("/api/decisions", { words: [form.norm], decision }))
      .then(() => toast(`« ${form.form} » ${decision === "keep" ? "gardé" : "supprimé"} · ↓ pour annuler`))
      .catch((error) => {
        form.decided = false;
        card.pending.push(form.norm);
        card.pending_count = card.pending.length;
        if (state.buffer[0] !== card) state.buffer.unshift(card);
        render();
        toast(error.message, true);
      });
  }

  function decide(decision) {
    const card = state.buffer.shift();
    if (!card) return;
    state.handled.add(card.family);
    state.decided += 1;
    state.open = null;
    render();
    enqueue(() => post("/api/decisions/family", { word: card.norm, decision }))
      .then((data) => {
        const verb = decision === "delete" ? "supprimées" : "gardées";
        toast(`${plural(data.words.length, "forme")} de « ${card.lemma} » ${verb} · ↓ pour annuler`);
      })
      .catch((error) => {
        state.handled.delete(card.family);
        state.decided = Math.max(0, state.decided - 1);
        state.buffer.unshift(card);
        render();
        toast(error.message, true);
      });
  }

  function skip() {
    const card = state.buffer.shift();
    if (!card) return;
    state.open = null;
    state.buffer.push(card);
    render();
  }

  function undo() {
    enqueue(() => post("/api/undo"))
      .then((data) => {
        if (!data.words.length) {
          toast("Rien à annuler");
          return;
        }
        // La famille annulée revient dans la file au prochain chargement
        state.decided = Math.max(0, state.decided - 1);
        state.buffer = [];
        state.after = -1;
        state.exhausted = false;
        state.open = null;
        state.handled.clear();
        render();
        toast(`Annulé : ${plural(data.words.length, "mot")}`);
      })
      .catch((error) => toast(error.message, true));
  }

  // --- Clavier (AZERTY : flèches et Retour arrière) ---

  document.addEventListener("keydown", (event) => {
    if (event.target.closest("select, input, textarea, a, .form-details")) return;
    const handlers = {
      ArrowLeft: () => decide("delete"),
      ArrowRight: () => decide("keep"),
      ArrowUp: skip,
      ArrowDown: undo,
      Backspace: undo,
    };
    const handler = handlers[event.key];
    if (!handler) return;
    event.preventDefault();
    if (event.repeat) return; // une touche maintenue ne décide qu'une fois
    handler();
  });

  // --- Boutons et démarrage ---

  $("btn-delete").addEventListener("click", () => decide("delete"));
  $("btn-keep").addEventListener("click", () => decide("keep"));
  $("btn-skip").addEventListener("click", skip);
  $("btn-undo").addEventListener("click", undo);
  $("filter-length").addEventListener("change", () => {
    storage.set(STORAGE_FILTER, $("filter-length").value);
    state.buffer = [];
    state.after = -1;
    state.exhausted = false;
    state.open = null;
    render();
  });

  const saved = storage.get(STORAGE_FILTER, "2-5");
  if (saved) $("filter-length").value = saved;
  render();
})();
