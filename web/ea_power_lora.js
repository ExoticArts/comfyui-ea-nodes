// web/ea_power_lora.js
// v0.4.0 — DOM header row (precise spacing), same compact layout
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] UI v0.4.0 loaded");

const GAP   = 6;
const CHK_W = 20;
const DEL_W = 20;
const NUM_W = 68;
const ROW_H = 28;

// header nudges to match your alignment
const SHIFT_LORA = 14;  // push LoRA label right a bit
const SHIFT_NUM  = -6;  // pull Model/CLIP slightly left

async function getLoraList() {
  try { const r = await api.fetchApi("/models/loras"); const j = await r.json(); if (Array.isArray(j)) return j; } catch {}
  try { const r = await api.fetchApi("/view?type=loras"); const j = await r.json(); if (Array.isArray(j)) return j.map(x => x?.name).filter(Boolean); } catch {}
  return [];
}

/* ---------- hidden JSON ---------- */
function ensureHidden(node){
  let w = node.widgets?.find(x => x.name === "loras_json");
  if (!w) { w = node.addWidget("text","loras_json","{}",()=>{}); w.serialize = true; }
  if (!w.__ea_hidden) {
    w.__ea_hidden = true;
    if (w.inputEl) {
      w.inputEl.style.display = "none";
      if (w.inputEl.parentElement) w.inputEl.parentElement.style.display = "none";
    }
    w.hidden = true;
    w.computeSize = () => [0, 0];
  }
  return w;
}
function readRows(node, clip){
  const h = ensureHidden(node);
  try {
    const o = JSON.parse(h.value || "{}");
    const rows = Array.isArray(o?.rows) ? o.rows : [];
    return rows.map(x => ({
      enabled: x?.enabled !== false,
      name: x?.name ?? "",
      strength_model: Number.isFinite(+x?.strength_model) ? +x?.strength_model : 1.0,
      strength_clip: clip ? (Number.isFinite(+x?.strength_clip) ? +x?.strength_clip : 1.0) : undefined,
    }));
  } catch {}
  return [];
}
function writeRows(node, clip){
  const rows = node.__ea_rows || [];
  const payload = clip ? { rows } : { rows: rows.map(r => ({ enabled: r.enabled, name: r.name, strength_model: r.strength_model })) };
  ensureHidden(node).value = JSON.stringify(payload);
  node.setDirtyCanvas(true, true);
}

/* ---------- helpers ---------- */
const twoDecimals = (v, fallback = 1.0) => {
  const n = Number.parseFloat(v);
  return Number.isFinite(n) ? n.toFixed(2) : Number(fallback).toFixed(2);
};

/* ---------- DOM header row ---------- */
function makeHeaderRow(clip) {
  const header = document.createElement("div");
  header.dataset.header = "1";
  header.style.display = "grid";
  header.style.gridTemplateColumns = clip
    ? `${CHK_W}px 1fr ${NUM_W}px ${NUM_W}px ${DEL_W}px`
    : `${CHK_W}px 1fr ${NUM_W}px ${DEL_W}px`;
  header.style.columnGap = `${GAP}px`;
  header.style.alignItems = "center";
  header.style.width = "100%";
  header.style.boxSizing = "border-box";
  header.style.margin = "2px 0 2px 0";      // tight top/bottom spacing

  const spacer = document.createElement("div"); // checkbox column spacer
  const lora = document.createElement("div");
  lora.textContent = "LoRA";
  lora.style.color = "#9aa0a6";
  lora.style.paddingLeft = `${SHIFT_LORA}px`;

  const model = document.createElement("div");
  model.textContent = "Model";
  model.style.color = "#9aa0a6";
  model.style.paddingLeft = `${Math.max(0, SHIFT_NUM)}px`; // if negative, zero for DOM
  model.style.textAlign = "left";

  header.append(spacer, lora, model);

  if (clip) {
    const clipLbl = document.createElement("div");
    clipLbl.textContent = "CLIP";
    clipLbl.style.color = "#9aa0a6";
    clipLbl.style.paddingLeft = `${Math.max(0, SHIFT_NUM)}px`;
    clipLbl.style.textAlign = "left";
    header.append(clipLbl);
  }

  // delete column spacer
  header.append(document.createElement("div"));
  return header;
}

/* ---------- row DOM ---------- */
function makeRow(node, list, row, clip, onChange){
  const wrap = document.createElement("div");
  wrap.style.display = "grid";
  wrap.style.gridTemplateColumns = clip
    ? `${CHK_W}px 1fr ${NUM_W}px ${NUM_W}px ${DEL_W}px`
    : `${CHK_W}px 1fr ${NUM_W}px ${DEL_W}px`;
  wrap.style.columnGap = `${GAP}px`;
  wrap.style.alignItems = "center";
  wrap.style.width = "100%";
  wrap.style.boxSizing = "border-box";

  const chk = document.createElement("input");
  chk.type = "checkbox";
  chk.checked = row.enabled !== false;
  chk.style.transform = "scale(1.15)";
  chk.style.transformOrigin = "left center";
  chk.style.height = `${ROW_H}px`;
  chk.onchange = () => onChange();

  const sel = document.createElement("select");
  sel.style.width = "100%";
  sel.style.flex = "1 1 auto";
  sel.style.height = `${ROW_H}px`;
  list.forEach(n => { const o = document.createElement("option"); o.value = n; o.textContent = n; if (n === row.name) o.selected = true; sel.appendChild(o); });
  sel.onchange = () => onChange();

  const numM = document.createElement("input");
  numM.type = "number"; numM.step = "0.05"; numM.min = "-3"; numM.max = "3";
  numM.style.width = `${NUM_W}px`;
  numM.style.height = `${ROW_H}px`;
  numM.style.textAlign = "left";
  numM.style.paddingLeft = "6px";
  numM.style.paddingRight = "12px"; // keep away from spinner
  numM.style.boxSizing = "border-box";
  numM.value = twoDecimals(row.strength_model, 1.0);
  numM.onchange = () => onChange();
  numM.onblur = () => { numM.value = twoDecimals(numM.value, 1.0); };

  let numC = null;
  if (clip) {
    numC = document.createElement("input");
    numC.type = "number"; numC.step = "0.05"; numC.min = "-3"; numC.max = "3";
    numC.style.width = `${NUM_W}px`;
    numC.style.height = `${ROW_H}px`;
    numC.style.textAlign = "left";
    numC.style.paddingLeft = "6px";
    numC.style.paddingRight = "12px";
    numC.style.boxSizing = "border-box";
    numC.value = twoDecimals(row.strength_clip, 1.0);
    numC.onchange = () => onChange();
    numC.onblur = () => { numC.value = twoDecimals(numC.value, 1.0); };
  }

  const del = document.createElement("button");
  del.textContent = "×";
  del.title = "Remove";
  del.style.width = `${DEL_W}px`;
  del.style.height = `${DEL_W}px`;
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
  else      wrap.append(chk, sel, numM, del);
  return { wrap, chk, sel, numM, numC };
}

/* ---------- auto-height ---------- */
function attachAutoHeight(node, box){
  box.computeSize = () => [node.size?.[0] || 200, Math.ceil(box.element.scrollHeight) + GAP];
  const obs = new MutationObserver(() => node.setDirtyCanvas(true, true));
  obs.observe(box.element, { childList: true, subtree: true, attributes: true });
  window.addEventListener("resize", () => node.setDirtyCanvas(true, true));
}

/* ---------- main UI ---------- */
async function buildUI(node, clip){
  if (node.__ea_built) return;
  node.__ea_built = true;

  ensureHidden(node);
  node.__ea_rows = readRows(node, clip);

  // Add button at the top
  let addBtn = node.widgets?.find(w => w.__ea_add_btn);
  if (!addBtn) {
    addBtn = node.addWidget("button", "＋ Add LoRA", null, async () => {
      node.__ea_rows = node.__ea_rows || [];
      node.__ea_rows.push(clip
        ? { enabled: true, name: "", strength_model: 1.0, strength_clip: 1.0 }
        : { enabled: true, name: "", strength_model: 1.0 });
      await rebuild();
    });
    addBtn.__ea_add_btn = true;
    addBtn.serialize = false;
  }

  // Rows container (we'll put the DOM header inside this)
  const box = node.addDOMWidget("ea_rows","ea_rows",document.createElement("div"));
  box.element.style.display = "flex";
  box.element.style.flexDirection = "column";
  box.element.style.gap = `${GAP}px`;
  box.element.style.width = "100%";
  box.element.style.alignSelf = "stretch";
  box.element.style.boxSizing = "border-box";
  attachAutoHeight(node, box);

  // Build/rebuild content
  const rebuild = async () => {
    const list = await getLoraList();
    box.element.innerHTML = "";

    // Header row only when we have at least one LoRA
    if ((node.__ea_rows?.length || 0) > 0) {
      const hdr = makeHeaderRow(clip);
      box.element.appendChild(hdr);
    }

    (node.__ea_rows || []).forEach(row => {
      const { wrap, chk, sel, numM, numC } = makeRow(node, list, row, clip, () => {
        row.enabled = chk.checked;
        row.name = sel.value || "";
        row.strength_model = parseFloat(numM.value || "1.00");
        if (clip) row.strength_clip = parseFloat((numC?.value) || "1.00");
        writeRows(node, clip);
      });
      box.element.appendChild(wrap);
    });

    writeRows(node, clip);
    node.setDirtyCanvas(true, true);
  };

  await rebuild();
}

/* ---------- register ---------- */
app.registerExtension({
  name: "EA.PowerLora.UI",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    const name = nodeData?.name;
    const isNonClip = name === "EA_PowerLora" || name === "EA_PowerLora_WanVideo";
    const isClip = name === "EA_PowerLora_CLIP";
    if (!isNonClip && !isClip) return;

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
  },
  nodeCreated(node) {
    if (!node) return;
    if (node.comfyClass === "EA_PowerLora" || node.comfyClass === "EA_PowerLora_WanVideo") buildUI(node, false);
    if (node.comfyClass === "EA_PowerLora_CLIP") buildUI(node, true);
  },
});
