// web/ea_power_lora.js
// EA Power LoRA — compact UI with filterable picker
// - Add button opens big quick-pick list (type to filter)
// - Clicking the LoRA name also opens the picker
// - Enable toggle per row, Model/CLIP strengths, Remove
// - Persists rows via hidden STRING widget `loras_json`

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] web extension loaded");

// ---------- data helpers -----------------------------------------------------
function makeRowDefaults(name = "") {
  return { enabled: true, name, strength_model: 1.0, strength_clip: 1.0 };
}

async function getLoraList() {
  // Prefer /models/loras; fallback to /object_info
  try {
    const r = await api.fetchApi("/models/loras");
    const j = await r.json();
    if (Array.isArray(j) && j.length) return j;
  } catch {}
  try {
    const r = await api.fetchApi("/object_info");
    const d = await r.json();
    const l = d?.models?.loras;
    if (Array.isArray(l) && l.length) return l;
  } catch {}
  return [];
}

function ensureHiddenJSON(node) {
  let hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (!hidden) {
    hidden = node.addWidget("text", "loras_json", "[]", () => {});
    hidden.hidden = true;
    hidden.name = "loras_json";
  } else hidden.hidden = true;
  return hidden;
}

function syncToHiddenJSON(node) {
  const hidden = ensureHiddenJSON(node);
  hidden.value = JSON.stringify(node.__ea_rows || []);
  node.setDirtyCanvas(true, true);
}

function removeRowWidgets(node) {
  node.widgets = (node.widgets || []).filter((w) => !w.__ea_row);
}

function truncate(name, max = 36) {
  if (!name) return "Choose LoRA…";
  return name.length > max ? name.slice(0, max - 1) + "…" : name;
}

// ---------- quick pick overlay (filterable) ---------------------------------
function openQuickPick(loraList, onPick) {
  const overlay = document.createElement("div");
  Object.assign(overlay.style, {
    position: "fixed",
    inset: "0",
    background: "rgba(0,0,0,0.25)",
    zIndex: 10000,
  });

  const panel = document.createElement("div");
  Object.assign(panel.style, {
    position: "absolute",
    left: "50%",
    top: "20%",
    transform: "translateX(-50%)",
    minWidth: "460px",
    maxHeight: "60vh",
    overflow: "auto",
    background: "var(--bg-color, #222)",
    color: "var(--color-text, #ddd)",
    border: "1px solid var(--color-border, #444)",
    borderRadius: "10px",
    boxShadow: "0 10px 28px rgba(0,0,0,0.35)",
  });

  const input = document.createElement("input");
  Object.assign(input, { type: "text", placeholder: "Filter LoRAs…" });
  Object.assign(input.style, {
    width: "100%",
    boxSizing: "border-box",
    padding: "10px 12px",
    background: "transparent",
    border: "0",
    borderBottom: "1px solid var(--color-border,#444)",
    color: "inherit",
    outline: "none",
    fontSize: "14px",
  });

  const list = document.createElement("div");
  list.style.padding = "6px 0";

  panel.appendChild(input);
  panel.appendChild(list);
  overlay.appendChild(panel);
  document.body.appendChild(overlay);

  const makeItem = (name) => {
    const el = document.createElement("div");
    el.textContent = name;
    el.style.padding = "8px 12px";
    el.style.cursor = "pointer";
    el.onmouseenter = () => (el.style.background = "rgba(255,255,255,0.06)");
    el.onmouseleave = () => (el.style.background = "transparent");
    el.onclick = () => {
      onPick(name);
      close();
    };
    return el;
  };

  const render = () => {
    list.innerHTML = "";
    const q = input.value.toLowerCase();
    const filtered = (loraList || [])
      .filter((n) => !q || n.toLowerCase().includes(q))
      .slice(0, 1000);
    if (!filtered.length) {
      const empty = document.createElement("div");
      empty.textContent = "No matches. Esc to cancel.";
      empty.style.opacity = "0.6";
      empty.style.padding = "10px 12px";
      list.appendChild(empty);
      return;
    }
    filtered.forEach((n) => list.appendChild(makeItem(n)));
  };

  const onKey = (e) => {
    if (e.key === "Escape") close();
    if (e.key === "Enter") {
      const first = list.querySelector("div");
      if (first && first.textContent && !first.textContent.startsWith("No matches")) {
        onPick(first.textContent);
        close();
      }
    }
  };

  const close = () => {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
  };

  document.addEventListener("keydown", onKey);
  overlay.addEventListener("click", (e) => {
    if (e.target === overlay) close();
  });
  input.addEventListener("input", render);

  input.focus();
  render();
}

// ---------- UI build (compact) ----------------------------------------------
function rebuildRows(node, loraList) {
  removeRowWidgets(node);
  const rows = node.__ea_rows || [];

  rows.forEach((row, idx) => {
    // Enable toggle
    const en = node.addWidget("toggle", "Enable", !!row.enabled, (v) => {
      row.enabled = !!v;
      syncToHiddenJSON(node);
    });
    en.__ea_row = true;
    en.serialize = false;

    // Name button (this IS the picker; no "LoRA #n" prefix)
    const labelFor = () => truncate(row.name);
    const nameBtn = node.addWidget("button", labelFor(), null, async () => {
      const list = loraList?.length ? loraList : await getLoraList();
      if (list.length) {
        openQuickPick(list, (picked) => {
          row.name = picked;
          nameBtn.name = labelFor();
          nameBtn.tooltip = picked;
          syncToHiddenJSON(node);
        });
      } else {
        const typed = prompt("LoRA filename (in /models/loras):", row.name || "");
        if (typed != null) {
          row.name = String(typed).trim();
          nameBtn.name = labelFor();
          nameBtn.tooltip = row.name;
          syncToHiddenJSON(node);
        }
      }
    });
    nameBtn.__ea_row = true;
    nameBtn.serialize = false;
    nameBtn.tooltip = row.name || "Click to choose installed LoRA (type to filter)";

    // Strengths (short labels)
    const sm = node.addWidget(
      "number",
      "Model",
      row.strength_model,
      (v) => {
        const n = Number(v);
        row.strength_model = Number.isFinite(n) ? n : 0.0;
        syncToHiddenJSON(node);
      },
      { min: 0.0, max: 2.0, step: 0.05 }
    );
    sm.__ea_row = true;
    sm.serialize = false;
    sm.tooltip = "Strength (Model)";

    const sc = node.addWidget(
      "number",
      "CLIP",
      row.strength_clip,
      (v) => {
        const n = Number(v);
        row.strength_clip = Number.isFinite(n) ? n : 0.0;
        syncToHiddenJSON(node);
      },
      { min: 0.0, max: 2.0, step: 0.05 }
    );
    sc.__ea_row = true;
    sc.serialize = false;
    sc.tooltip = "Strength (CLIP)";

    // Remove
    const del = node.addWidget("button", "🗑 Remove", null, () => {
      rows.splice(idx, 1);
      rebuildRows(node, loraList);
    });
    del.__ea_row = true;
    del.serialize = false;
  });

  syncToHiddenJSON(node);
}

async function ensureUI(node) {
  if (!node || node.comfyClass !== "EA_PowerLora") return;

  const hidden = ensureHiddenJSON(node);

  // Restore rows from hidden JSON
  try {
    const parsed = JSON.parse(hidden.value || "[]");
    node.__ea_rows = Array.isArray(parsed)
      ? parsed.map((x) => ({
          enabled: x?.enabled !== false,
          name: x?.name ?? "",
          strength_model: Number(x?.strength_model ?? 1.0),
          strength_clip: Number(x?.strength_clip ?? 1.0),
        }))
      : [];
  } catch {
    node.__ea_rows = [];
  }

  // Top Add button -> quick pick
  let addBtn = node.widgets?.find((w) => w.__ea_add_btn);
  if (!addBtn) {
    addBtn = node.addWidget("button", "＋ Add LoRA", null, async () => {
      const list = node.__ea_lora_list?.length ? node.__ea_lora_list : await getLoraList();
      if (list.length) {
        openQuickPick(list, (picked) => {
          node.__ea_rows.push(makeRowDefaults(picked));
          rebuildRows(node, list);
        });
      } else {
        node.__ea_rows.push(makeRowDefaults(""));
        rebuildRows(node, []);
      }
    });
    addBtn.__ea_add_btn = true;
    addBtn.serialize = false;
  }

  node.__ea_lora_list = await getLoraList();
  rebuildRows(node, node.__ea_lora_list);
}

// ---------- register extension ----------------------------------------------
app.registerExtension({
  name: "ea.PowerLora",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== "EA_PowerLora") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onNodeCreated?.apply(this, arguments);
      ensureUI(this);
      return r;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (info) {
      const r = onConfigure?.apply(this, arguments);
      ensureUI(this);
      return r;
    };
  },
  nodeCreated(node) {
    // Patch nodes created before the extension loaded
    ensureUI(node);
  },
});
