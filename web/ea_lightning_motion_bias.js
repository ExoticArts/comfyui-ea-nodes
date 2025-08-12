// EA Motion Bias (Lightning) — JS preset dropdown + colored overlay + autosize
// - Visible "preset" dropdown (JS-only) at the bottom; Python preset is hidden/renamed.
// - Picking a preset pushes values into widgets (+fires callbacks). Editing any tuning field flips to Custom.
// - Overlay highlights scheduler + cfg lines to signal "set these manually" and uses space-separated lists.
// - Wrapped in an IIFE to avoid redeclare errors.

import { app } from "/scripts/app.js";

(() => {
  const clamp = (x, lo, hi) => Math.max(lo, Math.min(hi, x));
  const lerp  = (a, b, t) => a + (b - a) * t;
  const round5 = (x) => parseFloat(x.toFixed(5));

  // Presets (numbers pushed into widgets & shown in overlay)
  const PRESETS = {
    "Lightning Default 2/2": {
      steps: 4, split: 2,
      sigmas: [1.0, 0.9375, 0.83333, 0.625, 0.0],
      high: 1.0, low: 1.0,
      cfgHigh: 1.0, cfgLow: 1.0,
      addNoiseHigh: false, addNoiseLow: false,
      scheduler: "euler",
      widgets: { steps: 4, motion_bias: 0.00, profile: "hold_high", base_high: 1.00, base_low: 1.00, min_low_steps: 2 },
    },
    "Aggressive 3/2": {
      steps: 5, split: 3,
      sigmas: [1.0, 0.95, 0.85, 0.70, 0.55, 0.0],
      high: 1.25, low: 1.00,
      cfgHigh: 0.80, cfgLow: 1.00,
      addNoiseHigh: true, addNoiseLow: false,
      scheduler: "dpm++_sde",
      widgets: { steps: 5, motion_bias: 0.80, profile: "big_drop", base_high: 1.04, base_low: 1.14, min_low_steps: 2 },
    },
    "Balanced 3/2": {
      steps: 5, split: 3,
      sigmas: [1.0, 0.97, 0.92, 0.78, 0.60, 0.0],
      high: 1.22, low: 1.05,
      cfgHigh: 0.85, cfgLow: 1.02,
      addNoiseHigh: true, addNoiseLow: false,
      scheduler: "dpm++_sde/beta",
      widgets: { steps: 5, motion_bias: 0.70, profile: "hold_high", base_high: 1.10, base_low: 1.10, min_low_steps: 2 },
    },
    "Speedrun 4/1": {
      steps: 5, split: 4,
      sigmas: [1.0, 0.94, 0.80, 0.64, 0.50, 0.0],
      high: 1.28, low: 0.95,
      cfgHigh: 0.78, cfgLow: 0.98,
      addNoiseHigh: true, addNoiseLow: false,
      scheduler: "dpm++_sde",
      widgets: { steps: 5, motion_bias: 0.90, profile: "big_drop", base_high: 1.05, base_low: 1.10, min_low_steps: 1 },
    },
    "Detail 6/2": {
      steps: 6, split: 4,
      sigmas: [1.0, 0.97, 0.93, 0.80, 0.62, 0.50, 0.0],
      high: 1.20, low: 1.08,
      cfgHigh: 0.85, cfgLow: 1.05,
      addNoiseHigh: true, addNoiseLow: false,
      scheduler: "dpm++_sde/beta",
      widgets: { steps: 6, motion_bias: 0.65, profile: "hold_high", base_high: 1.08, base_low: 1.12, min_low_steps: 2 },
    },
    "Custom": null,
  };

  // math for Custom overlay only
  function strictlyDecreasing(vals){const out=[];let prev=10;for(const v0 of vals){const v=Math.min(v0,prev-1e-6);out.push(v);prev=v}return out;}
  function sigmasHoldHigh(steps,bias){const p=lerp(1.1,3,clamp(bias,0,1));const v=[];for(let i=0;i<steps;i++){const t=i/steps;v.push(1-Math.pow(t,p))}v.push(0);const s=strictlyDecreasing(v);s[0]=1;s[s.length-1]=0;return s.map(round5);}
  function sigmasBigDrop(steps,bias){const q=lerp(0.8,1.4,clamp(bias,0,1));const v=[];for(let i=0;i<steps;i++){const t=i/steps;v.push(Math.pow(1-t,q))}v.push(0);const s=strictlyDecreasing(v);s[0]=1;s[s.length-1]=0;return s.map(round5);}
  function chooseSchedulerAuto(bias,profile){const b=clamp(bias,0,1);if(b<0.55)return "euler/beta";if(b<0.75)return profile==="hold_high"?"dpm++_sde/beta":"dpm++_sde";return "dpm++_sde";}
  function noiseHints(bias){const b=clamp(bias,0,1);return {addNoiseHigh:b>=0.65,addNoiseLow:false};}

  // widget helpers
  const get = (node,name)=>node.widgets?.find(w=>w.name===name);
  const read = (node,name,def,num=false)=>{const w=get(node,name);if(!w)return def;const v=w.value;if(!num)return v??def;const n=Number(v);return Number.isFinite(n)?n:def;};

  // Programmatically set widget and fire callbacks
  function setWidget(node, name, val) {
    const w = get(node, name); if (!w) return;
    const idx = node.widgets.indexOf(w);
    const prev = w.value;
    if (prev === val) return;
    node.__ea_prog = true;
    try {
      w.value = val;
      if (typeof w.callback === "function") { try { w.callback(val); } catch {} }
      if (typeof node.onWidgetChanged === "function") { try { node.onWidgetChanged(w, idx, prev); } catch {} }
    } finally {
      setTimeout(() => { node.__ea_prog = false; node.graph?.setDirtyCanvas(true, true); }, 0);
    }
  }

  // Spacer to reserve overlay height
  function ensureSpacer(node){
    let w=get(node,"__ea_spacer__");
    if(!w){w=node.addWidget("info","","");w.name="__ea_spacer__";w.serialize=false;w.draw=()=>{};w.getHeight=()=>node.__ea_overlay_h||0;w.computeSize=(width)=>[width,node.__ea_overlay_h||0];}
    return w;
  }

  // Hide/rename Python 'preset' to avoid name clash; add JS "preset" combo
  function hidePythonPreset(node) {
    const pw = get(node, "preset");
    if (pw) { pw.hidden = true; pw.name = "(preset hidden)"; }
  }
  function ensureJsPreset(node) {
    if (node.__ea_js_widget) return node.__ea_js_widget;
    const options = Object.keys(PRESETS);
    const w = node.addWidget("combo", "preset", "Aggressive 3/2", (val) => {
      node.__ea_js_preset = val;
      if (val !== "Custom") {
        const cfg = PRESETS[val].widgets;
        setWidget(node, "steps", cfg.steps);
        setWidget(node, "motion_bias", cfg.motion_bias);
        setWidget(node, "profile", cfg.profile);
        setWidget(node, "base_high", cfg.base_high);
        setWidget(node, "base_low", cfg.base_low);
        setWidget(node, "min_low_steps", cfg.min_low_steps);
      }
      node.graph?.setDirtyCanvas(true, true);
    }, { values: options });
    w.serialize = false;     // JS-only control
    node.__ea_js_widget = w; // keep a handle
    return w;
  }

  function currentPreset(node) {
    return node.__ea_js_preset || node.__ea_js_widget?.value || "Aggressive 3/2";
  }

  // Build overlay lines (with per-line colors)
  function makeLines(node, width) {
    const preset = currentPreset(node);
    let info;

    if (preset !== "Custom" && PRESETS[preset]) {
      const P = PRESETS[preset];
      info = {
        steps: P.steps, split: P.split, sigmas: P.sigmas.slice(),
        highW: P.high, lowW: P.low, cfgHigh: P.cfgHigh, cfgLow: P.cfgLow,
        addNoiseHigh: P.addNoiseHigh, addNoiseLow: P.addNoiseLow, scheduler: P.scheduler
      };
    } else {
      const steps = Math.max(3, Math.floor(read(node, "steps", 5, true)));
      const bias  = clamp(read(node, "motion_bias", 0.8, true), 0, 1);
      const profile = read(node, "profile", "big_drop");
      const baseHigh = read(node, "base_high", 1.04, true);
      const baseLow  = read(node, "base_low", 1.14, true);
      const minLow   = Math.max(1, Math.floor(read(node, "min_low_steps", 2, true)));

      let splitF = 0.5 + 0.2 * bias;
      let split = Math.round(steps * splitF);
      split = Math.max(1, Math.min(split, steps - minLow));

      const sigmas = (profile === "big_drop") ? sigmasBigDrop(steps, bias) : sigmasHoldHigh(steps, bias);
      const highW = round5(baseHigh * (1.0 + 0.25 * bias));
      const lowW  = round5(baseLow  * (1.0 - 0.15 * bias));
      const scheduler = chooseSchedulerAuto(bias, profile);
      const { addNoiseHigh, addNoiseLow } = noiseHints(bias);

      const cfgHigh = Math.max(0.75, Math.min(1.0, 1.0 - 0.25 * bias));
      const cfgLow  = Math.max(1.0, Math.min(1.1, 1.0 + 0.05 * bias));

      info = { steps, split, sigmas, highW, lowW, cfgHigh, cfgLow, addNoiseHigh, addNoiseLow, scheduler };
    }

    const sigmasStr = info.sigmas
      .map(v => typeof v === "number" ? v.toFixed(5).replace(/0+$/,"").replace(/\.$/,"") : String(v))
      .join(" ");

    const lines = [];
    // special color for scheduler + cfg: amber-ish (visible in light/dark)
    const EMP = "#ffcc66";

    lines.push({ t: `scheduler: ${info.scheduler}`, c: EMP });
    lines.push({ t: `cfg (high/low): ${info.cfgHigh} / ${info.cfgLow}`, c: EMP });
    lines.push({ t: `split: ${info.split}/${info.steps - info.split}` });
    lines.push({ t: `steps: ${info.steps}` });
    lines.push({ t: `lightning high: ${info.highW}` });
    lines.push({ t: `lightning low: ${info.lowW}` });
    lines.push({ t: `add_noise: high ${info.addNoiseHigh ? "✓" : "✗"} low ${info.addNoiseLow ? "✓" : "✗"}` });
    lines.push({ t: `sigmas: ${sigmasStr}` });

    // wrap text (approx)
    const innerW = Math.max(120, width - 16);
    const wrapped = [];
    for (const line of lines) {
      const words = line.t.split(" ");
      let row = words.shift();
      for (const w of words) {
        if ((row + " " + w).length * 6.2 > innerW) {
          wrapped.push({ t: row, c: line.c });
          row = w;
        } else {
          row += " " + w;
        }
      }
      wrapped.push({ t: row, c: line.c });
    }
    return wrapped;
  }

  app.registerExtension({
    name: "ea.lightning_motion_bias.overlay.v8",
    nodeCreated(node) {
      if (node?.comfyClass !== "EA_LightningMotionBias") return;
      if (node.__ea_lmb_installed) return;
      node.__ea_lmb_installed = true;

      hidePythonPreset(node);
      ensureJsPreset(node);
      ensureSpacer(node);

      // If Python preset had a saved value, mirror once
      const pySaved = get(node, "(preset hidden)")?.value;
      if (pySaved && PRESETS[pySaved] && node.__ea_js_widget) {
        node.__ea_js_widget.value = pySaved;
        node.__ea_js_preset = pySaved;
        const cfg = PRESETS[pySaved].widgets;
        setWidget(node, "steps", cfg.steps);
        setWidget(node, "motion_bias", cfg.motion_bias);
        setWidget(node, "profile", cfg.profile);
        setWidget(node, "base_high", cfg.base_high);
        setWidget(node, "base_low", cfg.base_low);
        setWidget(node, "min_low_steps", cfg.min_low_steps);
      }

      const padX = 8, padY = 6, lineH = 14;
      const prevDraw = node.onDrawForeground;
      node.onDrawForeground = function(ctx) {
        if (prevDraw) prevDraw.apply(this, arguments);
        const lines = makeLines(this, this.size[0] - padX * 2);
        const overlayH = Math.min(340, lines.length * lineH) + padY;
        if (this.__ea_overlay_h !== overlayH) { this.__ea_overlay_h = overlayH; this.graph?.setDirtyCanvas(true, true); }
        const x = padX, y = this.size[1] - overlayH;

        ctx.save();
        ctx.font = "12px ui-monospace, SFMono-Regular, Menlo, Monaco, Consolas, 'Liberation Mono', 'Courier New', monospace";
        ctx.shadowColor = "rgba(0,0,0,0.6)";
        ctx.shadowBlur = 2;

        let yy = y + 10;
        for (const line of lines) {
          ctx.fillStyle = line.c || "#ffffff";
          ctx.fillText(line.t, x, yy);
          yy += lineH;
        }
        ctx.restore();
      };

      // Flip JS preset to Custom on manual edits
      const prevChanged = node.onWidgetChanged;
      node.onWidgetChanged = function(w, i, prev) {
        const rv = prevChanged ? prevChanged.apply(this, arguments) : undefined;
        if (this.__ea_prog) return rv;

        const customFields = ["steps","motion_bias","profile","base_high","base_low","min_low_steps"];
        if (customFields.includes(w?.name) && node.__ea_js_widget) {
          if (node.__ea_js_widget.value !== "Custom") {
            node.__ea_js_widget.value = "Custom";
            node.__ea_js_preset = "Custom";
            this.graph?.setDirtyCanvas(true, true);
          }
        }
        return rv;
      };

      const prevCfg = node.onConfigure;
      node.onConfigure = function() {
        const rv = prevCfg ? prevCfg.apply(this, arguments) : undefined;
        setTimeout(() => this.graph?.setDirtyCanvas(true, true), 0);
        return rv;
      };
    },
  });
})();
