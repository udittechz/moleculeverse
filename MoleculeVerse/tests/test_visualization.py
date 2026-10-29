import json
import re

from modules import visualization as v


def _style_from(html):
    m = re.search(r"STYLE = (\{.*?\}), BG = ", html)
    return json.loads(m.group(1))


def test_every_style_changes_the_rendered_style_spec():
    specs = {}
    for name in v.STYLE_NAMES:
        html = v.build_viewer_html("MOL\n  M  END\n", style=name)
        specs[name] = _style_from(html)
    assert set(specs["Ball-and-stick"]) == {"stick", "sphere"}
    assert set(specs["Stick"]) == {"stick"}
    assert set(specs["Space-filling"]) == {"sphere"}
    assert set(specs["Wireframe"]) == {"line"}
    assert len({json.dumps(s, sort_keys=True) for s in specs.values()}) == len(v.STYLE_NAMES)


def test_colour_scheme_background_and_spin():
    html = v.build_viewer_html("X", colors="Single colour (mint)", background="White", spin=True)
    assert "#72E0AD" in html and "#FFFFFF" in html and "SPIN = true" in html
    jmol = v.build_viewer_html("X", colors="Element colours (Jmol)")
    assert '"colorscheme": "Jmol"' in jmol


def test_molblock_is_escaped_for_script_context():
    html = v.build_viewer_html("</script><b>")
    assert "</script><b>" not in html.split("var MOL = ")[1].split(", STYLE")[0]
