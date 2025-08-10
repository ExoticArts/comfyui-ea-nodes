// web/ea_power_lora.js
import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] web extension loaded");

function makeRowDefaults() {
  return { name: "", strength_model: 1.0, strength_clip: 1.0 };
}

async function fetchLoraList() {
  try {
    const resp = await api.fetchApi("/object_info");
    const data = await resp.json();
    const loras = (data?.models?.loras ?? []);
    return Array.isArray(loras) ? loras : [];
  } catch {
    return [];
  }
}

function syncToHiddenJSON(node) {
  const rows = node.__ea_rows || [];
  const payload = JSON.stringify(rows);
  const hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (hidden) hidden.value = payload;
  node.setDirtyCanvas(true, true);
}

function rebuildRows(node, loraList) {
  const preserved = ["loras_json", "__add_lora_btn"];
  node.widgets = node.widgets?.filter((w) => preserved.includes(w.name)) ?? [];

  const rows = node.__ea_rows || [];
  rows.forEach((row, idx) => {
    const label = `LoRA #${idx + 1}`;
    const values = Array.isArray(loraList) && loraList.length ? loraList : null;

    const nameWidget = node.addWidget(values ? "combo" : "text", label, row.name, (v) => {
      row.name = v;
      syncToHiddenJSON(node);
    }, values ? { values } : {});
    nameWidget.serialize = false;
    nameWidget.tooltip = "Select or type a LoRA filename from /models/loras";
    nameWidget.options = nameWidget.options || {};
    nameWidget.options.placeholder = "example.safetensors";

    const sm = node.addWidget("number", "Strength (Model)", row.strength_model, (v) => {
      const n = Number(v);
      row.strength_model = Number.isFinite(n) ? n : 0.0;
      syncToHiddenJSON(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sm.serialize = false;

    const sc = node.addWidget("number", "Strength (CLIP)", row.strength_clip, (v) => {
      const n = Number(v);
      row.strength_clip = Number.isFinite(n) ? n : 0.0;
      syncToHiddenJSON(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sc.serialize = false;

    const del = node.addWidget("button", "🗑 Remove", null, () => {
      node.__ea_rows.splice(idx, 1);
      rebuildRows(node, loraList);
    });
    del.serialize = false;
  });

  syncToHiddenJSON(node);
}

async function ensureUI(node) {
  if (!node || node.comfyClass !== "EA_PowerLora") return;

  let hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (!hidden) {
    hidden = node.addWidget("text", "loras_json", "[]", () => {});
    hidden.hidden = true;
    hidden.name = "loras_json";
  } else {
    hidden.hidden = true;
  }

  let addBtn = node.widgets?.find((w) => w.name === "__add_lora_btn");
  if (!addBtn) {
    addBtn = node.addWidget("button", "＋ Add LoRA", null, () => {
      if (!node.__ea_rows) node.__ea_rows = [];
      node.__ea_rows.push(makeRowDefaults());
      rebuildRows(node, node.__ea_lora_list || []);
    });
    addBtn.name = "__add_lora_btn";
  }

  try {
    const parsed = JSON.parse(hidden.value || "[]");
    if (Array.isArray(parsed)) {
      node.__ea_rows = parsed.map((x) => ({
        name: x?.name ?? "",
        strength_model: Number(x?.strength_model ?? 1.0),
        strength_clip: Number(x?.strength_clip ?? 1.0),
      }));
    } else {
      node.__ea_rows = [];
    }
  } catch {
    node.__ea_rows = [];
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
  nodeCreated(node) {
    // Also patch nodes created before our extension loaded
    ensureUI(node);
  },
});
