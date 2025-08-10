// web/ea_power_lora.js
// EA Power LoRA — stable UI (native widgets only)
// - Global "Apply to CLIP" toggle at the top
// - When off: CLIP rows are hidden and CLIP strengths are ignored in Python
// - Rows stay top-aligned; small gaps after each "✕ Remove" and above "+ Add LoRA"
// - State is persisted in hidden STRING `loras_json` as:
//   { clip_enabled: boolean, rows: [ ... ] }

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] web extension loaded (global CLIP toggle)");

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
  return {
    enabled: true,
    name,
    strength_model: 1.0,
    strength_clip: 1.0,
    // per-row clip toggle removed; now global
  };
}

// ------- persistence helpers -------------------------------------------------
function ensureHiddenJSON(node) {
  let hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (!hidden) {
    hidden = node.addWidget("text", "loras_json", "[]", () => {});
    hidden.name = "loras_json";
  }
  hidden.hidden = true;
  hidden.computeSize = () => [0, 0];
  return hidden;
}

function readState(node) {
  const hidden = ensureHiddenJSON(node);
  try {
    const parsed = JSON.parse(hidden.value || "[]");
    if (Array.isArray(parsed)) {
      // legacy list -> upgrade to object
      return { clip_enabled: true, rows: parsed.map(upgradeRow) };
    }
    if (parsed && typeof parsed === "object") {
      return {
        clip_enabled: parsed.clip_enabled !== false,
        rows: Array.isArray(parsed.rows) ? parsed.rows.map(upgradeRow) : [],
      };
    }
  } catch {}
  return { clip_enabled: true, rows: [] };
}

function writeState(node) {
  const hidden = ensureHiddenJSON(node);
  const state = { clip_enabled: !!node.__ea_clip_enabled, rows: node.__ea_rows || [] };
  hidden.value = JSON.stringify(state);
  node.setDirtyCanvas(true, true);
}

function upgradeRow(x) {
  return {
    enabled: x?.enabled !== false,
    name: x?.name ?? "",
    strength_model: Number.isFinite(+x?.strength_model) ? +x.strength_model : 1.0,
    strength_clip: Number.isFinite(+x?.strength_clip) ? +x.strength_clip : 1.0,
  };
}

// ------- layout helpers ------------------------------------------------------
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

function addSpacer(node, h = 6) {
  const spacer = {
    __ea_row: true,
    name: "__ea_spacer",
    serialize: false,
    draw: () => {},
    computeSize: () => [0, h],
  };
  node.widgets.push(spacer);
  return spacer;
}

function setHidden(widget, hidden) {
  widget.hidden = !!hidden;
  if (!widget.__ea_orig_cs) widget.__ea_orig_cs = widget.computeSize;
  widget.computeSize = function () {
    if (this.hidden) return [0, 0];
    return this.__ea_orig_cs ? this.__ea_orig_cs.apply(this, arguments) : [0, 20];
  };
}

// ------- rebuild -------------------------------------------------------------
async function rebuild(node) {
  // cache lora list
  if (!node.__ea_lora_list || !node.__ea_lora_list.length) {
    node.__ea_lora_list = await getLoraList();
  }
  const loras = node.__ea_lora_list;

  clearRowWidgets(node);

  const rows = node.__ea_rows || [];
  const useClip = !!node.__ea_clip_enabled;

  rows.forEach((row, idx) => {
    // 1) On/off per row
    const en = node.addWidget("toggle", "On", !!row.enabled, (v) => {
      row.enabled = !!v;
      sm.disabled = !row.enabled;
      sc.disabled = !row.enabled || !useClip;
      writeState(node);
    });
    en.__ea_row = true; en.serialize = false;

    // 2) LoRA selector (native widget)
    const type = loras.length ? "combo" : "text";
    const opts = loras.length ? { values: loras } : {};
    const nameW = node.addWidget(type, "LoRA", row.name, (v) => {
      row.name = String(v || "");
      writeState(node);
    }, opts);
    nameW.__ea_row = true; nameW.serialize = false;
    nameW.tooltip = "Select an installed LoRA (from /models/loras).";

    // 3) Model strength
    const sm = node.addWidget("number", "Model", row.strength_model, (v) => {
      const n = Number(v);
      row.strength_model = Number.isFinite(n) ? n : 0.0;
      writeState(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sm.__ea_row = true; sm.serialize = false;

    // 4) CLIP strength (hidden when global CLIP is off)
    const sc = node.addWidget("number", "CLIP", row.strength_clip, (v) => {
      const n = Number(v);
      row.strength_clip = Number.isFinite(n) ? n : 0.0;
      writeState(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sc.__ea_row = true; sc.serialize = false;

    sm.disabled = !row.enabled;
    sc.disabled = !row.enabled || !useClip;
    setHidden(sc, !useClip); // hide CLIP row globally

    // 5) Remove + small gap
    const del = node.addWidget("button", "✕ Remove", null, () => {
      rows.splice(idx, 1);
      rebuild(node);
    });
    del.__ea_row = true; del.serialize = false;

    addSpacer(node, 6); // tiny gap after each row
  });

  // gap above add button when there are rows
  if (rows.length) addSpacer(node, 6);

  moveAddBtnToBottom(node);

  // tighten height so rows sit at the top
  try {
    const sz = node.computeSize?.();
    if (Array.isArray(sz) && sz[1]) node.setSize(sz);
  } catch {}

  writeState(node);
}

// ------- bootstrap -----------------------------------------------------------
async function ensureUI(node) {
  if (!node || node.comfyClass !== "EA_PowerLora") return;

  // restore state
  const state = readState(node);
  node.__ea_clip_enabled = !!state.clip_enabled;
  node.__ea_rows = state.rows;

  // GLOBAL: Apply to CLIP toggle (top)
  let globalClip = node.widgets?.find((w) => w.__ea_global_clip);
  if (!globalClip) {
    globalClip = node.addWidget("toggle", "Apply to CLIP", node.__ea_clip_enabled, (v) => {
      node.__ea_clip_enabled = !!v;
      rebuild(node); // re-hide/show CLIP rows + recompute size
    });
    globalClip.__ea_global_clip = true;
    globalClip.serialize = false;
  } else {
    globalClip.value = node.__ea_clip_enabled;
  }

  // Add button (bottom)
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

// ------- register ------------------------------------------------------------
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
