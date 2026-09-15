"use strict";

(() => {
  const API_HEADERS = { "Content-Type": "application/json", "X-Curator": "1" };
  const MIN_SIDE = 2;
  const MAX_SIDE = 30;
  const DEFINITION = "x";
  const LETTER = "-";
  const DRAFT_KEY = "curator-layout-draft";
  const CHECK_DELAY = 150;
  const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)").matches;

  const $ = (id) => document.getElementById(id);
  const state = {
    width: 11,
    height: 6,
    cells: [],
    cursor: { x: 0, y: 0 },
    source: null, // layout du catalogue copié dans l'éditeur
    report: null,
    checkSequence: 0,
    checkTimer: null,
    saving: false,
  };

  // --- Utilitaires ---

  const number = (value) => value.toLocaleString("fr-FR");
  const plural = (count, word) => `${number(count)} ${word}${count > 1 ? "s" : ""}`;
  const rows = () => state.cells.map((row) => row.join(""));

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
        // Stockage indisponible : le brouillon n'est simplement pas conservé
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

  const post = (path, body) => api(path, { method: "POST", headers: API_HEADERS, body: JSON.stringify(body) });

  // --- Grille ---

  function clampSide(value, fallback) {
    const parsed = Number.parseInt(value, 10);
    return Number.isFinite(parsed) ? Math.min(MAX_SIDE, Math.max(MIN_SIDE, parsed)) : fallback;
  }

  function resize(width, height) {
    // Les cases existantes sont conservées : on peut corriger une taille mal comptée sans tout refaire
    state.cells = Array.from({ length: height }, (_, y) =>
      Array.from({ length: width }, (_, x) => (state.cells[y] && state.cells[y][x]) || LETTER));
    state.width = width;
    state.height = height;
    state.cursor = { x: Math.min(state.cursor.x, width - 1), y: Math.min(state.cursor.y, height - 1) };
    $("width").value = width;
    $("height").value = height;
    buildGrid();
    changed();
  }

  function buildGrid() {
    const grid = $("grid");
    grid.style.setProperty("--cols", state.width);
    grid.style.setProperty("--rows", state.height);
    const nodes = [];
    for (let y = 0; y < state.height; y += 1) {
      for (let x = 0; x < state.width; x += 1) {
        const cell = element("button", "cell");
        cell.type = "button";
        cell.dataset.x = x;
        cell.dataset.y = y;
        nodes.push(cell);
      }
    }
    grid.replaceChildren(...nodes);
    paint();
  }

  const cellNode = (x, y) => $("grid").children[y * state.width + x];

  function paint() {
    const invalid = new Set((state.report ? state.report.errors : [])
      .flatMap((error) => error.cells.map(([x, y]) => `${x},${y}`)));
    for (let y = 0; y < state.height; y += 1) {
      for (let x = 0; x < state.width; x += 1) {
        const node = cellNode(x, y);
        const isDefinition = state.cells[y][x] === DEFINITION;
        const isCursor = state.cursor.x === x && state.cursor.y === y;
        node.classList.toggle("definition", isDefinition);
        node.classList.toggle("invalid", invalid.has(`${x},${y}`));
        node.classList.toggle("cursor", isCursor);
        node.tabIndex = isCursor ? 0 : -1;
        node.setAttribute("aria-label",
          `Ligne ${y + 1}, colonne ${x + 1} : ${isDefinition ? "case définition" : "case lettre"}`);
      }
    }
  }

  function changed() {
    paint();
    storage.set(DRAFT_KEY, { rows: rows(), source: state.source });
    $("btn-save").disabled = true;
    $("check-status").textContent = "Vérification…";
    $("check-status").dataset.state = "";
    clearTimeout(state.checkTimer);
    state.checkTimer = setTimeout(check, CHECK_DELAY);
  }

  function setCell(x, y, value) {
    state.cells[y][x] = value;
    changed();
  }

  const toggle = (x, y) => setCell(x, y, state.cells[y][x] === DEFINITION ? LETTER : DEFINITION);

  function moveCursor(x, y) {
    state.cursor = {
      x: Math.min(Math.max(x, 0), state.width - 1),
      y: Math.min(Math.max(y, 0), state.height - 1),
    };
    paint();
    cellNode(state.cursor.x, state.cursor.y).focus();
  }

  // Recopie rangée par rangée : après la dernière case d'une rangée, on passe au début de la suivante
  function advance() {
    const { x, y } = state.cursor;
    if (x < state.width - 1) moveCursor(x + 1, y);
    else if (y < state.height - 1) moveCursor(0, y + 1);
    else moveCursor(x, y);
  }

  function retreat() {
    const { x, y } = state.cursor;
    if (x > 0) moveCursor(x - 1, y);
    else if (y > 0) moveCursor(state.width - 1, y - 1);
  }

  // --- Vérification (règles du serveur) ---

  function check() {
    const sequence = ++state.checkSequence;
    post("/api/layouts/check", { rows: rows() })
      .then((report) => {
        if (sequence !== state.checkSequence) return; // la grille a changé entre-temps
        state.report = report;
        renderReport();
        paint();
      })
      .catch((error) => {
        if (sequence !== state.checkSequence) return;
        $("check-status").textContent = error.message;
        $("check-status").dataset.state = "error";
      });
  }

  function renderReport() {
    const report = state.report;
    if (!report) return;
    const status = $("check-status");
    if (!report.valid) {
      status.textContent = `${plural(report.errors.length, "erreur")} à corriger`;
      status.dataset.state = "error";
    } else if (report.duplicate_of) {
      status.textContent = `Cette grille est déjà dans le catalogue : ${report.duplicate_of}`;
      status.dataset.state = "warning";
    } else {
      status.textContent = `Grille valide · elle sera enregistrée sous ${report.next_id}`;
      status.dataset.state = "ok";
    }

    $("issues").replaceChildren(
      ...report.errors.map((error) => element("li", "error", error.message)),
      ...report.warnings.map((warning) => element("li", "warning", warning.message)),
    );

    const stats = report.stats;
    $("stat-words").textContent = stats ? number(stats.words) : "—";
    $("stat-definitions").textContent = stats
      ? `${number(stats.definition_cells)} (${Math.round(stats.definition_ratio * 100)} %)` : "—";
    $("stat-lengths").textContent = stats && stats.words
      ? Object.entries(stats.lengths).map(([length, count]) => `${count} de ${length}`).join(", ") + " lettres"
      : "—";

    $("btn-save").disabled = !report.valid || Boolean(report.duplicate_of) || state.saving;
  }

  // --- Enregistrement ---

  function save() {
    if ($("btn-save").disabled) return;
    state.saving = true;
    $("btn-save").disabled = true;
    post("/api/layouts", { rows: rows() })
      .then((data) => {
        toast(`✓ Layout enregistré : ${data.id}`);
        state.source = null;
        renderSource();
        loadCatalog();
      })
      .catch((error) => toast(error.message, true))
      .finally(() => {
        state.saving = false;
        check();
      });
  }

  // --- Catalogue ---

  function renderSource() {
    $("source").hidden = !state.source;
    $("source").textContent = state.source
      ? `Copie de ${state.source} : l'original ne sera pas modifié, l'enregistrement crée un nouveau layout.` : "";
  }

  const hasUnsavedWork = () =>
    rows().some((row) => row.includes(DEFINITION)) && !(state.report && state.report.duplicate_of);

  function copyLayout(layout) {
    if (hasUnsavedWork() && !window.confirm(`Remplacer la grille en cours par une copie de ${layout.id} ?`)) return;
    state.source = layout.id;
    state.cells = layout.rows.map((row) => [...row]);
    state.cursor = { x: 0, y: 0 };
    renderSource();
    resize(layout.rows[0].length, layout.rows.length);
    $("editor").scrollIntoView({ behavior: reducedMotion ? "auto" : "smooth", block: "start" });
  }

  function miniGrid(layout, width) {
    const mini = element("span", "mini-grid");
    mini.style.setProperty("--cols", width);
    for (const row of layout.rows) {
      for (const char of row) mini.append(element("span", char === DEFINITION ? "definition" : ""));
    }
    return mini;
  }

  function renderCatalog(formats) {
    const total = formats.reduce((count, format) => count + format.layouts.length, 0);
    $("catalog-count").textContent = total ? `(${number(total)})` : "";
    if (!total) {
      $("catalog").replaceChildren(element("p", "muted", "Aucun layout pour l'instant : enregistrez le premier !"));
      return;
    }
    $("catalog").replaceChildren(...formats.map((format) => {
      const group = element("section", "catalog-format");
      group.append(element("h3", "", `${format.width} × ${format.height}`));
      const list = element("div", "catalog-list");
      for (const layout of format.layouts) {
        const item = element("button", "catalog-item");
        item.type = "button";
        item.setAttribute("aria-label", `Copier ${layout.id} dans l'éditeur`);
        item.append(miniGrid(layout, format.width), element("span", "catalog-id", layout.id),
          element("small", "muted", plural(layout.stats.words, "mot")));
        item.addEventListener("click", () => copyLayout(layout));
        list.append(item);
      }
      group.append(list);
      return group;
    }));
  }

  function loadCatalog() {
    api("/api/layouts")
      .then((data) => renderCatalog(data.formats))
      .catch((error) => $("catalog").replaceChildren(element("p", "error", error.message)));
  }

  // --- Événements ---

  $("grid").addEventListener("click", (event) => {
    const cell = event.target.closest(".cell");
    if (!cell) return;
    const x = Number(cell.dataset.x);
    const y = Number(cell.dataset.y);
    state.cursor = { x, y };
    toggle(x, y); // clic, toucher, ou Espace (activation native du bouton)
  });

  // Clavier (AZERTY) : x et - sans Maj, flèches, Entrée, Retour arrière
  $("grid").addEventListener("keydown", (event) => {
    if (event.metaKey || event.ctrlKey || event.altKey) return;
    const { x, y } = state.cursor;
    const handlers = {
      ArrowLeft: () => moveCursor(x - 1, y),
      ArrowRight: () => moveCursor(x + 1, y),
      ArrowUp: () => moveCursor(x, y - 1),
      ArrowDown: () => moveCursor(x, y + 1),
      Enter: () => moveCursor(0, y + 1),
      Backspace: retreat,
      x: () => { setCell(x, y, DEFINITION); advance(); },
      X: () => { setCell(x, y, DEFINITION); advance(); },
      "-": () => { setCell(x, y, LETTER); advance(); },
    };
    const handler = handlers[event.key];
    if (!handler) return;
    event.preventDefault(); // Entrée ne doit pas aussi « cliquer » la case
    handler();
  });

  for (const id of ["width", "height"]) {
    $(id).addEventListener("change", () =>
      resize(clampSide($("width").value, state.width), clampSide($("height").value, state.height)));
  }

  $("btn-clear").addEventListener("click", () => {
    if (rows().some((row) => row.includes(DEFINITION)) && !window.confirm("Remettre toutes les cases en cases lettres ?")) return;
    state.cells = [];
    state.source = null;
    renderSource();
    resize(state.width, state.height);
  });

  $("btn-save").addEventListener("click", save);

  // --- Démarrage : reprise du brouillon de cet appareil ---

  const draft = storage.get(DRAFT_KEY, null);
  const draftRows = draft && Array.isArray(draft.rows) ? draft.rows : [];
  const draftIsUsable = draftRows.length >= MIN_SIDE && draftRows.length <= MAX_SIDE
    && draftRows.every((row) => typeof row === "string" && row.length === draftRows[0].length
      && row.length >= MIN_SIDE && row.length <= MAX_SIDE && /^[x-]+$/.test(row));
  if (draftIsUsable) {
    state.cells = draftRows.map((row) => [...row]);
    state.source = typeof draft.source === "string" ? draft.source : null;
    resize(draftRows[0].length, draftRows.length);
  } else {
    resize(state.width, state.height);
  }
  renderSource();
  loadCatalog();
})();
