// web/ea_power_lora.js
// v0.2.0 experimental — stable native UI, no legacy shapes
// Registers UI for both: EA_PowerLora (no CLIP) and EA_PowerLora_CLIP (global CLIP toggle)

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] UI v0.2.0 loaded");

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

function ensureHidden(node) {
  let hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (!hidden) {
    hidden = node.addWidget("text", "loras_json", "{}", () => {});
    hidden.name = "loras_json";
  }
  hidden.hidden = true;
  hidden.computeSize = () => [0, 0];
  return hidden;
}

function clearRows(node) {
  node.widgets = (node.widgets || []).filter((w) => !w.__ea_row);
}
function spacer(node, h = 6) {
  node.widgets.push({
    __ea_row: true,
    name: "__ea_spacer",
    serialize: false,
    draw: () => {},
    computeSize: () => [0, h],
  });
}
function moveAddToBottom(node) {
  const i = node.widgets?.findIndex((w) => w.__ea_add_btn) ?? -1;
  if (i >= 0 && i !== node.widgets.length - 1) {
    const [btn] = node.widgets.splice(i, 1);
    node.widgets.push(btn);
  }
}
function setHidden(widget, hidden) {
  widget.hidden = !!hidden;
  if (!widget.__ea_orig_cs) widget.__ea_orig_cs = widget.computeSize;
  widget.computeSize = function () {
    if (this.hidden) return [0, 0];
    return this.__ea_orig_cs ? this.__ea_orig_cs.apply(this, arguments) : [0, 20];
  };
}
function resizeTight(node) {
  try {
    const sz = node.computeSize?.();
    if (Array.isArray(sz) && sz[1]) node.setSize(sz);
  } catch {}
}

// ---------- EA_PowerLora (no CLIP) ----------
function readNonClip(node) {
  const h = ensureHidden(node);
  try {
    const obj = JSON.parse(h.value || "{}");
    if (obj && typeof obj === "object" && Array.isArray(obj.rows)) {
      return obj.rows.map((x) => ({
        enabled: x?.enabled !== false,
        name: x?.name ?? "",
        strength_model: Number.isFinite(+x?.strength_model) ? +x.strength_model : 1.0,
      }));
    }
  } catch {}
  return [];
}
function writeNonClip(node) {
  ensureHidden(node).value = JSON.stringify({ rows: node.__ea_rows || [] });
  node.setDirtyCanvas(true, true);
}
async function rebuildNonClip(node) {
  if (!node.__ea_loras || !node.__ea_loras.length) {
    node.__ea_loras = await getLoraList();
  }
  const loras = node.__ea_loras;

  clearRows(node);
  const rows = node.__ea_rows || [];

  rows.forEach((row, idx) => {
    const en = node.addWidget("toggle", "On", !!row.enabled, (v) => {
      row.enabled = !!v;
      sm.disabled = !row.enabled;
      writeNonClip(node);
    });
    en.__ea_row = true; en.serialize = false;

    const type = loras.length ? "combo" : "text";
    const opts = loras.length ? { values: loras } : {};
    const nameW = node.addWidget(type, "LoRA", row.name, (v) => {
      row.name = String(v || "");
      writeNonClip(node);
    }, opts);
    nameW.__ea_row = true; nameW.serialize = false;

    const sm = node.addWidget("number", "Model", row.strength_model, (v) => {
      const n = Number(v); row.strength_model = Number.isFinite(n) ? n : 0.0;
      writeNonClip(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sm.__ea_row = true; sm.serialize = false;
    sm.disabled = !row.enabled;

    const del = node.addWidget("button", "✕ Remove", null, () => {
      rows.splice(idx, 1);
      rebuildNonClip(node);
    });
    del.__ea_row = true; del.serialize = false;

    spacer(node, 6);
  });

  if (rows.length) spacer(node, 6);
  moveAddToBottom(node);
  resizeTight(node);
  writeNonClip(node);
}
async function ensureUINonClip(node) {
  if (!node || node.comfyClass !== "EA_PowerLora") return;

  node.__ea_rows = readNonClip(node);

  let addBtn = node.widgets?.find((w) => w.__ea_add_btn);
  if (!addBtn) {
    addBtn = node.addWidget("button", "＋ Add LoRA", null, async () => {
      if (!node.__ea_rows) node.__ea_rows = [];
      node.__ea_rows.push({ enabled: true, name: "", strength_model: 1.0 });
      await rebuildNonClip(node);
    });
    addBtn.__ea_add_btn = true;
    addBtn.serialize = false;
  }

  await rebuildNonClip(node);
}

// ---------- EA_PowerLora_CLIP ----------
function readClip(node) {
  const h = ensureHidden(node);
  try {
    const obj = JSON.parse(h.value || "{}");
    const clip_enabled = obj?.clip_enabled !== false;
    const rows = Array.isArray(obj?.rows) ? obj.rows.map((x) => ({
      enabled: x?.enabled !== false,
      name: x?.name ?? "",
      strength_model: Number.isFinite(+x?.strength_model) ? +x.strength_model : 1.0,
      strength_clip: Number.isFinite(+x?.strength_clip) ? +x.strength_clip : 1.0,
    })) : [];
    return { clip_enabled, rows };
  } catch {}
  return { clip_enabled: true, rows: [] };
}
function writeClip(node) {
  ensureHidden(node).value = JSON.stringify({
    clip_enabled: !!node.__ea_clip_enabled,
    rows: node.__ea_rows || [],
  });
  node.setDirtyCanvas(true, true);
}
async function rebuildClip(node) {
  if (!node.__ea_loras || !node.__ea_loras.length) {
    node.__ea_loras = await getLoraList();
  }
  const loras = node.__ea_loras;
  const useClip = !!node.__ea_clip_enabled;

  clearRows(node);
  const rows = node.__ea_rows || [];

  rows.forEach((row, idx) => {
    const en = node.addWidget("toggle", "On", !!row.enabled, (v) => {
      row.enabled = !!v;
      sm.disabled = !row.enabled;
      sc.disabled = !row.enabled || !useClip;
      writeClip(node);
    });
    en.__ea_row = true; en.serialize = false;

    const type = loras.length ? "combo" : "text";
    const opts = loras.length ? { values: loras } : {};
    const nameW = node.addWidget(type, "LoRA", row.name, (v) => {
      row.name = String(v || "");
      writeClip(node);
    }, opts);
    nameW.__ea_row = true; nameW.serialize = false;

    const sm = node.addWidget("number", "Model", row.strength_model, (v) => {
      const n = Number(v); row.strength_model = Number.isFinite(n) ? n : 0.0;
      writeClip(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sm.__ea_row = true; sm.serialize = false;

    const sc = node.addWidget("number", "CLIP", row.strength_clip, (v) => {
      const n = Number(v); row.strength_clip = Number.isFinite(n) ? n : 0.0;
      writeClip(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sc.__ea_row = true; sc.serialize = false;
    sc.disabled = !row.enabled || !useClip;
    setHidden(sc, !useClip);

    const del = node.addWidget("button", "✕ Remove", null, () => {
      rows.splice(idx, 1);
      rebuildClip(node);
    });
    del.__ea_row = true; del.serialize = false;

    spacer(node, 6);
  });

  if (rows.length) spacer(node, 6);
  moveAddToBottom(node);
  resizeTight(node);
  writeClip(node);
}
async function ensureUIClip(node) {
  if (!node || node.comfyClass !== "EA_PowerLora_CLIP") return;

  const st = readClip(node);
  node.__ea_clip_enabled = !!st.clip_enabled;
  node.__ea_rows = st.rows;

  let globalClip = node.widgets?.find((w) => w.__ea_global_clip);
  if (!globalClip) {
    globalClip = node.addWidget("toggle", "Apply to CLIP", node.__ea_clip_enabled, (v) => {
      node.__ea_clip_enabled = !!v;
      rebuildClip(node);
    });
    globalClip.__ea_global_clip = true;
    globalClip.serialize = false;
  } else {
    globalClip.value = node.__ea_clip_enabled;
  }

  let addBtn = node.widgets?.find((w) => w.__ea_add_btn);
  if (!addBtn) {
    addBtn = node.addWidget("button", "＋ Add LoRA", null, async () => {
      if (!node.__ea_rows) node.__ea_rows = [];
      node.__ea_rows.push({ enabled: true, name: "", strength_model: 1.0, strength_clip: 1.0 });
      await rebuildClip(node);
    });
    addBtn.__ea_add_btn = true;
    addBtn.serialize = false;
  }

  await rebuildClip(node);
}

// ---------- register both ----------
app.registerExtension({
  name: "ea.PowerLora",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name === "EA_PowerLora") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        const r = onNodeCreated?.apply(this, arguments);
        ensureUINonClip(this);
        return r;
      };
      const onConfigure = nodeType.prototype.onConfigure;
      nodeType.prototype.onConfigure = function (info) {
        const r = onConfigure?.apply(this, arguments);
        ensureUINonClip(this);
        return r;
      };
    }
    if (nodeData?.name === "EA_PowerLora_CLIP") {
      const onNodeCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        const r = onNodeCreated?.apply(this, arguments);
        ensureUIClip(this);
        return r;
      };
      const onConfigure = nodeType.prototype.onConfigure;
      nodeType.prototype.onConfigure = function (info) {
        const r = onConfigure?.apply(this, arguments);
        ensureUIClip(this);
        return r;
      };
    }
  },
  nodeCreated(node) {
    if (node?.comfyClass === "EA_PowerLora") ensureUINonClip(node);
    if (node?.comfyClass === "EA_PowerLora_CLIP") ensureUIClip(node);
  },
});
