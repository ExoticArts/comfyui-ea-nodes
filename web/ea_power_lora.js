// web/ea_power_lora.js
// v0.2.0 experimental — stable native UI, no legacy shapes
// Registers UI for: EA_PowerLora, EA_PowerLora_CLIP, EA_PowerLora_WanVideo

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
    // fallback for older Comfy versions
    const r = await api.fetchApi("/view?type=loras");
    const j = await r.json();
    if (Array.isArray(j)) return j.map((x) => x?.name).filter(Boolean);
  } catch {}
  return [];
}

function ensureHidden(node) {
  let widget = node.widgets?.find((w) => w.name === "loras_json");
  if (!widget) {
    widget = node.addWidget("text", "loras_json", "{}", () => {});
    widget.serialize = true;
  }
  if (!widget.__ea_hidden) {
    widget.__ea_hidden = true;
    widget.inputEl.style.display = "none";
    widget.inputEl.parentElement.style.display = "none";
    widget.hidden = true;
    widget.computeSize = function () {
      if (this.hidden) return [0, 0];
      return this.__ea_orig_cs ? this.__ea_orig_cs.apply(this, arguments) : [0, 20];
    };
  }
  return widget;
}

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
}

function makeRow(node, list, row, onChange) {
  const wrap = document.createElement("div");
  wrap.style.display = "flex";
  wrap.style.alignItems = "center";
  wrap.style.gap = "6px";

  const chk = document.createElement("input");
  chk.type = "checkbox";
  chk.checked = row.enabled !== false;
  chk.onchange = () => onChange();

  const sel = document.createElement("select");
  list.forEach((n) => {
    const opt = document.createElement("option");
    opt.value = n;
    opt.textContent = n;
    if (n === row.name) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.onchange = () => onChange();

  const num = document.createElement("input");
  num.type = "number";
  num.step = "0.05";
  num.min = "-3";
  num.max = "3";
  num.value = String(Number.isFinite(+row.strength_model) ? +row.strength_model : 1.0);
  num.onchange = () => onChange();

  const del = document.createElement("button");
  del.textContent = "✕";
  del.onclick = () => {
    wrap.remove();
    node.__ea_rows = [...(node.__ea_rows || [])].filter((x) => x !== row);
    writeNonClip(node);
    app.graph.setDirtyCanvas(true, true);
  };

  wrap.append(chk, sel, num, del);
  return { wrap, chk, sel, num };
}

function ensureUINonClip(node) {
  if (node.__ea_built) return;
  node.__ea_built = true;

  ensureHidden(node);
  node.__ea_rows = readNonClip(node);

  // Container
  const box = node.addDOMWidget("ea_rows", "ea_rows", document.createElement("div"));
  box.element.style.display = "flex";
  box.element.style.flexDirection = "column";
  box.element.style.gap = "6px";

  const listPromise = getLoraList();

  const rebuild = async () => {
    const list = await listPromise;
    box.element.innerHTML = "";
    node.__ea_rows.forEach((row) => {
      const { wrap, chk, sel, num } = makeRow(node, list, row, () => {
        row.enabled = chk.checked;
        row.name = sel.value || "";
        row.strength_model = parseFloat(num.value || "1.0");
        writeNonClip(node);
      });
      box.element.appendChild(wrap);
    });
    writeNonClip(node);
  };

  // Add btn
  const addBtn = node.addWidget("button", "＋ Add LoRA", null, async () => {
    if (!node.__ea_rows) node.__ea_rows = [];
    node.__ea_rows.push({ enabled: true, name: "", strength_model: 1.0 });
    await rebuild();
  });
  addBtn.__ea_add_btn = true;

  rebuild();
}

function readClip(node) {
  const h = ensureHidden(node);
  try {
    const obj = JSON.parse(h.value || "{}");
    const rows = Array.isArray(obj?.rows) ? obj.rows : [];
    return {
      clip_enabled: obj?.clip_enabled !== false,
      rows: rows.map((x) => ({
        enabled: x?.enabled !== false,
        name: x?.name ?? "",
        strength_model: Number.isFinite(+x?.strength_model) ? +x.strength_model : 1.0,
        strength_clip: Number.isFinite(+x?.strength_clip) ? +x.strength_clip : 1.0,
      })),
    };
  } catch {}
  return { clip_enabled: true, rows: [] };
}
function writeClip(node) {
  ensureHidden(node).value = JSON.stringify({
    clip_enabled: !!node.__ea_clip_enabled,
    rows: node.__ea_rows || [],
  });
}

function ensureUIClip(node) {
  if (node.__ea_built) return;
  node.__ea_built = true;

  ensureHidden(node);
  const initial = readClip(node);
  node.__ea_rows = initial.rows || [];
  node.__ea_clip_enabled = !!initial.clip_enabled;

  const box = node.addDOMWidget("ea_rows", "ea_rows", document.createElement("div"));
  box.element.style.display = "flex";
  box.element.style.flexDirection = "column";
  box.element.style.gap = "6px";

  const listPromise = getLoraList();

  const rebuildClip = async () => {
    const list = await listPromise;
    box.element.innerHTML = "";
    node.__ea_rows.forEach((row) => {
      const { wrap, chk, sel, num } = makeRow(node, list, row, () => {
        row.enabled = chk.checked;
        row.name = sel.value || "";
        row.strength_model = parseFloat(num.value || "1.0");
        writeClip(node);
      });

      // extra input for clip strength
      const numClip = document.createElement("input");
      numClip.type = "number";
      numClip.step = "0.05";
      numClip.min = "-3";
      numClip.max = "3";
      numClip.value = String(Number.isFinite(+row.strength_clip) ? +row.strength_clip : 1.0);
      numClip.onchange = () => {
        row.strength_clip = parseFloat(numClip.value || "1.0");
        writeClip(node);
      };

      wrap.insertBefore(numClip, wrap.lastChild); // before delete button
      box.element.appendChild(wrap);
    });
    writeClip(node);
  };

  // Global CLIP toggle
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
  }

  rebuildClip();
}

app.registerExtension({
  name: "ea.PowerLora",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name === "EA_PowerLora" || nodeData?.name === "EA_PowerLora_WanVideo") {
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
    if (node?.comfyClass === "EA_PowerLora" || node?.comfyClass === "EA_PowerLora_WanVideo") ensureUINonClip(node);
    if (node?.comfyClass === "EA_PowerLora_CLIP") ensureUIClip(node);
  },
});
