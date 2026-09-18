"use strict";

(() => {
  const API_HEADERS = { "Content-Type": "application/json", "X-Curator": "1" };
  const FETCH_SIZE = 50;
  const BUFFER_MIN = 5;

  const REASON_LABELS = {
    "famille-incoherente": "Famille jugée à l'opposé",
    "mot-courant-supprime": "Mot courant supprimé",
    "decision-eclair": "Décision en rafale",
  };

  const $ = (id) => document.getElementById(id);
  const state = { buffer: [], counts: {}, remaining: 0, loading: null, exhausted: false };
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

  function enqueue(task) {
    const run = serverChain.then(task);
    serverChain = run.catch(() => {});
    return run;
  }

  // --- Liste des décisions à revoir ---

  function load(reset = false) {
    if (reset) {
      state.buffer = [];
      state.exhausted = false;
      state.loading = null;
    } else if (state.loading) {
      return state.loading;
    }
    state.loading = api(`/api/revisions?${new URLSearchParams({ limit: FETCH_SIZE })}`)
      .then((data) => {
        const known = new Set(state.buffer.map((item) => item.norm));
        const fresh = data.items.filter((item) => !known.has(item.norm));
        state.buffer.push(...fresh);
        state.counts = data.counts;
        state.remaining = data.total;
        // Le serveur renvoie toujours les mêmes décisions tant qu'elles ne sont pas revues :
        // sans nouveauté, la file est vraiment finie.
        if (!fresh.length) state.exhausted = true;
      })
      .catch((error) => toast(error.message, true))
      .finally(() => { state.loading = null; });
    return state.loading;
  }

  function renderReasons() {
    const entries = Object.entries(state.counts).filter(([, count]) => count > 0);
    $("reasons").replaceChildren(...entries.map(([reason, count]) => {
      const item = element("li", "reason-count");
      item.append(element("strong", "", number(count)));
      item.append(element("span", "", REASON_LABELS[reason] || reason));
      return item;
    }));
  }

  function frequencyLabel(zipf) {
    if (zipf === 0) return "absent des corpus";
    if (zipf < 2) return "très rare";
    if (zipf < 3) return "rare";
    if (zipf < 4) return "courant";
    return "très courant";
  }

  function render() {
    const item = state.buffer[0];
    $("card").hidden = !item;
    $("loading").hidden = Boolean(item) || state.exhausted;
    $("empty").hidden = Boolean(item) || !state.exhausted;
    for (const id of ["btn-delete", "btn-keep", "btn-skip"]) $(id).disabled = !item;
    $("stat-remaining").textContent = number(Math.max(state.remaining, 0));
    renderReasons();

    if (!item) {
      if (!state.exhausted) load().then(() => { if (state.buffer.length || state.exhausted) render(); });
      return;
    }

    const badge = $("card-reason");
    badge.textContent = REASON_LABELS[item.reason] || item.reason;
    badge.dataset.suggestion = item.reason === "mot-courant-supprime" ? "likely_keep" : "review";
    $("card-length").textContent = `${item.length} lettres · ${item.norm}`;
    $("card-word").textContent = item.form;
    $("card-explanation").textContent = item.explanation;

    const current = $("card-current");
    current.textContent = item.decision === "delete" ? "Vous aviez supprimé ce mot" : "Vous aviez gardé ce mot";
    current.dataset.decision = item.decision;

    const definition = $("card-definition");
    if (item.definition) {
      definition.textContent = item.definition;
      definition.classList.remove("missing");
    } else {
      definition.textContent = "Aucune définition trouvée dans le Wiktionnaire.";
      definition.classList.add("missing");
    }

    $("card-freq-bar").style.width = `${Math.min(item.zipf / 7, 1) * 100}%`;
    $("card-freq-label").textContent = `${frequencyLabel(item.zipf)} (${item.zipf.toFixed(1)})`;
    $("card-lemma").textContent = item.lemma || "—";
    $("card-date").textContent = new Date(item.decided_at).toLocaleString("fr-FR", { dateStyle: "short", timeStyle: "short" });

    if (state.buffer.length < BUFFER_MIN && !state.exhausted) load();
  }

  // --- Actions : les mêmes qu'au tri (← supprimer, → garder) ---

  function decide(decision) {
    const item = state.buffer.shift();
    if (!item) return;
    state.remaining = Math.max(0, state.remaining - 1);
    render();
    enqueue(() => post("/api/revisions", { words: [item.norm], decision }))
      .then(() => {
        const changed = decision !== item.decision;
        const verb = decision === "keep" ? "gardé" : "supprimé";
        toast(changed ? `« ${item.form} » finalement ${verb} · ↓ pour annuler`
          : `« ${item.form} » reste ${verb} · ↓ pour annuler`);
      })
      .catch((error) => {
        state.buffer.unshift(item);
        state.remaining += 1;
        render();
        toast(error.message, true);
      });
  }

  function skip() {
    const item = state.buffer.shift();
    if (!item) return;
    state.buffer.push(item);
    render();
  }

  function undo() {
    enqueue(() => post("/api/undo"))
      .then((data) => {
        if (!data.words.length) {
          toast("Rien à annuler");
          return;
        }
        // La décision annulée redevient douteuse : on relit la liste depuis le serveur
        toast(`Annulé : ${data.words.join(", ")}`);
        return load(true).then(render);
      })
      .catch((error) => toast(error.message, true));
  }

  // --- Clavier (AZERTY : flèches, Retour arrière) ---

  document.addEventListener("keydown", (event) => {
    if (event.target.closest("select, input, textarea, a")) return;
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

  $("btn-delete").addEventListener("click", () => decide("delete"));
  $("btn-keep").addEventListener("click", () => decide("keep"));
  $("btn-skip").addEventListener("click", skip);
  $("btn-undo").addEventListener("click", undo);

  render();
})();
