// web/ea_power_lora.js
// EA Power LoRA — stable, top-aligned UI using native widgets
// - Each row: On (toggle) | LoRA (combo) | Model | CLIP | ✕ Remove
// - "+ Add LoRA" stays at the bottom
// - Hidden JSON widget has zero height so it doesn't push rows down

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] web extension loaded (stable top-aligned)");

async function getLoraList() {
  try {
    const r = await api.fetchApi("/models/loras");
    const j = await r.json();
    if (Array.isArray(j)) return j;
  } catch {}
  try {
    const r = await api.fetchApi("/object_info");
    const d = await r.json();
    const l = d?.models?.loras;
    if (Array.isArray(l)) return l;
  } catch {}
  return [];
}

function makeRowDefaults(name = "") {
  return { enabled: true, name, strength_model: 1.0, strength_clip: 1.0 };
}

function ensureHiddenJSON(node) {
  let hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (!hidden) {
    hidden = node.addWidget("text", "loras_json", "[]", () => {});
    hidden.name = "loras_json";
  }
  // Ensure it is hidden and does NOT take layout space
  hidden.hidden = true;
  hidden.computeSize = () => [0, 0];
  return hidden;
}

function readRows(node) {
  try {
    const hidden = ensureHiddenJSON(node);
    const parsed = JSON.parse(hidden.value || "[]");
    return Array.isArray(parsed)
      ? parsed.map((x) => ({
          enabled: x?.enabled !== false,
          name: x?.name ?? "",
          strength_model: Number(x?.strength_model ?? 1.0),
          strength_clip: Number(x?.strength_clip ?? 1.0),
        }))
      : [];
  } catch {
    return [];
  }
}

function writeRows(node) {
  const hidden = ensureHiddenJSON(node);
  hidden.value = JSON.stringify(node.__ea_rows || []);
  node.setDirtyCanvas(true, true);
}

async function primeLoras(node) {
  if (!node.__ea_lora_list || !node.__ea_lora_list.length) {
    node.__ea_lora_list = await getLoraList();
  }
  return node.__ea_lora_list;
}

// Remove only our dynamic row widgets; keep hidden json and add button
function clearRowWidgets(node) {
  node.widgets = (node.widgets || []).filter((w) => !w.__ea_row);
}

function moveAddBtnToBottom(node) {
  const idx = node.widgets?.findIndex((w) => w.__ea_add_btn) ?? -1;
  if (idx >= 0 && idx !== node.widgets.length - 1) {
    const [btn] = node.widgets.splice(idx, 1);
    node.widgets.push(btn);
  }
}

async function rebuild(node) {
  const loras = await primeLoras(node);
  clearRowWidgets(node);

  const rows = node.__ea_rows || [];

  rows.forEach((row, idx) => {
    // 1) Enable toggle (fixed short label)
    const en = node.addWidget("toggle", "On", !!row.enabled, (v) => {
      row.enabled = !!v;
      sm.disabled = sc.disabled = !row.enabled;
      writeRows(node);
    });
    en.__ea_row = true; en.serialize = false;

    // 2) LoRA name — IMPORTANT: fixed label "LoRA", value is the filename
    const type = loras.length ? "combo" : "text";
    const opts = loras.length ? { values: loras } : {};
    const nameW = node.addWidget(type, "LoRA", row.name, (v) => {
      row.name = String(v || "");
      writeRows(node);
    }, opts);
    nameW.__ea_row = true; nameW.serialize = false;
    nameW.tooltip = "Select an installed LoRA (from /models/loras).";

    // 3) Strengths
    const sm = node.addWidget("number", "Model", row.strength_model, (v) => {
      const n = Number(v); row.strength_model = Number.isFinite(n) ? n : 0.0;
      writeRows(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sm.__ea_row = true; sm.serialize = false;

    const sc = node.addWidget("number", "CLIP", row.strength_clip, (v) => {
      const n = Number(v); row.strength_clip = Number.isFinite(n) ? n : 0.0;
      writeRows(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sc.__ea_row = true; sc.serialize = false;

    sm.disabled = sc.disabled = !row.enabled;

    // 4) Remove row
    const del = node.addWidget("button", "✕ Remove", null, () => {
      rows.splice(idx, 1);
      rebuild(node); // full rebuild to refresh indices
    });
    del.__ea_row = true; del.serialize = false;
  });

  moveAddBtnToBottom(node);

  // Force a resize to the true minimal top-aligned size (no big blank gap)
  try {
    const sz = node.computeSize?.();
    if (Array.isArray(sz) && sz[1]) node.setSize(sz);
  } catch {}

  writeRows(node);
}

async function ensureUI(node) {
  if (!node || node.comfyClass !== "EA_PowerLora") return;

  ensureHiddenJSON(node);
  node.__ea_rows = readRows(node);

  // Create Add button once (we’ll keep it at bottom in rebuild)
  let addBtn = node.widgets?.find((w) => w.__ea_add_btn);
  if (!addBtn) {
    addBtn = node.addWidget("button", "＋ Add LoRA", null, async () => {
      if (!node.__ea_rows) node.__ea_rows = [];
      node.__ea_rows.push(makeRowDefaults(""));
      await rebuild(node);
    });
    addBtn.__ea_add_btn = true;
    addBtn.serialize = false;
  }

  await rebuild(node);
}

// --- register ---------------------------------------------------------------
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
  nodeCreated(node) { ensureUI(node); },
});
