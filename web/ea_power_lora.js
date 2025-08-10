// web/ea_power_lora.js
// Client-side extension for EA_PowerLora:
// - Adds "Add LoRA" button
// - Renders N rows (lora name + strengths)
// - Packs rows into hidden loras_json STRING

import { app } from "/scripts/app.js";
import { api } from "/scripts/api.js";

console.log("[EA Power LoRA] web extension loaded");

function makeRowDefaults() {
  return {
    name: "",
    strength_model: 1.0,
    strength_clip: 1.0,
  };
}

async function fetchLoraList() {
  // Pull from ComfyUI's object info
  // Fallback to empty array if endpoint shape changes
  try {
    const resp = await api.fetchApi("/object_info");
    const data = await resp.json();
    // Typical key: data?.models?.loras
    const loras = (data?.models?.loras ?? []);
    // Return array of strings
    return Array.isArray(loras) ? loras : [];
  } catch (e) {
    console.warn("[EA Power LoRA] Could not fetch lora list", e);
    return [];
  }
}

function syncToHiddenJSON(node) {
  // Collect our rows from node.__ea_rows
  const rows = node.__ea_rows || [];
  const payload = JSON.stringify(rows);
  // Write into the hidden STRING widget called 'loras_json'
  const hidden = node.widgets?.find((w) => w.name === "loras_json");
  if (hidden) {
    hidden.value = payload;
  }
  // Force redraw
  node.setDirtyCanvas(true, true);
}

function addRow(node, loraList) {
  if (!node.__ea_rows) node.__ea_rows = [];
  node.__ea_rows.push(makeRowDefaults());
  rebuildRows(node, loraList);
}

function deleteRow(node, idx, loraList) {
  if (!node.__ea_rows) return;
  node.__ea_rows.splice(idx, 1);
  rebuildRows(node, loraList);
}

function rebuildRows(node, loraList) {
  // remove prior UI widgets except hidden json + add button
  const preserved = ["loras_json", "__add_lora_btn"];
  node.widgets = node.widgets?.filter((w) => preserved.includes(w.name)) ?? [];

  const rows = node.__ea_rows || [];

  rows.forEach((row, idx) => {
    // LoRA name (combo if possible, string fallback)
    const label = `LoRA #${idx + 1}`;
    const values = Array.isArray(loraList) && loraList.length ? loraList : null;

    const nameWidget = node.addWidget(values ? "combo" : "text", label, row.name, (v) => {
      row.name = v;
      syncToHiddenJSON(node);
    }, values ? { values } : {});

    nameWidget.serialize = false; // we serialize via hidden JSON
    nameWidget.tooltip = "Select or type a LoRA filename in the /loras folder";
    nameWidget.options = nameWidget.options || {};
    nameWidget.options.placeholder = "example.safetensors";

    // strength_model
    const sm = node.addWidget("number", "Strength (Model)", row.strength_model, (v) => {
      row.strength_model = Number(v) || 0.0;
      syncToHiddenJSON(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sm.serialize = false;

    // strength_clip
    const sc = node.addWidget("number", "Strength (CLIP)", row.strength_clip, (v) => {
      row.strength_clip = Number(v) || 0.0;
      syncToHiddenJSON(node);
    }, { min: 0.0, max: 2.0, step: 0.05 });
    sc.serialize = false;

    // delete button
    const del = node.addWidget("button", "🗑 Remove", null, () => {
      deleteRow(node, idx, loraList);
    });
    del.serialize = false;
  });

  syncToHiddenJSON(node);
}

app.registerExtension({
  name: "ea.PowerLora",
  async beforeRegisterNodeDef(nodeType, nodeData) {
    if (nodeData?.name !== "EA_PowerLora") return;

    const onNodeCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = async function () {
      const r = onNodeCreated?.apply(this, arguments);

      // Ensure hidden JSON widget exists
      let hidden = this.widgets?.find((w) => w.name === "loras_json");
      if (!hidden) {
        hidden = this.addWidget("text", "loras_json", "[]", () => {});
        hidden.hidden = true;
        hidden.name = "loras_json";
      } else {
        hidden.hidden = true;
      }

      // Add button (preserved across rebuilds)
      let addBtn = this.widgets?.find((w) => w.name === "__add_lora_btn");
      if (!addBtn) {
        addBtn = this.addWidget("button", "＋ Add LoRA", null, () => {
          addRow(this, this.__ea_lora_list);
        });
        addBtn.name = "__add_lora_btn";
      }

      // Restore rows from hidden json (if any)
      try {
        const parsed = JSON.parse(hidden.value || "[]");
        if (Array.isArray(parsed)) {
          this.__ea_rows = parsed.map((x) => ({
            name: x?.name ?? "",
            strength_model: Number(x?.strength_model ?? 1.0),
            strength_clip: Number(x?.strength_clip ?? 1.0),
          }));
        }
      } catch {
        this.__ea_rows = [];
      }

      // Fetch lora list and render
      this.__ea_lora_list = await fetchLoraList();
      rebuildRows(this, this.__ea_lora_list);

      return r;
    };

    // When loading a workflow, rebuild UI
    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (info) {
      const r = onConfigure?.apply(this, arguments);
      const hidden = this.widgets?.find((w) => w.name === "loras_json");
      try {
        const parsed = JSON.parse(hidden?.value || "[]");
        if (Array.isArray(parsed)) {
          this.__ea_rows = parsed;
        }
      } catch { /* ignore */ }
      (async () => {
        this.__ea_lora_list = await fetchLoraList();
        rebuildRows(this, this.__ea_lora_list);
      })();
      return r;
    };
  },
});
