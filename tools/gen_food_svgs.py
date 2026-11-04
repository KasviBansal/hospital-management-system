"""Generates the cafeteria illustrations (original vector art) into static/img/cafeteria/."""
import os
OUT = os.path.join(os.path.dirname(__file__), "..", "static", "img", "cafeteria")
W, H = 640, 400

def wrap(bg1, bg2, body):
    return f'''<svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 {W} {H}" role="img">
<defs><linearGradient id="g" x1="0" y1="0" x2="1" y2="1"><stop offset="0" stop-color="{bg1}"/><stop offset="1" stop-color="{bg2}"/></linearGradient></defs>
<rect width="{W}" height="{H}" fill="url(#g)"/>
<ellipse cx="320" cy="352" rx="190" ry="16" fill="#000" opacity=".10"/>
{body}</svg>'''

def plate(cx=320, cy=210, r=150):
    return (f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="#fff"/><circle cx="{cx}" cy="{cy}" r="{r-18}" fill="#F3F5F7"/>')

def cup(color="#fff", liquid="#8B5A2B", steam=True):
    s = '<g fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".8"><path d="M285 120c-14 20 14 30 0 52"/><path d="M325 110c-14 22 14 32 0 56"/><path d="M365 120c-14 20 14 30 0 52"/></g>' if steam else ''
    return (f'{s}<path d="M220 190h200l-18 130a24 24 0 0 1-24 20H262a24 24 0 0 1-24-20z" fill="{color}"/>'
            f'<path d="M226 198h188l-4 28H230z" fill="{liquid}"/>'
            f'<path d="M420 215c52-6 52 70 0 76" fill="none" stroke="{color}" stroke-width="16" stroke-linecap="round"/>')

def bowl(fill, inner):
    return (f'<path d="M150 200h340c0 90-64 140-170 140S150 290 150 200z" fill="#fff"/>'
            f'<ellipse cx="320" cy="200" rx="170" ry="34" fill="{inner}"/>{fill}')

ITEMS = {}

ITEMS["veg_thali"] = wrap("#FFE9B8", "#FFC66B", plate(r=160) +
  '<circle cx="320" cy="210" r="140" fill="#D9DEE3"/><circle cx="320" cy="210" r="132" fill="#fff"/>'
  '<circle cx="262" cy="170" r="42" fill="#E08A2E"/><circle cx="262" cy="170" r="28" fill="#F2A950"/>'
  '<circle cx="378" cy="170" r="42" fill="#7BA23F"/><circle cx="378" cy="170" r="28" fill="#98BF5A"/>'
  '<circle cx="262" cy="258" r="38" fill="#B8432F"/><circle cx="262" cy="258" r="24" fill="#D9634B"/>'
  '<ellipse cx="372" cy="258" rx="52" ry="34" fill="#F7E4B0"/><circle cx="350" cy="250" r="5" fill="#fff"/><circle cx="385" cy="262" r="5" fill="#fff"/><circle cx="368" cy="272" r="5" fill="#fff"/>')

ITEMS["chicken_curry"] = wrap("#FFD9B0", "#F59A5B", plate() +
  '<ellipse cx="270" cy="215" rx="80" ry="62" fill="#E8EDF1"/><g fill="#fff"><circle cx="240" cy="200" r="5"/><circle cx="262" cy="222" r="5"/><circle cx="288" cy="196" r="5"/><circle cx="300" cy="228" r="5"/><circle cx="252" cy="240" r="5"/></g>'
  '<path d="M340 160c40-20 90 10 80 60s-70 70-100 40-20-80 20-100z" fill="#C8581D"/><circle cx="370" cy="195" r="20" fill="#9A3F10"/><circle cx="395" cy="228" r="16" fill="#9A3F10"/><circle cx="352" cy="240" r="14" fill="#9A3F10"/>'
  '<path d="M355 170l10-8 8 10zM400 200l12-4 2 12z" fill="#6FA34A"/>')

ITEMS["grilled_sandwich"] = wrap("#FFF0C9", "#F7C873", plate() +
  '<path d="M200 250l90-100 150 20-80 110z" fill="#C98B3E"/><path d="M200 250l150 30 90-110-150-20z" fill="#E9B467"/>'
  '<path d="M214 252l130 26 82-98-128-18z" fill="#F4CB86"/><path d="M230 240l110 22" stroke="#7A4A18" stroke-width="7" stroke-linecap="round" opacity=".55"/>'
  '<path d="M256 220l100 20" stroke="#7A4A18" stroke-width="7" stroke-linecap="round" opacity=".55"/><path d="M215 262l140 28 3-14-140-28z" fill="#6FA34A"/><path d="M216 276l142 28 2-12-140-28z" fill="#F2D24B"/>')

ITEMS["vegetable_soup"] = wrap("#FFE2C9", "#F3A472", bowl(
  '<ellipse cx="320" cy="200" rx="150" ry="26" fill="#E8812E"/><circle cx="270" cy="196" r="14" fill="#F4C20D"/><circle cx="318" cy="206" r="12" fill="#6FA34A"/><circle cx="360" cy="194" r="13" fill="#D64A2B"/><circle cx="390" cy="208" r="10" fill="#F4C20D"/><circle cx="300" cy="190" r="9" fill="#6FA34A"/>',
  "#FFF") +
  '<g fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".85"><path d="M280 140c-14 20 14 30 0 46"/><path d="M330 128c-14 22 14 32 0 52"/><path d="M380 140c-14 20 14 30 0 46"/></g>')

ITEMS["idli_sambhar"] = wrap("#E4F3E1", "#9ED39A", plate() +
  '<g fill="#fff" stroke="#E4E8EC" stroke-width="4"><ellipse cx="260" cy="190" rx="52" ry="30"/><ellipse cx="350" cy="178" rx="52" ry="30"/><ellipse cx="300" cy="228" rx="52" ry="30"/></g>'
  '<path d="M390 230h70c0 36-22 56-52 56s-52-20-52-56z" fill="#fff" stroke="#E4E8EC" stroke-width="4"/><ellipse cx="425" cy="232" rx="34" ry="9" fill="#D07A1E"/><circle cx="415" cy="232" r="4" fill="#6FA34A"/>')

ITEMS["poha"] = wrap("#FFF4C2", "#F4D45B", plate() +
  '<path d="M190 215c10-60 80-80 130-70s110 20 130 70c-20 40-110 56-130 56s-120-16-130-56z" fill="#F4D03F"/>'
  '<g fill="#D9A60A"><circle cx="250" cy="200" r="7"/><circle cx="300" cy="180" r="7"/><circle cx="350" cy="200" r="7"/><circle cx="400" cy="215" r="7"/><circle cx="280" cy="235" r="7"/><circle cx="340" cy="240" r="7"/></g>'
  '<g fill="#B67A3A"><circle cx="270" cy="215" r="6"/><circle cx="320" cy="205" r="6"/><circle cx="380" cy="190" r="6"/></g><path d="M330 160l14-10 6 14zM260 170l12-10 8 12z" fill="#6FA34A"/><path d="M400 235l30 20-8 10z" fill="#F2E27A"/>')

ITEMS["fruit_bowl"] = wrap("#FFE0E6", "#F59DB1", bowl(
  '<circle cx="250" cy="190" r="40" fill="#E5484D"/><circle cx="330" cy="170" r="44" fill="#F5A623"/><circle cx="400" cy="195" r="38" fill="#8BC34A"/><circle cx="300" cy="205" r="30" fill="#7B4FA8"/><circle cx="360" cy="215" r="24" fill="#7B4FA8"/>'
  '<path d="M320 128c10-20 26-22 36-18-4 14-20 24-36 18z" fill="#4E8F3A"/>', "#FFF"))

ITEMS["curd_cup"] = wrap("#EAF1FF", "#B6CCF5",
  '<path d="M230 170h180l-20 160a20 20 0 0 1-20 18H270a20 20 0 0 1-20-18z" fill="#fff"/><path d="M236 176h168l-4 34H240z" fill="#DDE7FA"/>'
  '<ellipse cx="320" cy="170" rx="90" ry="20" fill="#FFFDF7"/><path d="M270 168c20-26 60-26 80 0z" fill="#F7F3E4"/><circle cx="320" cy="150" r="9" fill="#E5484D"/><path d="M320 142c2-8 8-10 12-8" stroke="#4E8F3A" stroke-width="4" fill="none"/>')

ITEMS["masala_chai"] = wrap("#FBE3CF", "#E8A56F", cup("#fff", "#B8742F"))
ITEMS["black_coffee"] = wrap("#E9DED3", "#A98467", cup("#fff", "#3B2417"))

ITEMS["lime_water"] = wrap("#E6F8D8", "#A8DC7A",
  '<path d="M240 130h160l-20 200a18 18 0 0 1-18 16H278a18 18 0 0 1-18-16z" fill="#fff" opacity=".85"/>'
  '<path d="M246 190h148l-14 140H260z" fill="#D7F087"/><g fill="#fff" opacity=".8"><circle cx="290" cy="260" r="7"/><circle cx="340" cy="230" r="6"/><circle cx="355" cy="290" r="8"/><circle cx="300" cy="305" r="5"/></g>'
  '<circle cx="400" cy="130" r="36" fill="#8BC34A"/><circle cx="400" cy="130" r="26" fill="#C6E86A"/><path d="M400 104v52M374 130h52M382 112l36 36M418 112l-36 36" stroke="#8BC34A" stroke-width="3"/>'
  '<path d="M330 118l30-70" stroke="#E5484D" stroke-width="8" stroke-linecap="round"/>')

ITEMS["mineral_water"] = wrap("#E0F2FD", "#8FCDF2",
  '<rect x="292" y="80" width="56" height="30" rx="8" fill="#2D8CD6"/><path d="M296 108h48c0 24 34 30 34 70v140a22 22 0 0 1-22 22H284a22 22 0 0 1-22-22V178c0-40 34-46 34-70z" fill="#fff" opacity=".9"/>'
  '<path d="M270 215h100v90a14 14 0 0 1-14 14h-72a14 14 0 0 1-14-14z" fill="#8FCDF2" opacity=".75"/><rect x="262" y="180" width="116" height="44" fill="#2D8CD6"/><path d="M290 205c10-14 20-14 30 0s20 14 30 0" stroke="#fff" stroke-width="5" fill="none" stroke-linecap="round"/>')

ITEMS["boiled_egg"] = wrap("#FFF3DC", "#F6CF8A", plate() +
  '<g><ellipse cx="270" cy="210" rx="58" ry="74" fill="#fff" stroke="#E9E2D3" stroke-width="5"/><ellipse cx="270" cy="228" rx="30" ry="34" fill="#F6B73C"/></g>'
  '<g><ellipse cx="380" cy="215" rx="58" ry="74" fill="#fff" stroke="#E9E2D3" stroke-width="5"/><ellipse cx="380" cy="233" rx="30" ry="34" fill="#F6B73C"/></g>')

ITEMS["khichdi"] = wrap("#FFF1B8", "#E9C14B", bowl(
  '<ellipse cx="320" cy="200" rx="150" ry="26" fill="#F2D36B"/><g fill="#D9A60A"><circle cx="260" cy="198" r="6"/><circle cx="300" cy="190" r="6"/><circle cx="350" cy="204" r="6"/><circle cx="390" cy="196" r="6"/></g>'
  '<path d="M300 180c10-14 30-14 40 0z" fill="#E8812E"/><path d="M330 188l12-8 6 12z" fill="#6FA34A"/>', "#FFF") +
  '<g fill="none" stroke="#fff" stroke-width="7" stroke-linecap="round" opacity=".85"><path d="M290 140c-14 20 14 30 0 44"/><path d="M340 128c-14 22 14 32 0 50"/></g>')

ITEMS["biscuit_pack"] = wrap("#FFE4C4", "#E9A66A",
  '<rect x="230" y="90" width="180" height="250" rx="14" fill="#2D8CD6"/><rect x="230" y="150" width="180" height="120" fill="#F5C242"/>'
  '<rect x="230" y="90" width="180" height="22" rx="10" fill="#1F6FB2"/><rect x="230" y="318" width="180" height="22" rx="10" fill="#1F6FB2"/>'
  '<circle cx="320" cy="210" r="42" fill="#C98B3E"/><circle cx="320" cy="210" r="34" fill="#E0A557"/><g fill="#9A6224"><circle cx="305" cy="200" r="4"/><circle cx="335" cy="203" r="4"/><circle cx="320" cy="222" r="4"/><circle cx="308" cy="226" r="3"/></g>')

# Category fallbacks
for cat, (a, b, body) in {
    "meals": ("#FFE9B8", "#FFC66B", plate(r=140) + '<circle cx="320" cy="210" r="70" fill="#E08A2E"/>'),
    "snacks": ("#FFF0C9", "#F7C873", plate(r=140) + '<rect x="250" y="170" width="140" height="80" rx="14" fill="#C98B3E"/>'),
    "beverages": ("#E9DED3", "#A98467", cup()),
    "desserts": ("#FFE0E6", "#F59DB1", bowl('<circle cx="320" cy="190" r="40" fill="#E5484D"/>', "#FFF")),
}.items():
    ITEMS["cat_" + cat] = wrap(a, b, body)

if __name__ == "__main__":
    os.makedirs(OUT, exist_ok=True)
    for name, svg in ITEMS.items():
        with open(os.path.join(OUT, name + ".svg"), "w") as f:
            f.write(svg)
    print("wrote", len(ITEMS), "images")
