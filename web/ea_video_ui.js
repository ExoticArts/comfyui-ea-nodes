// web/ea_video_ui.js
// Folder picker for EA List Videos & EA Video Load.
// - Uses native ComfyWidgets.FOLDER when present (true folder browser).
// - Otherwise adds a normal canvas "Pick Folder" button (full width, default style).

import { app } from "/scripts/app.js";
import { ComfyWidgets } from "/scripts/widgets.js";

const TARGET_CLASSES = new Set(["EA_ListVideos", "EA_VideoLoad"]);
const CANDIDATE_NAMES = ["path", "root", "dir", "folder", "directory", "base"];

function findPathWidget(node) {
  if (!node.widgets || node.widgets.length === 0) return null;

  // Prefer known names
  for (const name of CANDIDATE_NAMES) {
    const w = node.widgets.find((x) => x && x.name === name);
    if (w) return w;
  }
  // Otherwise first text-like widget
  return node.widgets.find(
    (x) => x && (x.type === "text" || x.type === "STRING" || typeof x.value === "string")
  ) || null;
}

function replaceWithFolderWidget(node, w, idx) {
  // Replace the plain text path with ComfyUI's folder widget
  const inputName = w.name || "path";
  const inputData = { default: w.value ?? "", widget: { value: w.value ?? "" } };

  node.widgets.splice(idx, 1); // remove original
  const fol = ComfyWidgets.FOLDER(node, inputName, inputData, app);
  fol.name = inputName;
  fol.__ea_folderized = true;

  node.widgets.splice(idx, 0, fol); // insert in same place
  node.setSize(node.computeSize());
}

function addCanvasPickButton(node, w) {
  if (w.__ea_folderized) return;
  w.__ea_folderized = true;

  // Default canvas-styled full-width button (fits theme, no extra margins)
  const btn = node.addWidget("button", "📁 Pick Folder", null, () => {
    const v = window.prompt("Folder path on the server:", String(w.value ?? ""));
    if (v != null) {
      w.value = v;
      node.setDirtyCanvas(true, true);
    }
  });
  btn.serialize = false; // don't save the button itself into the workflow
}

function folderize(node) {
  if (!TARGET_CLASSES.has(node.comfyClass)) return;
  const w = findPathWidget(node);
  if (!w || w.__ea_folderized) return;

  const idx = node.widgets.indexOf(w);
  if (idx < 0) return;

  if (ComfyWidgets && typeof ComfyWidgets.FOLDER === "function") {
    replaceWithFolderWidget(node, w, idx);
  } else {
    addCanvasPickButton(node, w);
  }
}

app.registerExtension({
  name: "ea.video.folderpicker",
  beforeRegisterNodeDef(nodeType, nodeData) {
    if (!TARGET_CLASSES.has(nodeData?.name)) return;

    const onCreated = nodeType.prototype.onNodeCreated;
    nodeType.prototype.onNodeCreated = function () {
      const r = onCreated?.apply(this, arguments);
      folderize(this);
      return r;
    };

    const onConfigure = nodeType.prototype.onConfigure;
    nodeType.prototype.onConfigure = function (info) {
      const r = onConfigure?.apply(this, arguments);
      folderize(this);
      return r;
    };
  },
});
