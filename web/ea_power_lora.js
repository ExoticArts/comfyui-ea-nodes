// web/ea_power_lora.js
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] web extension loaded");

function makeRowDefaults(name = "") {
  return { enabled: true, name, strength_model: 1.0, strength_clip: 1.0 };
}

async function fetchLoraList() {
  try {
    const resp = await api.fetchApi("/object_info");
    const data = await resp.json();
    const loras = (data?.models?.loras ?? []);
    return Array.isArray(loras) ? loras : [];
  } catch { return []; }
}

function syncToHiddenJSON(node) {
  const rows = node.__ea_rows || [];
  const payload = JSON.stringify(rows);
  const hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (hidden) hidden.value = payload;
  node.setDirtyCanvas(true, true);
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

function removeRowWidgets(node) {
  node.widgets = (node.widgets || []).filter((w) => !w.__ea_row);
}

function openQuickPick(node, loraList, onPick) {
  // simple overlay picker with filter
  const overlay = document.createElement("div");
  overlay.style.position = "fixed";
  overlay.style.inset = "0";
  overlay.style.background = "rgba(0,0,0,0.2)";
  overlay.style.zIndex = 10000;

  const panel = document.createElement("div");
  panel.style.position = "absolute";
  panel.style.left = "50%";
  panel.style.top = "20%";
  panel.style.transform = "translateX(-50%)";
  panel.style.minWidth = "420px";
  panel.style.maxHeight = "50vh";
  panel.style.overflow = "auto";
  panel.style.background = "var(--bg-color, #222)";
  panel.style.border = "1px solid var(--color-border, #444)";
  panel.style.borderRadius = "8px";
  panel.style.boxShadow = "0 8px 24px rgba(0,0,0,0.35)";

  const input = document.createElement("input");
  input.type = "text";
  input.placeholder = "Filter LoRAs…";
  input.style.width = "100%";
  input.style.boxSizing = "border-box";
  input.style.padding = "10px 12px";
  input.style.border = "0";
  input.style.borderBottom = "1px solid var(--color-border, #444)";
  input.style.background = "transparent";
  input.style.color = "var(--color-text, #ddd)";

  const list = document.createElement("div");
  list.style.padding = "6px 0";

  panel.appendChild(input);
  panel.appendChild(list);
  overlay.appendChild(panel);
  document.body.appendChild(overlay);

  const makeRow = (name) => {
    const item = document.createElement("div");
    item.textContent = name;
    item.style.padding = "8px 12px";
    item.style.cursor = "pointer";
    item.onmouseenter = () => item.style.background = "rgba(255,255,255,0.06)";
    item.onmouseleave = () => item.style.background = "transparent";
    item.onclick = () => { onPick(name); close(); };
    return item;
  };

  const render = () => {
    list.innerHTML = "";
    const q = input.value.toLowerCase();
    (loraList || []).filter(n => !q || n.toLowerCase().includes(q)).slice(0, 500)
      .forEach(n => list.appendChild(makeRow(n)));
    if (!list.childElementCount) {
      const empty = document.createElement("div");
      empty.textContent = "No matches. Press Esc to cancel.";
      empty.style.opacity = "0.6";
      empty.style.padding = "10px 12px";
      list.appendChild(empty);
    }
  };

  const close = () => {
    document.removeEventListener("keydown", onKey);
    overlay.remove();
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
  document.addEventListener("keydown", onKey);
  input.addEventListener("input", render);
  overlay.addEventListener("click", (e) => { if (e.target === overlay) close(); });

  input.focus();
  render();
}

function rebuildRows(node, loraList) {
  removeRowWidgets(node);

  const rows = node.__ea_rows || [];
  rows.forEach((row, idx) => {
    const label = `LoRA #${idx + 1}`;

    // Enable toggle
    const en = node.addWidget("toggle", "Enable", !!row.enabled, (v) => {
      row.enabled = !!v;
      syncToHiddenJSON(node);
    });
    en.__ea_row = true;
    en.serialize = false;

    // Name (combo if list available)
    const values = Array.isArray(loraList) && loraList.length ? loraList : null;
    const nameWidget = node.addWidget(values ? "combo" : "text", label, row.name, (v) => {
      row.name = v || "";
      syncToHiddenJSON(node);
    }, values ? { values } : {});
    nameWidget.__ea_row = true;
    nameWidget.serialize = false;
    nameWidget.options = nameWidget.options || {};
    nameWidget.options.placeholder = "example.safetensors";

    // Strength model
    const sm = node.addWidget("number", "Strength (Model)", row.strength_model, (v) => {
      const n = Number(v);
      row.strength_model = Number.isFinite(n) ? n : 0.0;
      syncToHiddenJSON(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sm.__ea_row = true; sm.serialize = false;

    // Strength clip
    const sc = node.addWidget("number", "Strength (CLIP)", row.strength_clip, (v) => {
      const n = Number(v);
      row.strength_clip = Number.isFinite(n) ? n : 0.0;
      syncToHiddenJSON(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sc.__ea_row = true; sc.serialize = false;

    // Delete button
    const del = node.addWidget("button", "🗑 Remove", null, () => {
      rows.splice(idx, 1);
      rebuildRows(node, loraList);
    });
    del.__ea_row = true; del.serialize = false;
  });

  syncToHiddenJSON(node);
}

async function ensureUI(node) {
  if (!node || node.comfyClass !== "EA_PowerLora") return;

  const hidden = ensureHiddenJSON(node);

  // parse existing rows from hidden json
  try {
    const parsed = JSON.parse(hidden.value || "[]");
    node.__ea_rows = Array.isArray(parsed)
      ? parsed.map(x => ({
          enabled: x?.enabled !== false, // default true
          name: x?.name ?? "",
          strength_model: Number(x?.strength_model ?? 1.0),
          strength_clip: Number(x?.strength_clip ?? 1.0),
        }))
      : [];
  } catch { node.__ea_rows = []; }

  // add the real “＋ Add LoRA” button (don’t rename it!)
  let addBtn = node.widgets?.find((w) => w.__ea_add_btn);
  if (!addBtn) {
    addBtn = node.addWidget("button", "＋ Add LoRA", null, () => {
      const list = node.__ea_lora_list || [];
      if (Array.isArray(list) && list.length) {
        openQuickPick(node, list, (picked) => {
          if (!node.__ea_rows) node.__ea_rows = [];
          node.__ea_rows.push(makeRowDefaults(picked));
          rebuildRows(node, list);
        });
      } else {
        // no list? just add an empty row
        if (!node.__ea_rows) node.__ea_rows = [];
        node.__ea_rows.push(makeRowDefaults(""));
        rebuildRows(node, []);
      }
    });
    addBtn.__ea_add_btn = true;
    addBtn.serialize = false;
  }

  node.__ea_lora_list = await fetchLoraList();
  rebuildRows(node, node.__ea_lora_list);
}

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
