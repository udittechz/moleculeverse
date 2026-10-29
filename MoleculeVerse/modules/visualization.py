"""3D viewer HTML (3Dmol.js) for Streamlit's components.html. Pure Python; no Streamlit import."""
from __future__ import annotations

import json

STYLES = {
    "Ball-and-stick": {"stick": {"radius": 0.15}, "sphere": {"scale": 0.28}},
    "Stick": {"stick": {"radius": 0.22}},
    "Space-filling": {"sphere": {"scale": 1.0}},
    "Wireframe": {"line": {"linewidth": 2}},
}
STYLE_NAMES = list(STYLES)

COLOR_SCHEMES = {
    "Element colours (Jmol)": {"colorscheme": "Jmol"},
    "Element colours (green carbon)": {"colorscheme": "greenCarbon"},
    "Single colour (mint)": {"color": "#72E0AD"},
}
COLOR_NAMES = list(COLOR_SCHEMES)

BACKGROUNDS = {"Dark navy": "#081522", "Dark green": "#0C211C", "Black": "#000000", "White": "#FFFFFF"}
BACKGROUND_NAMES = list(BACKGROUNDS)

SCRIPT_SOURCES = [
    "https://3Dmol.org/build/3Dmol-min.js",
    "https://cdn.jsdelivr.net/npm/3dmol@2.4.2/build/3Dmol-min.js",
]

_TEMPLATE = """
<div id="wrap" style="position:relative;width:100%;height:__H__px;border:1px solid #2A4A40;border-radius:12px;overflow:hidden;background:__BG__;">
  <div id="viewer" style="width:100%;height:100%;position:relative;"></div>
  <div id="status" role="status" style="position:absolute;inset:0;display:flex;align-items:center;justify-content:center;color:#A5B8B0;font-family:Arial,sans-serif;font-size:14px;padding:16px;text-align:center;">Loading 3D viewer...</div>
  <div style="position:absolute;right:10px;bottom:10px;display:flex;gap:6px;z-index:5;">
    <button id="reset" type="button" style="background:#176B4D;color:#fff;border:0;border-radius:8px;padding:6px 12px;font:13px Arial,sans-serif;cursor:pointer;">Reset view</button>
    <button id="spin" type="button" aria-pressed="false" style="background:#10251F;color:#F1F7F4;border:1px solid #2A4A40;border-radius:8px;padding:6px 12px;font:13px Arial,sans-serif;cursor:pointer;">Spin: off</button>
  </div>
</div>
<script>
(function () {
  var MOL = __MOL__, STYLE = __STYLE__, BG = __BGJS__, SPIN = __SPIN__, SOURCES = __SOURCES__;
  var status = document.getElementById('status'), viewer = null, spinning = false;
  function fail(msg) { status.style.display = 'flex'; status.textContent = msg; }
  function setSpin(on) {
    spinning = on; if (viewer) { viewer.spin(on ? 'y' : false); }
    var b = document.getElementById('spin'); b.textContent = 'Spin: ' + (on ? 'on' : 'off'); b.setAttribute('aria-pressed', on ? 'true' : 'false');
  }
  function init() {
    try {
      viewer = $3Dmol.createViewer(document.getElementById('viewer'), { backgroundColor: BG });
      viewer.addModel(MOL, 'sdf'); viewer.setStyle({}, STYLE); viewer.zoomTo(); viewer.render();
      status.style.display = 'none'; if (SPIN) { setSpin(true); }
      document.getElementById('reset').onclick = function () { viewer.zoomTo(); viewer.render(); };
      document.getElementById('spin').onclick = function () { setSpin(!spinning); };
    } catch (e) { fail('The 3D structure could not be rendered in this browser.'); }
  }
  function load(i) {
    if (window.$3Dmol) { init(); return; }
    if (i >= SOURCES.length) { fail('The 3Dmol.js library could not be loaded. Check your internet connection (it is fetched from a CDN).'); return; }
    var s = document.createElement('script'); s.src = SOURCES[i];
    s.onload = init; s.onerror = function () { load(i + 1); }; document.head.appendChild(s);
  }
  load(0);
})();
</script>
"""


def _js(value) -> str:
    return json.dumps(value).replace("</", "<\\/")


def build_viewer_html(molblock: str, style: str = "Ball-and-stick", colors: str = "Element colours (Jmol)",
                      background: str = "Dark navy", spin: bool = False, height: int = 460) -> str:
    """Return a self-contained HTML document that renders ``molblock`` with the chosen style."""
    style_spec = dict(STYLES.get(style, STYLES["Ball-and-stick"]))
    color_spec = COLOR_SCHEMES.get(colors, COLOR_SCHEMES[COLOR_NAMES[0]])
    style_spec = {kind: {**opts, **color_spec} for kind, opts in style_spec.items()}
    bg = BACKGROUNDS.get(background, BACKGROUNDS["Dark navy"])
    return (_TEMPLATE
            .replace("__H__", str(int(height)))
            .replace("__BGJS__", _js(bg))
            .replace("__BG__", bg)
            .replace("__MOL__", _js(molblock.rstrip("\n") + "\n$$$$\n"))
            .replace("__STYLE__", _js(style_spec))
            .replace("__SPIN__", "true" if spin else "false")
            .replace("__SOURCES__", _js(SCRIPT_SOURCES)))
