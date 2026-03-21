"""
Idle Planet Miner – Recipe Value Calculator  (Dear PyGui rewrite)

Files (all in same folder as this script):
  ipm_base.json   – static reference data: recipes, base prices, planet defs
                    Never written by the app.
  ipm_state.json  – mutable game state: unlocks, levels, market, stars, bonuses
  ipm_prefs.json  – UI preferences: sort choices
"""

import json, os, re, copy
import dearpygui.dearpygui as dpg
import copy
from PIL import Image

# ── paths ─────────────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
BASE_FILE  = os.path.join(SCRIPT_DIR, "ipm_base.json")
STATE_FILE = os.path.join(SCRIPT_DIR, "ipm_state.json")
PREFS_FILE = os.path.join(SCRIPT_DIR, "ipm_prefs.json")

# ── colours (R,G,B,A 0-255) ───────────────────────────────────────────────────
C_BG      = (30,  30,  46,  255)
C_PANEL   = (42,  42,  62,  255)
C_ACCENT  = (124, 106, 247, 255)
C_TEAL    = (86,  207, 178, 255)
C_TEXT    = (224, 224, 240, 255)
C_MUTED   = (136, 136, 153, 255)
C_GOOD    = (86,  207, 178, 255)
C_BAD     = (224, 92,  106, 255)
C_WARN    = (240, 192, 64,  255)
C_ROW_A   = (37,  37,  56,  255)
C_ROW_B   = (42,  42,  62,  255)
C_ENTRY   = (51,  51,  74,  255)
C_BTN     = (74,  63,  191, 255)
C_BTN_DIS = (47,  41,  105, 255)
C_SEP     = (55,  55,  80,  255)

# ── number / time formatting ───────────────────────────────────────────────────
_SFX = [(1e33,"D"),(1e30,"N"),(1e27,"O"),(1e24,"Sp"),(1e21,"Sx"),
        (1e18,"Qi"),(1e15,"Q"),(1e12,"T"),(1e9,"B"),(1e6,"M"),(1e3,"K")]

def fmt(n: float) -> str:
    if n == 0: return "$0"
    neg = n < 0; n = abs(n)
    for thr, sfx in _SFX:
        if n >= thr: return f"{'−' if neg else ''}${n/thr:.1f}{sfx}"
    return f"{'−' if neg else ''}${n:.2f}"

def fmt_time(s: float) -> str:
    if s <= 0: return "—"
    s = int(s)
    if s < 60:   return f"{s}s"
    m, s = divmod(s, 60)
    if m < 60:   return f"{m}m{s:02d}s"
    h, m = divmod(m, 60)
    if h < 24:   return f"{h}h{m:02d}m"
    d, h = divmod(h, 24)
    return f"{d}d{h:02d}h"

# ── base data ──────────────────────────────────────────────────────────────────
def load_base() -> dict:
    with open(BASE_FILE) as f:
        return json.load(f)

# ── state ──────────────────────────────────────────────────────────────────────
def default_state(base: dict) -> dict:
    planets = {}
    for pid, p in base["planets"].items():
        owned = (p["telescope"] == 0)
        lvl   = 1 if owned else 0
        planets[pid] = {
            "owned":  owned,
            "levels": {"mining": lvl, "speed": lvl, "cargo": lvl},
            "probes": [1.0, 1.0, 1.0],
            "colony": [1.0, 1.0, 1.0],
        }
    return {
        "ores":     {k: {"stars": 0, "market": 0}                     for k in base["ores"]},
        "alloys":   {k: {"unlocked": False, "stars": 0, "market": 0}  for k in base["alloys"]},
        "items":    {k: {"unlocked": False, "stars": 0, "market": 0}  for k in base["items"]},
        "projects": {k: {"researched": False}                         for k in base["projects"]},
        "planets":  planets,
        "globals":  {"mining":1.0,"speed":1.0,"cargo":1.0,
                     "smelt_speed":1.0,"craft_speed":1.0},
        "smelters": 1,
        "crafters": 1,
        "colonies": [],
        "beacons":  {str(i): {"mining": 1.0, "speed": 1.0, "cargo": 1.0}
                     for i in range(23)},
        "rooms":    {},
        "managers": [],
    }

def _deep_merge(fresh: dict, saved: dict):
    for k, v in fresh.items():
        if k not in saved:
            saved[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(saved.get(k), dict):
            _deep_merge(v, saved[k])

def load_state(base: dict) -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                saved = json.load(f)
            _deep_merge(default_state(base), saved)
            return saved
        except Exception:
            pass
    return default_state(base)

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ── prefs ──────────────────────────────────────────────────────────────────────
_DEF_PREFS = {"dashboard_filter":"All","dashboard_sort":"vps_profit_ore",
              "projects_sort":"time", "colonies_sort":"planet",
              "beacons_sort":"level"}

def load_prefs() -> dict:
    if os.path.exists(PREFS_FILE):
        try:
            with open(PREFS_FILE) as f:
                p = json.load(f)
            for k, v in _DEF_PREFS.items():
                p.setdefault(k, v)
            return p
        except Exception:
            pass
    return dict(_DEF_PREFS)

def save_prefs(prefs: dict):
    with open(PREFS_FILE, "w") as f:
        json.dump(prefs, f, indent=2)

# ── price (always computed, never cached) ─────────────────────────────────────
def effective_price(name: str, base: dict, state: dict) -> float:
    for cat in ("ores","alloys","items"):
        if name in base[cat]:
            bp  = base[cat][name]["base_price"]
            st  = state[cat][name]
            mv  = [0.33,0.5,1,2,3,4,5][st.get("market",0)+2]
            sv  = 1.0 + 0.2 * st.get("stars",0)
            return bp * mv * sv
    return 0.0

def ore_unlocked(ore: str, base: dict, state: dict) -> bool:
    return any(ps["owned"] and ore in base["planets"][pid]["resources"]
               for pid, ps in state["planets"].items())

def ore_mining_rate(ore: str, base: dict, state: dict) -> float:
    total = 0.0
    gm    = global_mining_bonus(state)
    for pid, ps in state["planets"].items():
        if not ps["owned"]: continue
        pct = base["planets"][pid]["resources"].get(ore, 0)
        if pct == 0: continue
        lvl   = ps["levels"]["mining"]
        bonus = ps["probes"][0] * ps["colony"][0] * gm
        total += _mining_rate(lvl, bonus) * (pct / 100.0)
    return total

def _mining_rate(lv: int, bonus: float=1.0) -> float:
    if lv == 0: return 0.0
    l = lv - 1
    return bonus * (0.25 + 0.1*l + 0.017*l*l)

def _ship_speed(lv: int, bonus: float=1.0) -> float:
    if lv == 0: return 0.0
    l = lv - 1
    return bonus * (1.0 + 0.2*l + l*l/75.0)

def _ship_cargo(lv: int, bonus: float=1.0) -> int:
    if lv == 0: return 0
    l = lv - 1
    return round(bonus * (5.0 + 2.0*l + (0.1*(l**2))))

def _planet_transport(dist: int, speed: float, cargo: int):
    # dist is in Mkm times some factor - pulled from wiki (probably guesses)
    # speed is in Mkm/h
    if speed == 0:
        return 0
    dist = dist * 2 # account for return trip
    Mkps = speed * 3
    
    # return cargo per second
    transport = cargo * (Mkps / dist)
    return transport

# ── global bonuses ─────────────────────────────────────────────────────────────
def _proj(state, name): return state["projects"].get(name,{}).get("researched",False)

# Module-level base reference set by App.__init__ so room_bonus can use it
_g_base = {}

def global_mining_bonus(state):
    v = float(state.get("globals",{}).get("mining",1))
    if _proj(state,"Advanced Mining"):  v *= 1.25
    if _proj(state,"Superior Mining"):  v *= 1.25
    v *= room_bonus("mining", _g_base, state)
    v *= manager_secondary_bonus("mining", state)
    return v

def global_speed_bonus(state):
    v = float(state.get("globals",{}).get("speed",1))
    if _proj(state,"Advanced Thrusters"): v *= 1.25
    if _proj(state,"Superior Thrusters"): v *= 1.25
    v *= room_bonus("speed", _g_base, state)
    v *= manager_secondary_bonus("speed", state)
    return v

def global_cargo_bonus(state):
    v = float(state.get("globals",{}).get("cargo",1))
    if _proj(state,"Advanced Cargo Handling"): v *= 1.25
    if _proj(state,"Superior Cargo Handling"): v *= 1.25
    v *= room_bonus("cargo", _g_base, state)
    v *= manager_secondary_bonus("cargo", state)
    return v

def global_smelt_speed(state):
    v = float(state.get("globals",{}).get("smelt_speed",1))
    v *= room_bonus("smelt_speed", _g_base, state)
    v *= manager_secondary_bonus("smelt_speed", state)
    return v

def global_craft_speed(state):
    v = float(state.get("globals",{}).get("craft_speed",1))
    v *= room_bonus("craft_speed", _g_base, state)
    v *= manager_secondary_bonus("craft_speed", state)
    return v

def beacon_bonus(pid: str, stat: str, base: dict, state: dict) -> float:
    """Return the beacon multiplier for planet pid and stat (mining/speed/cargo)."""
    scope = str(base["planets"][pid]["telescope"])
    return float(state.get("beacons", {}).get(scope, {}).get(stat, 1.0))

def room_bonus(stat: str, base: dict, state: dict) -> float:
    """Return combined room multiplier for a given stat.
    stat: mining | speed | cargo | smelt_speed | craft_speed
    Effect = base_effect + (level-1)*per_level, applied as a multiplier.
    """
    total = 1.0
    rooms_state = state.get("rooms", {})
    for room in base.get("rooms", []):
        if room.get("stat") != stat:
            continue
        level = rooms_state.get(room["name"], 0)
        if level <= 0:
            continue
        effect = room["base_effect"] + (level - 1) * room["per_level"]
        total *= effect
    return total


# ── manager bonus tables ──────────────────────────────────────────────────────
# Primary multiplier by star count (index 0 = 1 star)
_MGR_PRIMARY = {
    "mining": [1.25, 1.50, 1.75, 2.00, 2.25, 2.50, 2.95],
    "speed":  [1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.90],
    "cargo":  [1.50, 2.00, 2.50, 3.00, 3.50, 4.00, 4.90],
}
# Secondary additive bonus by star count (index 0 = 1 star; 0 at <3 stars)
_MGR_SECONDARY = {
    "mining":      [1.00, 1.00, 1.05, 1.10, 1.20, 1.30, 1.50],
    "speed":       [1.00, 1.00, 1.10, 1.20, 1.40, 1.60, 2.00],
    "cargo":       [1.00, 1.00, 1.10, 1.20, 1.40, 1.60, 2.00],
    "smelt_speed": [1.00, 1.00, 1.05, 1.10, 1.20, 1.40, 1.70],
    "craft_speed": [1.00, 1.00, 1.05, 1.10, 1.20, 1.40, 1.70],
}

def manager_primary_bonus(pid: str, stat: str, state: dict) -> float:
    """Multiplicative primary bonus from the manager assigned to planet pid."""
    for mgr in state.get("managers", []):
        if mgr.get("planet") == pid and mgr.get("primary") == stat:
            stars = max(1, min(7, mgr.get("stars", 1)))
            return _MGR_PRIMARY[stat][stars - 1]
    return 1.0

def manager_secondary_bonus(stat: str, state: dict) -> float:
    """Combined additive secondary bonus across all ASSIGNED managers for stat.
    Only managers with a planet assigned contribute.
    Returns a multiplier: 1.0 + sum of individual additive bonuses.
    """
    total = 0.0
    for mgr in state.get("managers", []):
        if not mgr.get("planet"):
            continue
        if mgr.get("secondary") == stat:
            stars = max(1, min(7, mgr.get("stars", 1)))
            total = total * (_MGR_SECONDARY.get(stat, [0.0]*7)[stars - 1])
    return 1.0 + total

# ── time helpers ───────────────────────────────────────────────────────────────
def total_smelt_time(name, cat, base, state):
    e   = base[cat][name]
    own = e["smelt_time"] if cat=="alloys" else 0.0
    t   = own / max(0.001, global_smelt_speed(state))
    for ing, qty in e.get("recipe",{}).items():
        c2 = "alloys" if ing in base["alloys"] else ("items" if ing in base["items"] else None)
        if c2: t += total_smelt_time(ing, c2, base, state) * qty
    return t

def total_craft_time(name, cat, base, state):
    e   = base[cat][name]
    own = e["craft_time"] if cat=="items" else 0.0
    t   = own / max(0.001, global_craft_speed(state))
    for ing, qty in e.get("recipe",{}).items():
        c2 = "alloys" if ing in base["alloys"] else ("items" if ing in base["items"] else None)
        if c2: t += total_craft_time(ing, c2, base, state) * qty
    return t

def wall_time(smelt, craft, smelters, crafters):
    return max(smelt/max(1,smelters), craft/max(1,crafters), 1.0)

def ore_cost_rec(recipe, base, state):
    total = 0.0
    for ing, qty in recipe.items():
        if   ing in base["ores"]:   total += effective_price(ing, base, state) * qty
        elif ing in base["alloys"]: total += ore_cost_rec(base["alloys"][ing]["recipe"], base, state) * qty
        elif ing in base["items"]:  total += ore_cost_rec(base["items"][ing]["recipe"],  base, state) * qty
    return total

def prereq_met(prereq, state):
    if not prereq: return True
    pr = state["projects"]
    if isinstance(prereq, list): return any(pr.get(p,{}).get("researched") for p in prereq)
    return pr.get(prereq,{}).get("researched",False)

def analyze(name, cat, base, state):
    e  = base[cat][name]
    ov = effective_price(name, base, state)
    tk = "smelt_time" if cat=="alloys" else "craft_time"
    t  = e.get(tk,1)
    adj_t = t / max(0.001, global_smelt_speed(state) if cat=="alloys" else global_craft_speed(state))
    sm = total_smelt_time(name, cat, base, state)
    cr = total_craft_time(name, cat, base, state)
    s  = state.get("smelters",1); c = state.get("crafters",1)
    wt = wall_time(sm, cr, s, c)
    dc = sum(effective_price(i,base,state)*q for i,q in e.get("recipe",{}).items())
    oc = ore_cost_rec(e.get("recipe",{}), base, state)
    pd = ov - dc; po = ov - oc
    return {"name":name,"category":cat,
            "unlocked":state[cat][name].get("unlocked",False),
            "output_value":ov,"direct_cost":dc,"ore_cost":oc,
            "profit_direct":pd,"profit_ore":po,
            "craft_time":adj_t,"smelt_raw":sm,"craft_raw":cr,"total_time":wt,
            "vps_output":ov/t if t else 0,
            "vps_profit_direct":pd/t if t else 0,
            "vps_profit_ore":po/wt if wt else 0}

def analyze_all(base, state):
    r = []
    for n in base["alloys"]: r.append(analyze(n,"alloys",base,state))
    for n in base["items"]:  r.append(analyze(n,"items", base,state))
    return r

# ═════════════════════════════════════════════════════════════════════════════
# Application
# ═════════════════════════════════════════════════════════════════════════════
class App:
    def __init__(self):
        self.base  = load_base()
        global _g_base; _g_base = self.base
        self.state = load_state(self.base)
        self.prefs = load_prefs()

        dpg.create_context()
        self._load_font()
        self._load_images()
        self._theme()

        with dpg.window(tag="main", no_title_bar=True, no_move=True,
                        no_resize=True, no_scrollbar=True):
            self._hdr()
            dpg.add_separator()
            with dpg.tab_bar():
                with dpg.tab(label="  Dashboard  "): self._tab_dash()
                with dpg.tab(label="  Ores       "): self._tab_ores()
                with dpg.tab(label="  Alloys     "): self._tab_alloys()
                with dpg.tab(label="  Items      "): self._tab_items()
                with dpg.tab(label="  Projects   "): self._tab_projects()
                with dpg.tab(label="  Planets    "): self._tab_planets()
                with dpg.tab(label="  Colonies   "): self._tab_colonies()
                with dpg.tab(label="  Managers   "): self._tab_managers()
                with dpg.tab(label="  Beacons    "): self._tab_beacons()
                with dpg.tab(label="  Rooms      "): self._tab_rooms()

        dpg.set_viewport_resize_callback(self._resize)
        dpg.create_viewport(title="Idle Planet Miner - Calculator",
                            width=1440, height=860, min_width=900, min_height=600)
        dpg.setup_dearpygui()
        dpg.show_viewport()
        self._resize()
        self._refresh_all()
        dpg.start_dearpygui()
        dpg.destroy_context()

    # ── font ───────────────────────────────────────────────────────────────────
    def _load_font(self):
        """Load a font with broad unicode coverage.
        Tries common system fonts; falls back to DPG default if none found.
        """
        candidates = [
            r"C:\Windows\Fonts\segoeui.ttf",          # Windows – Segoe UI
            r"C:\Windows\Fonts\arial.ttf",            # Windows – Arial
            "/usr/share/fonts/truetype/dejavu/DejaVuSans.ttf",  # Linux
            "/System/Library/Fonts/Helvetica.ttc",       # macOS
        ]
        font_path = next((p for p in candidates if os.path.exists(p)), None)
        if font_path is None:
            return  # use DPG default
        with dpg.font_registry():
            with dpg.font(font_path, 22, default_font=True) as fnt:
                # Add extended unicode ranges needed:
                # Basic Latin + Latin-1 (always included by default)
                # General Punctuation: ellipsis, bullets, dashes
                dpg.add_font_range(0x2000, 0x206F)
                # Arrows: ↑ ↓ ← →
                dpg.add_font_range(0x2100, 0x21FF)
                # Mathematical operators: × − ÷
                dpg.add_font_range(0x2200, 0x22FF)
                # Misc symbols: ★ ☑ ☐ ✓
                dpg.add_font_range(0x2600, 0x26FF)
                # Dingbats: ✓ ✗
                dpg.add_font_range(0x2700, 0x27BF)
                # Block elements: ▲ ▼ ▌
                dpg.add_font_range(0x2580, 0x259F)
                # Geometric shapes: ▲ ▼ ◆
                dpg.add_font_range(0x25A0, 0x25FF)
        dpg.bind_font(fnt)


    # ── images ─────────────────────────────────────────────────────────────────
    def _load_images(self):
        """Load PNG/JPEG assets as DPG static textures."""
        self._star_tex = None
        self._chev_tex = {}   # dict: market_value (-2..4) -> texture id
        self._chev_size = (40, 57)  # will be updated from actual image
        self._load_chevrons()
        star_path = os.path.join(SCRIPT_DIR, "Images/star.png")
        try:
            img  = Image.open(star_path).convert("RGBA")
            w, h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                self._star_tex = dpg.add_static_texture(
                    width=w, height=h, default_value=flat)
            self._star_size = (w, h)
        except Exception as e:
            print(f"[warn] Could not load star.png: {e}")
        self._no_star_tex = None
        no_star_path = os.path.join(SCRIPT_DIR, "Images/noStar.png")
        try:
            img  = Image.open(no_star_path).convert("RGBA")
            w, h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                self._no_star_tex = dpg.add_static_texture(
                    width=w, height=h, default_value=flat)
            self._no_star_size = (w, h)
        except Exception as e:
            print(f"[warn] Could not load noStar.png: {e}")
        
        for img_name in ["star_white", "star_black"]:
            img_path = f"{SCRIPT_DIR}/Images/{img_name}.png"
            if os.path.exists(img_path):
                img = Image.open(img_path).convert("RGBA")
                w,h = img.size
                flat = [c / 255.0 for px in img.getdata() for c in px]
                with dpg.texture_registry():
                    dpg.add_static_texture(
                            width=w, height=h, default_value=flat, tag=img_name)
        
        self._arrow_right = None
        arrow_right_path = os.path.join(SCRIPT_DIR, "Images/Arrow_Right.png")
        try:
            img  = Image.open(arrow_right_path).convert("RGBA")
            w, h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                self._arrow_right = dpg.add_static_texture(
                    width=w, height=h, default_value=flat)
            self._arrow_right_size = (w, h)
        except Exception as e:
            print(f"[warn] Could not load Arrow_Right.png: {e}")
        
        self._telescope = None
        telescope_path = os.path.join(SCRIPT_DIR, "Images/Telescope.png")
        try:
            img  = Image.open(telescope_path).convert("RGBA")
            w, h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                self._telescope = dpg.add_static_texture(
                    width=w, height=h, default_value=flat)
            self._telescope_size = (w, h)
        except Exception as e:
            print(f"[warn] Could not load telescope.png: {e}")
        
        img = Image.open(os.path.join(SCRIPT_DIR, "Images/Check.png")).convert("RGBA")
        w,h = img.size
        flat = [c / 255.0 for px in img.getdata() for c in px]
        with dpg.texture_registry():
            self._check = dpg.add_static_texture(
                width=w, height=h, default_value=flat)
        self._check_size = (w, h)
        for ore in self.base["ores"].keys():
            img_path = f"{SCRIPT_DIR}/Images/Ore_{ore}.png"
            if not os.path.exists(img_path):
                img_path = f"{SCRIPT_DIR}/Images/Ore_Unknown.png"
            img = Image.open(img_path).convert("RGBA")
            w,h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                dpg.add_static_texture(
                        width=w, height=h, default_value=flat, tag=f"Ore_{ore}")

        for alloy in self.base["alloys"].keys():
            img_path = f"{SCRIPT_DIR}/Images/Alloy_{alloy}.png"
            if not os.path.exists(img_path):
                img_path = f"{SCRIPT_DIR}/Images/Alloy_Unknown.png"
            img = Image.open(img_path).convert("RGBA")
            w,h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                dpg.add_static_texture(
                        width=w, height=h, default_value=flat, tag=f"Alloy_{alloy}")
           
        for item in self.base["items"].keys():
            img_path = f"{SCRIPT_DIR}/Images/Item_{item}.png"
            if not os.path.exists(img_path):
                img_path = f"{SCRIPT_DIR}/Images/Item_Unknown.png"
            img = Image.open(img_path).convert("RGBA")
            w,h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                dpg.add_static_texture(
                        width=w, height=h, default_value=flat, tag=f"Item_{item}")


    def _load_chevrons(self):
        """Load Chev-2.png .. Chev4.png as DPG static textures."""
        try:
            from PIL import Image
        except ImportError:
            print("[warn] Pillow not installed — chevron images unavailable")
            return
        with dpg.texture_registry():
            for v in range(-2, 5):
                path = os.path.join(SCRIPT_DIR, f"Images/Chev{v}.png")
                if not os.path.exists(path):
                    print(f"[warn] {path} not found")
                    continue
                try:
                    img  = Image.open(path).convert("RGBA")
                    w, h = img.size
                    flat = [c / 255.0 for px in img.getdata() for c in px]
                    self._chev_tex[v] = dpg.add_static_texture(
                        width=w, height=h, default_value=flat)
                    self._chev_size = (w, h)
                except Exception as e:
                    print(f"[warn] Could not load Chev{v}.png: {e}")

    def _gen_star_png(self, path: str):
        """Generate a gold star PNG programmatically (no dependencies)."""
        import struct, zlib, math
        W = H = 32
        cx = cy = W / 2 - 0.5
        def star_poly():
            pts = []
            for i in range(10):
                r = 7.0 if i % 2 == 0 else 3.0
                a = math.pi / 2 + i * math.pi / 5
                pts.append((cx + r * math.cos(a), cy - r * math.sin(a)))
            return pts
        def in_poly(px, py, poly):
            n = len(poly); inside = False; j = n - 1
            for i in range(n):
                xi, yi = poly[i]; xj, yj = poly[j]
                if ((yi > py) != (yj > py)) and px < (xj-xi)*(py-yi)/(yj-yi)+xi:
                    inside = not inside
                j = i
            return inside
        pts = star_poly()
        gold = [240, 192, 64]
        rgba = []
        for y in range(H):
            for x in range(W):
                rgba += gold + [255] if in_poly(x, y, pts) else [0, 0, 0, 0]
        def chunk(tag, data):
            crc = zlib.crc32(tag + data) & 0xFFFFFFFF
            return struct.pack(">I", len(data)) + tag + data + struct.pack(">I", crc)
        rows = b""
        for y in range(H):
            rows += b"\x00"
            for x in range(W):
                i = (y * W + x) * 4
                rows += bytes(rgba[i:i+3])  # RGB only for PNG
        png = (b"\x89PNG\r\n\x1a\n"
               + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 2, 0, 0, 0))
               + chunk(b"IDAT", zlib.compress(rows))
               + chunk(b"IEND", b""))
        # Now store as RGBA for DPG
        with open(path, "wb") as f:
            # Write a proper RGBA PNG
            rows2 = b""
            for y in range(H):
                rows2 += b"\x00"
                for x in range(W):
                    i = (y*W+x)*4
                    rows2 += bytes(rgba[i:i+4])
            png2 = (b"\x89PNG\r\n\x1a\n"
                    + chunk(b"IHDR", struct.pack(">IIBBBBB", W, H, 8, 6, 0, 0, 0))
                    + chunk(b"IDAT", zlib.compress(rows2))
                    + chunk(b"IEND", b""))
            f.write(png2)

    def _decode_png(self, raw: bytes):
        """Minimal PNG decoder returning (w, h, rgba_bytes). RGBA/RGB only."""
        import struct, zlib
        sig = raw[:8]
        assert sig == b"\x89PNG\r\n\x1a\n"
        pos = 8; w = h = 0; idat_chunks = []; color_type = 2
        while pos < len(raw):
            length = struct.unpack(">I", raw[pos:pos+4])[0]
            tag  = raw[pos+4:pos+8]
            data = raw[pos+8:pos+8+length]
            if tag == b"IHDR":
                w, h = struct.unpack(">II", data[:8])
                color_type = data[9]
            elif tag == b"IDAT":
                idat_chunks.append(data)
            elif tag == b"IEND":
                break
            pos += 12 + length
        raw_img = zlib.decompress(b"".join(idat_chunks))
        # Un-filter
        bpp = 4 if color_type == 6 else 3
        stride = w * bpp
        rows = []; pos = 0
        prev = bytes(stride)
        for _ in range(h):
            flt  = raw_img[pos]; row = bytearray(raw_img[pos+1:pos+1+stride]); pos += 1 + stride
            if flt == 0: pass
            elif flt == 1:
                for i in range(bpp, stride): row[i] = (row[i] + row[i-bpp]) & 0xFF
            elif flt == 2:
                for i in range(stride): row[i] = (row[i] + prev[i]) & 0xFF
            elif flt == 3:
                for i in range(stride):
                    a = row[i-bpp] if i >= bpp else 0
                    row[i] = (row[i] + (a + prev[i]) // 2) & 0xFF
            elif flt == 4:
                for i in range(stride):
                    a = row[i-bpp] if i >= bpp else 0
                    b2 = prev[i]; c = prev[i-bpp] if i >= bpp else 0
                    p = a + b2 - c; pa=abs(p-a); pb=abs(p-b2); pc=abs(p-c)
                    pr = a if pa<=pb and pa<=pc else (b2 if pb<=pc else c)
                    row[i] = (row[i] + pr) & 0xFF
            rows.append(bytes(row)); prev = bytes(row)
        rgba = bytearray()
        for row in rows:
            for i in range(0, len(row), bpp):
                rgba += row[i:i+3]
                rgba += bytes([row[i+3]]) if bpp == 4 else bytes([255])
        return w, h, bytes(rgba)

    # ── theme ──────────────────────────────────────────────────────────────────
    def _theme(self):
        with dpg.theme() as th:
            with dpg.theme_component(dpg.mvAll):
                for col, val in [
                    (dpg.mvThemeCol_WindowBg,    C_BG),
                    (dpg.mvThemeCol_ChildBg,     C_PANEL),
                    (dpg.mvThemeCol_TitleBg,     C_PANEL),
                    (dpg.mvThemeCol_TitleBgActive,C_BTN),
                    (dpg.mvThemeCol_Tab,         C_PANEL),
                    (dpg.mvThemeCol_TabActive,   C_BTN),
                    (dpg.mvThemeCol_TabHovered,  C_ACCENT),
                    (dpg.mvThemeCol_Header,      C_BTN),
                    (dpg.mvThemeCol_HeaderHovered,(90,78,210,255)),
                    (dpg.mvThemeCol_HeaderActive, C_ACCENT),
                    (dpg.mvThemeCol_Button,      C_BTN),
                    (dpg.mvThemeCol_ButtonHovered,(90,78,210,255)),
                    (dpg.mvThemeCol_ButtonActive, C_ACCENT),
                    (dpg.mvThemeCol_FrameBg,     C_ENTRY),
                    (dpg.mvThemeCol_FrameBgHovered,(60,60,90,255)),
                    (dpg.mvThemeCol_CheckMark,   C_TEAL),
                    (dpg.mvThemeCol_Text,        C_TEXT),
                    (dpg.mvThemeCol_TableRowBg,  C_ROW_A),
                    (dpg.mvThemeCol_TableRowBgAlt,C_ROW_B),
                    (dpg.mvThemeCol_TableBorderLight,(60,60,80,255)),
                    (dpg.mvThemeCol_TableHeaderBg,C_PANEL),
                    (dpg.mvThemeCol_ScrollbarBg, C_BG),
                    (dpg.mvThemeCol_ScrollbarGrab,C_BTN),
                    (dpg.mvThemeCol_PopupBg,     C_PANEL),
                ]:
                    dpg.add_theme_color(col, val)
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  3)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,  4)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding,     4)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,     6, 4)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding,     4, 3)
            with dpg.theme_component(dpg.mvButton, enabled_state=False):
                for col, val in [
                    (dpg.mvThemeCol_Button,      C_BTN_DIS)
                ]:
                    dpg.add_theme_color(col,val)
            with dpg.theme_component(dpg.mvCombo, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Text, C_BTN_DIS)
                dpg.add_theme_color(dpg.mvThemeCol_Button, C_BTN_DIS)
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, C_BTN_DIS)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBgHovered, C_ENTRY)
        dpg.bind_theme(th)
        
        with dpg.theme(tag="red_button_theme"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (150,0,0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (170,0,0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (230,0,0))
                dpg.add_theme_color(dpg.mvThemeCol_Text, (0,0,0))
                
        with dpg.theme(tag="clear_button"):
            with dpg.theme_component(dpg.mvAll):
                dpg.add_theme_color(dpg.mvThemeCol_Button, (0,0,0,0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonHovered, (0,0,0,0))
                dpg.add_theme_color(dpg.mvThemeCol_ButtonActive, (0,0,0,0))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding,  0, 5)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,  0)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding,     0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,     0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding,     0, 0)
            

    def _resize(self, *_):
        w = dpg.get_viewport_client_width()
        h = dpg.get_viewport_client_height()
        dpg.set_item_pos("main", [0, 0])
        dpg.set_item_width("main", w)
        dpg.set_item_height("main", h)

    # ── header ─────────────────────────────────────────────────────────────────
    def _hdr(self):
        with dpg.group(horizontal=True):
            dpg.add_text("Idle Planet Miner", color=C_ACCENT)
            dpg.add_text("  Recipe Value Calculator", color=C_MUTED)
            dpg.add_spacer(width=1)
            dpg.add_button(label="Save",           callback=self._cb_save)
            dpg.add_button(label="Reset Defaults",  callback=self._cb_reset)
            dpg.add_button(label="Sell Galaxy",    callback=self._cb_sell_galaxy)

    # ── helpers: bonus entry strip ────────────────────────────────────────────
    def _bonus_strip(self, key, label, fn_comp, tag_comp, tag_manual, cb):
        dpg.add_text(f"{label}:", color=C_MUTED)
        dpg.add_text(f"×{fn_comp(self.state):.3f}", color=C_TEAL, tag=tag_comp)
        dpg.add_text(" Manual:", color=C_MUTED)
        dpg.add_input_text(default_value=str(self.state["globals"][key]),
                           width=58, tag=tag_manual, on_enter=True,
                           user_data=key, callback=cb)
        dpg.add_spacer(width=14)

    def _machines_strip(self):
        for which, label in [("smelters","Smelters"),("crafters","Crafters")]:
            dpg.add_text(f"{label}:", color=C_MUTED)
            dpg.add_button(label=" - ", width=28,
                           user_data=(which,-1), callback=self._cb_adj_machines)
            dpg.add_text(str(self.state.get(which,1)),
                         tag=f"lbl_{which}", color=C_TEAL)
            dpg.add_button(label=" + ", width=28,
                           user_data=(which,1),  callback=self._cb_adj_machines)
            dpg.add_spacer(width=10)

    def _cb_adj_machines(self, s, v, ud):
        which, delta = ud
        self.state[which] = max(1, self.state.get(which,1)+delta)
        dpg.set_value(f"lbl_{which}", str(self.state[which]))
        save_state(self.state)
        self._refresh_dashboard()

    # ── DASHBOARD ──────────────────────────────────────────────────────────────
    _DCOLS = [
        ("Name",         "name",              160),
        ("Type",         "category",           55),
        ("Output $",     "output_value",       105),
        ("Input Cost",   "direct_cost",        105),
        ("Ore Cost",     "ore_cost",           105),
        ("Profit/Input", "profit_direct",      105),
        ("Profit/Ore",   "profit_ore",         105),
        ("Time",         "craft_time",          72),
        ("Smelt",        "smelt_raw",           72),
        ("Craft",        "craft_raw",           72),
        ("Total",        "total_time",          72),
        ("$/s Out",      "vps_output",          92),
        ("$/s Input",    "vps_profit_direct",   92),
        ("$/s Ore",      "vps_profit_ore",      92),
    ]
    _TIME_KEYS  = {"craft_time","smelt_raw","craft_raw","total_time"}
    _MONEY_KEYS = {"output_value","direct_cost","ore_cost","profit_direct",
                   "profit_ore","vps_output","vps_profit_direct","vps_profit_ore"}

    def _tab_dash(self):
        with dpg.group(horizontal=True):
            dpg.add_text("Show:", color=C_MUTED)
            dpg.add_radio_button(
                items=["All","Alloys","Items"],
                default_value=self.prefs.get("dashboard_filter","All"),
                horizontal=True, tag="dash_filter",
                callback=lambda s,v: (self.prefs.update({"dashboard_filter":v}),
                                      save_prefs(self.prefs),
                                      self._refresh_dashboard()))
            dpg.add_spacer(width=18)
            dpg.add_text("Sort:", color=C_MUTED)
            sort_keys = [c[1] for c in self._DCOLS if c[1] not in ("name","category")]
            dpg.add_combo(items=sort_keys, width=180, tag="dash_sort",
                          default_value=self.prefs.get("dashboard_sort","vps_profit_ore"),
                          callback=lambda s,v: (self.prefs.update({"dashboard_sort":v}),
                                                save_prefs(self.prefs),
                                                self._refresh_dashboard()))
            dpg.add_spacer(width=18)
            self._machines_strip()

        with dpg.table(tag="dash_tbl", header_row=True, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, scrollX=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=1):
            for lbl, key, w in self._DCOLS:
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)

    def _refresh_dashboard(self):
        dpg.delete_item("dash_tbl", children_only=True, slot=1)
        rows  = analyze_all(self.base, self.state)
        flt   = self.prefs.get("dashboard_filter","All")
        sort  = self.prefs.get("dashboard_sort","vps_profit_ore")
        if flt == "Alloys": rows = [r for r in rows if r["category"]=="alloys"]
        if flt == "Items":  rows = [r for r in rows if r["category"]=="items"]
        rows  = [r for r in rows if r["unlocked"]]
        rows.sort(key=lambda r: r.get(sort,0), reverse=True)
        for r in rows:
            with dpg.table_row(parent="dash_tbl"):
                category = r.get("category")
                name = r.get("name")
                img = f"Alloy_{name}" if category == "alloys" else f"Item_{name}"
                
                for _, key, _ in self._DCOLS:
                    v = r.get(key,"")
                    if key == "category":
                        txt = "Alloy" if v=="alloys" else "Item"
                        col = C_TEAL if v=="alloys" else (192,160,255,255)
                    elif key in self._MONEY_KEYS:
                        txt = fmt(v)
                        col = C_BAD if "profit" in key and v<0 else C_TEXT
                    elif key in self._TIME_KEYS:
                        txt = fmt_time(v); col = C_TEXT
                    else:
                        txt = str(v); col = C_TEXT
                    if key == "name":
                        with dpg.group(horizontal=True):
                            dpg.add_image(img)
                            dpg.add_text(txt, color=col)
                    else:
                        dpg.add_text(txt, color=col)

    # ── ORES ───────────────────────────────────────────────────────────────────
    def _tab_ores(self):
        with dpg.table(tag="ores_tbl", header_row=True, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=1):
            for lbl, w in [("",28),("Ore",140),("Base $",105),
                            ("Stars",80),("Market",90),("Real $",105),("Ore/s",82)]:
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)

    def _refresh_ores(self):
        dpg.delete_item("ores_tbl", children_only=True, slot=1)
        for ore, bd in self.base["ores"].items():
            st = self.state["ores"][ore]
            bp = bd["base_price"]; stars = st.get("stars",0); mkt = st.get("market",0)
            rp = bp * [0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars)
            unl = ore_unlocked(ore, self.base, self.state)
            ors = ore_mining_rate(ore, self.base, self.state)
            ore_img = f"Ore_{ore}"
            with dpg.table_row(parent="ores_tbl"):
                if unl:
                    dpg.add_image(self._check)
                else:
                    dpg.add_text("·", color=C_MUTED)
                with dpg.group(horizontal=True):
                    dpg.add_image(ore_img)
                    dpg.add_text(ore)
                dpg.add_text(fmt(bp), color=C_MUTED)
                with dpg.group(horizontal=True):
                    self._star_widget(f"ost_{ore}", 
                                stars=stars,
                                ud=("ores", ore, "stars"))
                    dpg.add_button(label="+", width=22,
                                user_data=(("ores",ore,"stars"),1),
                                callback=self._cb_stars)
                with dpg.group(horizontal=True):
                    self._market_widget(f"mkt_or_{ore}", mkt, ("ores",ore,"market"))
                dpg.add_text(fmt(rp), tag=f"orp_{ore}", color=C_TEAL)
                dpg.add_text(f"{ors:.4f}" if ors else "—",
                             tag=f"ors_{ore}", color=C_MUTED)

    # ── ALLOYS ─────────────────────────────────────────────────────────────────
    def _tab_alloys(self):
        with dpg.group(horizontal=True):
            self._bonus_strip("smelt_speed","Smelt Speed",global_smelt_speed,
                              "alc_comp","alc_man",self._cb_smelt_speed)
        with dpg.table(tag="alloys_tbl", header_row=True, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, scrollX=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=1):
            for lbl, w in [("",28),("Alloy",150),("Base $",105),("Time",75),
                            ("Stars",80),("Market",115),("Real $",105),("Recipe",300)]:
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)

    def _cb_smelt_speed(self, s, v, ud):
        try: val = max(0.01, float(v))
        except: return
        self.state["globals"]["smelt_speed"] = val
        dpg.set_value("alc_comp", f"×{val:.3f}")
        dpg.set_value("alc_man",  str(val))
        save_state(self.state)
        self._refresh_alloys(); self._refresh_dashboard()

    def _refresh_alloys(self):
        dpg.delete_item("alloys_tbl", children_only=True, slot=1)
        ss = max(0.001, global_smelt_speed(self.state))
        dpg.set_value("alc_comp", f"×{ss:.3f}")
        for name, bd in self.base["alloys"].items():
            st = self.state["alloys"][name]
            bp = bd["base_price"]; stars = st.get("stars",0); mkt = st.get("market",0)
            rp = bp * [0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars)
            unl = st.get("unlocked",False)
            at  = bd["smelt_time"] / ss
            rec = ", ".join(f"{q:g}×{i}" for i,q in bd["recipe"].items())
            with dpg.table_row(parent="alloys_tbl"):
                dpg.add_checkbox(default_value=unl,
                                 user_data=("alloys",name,"unlocked"),
                                 callback=self._cb_unlocked)
                with dpg.group(horizontal=True):
                    dpg.add_image(f"Alloy_{name}")
                    dpg.add_text(name)
                dpg.add_text(fmt(bp), color=C_MUTED)
                dpg.add_text(fmt_time(at), color=C_MUTED)
                with dpg.group(horizontal=True):
                    self._star_widget(f"ast_{name}", 
                                ud=("alloys",name,"stars"),
                                stars=stars)
                    dpg.add_button(label="+", width=22,
                                user_data=(("alloys",name,"stars"),1),
                                callback=self._cb_stars)
                with dpg.group(horizontal=True):
                    self._market_widget(f"mkt_al_{name}", mkt, ("alloys",name,"market"))
                dpg.add_text(fmt(rp), tag=f"alp_{name}", color=C_TEAL)
                dpg.add_text(rec, color=C_MUTED)

    # ── ITEMS ──────────────────────────────────────────────────────────────────
    def _tab_items(self):
        with dpg.group(horizontal=True):
            self._bonus_strip("craft_speed","Craft Speed",global_craft_speed,
                              "itc_comp","itc_man",self._cb_craft_speed)
        with dpg.table(tag="items_tbl", header_row=True, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, scrollX=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=1):
            for lbl, w in [("",28),("Item",150),("Base $",105),("Time",75),
                            ("Stars",80),("Market",115),("Real $",105),("Recipe",300)]:
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)

    def _cb_craft_speed(self, s, v, ud):
        try: val = max(0.01, float(v))
        except: return
        self.state["globals"]["craft_speed"] = val
        dpg.set_value("itc_comp", f"×{val:.3f}")
        dpg.set_value("itc_man",  str(val))
        save_state(self.state)
        self._refresh_items(); self._refresh_dashboard()

    def _refresh_items(self):
        dpg.delete_item("items_tbl", children_only=True, slot=1)
        cs = max(0.001, global_craft_speed(self.state))
        dpg.set_value("itc_comp", f"×{cs:.3f}")
        for name, bd in self.base["items"].items():
            st = self.state["items"][name]
            bp = bd["base_price"]; stars = st.get("stars",0); mkt = st.get("market",0)
            rp = bp * [0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars)
            unl = st.get("unlocked",False)
            at  = bd["craft_time"] / cs
            rec = ", ".join(f"{q:g}×{i}" for i,q in bd["recipe"].items())
            with dpg.table_row(parent="items_tbl"):
                dpg.add_checkbox(default_value=unl,
                                 user_data=("items",name,"unlocked"),
                                 callback=self._cb_unlocked)
                with dpg.group(horizontal=True):
                    dpg.add_image(f"Item_{name}")
                    dpg.add_text(name)
                dpg.add_text(fmt(bp), color=C_MUTED)
                dpg.add_text(fmt_time(at), color=C_MUTED)
                with dpg.group(horizontal=True):
                    self._star_widget(f"ist_{name}", 
                                ud=("items",name,"stars"),
                                stars=stars)
                    dpg.add_button(label="+", width=22,
                                user_data=(("items",name,"stars"),1),
                                callback=self._cb_stars)
                with dpg.group(horizontal=True):
                    self._market_widget(f"mkt_it_{name}", mkt, ("items",name,"market"))
                dpg.add_text(fmt(rp), tag=f"itp_{name}", color=C_TEAL)
                dpg.add_text(rec, color=C_MUTED)

    # ── PROJECTS ───────────────────────────────────────────────────────────────
    def _tab_projects(self):
        with dpg.group(horizontal=True):
            dpg.add_text("Sort:", color=C_MUTED)
            dpg.add_radio_button(items=["name","cost","time"],
                                 default_value=self.prefs.get("projects_sort","time"),
                                 horizontal=True, tag="proj_sort",
                                 callback=lambda s,v: (self.prefs.update({"projects_sort":v}),
                                                        save_prefs(self.prefs),
                                                        self._refresh_projects()))
        with dpg.table(tag="proj_tbl", header_row=True, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, scrollX=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=1):
            for lbl, w in [("",28),("Project",200),("Cost",110),("Time",82),
                            ("Prereq",170),("Ingredients",380)]:
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)

    def _refresh_projects(self):
        dpg.delete_item("proj_tbl", children_only=True, slot=1)
        sort = self.prefs.get("projects_sort","time")
        sm = self.state.get("smelters",1); cr = self.state.get("crafters",1)

        def sk(item):
            n, bd = item
            if sort=="cost":
                return sum(effective_price(i,self.base,self.state)*q
                           for i,q in bd["recipe"].items())
            if sort=="time":
                st2=0; ct2=0
                for i,q in bd["recipe"].items():
                    c2 = "alloys" if i in self.base["alloys"] else ("items" if i in self.base["items"] else None)
                    if c2:
                        st2 += total_smelt_time(i,c2,self.base,self.state)*q
                        ct2 += total_craft_time(i,c2,self.base,self.state)*q
                return wall_time(st2,ct2,sm,cr)
            return n.lower()

        for name, bd in sorted(self.base["projects"].items(), key=sk):
            rec = bd["recipe"]; pre = bd.get("prereq","")
            met  = prereq_met(pre, self.state)
            done = self.state["projects"].get(name,{}).get("researched",False)
            cost = sum(effective_price(i,self.base,self.state)*q for i,q in rec.items())
            st2=0; ct2=0
            for i,q in rec.items():
                c2 = "alloys" if i in self.base["alloys"] else ("items" if i in self.base["items"] else None)
                if c2:
                    st2 += total_smelt_time(i,c2,self.base,self.state)*q
                    ct2 += total_craft_time(i,c2,self.base,self.state)*q
            wt  = wall_time(st2,ct2,sm,cr)
            pre_str = (" OR ".join(pre) if isinstance(pre,list) else pre) or "—"
            rec_str = ", ".join(f"{q:g}×{i}" for i,q in rec.items())
            col = C_TEAL if done else ((85,85,112,255) if not met else C_TEXT)
            with dpg.table_row(parent="proj_tbl"):
                dpg.add_checkbox(default_value=done, user_data=name,
                                 callback=self._cb_proj_check)
                dpg.add_text(name,    color=col)
                dpg.add_text(fmt(cost),color=col)
                dpg.add_text(fmt_time(wt), color=col)
                dpg.add_text(pre_str, color=col)
                dpg.add_text(rec_str, color=col)

    def _cb_proj_check(self, s, v, ud):
        self.state["projects"][ud]["researched"] = v
        save_state(self.state)
        self._refresh_projects()
        self._refresh_dashboard()



    # ── MANAGERS ───────────────────────────────────────────────────────────────
    # State: state["managers"] = list of dicts:
    #   {"name": str, "planet": str|"", "primary": str, "secondary": str, "stars": int}

    _PRIMARY_OPTS   = ["Mine Rate", "Ship Speed", "Cargo"]
    _PRIMARY_KEYS   = ["mining",    "speed",      "cargo"]
    _SECONDARY_OPTS = ["All Mine Rate", "All Ship Speed", "All Cargo",
                       "All Craft Speed", "All Smelt Speed", "-"]
    _SECONDARY_KEYS = ["mining",        "speed",          "cargo",
                       "craft_speed",   "smelt_speed",    "none"]

    def _mgr_primary_label(self, key):
        try: return self._PRIMARY_OPTS[self._PRIMARY_KEYS.index(key)]
        except: return key

    def _mgr_secondary_label(self, key):
        try: return self._SECONDARY_OPTS[self._SECONDARY_KEYS.index(key)]
        except: return key

    def _mgr_primary_mult(self, primary, stars):
        stars = max(1, min(7, stars))
        return _MGR_PRIMARY.get(primary, [1.0]*7)[stars - 1]

    def _mgr_secondary_mult(self, secondary, stars):
        if secondary == "none" or stars < 3: return 0.0
        stars = max(1, min(7, stars))
        return _MGR_SECONDARY.get(secondary, [0.0]*7)[stars - 1]

    def _mgr_secondary_display(self, secondary, stars):
        add = self._mgr_secondary_mult(secondary, stars)
        if secondary == "none" or stars < 3: return "—"
        return f"x{1.0 + add:.2f}"

    def _tab_managers(self):
        with dpg.group(horizontal=True):
            dpg.add_button(label="+ Add Manager", callback=self._cb_mgr_add)
        with dpg.table(
            tag="mgr_tbl", header_row=True, row_background=True,
            borders_innerH=True, borders_outerH=True,
            borders_innerV=True, borders_outerV=True,
            scrollY=True, scrollX=True, resizable=True,
            policy=dpg.mvTable_SizingFixedFit, freeze_rows=1,
        ):
            for lbl, w in [
                ("",18), ("Name",140), ("Planet",150), ("Stars",225),
                ("Primary",115), ("",80), ("Secondary",130), ("",80),
            ]:
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)

    def _refresh_managers(self):
        dpg.delete_item("mgr_tbl", children_only=True, slot=1)
        managers = self.state.get("managers", [])
        planet_opts = [""] + [
            f"{pid}: {self.base['planets'][pid]['name']}"
            for pid, ps in sorted(self.state["planets"].items(), key=lambda x: int(x[0]))
            if ps["owned"]
        ]
        for idx, mgr in enumerate(managers):
            name      = mgr.get("name", f"Manager {idx+1}")
            planet    = mgr.get("planet", "")
            stars     = max(1, min(7, mgr.get("stars", 1)))
            primary   = mgr.get("primary", "mining")
            secondary = mgr.get("secondary", "none")
            planet_display = (f"{planet}: {self.base['planets'][planet]['name']}"
                              if planet else "")
            pri_mult = self._mgr_primary_mult(primary, stars)
            sec_disp = self._mgr_secondary_display(secondary, stars)

            with dpg.table_row(parent="mgr_tbl"):
                x_button = dpg.add_button(label="X", 
                               user_data=idx, callback=self._cb_mgr_delete)
                dpg.bind_item_theme(x_button, "red_button_theme")
                
                dpg.add_input_text(default_value=name, width=135,
                                   tag=f"mgr_name_{idx}", user_data=idx,
                                   on_enter=True, callback=self._cb_mgr_name)
                dpg.add_combo(items=planet_opts, default_value=planet_display,
                              width=145, user_data=idx,
                              callback=self._cb_mgr_planet)
                # 7 star images
                with dpg.group(horizontal=True):
                    for si in range(1, 8):
                        tex = "star_white" if si <= stars else "star_black"
                        dpg.add_image_button(
                            texture_tag=tex,
                            width=20, height=20,
                            tag=f"mgr_star_{idx}_{si}",
                            user_data=(idx, si),
                            callback=self._cb_mgr_star_click)
                        dpg.bind_item_theme(f"mgr_star_{idx}_{si}", "clear_button")
                        
                dpg.add_combo(items=self._PRIMARY_OPTS,
                              default_value=self._mgr_primary_label(primary),
                              width=110, user_data=idx,
                              callback=self._cb_mgr_primary)
                dpg.add_text(f"x{pri_mult:.2f}", color=C_TEAL, tag=f"mgr_pri_eff_{idx}")
                dpg.add_combo(items=self._SECONDARY_OPTS,
                              default_value=self._mgr_secondary_label(secondary),
                              width=125, user_data=idx,
                              callback=self._cb_mgr_secondary)
                dpg.add_text(sec_disp,
                             color=C_TEAL if sec_disp != "—" else C_MUTED,
                             tag=f"mgr_sec_eff_{idx}")

    def _mgr_assign_planet(self, mgr_idx, new_pid):
        managers = self.state.setdefault("managers", [])
        for i, m in enumerate(managers):
            if i != mgr_idx and m.get("planet") == new_pid:
                m["planet"] = ""
        managers[mgr_idx]["planet"] = new_pid

    def _cb_mgr_add(self):
        self.state.setdefault("managers", []).append({
            "name": f"Manager {len(self.state['managers'])+1}",
            "planet": "", "primary": "mining", "secondary": "none", "stars": 1
        })
        save_state(self.state)
        self._refresh_managers()

    def _cb_mgr_delete(self, s, v, ud):
        mgrs = self.state.get("managers", [])
        if 0 <= ud < len(mgrs): mgrs.pop(ud)
        save_state(self.state)
        self._refresh_managers()
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_mgr_name(self, s, v, ud):
        self.state["managers"][ud]["name"] = v.strip() or f"Manager {ud+1}"
        save_state(self.state)

    def _cb_mgr_planet(self, s, v, ud):
        pid = v.split(":")[0].strip() if v else ""
        self._mgr_assign_planet(ud, pid)
        save_state(self.state)
        self._refresh_managers()
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_mgr_star_click(self, s, v, ud):
        idx, si = ud
        self.state["managers"][idx]["stars"] = si
        save_state(self.state)
        for sj in range(1, 8):
            tag = f"mgr_star_{idx}_{sj}"
            if dpg.does_item_exist(tag):
                dpg.configure_item(tag, texture_tag=("star_white" if sj<=si else "star_black"))
        mgr = self.state["managers"][idx]
        pri_mult = self._mgr_primary_mult(mgr["primary"], si)
        if dpg.does_item_exist(f"mgr_pri_eff_{idx}"):
            dpg.set_value(f"mgr_pri_eff_{idx}", f"x{pri_mult:.2f}")
        sec_disp = self._mgr_secondary_display(mgr["secondary"], si)
        if dpg.does_item_exist(f"mgr_sec_eff_{idx}"):
            dpg.set_value(f"mgr_sec_eff_{idx}", sec_disp)
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_mgr_primary(self, s, v, ud):
        try: key = self._PRIMARY_KEYS[self._PRIMARY_OPTS.index(v)]
        except: return
        self.state["managers"][ud]["primary"] = key
        stars = self.state["managers"][ud].get("stars", 1)
        if dpg.does_item_exist(f"mgr_pri_eff_{ud}"):
            dpg.set_value(f"mgr_pri_eff_{ud}", f"x{self._mgr_primary_mult(key,stars):.2f}")
        save_state(self.state)
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_mgr_secondary(self, s, v, ud):
        try: key = self._SECONDARY_KEYS[self._SECONDARY_OPTS.index(v)]
        except: return
        self.state["managers"][ud]["secondary"] = key
        stars = self.state["managers"][ud].get("stars", 1)
        sec_disp = self._mgr_secondary_display(key, stars)
        if dpg.does_item_exist(f"mgr_sec_eff_{ud}"):
            dpg.set_value(f"mgr_sec_eff_{ud}", sec_disp)
        save_state(self.state)
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_planet_manager(self, s, v, ud):
        pid = ud
        mgr_name = v.strip() if v else ""
        managers = self.state.setdefault("managers", [])
        for m in managers:
            if m.get("planet") == pid: m["planet"] = ""
        if mgr_name:
            for i, m in enumerate(managers):
                if m.get("name") == mgr_name:
                    self._mgr_assign_planet(i, pid)
                    break
        save_state(self.state)
        self._refresh_managers()
        self._refresh_planets()
        self._refresh_dashboard()

    # ── COLONIES ───────────────────────────────────────────────────────────────
    # Colony rows are stored in state["colonies"] as a list of dicts:
    #   {"planet": "2", "recipe": {"Iron": 100, ...}}
    # planet "" means unassigned.

    _N_INGR = 5   # number of ingredient slots per colony row

    def _col_owned_planet_items(self):
        """List of "pid: name" strings for owned planets, plus blank."""
        items = [""]
        for pid, bd in sorted(self.base["planets"].items(), key=lambda x: int(x[0])):
            if self.state["planets"][pid]["owned"]:
                items.append(f"{pid}: {bd['name']}")
        return items

    def _col_ingredient_items(self):
        """All unlocked ores + unlocked alloys/items, plus blank."""
        opts = [""]
        for ore in self.base["ores"]:
            if ore_unlocked(ore, self.base, self.state):
                opts.append(ore)
        for name in self.base["alloys"]:
            if self.state["alloys"][name].get("unlocked"):
                opts.append(name)
        for name in self.base["items"]:
            if self.state["items"][name].get("unlocked"):
                opts.append(name)
        return opts

    def _col_recipe_cost_time(self, recipe: dict):
        """Return (cost, wall_time) for a colony recipe dict."""
        sm = self.state.get("smelters", 1)
        cr = self.state.get("crafters", 1)
        cost = sum(effective_price(i, self.base, self.state) * q
                   for i, q in recipe.items())
        st2 = 0; ct2 = 0
        for i, q in recipe.items():
            c2 = ("alloys" if i in self.base["alloys"]
                  else "items" if i in self.base["items"] else None)
            if c2:
                st2 += total_smelt_time(i, c2, self.base, self.state) * q
                ct2 += total_craft_time(i, c2, self.base, self.state) * q
        wt = wall_time(st2, ct2, sm, cr)
        return cost, wt

    def _tab_colonies(self):
        # Sort controls + Add row button
        with dpg.group(horizontal=True):
            dpg.add_text("Sort:", color=C_MUTED)
            dpg.add_radio_button(
                items=["planet", "cost", "time"],
                default_value=self.prefs.get("colonies_sort", "planet"),
                horizontal=True, tag="col_sort",
                callback=lambda s, v: (
                    self.prefs.update({"colonies_sort": v}),
                    save_prefs(self.prefs),
                    self._refresh_colonies()))
            dpg.add_spacer(width=20)
            dpg.add_button(label="+ Add Colony", callback=self._cb_col_add_row)

        ing_cols = []
        for i in range(1, self._N_INGR + 1):
            ing_cols += [(f"Ingredient {i}", 150), (f"Qty {i}", 60)]

        with dpg.table(
            tag="col_tbl", header_row=True, row_background=True,
            borders_innerH=True, borders_outerH=True,
            borders_innerV=True, borders_outerV=True,
            scrollY=True, scrollX=True, resizable=True,
            policy=dpg.mvTable_SizingFixedFit, freeze_rows=1,
        ):
            for lbl, w in (
                [(" ", 105), ("Planet", 150), ("Cost", 110), ("Time", 82)]
                + ing_cols
            ):
                dpg.add_table_column(label=lbl, width_fixed=True,
                                     init_width_or_weight=w)

    def _refresh_colonies(self):
        dpg.delete_item("col_tbl", children_only=True, slot=1)
        colonies = self.state.get("colonies", [])
        sort = self.prefs.get("colonies_sort", "planet")
        sm = self.state.get("smelters", 1)
        cr = self.state.get("crafters", 1)

        def sort_key(item):
            idx, row = item
            if sort == "cost":
                return self._col_recipe_cost_time(row.get("recipe", {}))[0]
            if sort == "time":
                return self._col_recipe_cost_time(row.get("recipe", {}))[1]
            # planet: sort by numeric planet id, unassigned last
            pid = row.get("planet", "")
            return (0, int(pid)) if pid else (1, 0)

        planet_items = self._col_owned_planet_items()
        ing_items    = self._col_ingredient_items()

        for orig_idx, row in sorted(enumerate(colonies), key=sort_key):
            recipe  = row.get("recipe", {})
            pid     = row.get("planet", "")
            cost, wt = self._col_recipe_cost_time(recipe)
            has_planet = bool(pid)
            planet_val = f"{pid}: {self.base['planets'][pid]['name']}" if pid else ""

            with dpg.table_row(parent="col_tbl"):
                # Complete button — disabled if no planet selected
                with dpg.group(horizontal=True):
                    dpg.add_button(
                        label="Complete",
                        enabled=has_planet,
                        user_data=orig_idx,
                        callback=self._cb_col_complete)
                    x_button = dpg.add_button(
                        label="X",
                        user_data=orig_idx,
                        callback=self._cb_col_cancel)
                    dpg.bind_item_theme(x_button, "red_button_theme")

                # Planet dropdown
                dpg.add_combo(
                    items=planet_items,
                    default_value=planet_val,
                    width=145,
                    user_data=orig_idx,
                    callback=self._cb_col_planet)

                # Calculated columns
                dpg.add_text(fmt(cost), color=C_TEAL)
                dpg.add_text(fmt_time(wt), color=C_MUTED)

                # Ingredient slots
                recipe_items = list(recipe.items())
                for slot in range(self._N_INGR):
                    ing  = recipe_items[slot][0] if slot < len(recipe_items) else ""
                    qty  = recipe_items[slot][1] if slot < len(recipe_items) else 1
                    dpg.add_combo(
                        items=ing_items,
                        default_value=ing,
                        width=145,
                        user_data=(orig_idx, slot, "ing"),
                        callback=self._cb_col_ingredient)
                    dpg.add_input_int(
                        default_value=int(qty) if ing else 1,
                        width=55, step=0,
                        min_value=1, min_clamped=True,
                        on_enter=True,
                        user_data=(orig_idx, slot, "qty"),
                        callback=self._cb_col_qty)

    def _cb_col_add_row(self):
        self.state.setdefault("colonies", []).append({"planet": "", "recipe": {}})
        save_state(self.state)
        self._refresh_colonies()

    def _cb_col_planet(self, s, v, ud):
        orig_idx = ud
        pid = v.split(":")[0].strip() if v else ""
        self.state["colonies"][orig_idx]["planet"] = pid
        save_state(self.state)
        self._refresh_colonies()

    def _cb_col_ingredient(self, s, v, ud):
        orig_idx, slot, _ = ud
        row    = self.state["colonies"][orig_idx]
        recipe = row.get("recipe", {})
        items  = list(recipe.items())
        # Rebuild recipe preserving slot order
        new_recipe = {}
        for i in range(self._N_INGR):
            ing = items[i][0] if i < len(items) else ""
            qty = items[i][1] if i < len(items) else 1
            if i == slot:
                ing = v
            if ing:
                new_recipe[ing] = qty
        row["recipe"] = new_recipe
        save_state(self.state)
        self._refresh_colonies()

    def _cb_col_qty(self, s, v, ud):
        orig_idx, slot, _ = ud
        row    = self.state["colonies"][orig_idx]
        recipe = row.get("recipe", {})
        items  = list(recipe.items())
        if slot < len(items):
            ing = items[slot][0]
            row["recipe"][ing] = max(1, int(v))
            save_state(self.state)
            self._refresh_colonies()

    def _cb_col_cancel(self, s, v, ud):
        orig_idx = ud
        self.state["colonies"].pop(orig_idx)
        save_state(self.state)
        self._refresh_colonies()
        self._refresh_planets()
        self._refresh_dashboard()
        
        
    def _cb_col_complete(self, s, v, ud):
        orig_idx = ud
        row = self.state["colonies"][orig_idx]
        pid = row.get("planet", "")
        if not pid:
            return
        planet_name = self.base["planets"][pid]["name"]

        def _apply(sender, val, stat):
            dpg.delete_item("col_bonus_dlg")
            if stat is None:
                return
            bonuses = {"mining": 0.3, "speed": 0.6, "cargo": 0.6}
            idx_map  = {"mining": 0,   "speed": 1,   "cargo": 2}
            inc  = bonuses[stat]
            idx  = idx_map[stat]
            cur  = self.state["planets"][pid]["colony"][idx]
            self.state["planets"][pid]["colony"][idx] = round(cur + inc, 4)
            # Remove this colony row
            self.state["colonies"].pop(orig_idx)
            save_state(self.state)
            self._refresh_colonies()
            self._refresh_planets()
            self._refresh_dashboard()

        vp_w = dpg.get_viewport_client_width()
        vp_h = dpg.get_viewport_client_height()
        dlg_w, dlg_h = 320, 210
        px = (vp_w - dlg_w) // 2
        py = (vp_h - dlg_h) // 2
        colony_state = self.state["planets"][pid]["colony"]

        with dpg.window(label=f"Complete Colony – {planet_name}",
                        modal=True, tag="col_bonus_dlg",
                        width=dlg_w, height=dlg_h, pos=(px, py)):
            dpg.add_text("Apply bonus to:")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Mining Rate",
                        width=110,
                        user_data="mining", callback=_apply)
                dpg.add_text(f"{colony_state[0]}")
                dpg.add_image(self._arrow_right,
                        width=self._arrow_right_size[0],
                        height=self._arrow_right_size[1]
                        )
                dpg.add_text(f"{colony_state[0] + 0.3}")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Ship Speed",
                            width=110,
                            user_data="speed",  callback=_apply)
                dpg.add_text(f"{colony_state[1]}")
                dpg.add_image(self._arrow_right,
                        width=self._arrow_right_size[0],
                        height=self._arrow_right_size[1]
                        )
                dpg.add_text(f"{colony_state[1] + 0.6}")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Ship Cargo",
                            width=110,
                            user_data="cargo",  callback=_apply)
                dpg.add_text(f"{colony_state[2]}")
                dpg.add_image(self._arrow_right,
                        width=self._arrow_right_size[0],
                        height=self._arrow_right_size[1]
                        )
                dpg.add_text(f"{colony_state[2] + 0.3}")
            dpg.add_separator()
            dpg.add_button(label="Cancel", user_data=None, callback=_apply)


    # ── BEACONS ────────────────────────────────────────────────────────────────
    # Beacons are keyed by telescope level (str "0".."22").
    # Beacon "0" applies to scope-0 planets (1-4), beacon "1" to scope-1 (5-7), etc.
    # Unlocked once the matching Telescope project is researched (scope 0 always active).
    # Bonus increments: mining +0.02, speed/cargo +0.04.

    # Map: telescope level -> project name that unlocks it (scope 0 always active)
    _BEACON_PROJECT = {i: f"Telescope {i}" for i in range(1, 23)}

    def _beacon_unlocked(self, scope: int) -> bool:
        if scope == 0: return True
        proj = self._BEACON_PROJECT.get(scope, "")
        return self.state["projects"].get(proj, {}).get("researched", False)

    def _beacon_planet_range(self, scope: int) -> str:
        """Return e.g. '1-4' for the planets in this scope group."""
        import json as _json
        pids = sorted(
            int(k) for k, v in self.base["planets"].items()
            if v["telescope"] == scope)
        if not pids: return "—"
        return f"{pids[0]}–{pids[-1]}"

    def _tab_beacons(self):
        with dpg.table(
            tag="beacon_tbl", header_row=True, row_background=True,
            borders_innerH=True, borders_outerH=True,
            borders_innerV=True, borders_outerV=True,
            scrollY=True, resizable=True,
            policy=dpg.mvTable_SizingFixedFit, freeze_rows=1,
        ):
            for lbl, w in [
                ("Scope", 52), ("Planets", 70), ("Unlocked by", 150),
                ("Mining", 120), ("Speed", 120), ("Cargo", 120),
            ]:
                dpg.add_table_column(label=lbl, width_fixed=True,
                                     init_width_or_weight=w)

    def _refresh_beacons(self):
        dpg.delete_item("beacon_tbl", children_only=True, slot=1)
        beacons = self.state.get("beacons", {})

        for scope in range(23):
            key     = str(scope)
            vals    = beacons.get(key, {"mining":1.0,"speed":1.0,"cargo":1.0})
            active  = self._beacon_unlocked(scope)
            col     = C_TEXT if active else (85, 85, 112, 255)
            proj    = self._BEACON_PROJECT.get(scope, "—")
            planets = self._beacon_planet_range(scope)

            with dpg.table_row(parent="beacon_tbl"):
                dpg.add_text(str(scope), color=col)
                dpg.add_text(planets,    color=col)
                dpg.add_text(proj if scope > 0 else "Always active", color=col)

                # Mining bonus widget
                self._beacon_input(key, "mining", vals["mining"], active,
                                   inc=0.02, tag=f"bcn_{key}_mining")
                # Speed bonus widget
                self._beacon_input(key, "speed",  vals["speed"],  active,
                                   inc=0.04, tag=f"bcn_{key}_speed")
                # Cargo bonus widget
                self._beacon_input(key, "cargo",  vals["cargo"],  active,
                                   inc=0.04, tag=f"bcn_{key}_cargo")

    def _beacon_input(self, key: str, stat: str, val: float,
                      active: bool, inc: float, tag: str):
        """Editable float field + + button for a beacon bonus."""
        with dpg.group(horizontal=True):
            dpg.add_input_text(
                default_value=f"{val:.2f}",
                width=58, tag=tag,
                enabled=active,
                on_enter=True,
                user_data=(key, stat),
                callback=self._cb_beacon_edit)
            dpg.add_button(
                label="+", width=22,
                enabled=active,
                user_data=(key, stat, inc),
                callback=self._cb_beacon_inc)

    def _cb_beacon_edit(self, s, v, ud):
        key, stat = ud
        try:
            val = max(1.0, round(float(v), 4))
        except ValueError:
            return
        self.state.setdefault("beacons", {}).setdefault(key, {"mining":1.0,"speed":1.0,"cargo":1.0})[stat] = val
        tag = f"bcn_{key}_{stat}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, f"{val:.2f}")
        save_state(self.state)
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_beacon_inc(self, s, v, ud):
        key, stat, inc = ud
        beacons = self.state.setdefault("beacons", {})
        cur = beacons.setdefault(key, {"mining":1.0,"speed":1.0,"cargo":1.0}).get(stat, 1.0)
        val = round(cur + inc, 4)
        beacons[key][stat] = val
        tag = f"bcn_{key}_{stat}"
        if dpg.does_item_exist(tag):
            dpg.set_value(tag, f"{val:.2f}")
        save_state(self.state)
        self._refresh_planets()
        self._refresh_dashboard()

    # ── PLANETS ────────────────────────────────────────────────────────────────
    def _tab_planets(self):
        with dpg.group(horizontal=True):
            for key, label, fn, tc, tm in [
                ("mining","Mining Rate",global_mining_bonus,"gmc","gmm"),
                ("speed", "Ship Speed", global_speed_bonus, "gsc","gsm"),
                ("cargo", "Ship Cargo", global_cargo_bonus, "gcc","gcm"),
            ]:
                self._bonus_strip(key, label, fn, tc, tm, self._cb_planet_global)
        with dpg.table(tag="planet_tbl", header_row=False, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, scrollX=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=2):
            # 19 columns: 11 main + 3 probe + 3 colony + 2 separator
            for w in [
                28, 105, 25, 27,    # #, Planet, Scope, Owned, 
                140,                    # Manager
                58, 72,                 # M.Lvl, Min/s
                62,                     # Calculated transport speed
                58, 62,                 # S.Lvl, Spd
                58, 50,                 # C.Lvl, Crg
                50, 50, 50,             # Probe: Mng, Spd, Crg
                5,
                50, 50, 50,             # Colony: Mng, Spd, Crg
                5,
                210,                    # Ores
            ]:
                dpg.add_table_column(label="", width_fixed=True, init_width_or_weight=w)

    def _cb_planet_global(self, s, v, ud):
        key = ud
        try: val = max(0.01, float(v))
        except: return
        self.state["globals"][key] = val
        fn_map = {"mining":global_mining_bonus,"speed":global_speed_bonus,"cargo":global_cargo_bonus}
        tc_map = {"mining":"gmc","speed":"gsc","cargo":"gcc"}
        tm_map = {"mining":"gmm","speed":"gsm","cargo":"gcm"}
        dpg.set_value(tc_map[key], f"×{fn_map[key](self.state):.3f}")
        dpg.set_value(tm_map[key], str(val))
        save_state(self.state)
        self._refresh_planets()

    def _cb_planet_owned(self, s, v, ud):
        pid = ud
        self.state["planets"][pid]["owned"] = v
        if v:
            lvls = self.state["planets"][pid]["levels"]
            for k in lvls:
                if lvls[k] == 0: lvls[k] = 1
        save_state(self.state)
        self._refresh_planets()
        self._refresh_ores()
        self._refresh_dashboard()

    def _cb_planet_lvl(self, s, v, ud):
        pid, stat, delta = ud
        cur = self.state["planets"][pid]["levels"][stat]
        self.state["planets"][pid]["levels"][stat] = max(1, cur+delta)
        save_state(self.state)
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_planet_lvl_edit(self, s, v, ud):
        pid, stat = ud
        self.state["planets"][pid]["levels"][stat] = max(1, int(v))
        save_state(self.state)
        self._refresh_planets()
        self._refresh_dashboard()

    def _cb_planet_bonus_val(self, s, v, ud):
        pid, group, idx = ud
        try: val = float(v)
        except: return
        self.state["planets"][pid][group][idx] = val
        save_state(self.state)
        self._refresh_planets()
        self._refresh_dashboard()

    def _refresh_planets(self):
        # Save scroll position
        scroll_y = dpg.get_y_scroll("planet_tbl")
        
        dpg.delete_item("planet_tbl", children_only=True, slot=1)
        gm=global_mining_bonus(self.state); gs=global_speed_bonus(self.state); gc=global_cargo_bonus(self.state)
        # update bonus comp labels
        for tc, fn, key in [("gmc",global_mining_bonus,"mining"),
                             ("gsc",global_speed_bonus,"speed"),
                             ("gcc",global_cargo_bonus,"cargo")]:
            dpg.set_value(tc, f"×{fn(self.state):.3f}")

        # ── header row 1: group span labels ──────────────────────────────────
        with dpg.table_row(parent="planet_tbl"):
            # columns 0-10: plain labels, no group heading
            for lbl in ["","","","","","","","","","","",""]:
                dpg.add_text(lbl, color=C_ACCENT)
            # columns 11-13: "Probes" spanning — place in col 11, overflow right

            dpg.add_text("<----", color=C_TEAL)
            dpg.add_text("Probes", color=C_TEAL)
            dpg.add_text("---->", color=C_TEAL)  
            dpg.add_text() #Divider
            # columns 14-16: "Colony" spanning
            dpg.add_text("<----", color=C_TEAL)
            dpg.add_text("Colony", color=C_TEAL)
            dpg.add_text("---->", color=C_TEAL) 
            dpg.add_text() #Divider
            dpg.add_text("")

        # ── header row 2: sub-column labels ──────────────────────────────────
        with dpg.table_row(parent="planet_tbl"):
            # columns 0-10: plain labels, no group heading
            for lbl in ["#","Planet"]:
                dpg.add_text(lbl, color=C_ACCENT)
            dpg.add_image(self._telescope, width=self._telescope_size[0], height=self._telescope_size[1])
            for lbl in [" ","Manager",
                         "M.Lvl","Ore/s","Transport","S.Lvl","Speed","C.Lvl","Cargo"]:
                dpg.add_text(lbl, color=C_ACCENT)
            for lbl in ["Mng","Spd","Crg","","Mng","Spd","Crg",""]:
                dpg.add_text(lbl, color=C_MUTED)
            dpg.add_text("Ores", color=C_ACCENT)

        for pid, bd in sorted(self.base["planets"].items(), key=lambda x:int(x[0])):
            ps    = self.state["planets"][pid]
            owned = ps["owned"]; lvls = ps["levels"]
            probe = ps["probes"]; colony = ps["colony"]
            dist = self.base["planets"][pid]["distance"]
            bm = beacon_bonus(pid,"mining",self.base,self.state)
            bs = beacon_bonus(pid,"speed", self.base,self.state)
            bc = beacon_bonus(pid,"cargo", self.base,self.state)
            mm = manager_primary_bonus(pid,"mining",self.state)
            ms = manager_primary_bonus(pid,"speed", self.state)
            mc = manager_primary_bonus(pid,"cargo", self.state)
            mb = probe[0]*colony[0]*bm*mm*gm
            sb = probe[1]*colony[1]*bs*ms*gs
            cb = probe[2]*colony[2]*bc*mc*gc
            mr = _mining_rate(lvls["mining"],mb) if owned else 0
            sp = _ship_speed( lvls["speed"], sb) if owned else 0
            cg = _ship_cargo( lvls["cargo"], cb) if owned else 0
            scope = str(bd["telescope"]) if bd["telescope"] else "—"
            ores  = ", ".join(f"{o} {p}%" for o,p in bd["resources"].items())
            col   = C_TEXT if owned else (85,85,112,255)

            def lvl_grp(stat):
                with dpg.group(horizontal=True):
                    if owned:
                        dpg.add_input_text(default_value=int(lvls[stat]), on_enter=True, width=34, user_data=(pid,stat),callback=self._cb_planet_lvl_edit)
                        dpg.add_button(label="+",width=16,user_data=(pid,stat,1), callback=self._cb_planet_lvl)
                    else:
                        dpg.add_text("—", color=C_MUTED)

            with dpg.table_row(parent="planet_tbl"):
                dpg.add_text(pid, color=col)
                dpg.add_text(bd["name"], color=col)
                dpg.add_text(scope, color=C_MUTED)
                dpg.add_checkbox(default_value=owned, user_data=pid,
                                 callback=self._cb_planet_owned)
                # Manager column
                mgr_names = [""] + [m["name"] for m in self.state.get("managers", [])]
                cur_mgr = next((m["name"] for m in self.state.get("managers", []) if m.get("planet")==pid), "")
                dpg.add_combo(items=mgr_names, default_value=cur_mgr,
                              width=135, user_data=pid, enabled=owned,
                              callback=self._cb_planet_manager)
                lvl_grp("mining")
                with dpg.group():
                    dpg.add_text(f"{mr:.2f}" if owned else "—", color=col)
                    if owned:
                        with dpg.tooltip(dpg.last_item()):
                            base_mr = _mining_rate(lvls["mining"])
                            dpg.add_text(f"Base:    {base_mr:.4f}")
                            dpg.add_text(f"Probe:   ×{probe[0]:.2f}")
                            dpg.add_text(f"Colony:  ×{colony[0]:.2f}")
                            dpg.add_text(f"Beacon:  ×{bm:.2f}")
                            if mm != 1.0: dpg.add_text(f"Manager: ×{mm:.2f}")
                            if _proj(self.state,"Advanced Mining"):  dpg.add_text("Advanced Mining:  ×1.25")
                            if _proj(self.state,"Superior Mining"):  dpg.add_text("Superior Mining:  ×1.25")
                            manual_m = float(self.state.get("globals",{}).get("mining",1))
                            if manual_m != 1.0: dpg.add_text(f"Manual:  ×{manual_m:.3f}")
                            msec_m = manager_secondary_bonus("mining", self.state)
                            if msec_m != 1.0: dpg.add_text(f"Mgr Sec: ×{msec_m:.3f} (global)")
                
                ts = _planet_transport(dist, sp, cg)
                dpg.add_text(f"{ts:.1f}", color=C_TEAL)
                lvl_grp("speed")
                with dpg.group():
                    dpg.add_text(f"{sp:.2f}" if owned else "—", color=col)
                    if owned:
                        with dpg.tooltip(dpg.last_item()):
                            base_sp = _ship_speed(lvls["speed"])
                            dpg.add_text(f"Base:    {base_sp:.4f}")
                            dpg.add_text(f"Probe:   ×{probe[1]:.2f}")
                            dpg.add_text(f"Colony:  ×{colony[1]:.2f}")
                            dpg.add_text(f"Beacon:  ×{bs:.2f}")
                            if ms != 1.0: dpg.add_text(f"Manager: ×{ms:.2f}")
                            if _proj(self.state,"Advanced Thrusters"): dpg.add_text("Advanced Thrusters: ×1.25")
                            if _proj(self.state,"Superior Thrusters"): dpg.add_text("Superior Thrusters: ×1.25")
                            manual_s = float(self.state.get("globals",{}).get("speed",1))
                            if manual_s != 1.0: dpg.add_text(f"Manual:  ×{manual_s:.3f}")
                            msec_s = manager_secondary_bonus("speed", self.state)
                            if msec_s != 1.0: dpg.add_text(f"Mgr Sec: ×{msec_s:.3f} (global)")
                lvl_grp("cargo")
                with dpg.group():
                    dpg.add_text(str(cg) if owned else "—", color=col)
                    if owned:
                        with dpg.tooltip(dpg.last_item()):
                            base_cg = _ship_cargo(lvls["cargo"])
                            dpg.add_text(f"Base:    {base_cg}")
                            dpg.add_text(f"Probe:   ×{probe[2]:.2f}")
                            dpg.add_text(f"Colony:  ×{colony[2]:.2f}")
                            dpg.add_text(f"Beacon:  ×{bc:.2f}")
                            if mc != 1.0: dpg.add_text(f"Manager: ×{mc:.2f}")
                            if _proj(self.state,"Advanced Cargo Handling"): dpg.add_text("Adv Cargo Handling: ×1.25")
                            if _proj(self.state,"Superior Cargo Handling"): dpg.add_text("Sup Cargo Handling: ×1.25")
                            manual_c = float(self.state.get("globals",{}).get("cargo",1))
                            if manual_c != 1.0: dpg.add_text(f"Manual:  ×{manual_c:.3f}")
                            msec_c = manager_secondary_bonus("cargo", self.state)
                            if msec_c != 1.0: dpg.add_text(f"Mgr Sec: ×{msec_c:.3f} (global)")
                # Probe bonuses (cols 11-13)
                for idx in range(3):
                    dpg.add_input_text(default_value=str(probe[idx]),width=52,
                                       on_enter=True,
                                       user_data=(pid,"probes",idx),
                                       callback=self._cb_planet_bonus_val)
                dpg.add_text()
                # Colony bonuses (cols 14-16)
                for idx in range(3):
                    dpg.add_input_text(default_value=str(colony[idx]),width=52,
                                       on_enter=True,
                                       user_data=(pid,"colony",idx),
                                       callback=self._cb_planet_bonus_val)
                dpg.add_text("")
                dpg.add_text(ores, color=col)
        
        # Restore scroll position
        dpg.set_y_scroll("planet_tbl", scroll_y)

    def _market_widget(self, img_tag: str, mkt: int, user_data: tuple):
        """Render  −  [chevron image]  +  for a market cell."""
        dpg.add_button(label="-", width=20,
                       user_data=(user_data, -1), callback=self._cb_market_adj)
        tex = self._chev_tex.get(mkt)
        cw, ch = self._chev_size
        if tex is not None:
            dpg.add_image(tex, tag=img_tag, width=cw, height=ch)
        else:
            dpg.add_text(str(mkt), tag=img_tag)
        dpg.add_button(label="+", width=20,
                       user_data=(user_data, +1), callback=self._cb_market_adj)

    def _star_widget(self, tag: str, stars: int, ud: tuple):
        """Draw star image (if available) + count text. Returns text item tag."""
        img_tag = f"{tag}_img"
        if stars > 0:
            dpg.add_image(self._star_tex,
                        width=self._star_size[0],
                        height=self._star_size[1],
                        tag=img_tag
                        )
            dpg.add_input_text(default_value=str(stars), 
                        width=30,
                        user_data=(ud,0),
                        callback=self._cb_stars,
                        on_enter=True,
                        tag=tag)
        else:
            dpg.add_image(self._no_star_tex,
                        width=self._star_size[0],
                        height=self._star_size[1],
                        tag=img_tag)
            dpg.add_input_text(default_value="",
                        width=30,
                        user_data=(ud,0),
                        callback=self._cb_stars,
                        on_enter=True,
                        tag=tag)
    # ── shared callbacks ───────────────────────────────────────────────────────
    def _cb_stars(self, s, v, ud):
        (cat, name, _), delta = ud
        if delta == 0:
            self.state[cat][name]["stars"] = int(v)
        else:
            self.state[cat][name]["stars"] = self.state[cat][name].get("stars",0) + delta
        if self.state[cat][name]["stars"] < 0:
            self.state[cat][name]["stars"] = 0
        save_state(self.state)
        if cat == 'ores':
            img_tag = f"ost_{name}_img"
        elif cat == 'alloys':
            img_tag = f"ast_{name}_img"
        else:
            img_tag = f"ist_{name}_img"
        
        new_tex = self._no_star_tex
        if self.state[cat][name]["stars"] > 0:
            new_tex = self._star_tex
        dpg.configure_item(img_tag, texture_tag=new_tex)
        self._update_price_label(cat, name)
        self._refresh_dashboard()

    def _cb_market(self, s, v, ud):
        cat, name, _ = ud
        self.state[cat][name]["market"] = int(v)
        save_state(self.state)
        self._update_price_label(cat, name)
        self._refresh_dashboard()

    def _cb_market_adj(self, s, v, ud):
        """Called by − / + buttons around the chevron image."""
        (cat, name, _), delta = ud
        cur = self.state[cat][name].get("market", 0)
        new_mkt = max(-2, min(4, cur + delta))
        self.state[cat][name]["market"] = new_mkt
        save_state(self.state)
        # Swap the chevron texture in-place
        img_tag = f"mkt_{cat[:2]}_{name}"
        new_tex = self._chev_tex.get(new_mkt)
        if new_tex is not None and dpg.does_item_exist(img_tag):
            dpg.configure_item(img_tag, texture_tag=new_tex)
        elif dpg.does_item_exist(img_tag):
            dpg.set_value(img_tag, str(new_mkt))
        self._update_price_label(cat, name)
        self._refresh_dashboard()

    def _cb_unlocked(self, s, v, ud):
        cat, name, _ = ud
        self.state[cat][name]["unlocked"] = v
        save_state(self.state)
        self._refresh_dashboard()

    def _update_price_label(self, cat, name):
        st    = self.state[cat][name]
        bp    = self.base[cat][name]["base_price"]
        stars = st.get("stars",0); mkt = st.get("market",0)
        rp    = bp * [0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars)
        prefix_map = {"ores":"or","alloys":"al","items":"it"}
        pre = prefix_map[cat]
        if dpg.does_item_exist(f"{pre}p_{name}"):
            dpg.set_value(f"{pre}p_{name}", fmt(rp))
        star_tag = {"ores":f"ost_{name}","alloys":f"ast_{name}","items":f"ist_{name}"}[cat]
        if dpg.does_item_exist(star_tag):
            dpg.set_value(star_tag, str(stars) if stars > 0 else "")
        if cat=="ores" and dpg.does_item_exist(f"ors_{name}"):
            ors = ore_mining_rate(name, self.base, self.state)
            dpg.set_value(f"ors_{name}", f"{ors:.4f}" if ors else "—")

    # ── top-level actions ──────────────────────────────────────────────────────
    def _cb_save(self):
        save_state(self.state); save_prefs(self.prefs)

    def _cb_reset(self):
        def _go(s, v, u):
            dpg.delete_item("reset_dlg")
            if not u: return
            self.state = default_state(self.base)
            save_state(self.state)
            self._refresh_all()
        with dpg.window(label="Reset?", modal=True, tag="reset_dlg",
                        width=340, height=110, pos=(540,360)):
            dpg.add_text("Reset ALL data to defaults? Cannot be undone.")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Yes – Reset", user_data=True,  callback=_go)
                dpg.add_button(label="Cancel",       user_data=False, callback=_go)

    def _cb_sell_galaxy(self):
        def _go(s, v, u):
            dpg.delete_item("sell_dlg")
            if not u: return
            new_state = default_state(self.base)
            
            # Copy stars over
            for cat in ("ores","alloys","items"):
                for n in self.state[cat]:
                    new_state[cat][n]["stars"] = self.state[cat][n]["stars"]
            
            # Copy over states that don't get reset
            for cat in ("globals", "beacons", "rooms"):
                new_state[cat] = self.state[cat].copy()
            
            self.state = copy.deepcopy(new_state)
            save_state(self.state)
            self._refresh_all()
        with dpg.window(label="Sell Galaxy?", modal=True, tag="sell_dlg",
                        width=360, height=130, pos=(540,360)):
            dpg.add_text("Start a new galaxy?")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Yes – Sell Galaxy", user_data=True,  callback=_go)
                dpg.add_button(label="Cancel",             user_data=False, callback=_go)


    # ── ROOMS ──────────────────────────────────────────────────────────────────

    def _tab_rooms(self):
        with dpg.table(
            tag="rooms_tbl", header_row=True, row_background=True,
            borders_innerH=True, borders_outerH=True,
            borders_innerV=True, borders_outerV=True,
            scrollY=True, resizable=True,
            policy=dpg.mvTable_SizingFixedFit, freeze_rows=1,
        ):
            for lbl, w in [
                ("Unlocked", 68), ("Name", 140), ("Boost", 220),
                ("Level", 100), ("Effect", 140),
            ]:
                dpg.add_table_column(label=lbl, width_fixed=True,
                                     init_width_or_weight=w)

    def _room_effect_str(self, room: dict, level: int) -> str:
        """Compute display string for a room's effect at a given level."""
        if level <= 0:
            return "—"
        base  = room["base_effect"]
        per   = room["per_level"]
        stat  = room.get("stat")
        effect = base + (level - 1) * per
        # Surge rooms (Probability Drive etc.) show tier
        if stat is None and per == 1 and base == 0:
            return f"T{level - 1}"
        # Idle time room: show hours
        if room["name"] == "Backup Generator":
            hrs = effect
            h = int(hrs); m = int((hrs - h) * 60)
            return f"+{h}h{m:02d}m idle"
        # Percentage rooms (base < 1, e.g. 0.90)
        if base < 1.0:
            return f"×{effect:.0%}"
        # Multiplier rooms
        return f"×{effect:.2f}"

    def _refresh_rooms(self):
        dpg.delete_item("rooms_tbl", children_only=True, slot=1)
        rooms_state = self.state.get("rooms", {})

        for room in self.base.get("rooms", []):
            name     = room["name"]
            level    = rooms_state.get(name, 0)
            unlocked = level > 0
            col      = C_TEXT if unlocked else (85, 85, 112, 255)
            effect   = self._room_effect_str(room, level)
            max_lv   = room["max_level"]

            with dpg.table_row(parent="rooms_tbl"):
                dpg.add_checkbox(
                    default_value=unlocked,
                    user_data=name,
                    callback=self._cb_room_unlock)

                dpg.add_text(name, color=col)
                dpg.add_text(room["boost"], color=C_MUTED)

                # Level widget: input_int + + button (like Stars)
                with dpg.group(horizontal=True):
                    dpg.add_spacer(width=-1)
                    dpg.add_input_int(
                        default_value=level,
                        width=42, step=0,
                        min_value=0, min_clamped=True,
                        max_value=max_lv, max_clamped=True,
                        enabled=unlocked,
                        tag=f"room_lv_{name}",
                        user_data=name,
                        callback=self._cb_room_level_edit)
                    dpg.add_button(
                        label="+", width=22,
                        enabled=unlocked,
                        user_data=(name, 1),
                        callback=self._cb_room_level_inc)

                dpg.add_text(effect, tag=f"room_ef_{name}",
                             color=C_TEAL if unlocked else C_MUTED)

    def _cb_room_unlock(self, s, v, ud):
        name = ud
        rooms_state = self.state.setdefault("rooms", {})
        if v:
            # Unlock at level 1 if not already levelled
            if rooms_state.get(name, 0) == 0:
                rooms_state[name] = 1
        else:
            rooms_state[name] = 0
        save_state(self.state)
        self._refresh_rooms()
        # Rooms affect global bonuses — refresh everything that uses them
        self._refresh_planets()
        self._refresh_alloys()
        self._refresh_items()
        self._refresh_dashboard()

    def _cb_room_level_inc(self, s, v, ud):
        name, delta = ud
        rooms_state = self.state.setdefault("rooms", {})
        room = next((r for r in self.base.get("rooms", []) if r["name"] == name), None)
        if room is None:
            return
        cur = rooms_state.get(name, 0)
        new_lv = max(0, min(room["max_level"], cur + delta))
        rooms_state[name] = new_lv
        if dpg.does_item_exist(f"room_lv_{name}"):
            dpg.set_value(f"room_lv_{name}", new_lv)
        if dpg.does_item_exist(f"room_ef_{name}"):
            dpg.set_value(f"room_ef_{name}", self._room_effect_str(room, new_lv))
        save_state(self.state)
        self._refresh_planets()
        self._refresh_alloys()
        self._refresh_items()
        self._refresh_dashboard()

    def _cb_room_level_edit(self, s, v, ud):
        name = ud
        rooms_state = self.state.setdefault("rooms", {})
        room = next((r for r in self.base.get("rooms", []) if r["name"] == name), None)
        if room is None:
            return
        new_lv = max(0, min(room["max_level"], int(v)))
        rooms_state[name] = new_lv
        if dpg.does_item_exist(f"room_ef_{name}"):
            dpg.set_value(f"room_ef_{name}", self._room_effect_str(room, new_lv))
        save_state(self.state)
        self._refresh_planets()
        self._refresh_alloys()
        self._refresh_items()
        self._refresh_dashboard()

    def _refresh_all(self):
        self._refresh_ores()
        self._refresh_alloys()
        self._refresh_items()
        self._refresh_projects()
        self._refresh_colonies()
        self._refresh_beacons()
        self._refresh_rooms()
        self._refresh_planets()
        self._refresh_managers()
        self._refresh_dashboard()
        dpg.set_value("lbl_smelters", str(self.state.get("smelters",1)))
        dpg.set_value("lbl_crafters", str(self.state.get("crafters",1)))
        dpg.set_value("dash_filter",  self.prefs.get("dashboard_filter","All"))
        dpg.set_value("dash_sort",    self.prefs.get("dashboard_sort","vps_profit_ore"))
        dpg.set_value("proj_sort",    self.prefs.get("projects_sort","time"))


if __name__ == "__main__":
    App()