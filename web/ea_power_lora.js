// web/ea_power_lora.js
// v0.3.2 — Shared UI for: EA_PowerLora, EA_PowerLora_CLIP, EA_PowerLora_WanVideo
// - Button at the top (just under sockets)
// - Stretches to node width and auto-grows height
// - Compact row layout; weight field narrower, always shows 2 decimals
// - Checkbox slightly larger; close button smaller and perfectly centered
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] UI v0.3.2 loaded");

async function getLoraList() {
  try {
    const r = await api.fetchApi("/models/loras");
    const j = await r.json();
    if (Array.isArray(j)) return j;
  } catch {}
  try {
    const r = await api.fetchApi("/view?type=loras");
    const j = await r.json();
    if (Array.isArray(j)) return j.map(x => x?.name).filter(Boolean);
  } catch {}
  return [];
}

function ensureHidden(node) {
  let w = node.widgets?.find(x => x.name === "loras_json");
  if (!w) {
    w = node.addWidget("text", "loras_json", "{}", () => {});
    w.serialize = true;
  }
  if (!w.__ea_hidden) {
    w.__ea_hidden = true;
    if (w.inputEl) {
      w.inputEl.style.display = "none";
      if (w.inputEl.parentElement) w.inputEl.parentElement.style.display = "none";
    }
    w.hidden = true;
    w.computeSize = function () { return [0, 0]; }; // no vertical space
  }
  return w;
}

function readRows(node, clip) {
  const h = ensureHidden(node);
  try {
    const obj = JSON.parse(h.value || "{}");
    const rows = Array.isArray(obj?.rows) ? obj.rows : [];
    return rows.map(x => ({
      enabled: x?.enabled !== false,
      name: x?.name ?? "",
      strength_model: Number.isFinite(+x?.strength_model) ? +x.strength_model : 1.0,
      strength_clip: clip ? (Number.isFinite(+x?.strength_clip) ? +x.strength_clip : 1.0) : undefined,
    }));
  } catch {}
  return [];
}
function writeRows(node, clip) {
  const rows = node.__ea_rows || [];
  const payload = clip
    ? { rows }
    : { rows: rows.map(r => ({ enabled: r.enabled, name: r.name, strength_model: r.strength_model })) };
  ensureHidden(node).value = JSON.stringify(payload);
  node.setDirtyCanvas(true, true);
}

function twoDecimalsString(v, fallback = 1.0) {
  const n = Number.parseFloat(v);
  return Number.isFinite(n) ? n.toFixed(2) : Number(fallback).toFixed(2);
}

function makeRow(node, list, row, clip, onChange) {
  const wrap = document.createElement("div");
  wrap.dataset.row = "1";
  wrap.style.display = "grid";
  // columns: [checkbox] [select expands] [model weight] [clip weight?] [del]
  wrap.style.gridTemplateColumns = clip ? "20px 1fr 56px 56px 20px" : "20px 1fr 56px 20px";
  wrap.style.alignItems = "center";
  wrap.style.gap = "6px";
  wrap.style.width = "100%";
  wrap.style.boxSizing = "border-box";

  const chk = document.createElement("input");
  chk.type = "checkbox";
  chk.checked = row.enabled !== false;
  chk.style.transform = "scale(1.15)";            // a bit larger
  chk.style.transformOrigin = "left center";
  chk.onchange = () => onChange();

  const sel = document.createElement("select");
  sel.style.width = "100%";
  sel.style.flex = "1 1 auto";
  list.forEach(n => {
    const opt = document.createElement("option"); opt.value = n; opt.textContent = n;
    if (n === row.name) opt.selected = true;
    sel.appendChild(opt);
  });
  sel.onchange = () => onChange();

  const numM = document.createElement("input");
  numM.type = "number"; numM.step = "0.05"; numM.min = "-3"; numM.max = "3";
  numM.style.width = "56px"; numM.style.textAlign = "right";
  numM.value = twoDecimalsString(row.strength_model, 1.0);
  numM.onchange = () => onChange();
  numM.onblur = () => { numM.value = twoDecimalsString(numM.value, 1.0); }; // keep 2 decimals

  let numC = null;
  if (clip) {
    numC = document.createElement("input");
    numC.type = "number"; numC.step = "0.05"; numC.min = "-3"; numC.max = "3";
    numC.style.width = "56px"; numC.style.textAlign = "right";
    numC.value = twoDecimalsString(row.strength_clip, 1.0);
    numC.onchange = () => onChange();
    numC.onblur = () => { numC.value = twoDecimalsString(numC.value, 1.0); };
  }

  const del = document.createElement("button");
  del.textContent = "×";
  del.title = "Remove";
  del.style.width = "20px";
  del.style.height = "20px";
  del.style.padding = "0";
  del.style.margin = "0";
  del.style.display = "grid";
  del.style.placeItems = "center";
  del.style.lineHeight = "1";
  del.style.fontSize = "12px";
  del.onclick = () => {
    wrap.remove();
    node.__ea_rows = (node.__ea_rows || []).filter(x => x !== row);
    writeRows(node, clip);
    app.graph.setDirtyCanvas(true, true);
  };

  if (clip) wrap.append(chk, sel, numM, numC, del);
  else wrap.append(chk, sel, numM, del);
  return { wrap, chk, sel, numM, numC };
}

function attachAutoHeight(node, box) {
  // Make the DOM widget report its actual height so the node grows as rows overflow.
  const WIDGET_MARGIN = 6; // a smidge of breathing room
  const compute = () => {
    const h = Math.ceil(box.element.scrollHeight) + WIDGET_MARGIN;
    return [node.size?.[0] || 200, h];
  };
  box.computeSize = compute;
  // Recompute on mutation
  const obs = new MutationObserver(() => { node.setDirtyCanvas(true, true); });
  obs.observe(box.element, { childList: true, subtree: true, attributes: true });
  // Also recompute on window resize (graph zoom/resize can change widths)
  window.addEventListener("resize", () => node.setDirtyCanvas(true, true));
}

async function buildUI(node, clip) {
  if (node.__ea_built) return;
  node.__ea_built = true;

  ensureHidden(node);
  node.__ea_rows = readRows(node, clip);

  // Button at the top
  const addBtn = node.addWidget("button", "＋ Add LoRA", null, async () => {
    node.__ea_rows = node.__ea_rows || [];
    node.__ea_rows.push(clip
      ? { enabled: true, name: "", strength_model: 1.0, strength_clip: 1.0 }
      : { enabled: true, name: "", strength_model: 1.0 });
    await rebuild();
  });
  addBtn.__ea_add_btn = true;
  addBtn.serialize = false;

  // Container
  const box = node.addDOMWidget("ea_rows", "ea_rows", document.createElement("div"));
  box.element.style.display = "flex";
  box.element.style.flexDirection = "column";
  box.element.style.gap = "6px";
  box.element.style.width = "100%";
  box.element.style.alignSelf = "stretch";
  box.element.style.boxSizing = "border-box";
  attachAutoHeight(node, box);

  const rebuild = async () => {
    const list = await getLoraList();
    box.element.innerHTML = "";
    (node.__ea_rows || []).forEach(row => {
      const { wrap, chk, sel, numM, numC } = makeRow(node, list, row, clip, () => {
        row.enabled = chk.checked;
        row.name = sel.value || "";
        row.strength_model = parseFloat(numM.value || "1.0");
        if (clip) row.strength_clip = parseFloat((numC?.value) || "1.0");
        writeRows(node, clip);
      });
      box.element.appendChild(wrap);
    });
    writeRows(node, clip);
    node.setDirtyCanvas(true, true); // ensure size recalculated
  };

  await rebuild();
}

app.registerExtension({
  name: "EA.PowerLora.UI",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    const name = nodeData?.name;
    const isNonClip = name === "EA_PowerLora" || name === "EA_PowerLora_WanVideo";
    const isClip = name === "EA_PowerLora_CLIP";

    if (isNonClip || isClip) {
      const onCreated = nodeType.prototype.onNodeCreated;
      nodeType.prototype.onNodeCreated = function () {
        const r = onCreated?.apply(this, arguments);
        buildUI(this, isClip);
        return r;
      };
      const onConfigure = nodeType.prototype.onConfigure;
      nodeType.prototype.onConfigure = function (info) {
        const r = onConfigure?.apply(this, arguments);
        buildUI(this, isClip);
        return r;
      };
    }
  },
  nodeCreated(node) {
    if (!node) return;
    if (node.comfyClass === "EA_PowerLora" || node.comfyClass === "EA_PowerLora_WanVideo") buildUI(node, false);
    if (node.comfyClass === "EA_PowerLora_CLIP") buildUI(node, true);
  },
});
