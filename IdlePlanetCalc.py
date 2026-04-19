"""
Idle Planet Miner – Recipe Value Calculator  (Dear PyGui rewrite)

Files (all in same folder as this script):
  ipm_base.json   – static reference data: recipes, base prices, planet defs
                    Never written by the app.
  ipm_state.json  – mutable game state: unlocks, levels, market, stars, bonuses
  ipm_prefs.json  – UI preferences: sort choices
"""

import json, os, re, copy, math
import dearpygui.dearpygui as dpg
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
C_GOLD    = (196, 196, 0,   255)
C_WARN    = (255, 192, 64,  255)
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
    if n == 0: return "0"
    neg = n < 0; n = abs(n)
    for thr, sfx in _SFX:
        if n >= thr: return f"{'−' if neg else ''}{n/thr:.1f}{sfx}"
    if n < 100:
        return f"{'−' if neg else ''}{n:.2f}"
    return f"{'−' if neg else ''}{n:.1f}"

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

def fmt_exp(n: float, e: int, p=2) -> str:
    mantissa = n / (10 ** e)
    format_spec = f"{{:.{p}f}} E{{:+03d}}"
    return format_spec.format(mantissa,e)

def fmt_super(text: str) -> str:
    superscripts = {
            '0': '\u2070', '1': '\u00b9', '2': '\u00b2', '3': '\u00b3', '4': '\u2074',
            '5': '\u2075', '6': '\u2076', '7': '\u2077', '8': '\u2078', '9': '\u2079',
            '+': '\u207a', '-': '\u207b'
        }
    return "".join(superscripts.get(char, char) for char in str(text))
    
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
            "probe":  {"m":1, "s":1, "c":1},
            "colony": {"lvl":0, "m":1, "s":1, "c":1},
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
        "station":  {},
        "base_updates": [],
        "misc_bonuses": [],
    }

def _deep_merge(fresh: dict, saved: dict):
    for k, v in fresh.items():
        if k not in saved:
            saved[k] = copy.deepcopy(v)
        elif isinstance(v, dict) and isinstance(saved.get(k), dict):
            _deep_merge(v, saved[k])

def update_base(base: dict, path: list, op: str, value):
    if len(path) == 0:
        return
    # Walk to the parent of the target:
    node = base
    for key in path[:-1]:
        node = node[key]
        
    target_key = path[-1]
    
    if op == "replace":
        node[target_key] = value
    elif op == "update":
        node[target_key].update(value)
    elif op == "multiply":
        node[target_key] *= value
    

def load_state(base: dict) -> dict:
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                saved = json.load(f)
            _deep_merge(default_state(base), saved)
            for update in saved.get("base_updates",[]):
                update_base(base, update["path"], update["op"], update["value"])
            
            return saved
        except Exception:
            pass
    return default_state(base)

def save_state(state: dict):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f, indent=2)

# ── prefs ──────────────────────────────────────────────────────────────────────
_DEF_PREFS = {"dashboard_filter":"All",
              "dashboard_sort":"vps_profit_ore",
              "projects_sort":"time",
              "projects_show_r":True,
              "projects_show_locked":True,
              "colonies_sort":"planet",
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
    stat_lookup = {
        "ores": "ore_val",
        "alloys": "alloy_val",
        "items": "item_val"
    }
    for cat in ("ores","alloys","items"):
        if name in base[cat]:
            bp  = base[cat][name]["base_price"]
            st  = state[cat][name]
            mv  = [0.33,0.5,1,2,3,4,5][st.get("market",0)+2]
            sv  = 1.0 + 0.2 * st.get("stars",0)
            misc = _get_misc_bonus(cat, name, stat_lookup[cat], state)
            if cat in ("alloys", "items"):
                misc *= _get_misc_bonus(cat, name, "alloy_and_item_val", state)
            return bp * mv * sv * misc
    return 0.0
    
def ore_unlocked(ore: str, base: dict, state: dict) -> bool:
    return any(ps["owned"] and ore in base["planets"][pid]["resources"]
               for pid, ps in state["planets"].items())

def ore_mining_rate(ore: str, base: dict, state: dict) -> float:
    total = 0.0
    gm    = global_bonuses["mining"]
    for pid, ps in state["planets"].items():
        if not ps["owned"]: continue
        pct = base["planets"][pid]["resources"].get(ore, 0)
        if pct == 0: continue
        lvl   = ps["levels"]["mining"]
        bonus = ps["probe"]["m"] * ps["colony"]["m"] * gm
        total += _mining_rate(lvl, bonus) * (pct / 100.0)
    return total
    
def _planet_mining_rate(pid: str, base: dict, state: dict) -> float:
    total = 0.0
    gm = global_bonuses["mining"]
    ps = state["planets"][pid]
    if not ps["owned"]: return 0

    lvls = ps["levels"]
    probe = ps.get("probe",{"m":1})
    colony = ps.get("colony",{"m":1})
    bm = beacon_bonus(pid,"mining",base,state)
    mm = manager_primary_bonus(pid,"mining",state)
    mb = probe["m"]*colony["m"]*bm*mm*gm
    ore_p = _planet_ore_pri(pid, state, base)
    mr = _mining_rate(lvls["mining"],mb)
    for i,(ore,pct) in enumerate(base["planets"][pid]["resources"].items()):
        if (_proj(state, "Ore Targeting")) and (i == ore_p):
            pct += 15
        total += mr * pct / 100
    return total
    
def _ore_sell_rate(ore: str, base: dict, state: dict) -> float:
    # Returns the ore_mining_rate minus the amount used on the primary alloy in one smelter
    # Includes a 10% buffer
    # returns as a percentage
    mr = ore_mining_rate(ore, base, state)
    if mr == 0:
        return 0
    alloy = base["ores"].get(ore,{}).get("alloy","")
    ba = base["alloys"].get(alloy,{})
    smelt_time = ba.get("smelt_time", 60)
    smelt_time = smelt_time / global_bonuses.get("smelt_speed", 1)
    smelt_amt = ba.get("recipe",{}).get(ore,0)
    smelt_amt *= global_bonuses.get("smelt_ing", 1)
    smelt_rate = smelt_amt / smelt_time
    return 90 * (mr - smelt_rate) / mr
    

def _mining_rate(lv: int, bonus: float=1.0) -> float:
    # bonus input: excludes global bonuses
    if lv == 0: return 0.0
    l = lv - 1
    debug_str = f"    b: {bonus}   lv: {lv}"
    #print(debug_str)
    return bonus * (0.25 + 0.1*l + 0.017*l*l)

def _ship_speed(lv: int, bonus: float=1.0) -> float:
    if lv == 0: return 0.0
    l = lv - 1
    return bonus * (1.0 + 0.2*l + l*l/75.0)

def _ship_cargo(lv: int, bonus: float=1.0) -> int:
    if lv == 0: return 0
    l = lv - 1
    return round(bonus * (5.0 + 2.0*l + (0.1*(l**2))))


def _planet_transport(dist: int, speed: float, cargo: int) -> float:
    # dist is in Mkm
    # speed is in Mkm/h
    # cargo is in ore
    # transport is in ore/s
    if speed == 0:
        return 0
    dist = dist * 2 # account for return trip
    Mkps = 1000 * speed / 3.6
    
    # return cargo per second
    transport = cargo * (Mkps / dist)
    return transport
    
def _get_valuable_ore(ores: list, base) -> int:
    # input: list of ore names
    # output: index of most valuable ore, based on ipm_base
    max_i = 0
    max_v = 0
    for i, ore in enumerate(ores):
        v = base["ores"].get(ore,{}).get("base_price",0)
        if v > max_v:
            max_v = v
            max_i = i
    return max_i
    
def _planet_ore_pri(pid: str, state: dict, base: dict) -> int:
    # returns the prioritized ore.  If unset, defaults to most valuable ore
    # In the game, this *may* take into account market.  Need to check
    pla = state["planets"].get(pid,{})
    p = pla.get("ore_pri",-1)
    orelist = list(base["planets"].get(pid,{}).get("resources", {}).keys())
    if p < 0 or p >= len(orelist):
        p = _get_valuable_ore(orelist, base)
    return p

def _proj(state, name): return state["projects"].get(name,{}).get("researched",False)

def _get_probe_string(probe: dict):
    pStr = ''
    m = probe.get('m',1)
    s = probe.get('s',1)
    c = probe.get('c',1)
    if m + s + c == 3:
        return "—"
    smb = probe.get("smb", 1) # Secondary manager bonus
    pStr += "1/" if m == 1 else f"{m:.2f}/"
    pStr += "1/" if s == 1 else f"{s:.2f}/"
    pStr += "1" if c == 1 else f"{c:.2f} "
    if smb != 1:
        pStr += f"smb:{smb:.2f};"
    return pStr
     
def _get_col_string(col: dict):
    lvl = col.get('lvl',0)
    if lvl == 0:
        return "—"
    m = col.get('m',1)
    s = col.get('s',1)
    c = col.get('c',1)
    cStr = f"L{lvl}:"
    cStr += "1/" if m == 1 else f"{m:.2f}/"
    cStr += "1/" if s == 1 else f"{s:.2f}/"
    cStr += "1" if c == 1 else f"{c:.2f}"
    return cStr
        
    

# ── global bonuses ─────────────────────────────────────────────────────────────

# Module-level base reference set by App.__init__ so room_bonus can use it
_g_base = {}
global_bonuses = {
    "alloy_val": 1,
    "item_val": 1,
    "alloy_and_item_val": 1,
    "ast_val": 1,
    "deb_val": 1,
    "ast_and_deb_val": 1,
    "cargo": 1,       
    "cash_windfall": 1,
    "col_cost": 1,
    "colonizing_bonus": 1,
    "craft_speed": 1,
    "craft_cost": 1,
    "credits": 1,         
    "item_val": 1,         
    "manager_bonus": 1,  
    "manager_sec_bonus": 1,  
    "market_bonus": 1, 
    "mining": 1,  
    "ore_val": 1,    
    "pla_upg_price": 1,
    "prod_boost_speed": 1,
    "prod_boost_dur": 1,
    "rov_scan_time": 1, 
    "speed": 1,          
    "smelt_speed": 1,
    "proj_cost": 1    
}
gb_descriptions = {
    "alloy_val": "Alloy Value",
    "item_val": "Item Value",
    "alloy_and_item_val": "Alloy and Item Value",
    "ast_val": "Asteroid Value",
    "ast_time": "Time between asteroids",
    "deb_val": "Debris Value",
    "ast_and_deb_val": "Asteroid and Debris Value",
    "cargo": "Cargo",       
    "cash_windfall": "Cash Windfall",
    "col_cost": "Colonization Cost",
    "colonizing_bonus": "Colonizing Bonuses",
    "craft_speed": "Craft Speed",
    "craft_cost": "Craft Cost",
    "credits": "Credits",         
    "item_val": "Item Value",         
    "manager_bonus": "Manager Bonuses",  
    "manager_sec_bonus": "Manager Secondary Bonuses",  
    "market_bonus": "Market Bonus", 
    "mining": "Mining Rate",    
    "ore_val": "Ore Value",
    "pla_upg_price": "Planet Upgrade Price",
    "pla_unl_price": "Planet Unlock Price",
    "prod_boost_speed": "Production Boost Speed",
    "prod_boost_dur": "Production Boost Duration",
    "proj_cost": "Decrease Project Cost",
    "rov_scan_time": "Rover Scan Time", 
    "speed": "Ship Speed",          
    "smelt_speed": "Smelt Speed",
    "smelt_ing": "Decrease Smelter Ingredients"  ,
    "__": "__"    
}

def calculate_global_bonuses(base, state):
    global global_bonuses
    #print("Calculating Global Bonuses")
    # reset bonuses to 1
    for bonus in global_bonuses:
        global_bonuses[bonus] = 1
        
    for proj_name in state["projects"]:
        if _proj(state,proj_name):
            if "boost" in base["projects"][proj_name]:
                debug_str = f"  Project {proj_name}"
                bn = base["projects"][proj_name]["boost"]
                v = base["projects"][proj_name]["boost_val"]
                global_bonuses[bn] *= v
                debug_str += f": Multiplying bonus '{bn}' by {v}"
                #print(debug_str)
                
    for room in base.get("rooms",[]):
        n = room["name"]
        level = state.get("rooms",{}).get(n,0)
        if level == 0:
            continue
        stat = room["stat"]
        be = room["base_effect"]
        pl = room["per_level"]
        if stat:
            v = be + (pl * (level - 1))
            global_bonuses[stat] = global_bonuses.get(stat,1) * v
            debug_str = f"  Room '{room['name']}': Multiplying bonus '{stat}' by {v}"
            #print(debug_str)
    # include manual adjustments
    for stat, m in state.get("globals",{}).items():
        global_bonuses[stat] *= m
        debug_str = f"  Manual Adjustment: Multiplying bonus '{stat}' by {m}"
        #print(debug_str)
    
    # Manager bonus
    for stat in ("mining", "speed", "cargo", "craft_speed","smelt_speed"):
        m = manager_secondary_bonus(stat, state)
        global_bonuses[stat] *= m
        debug_str = f"  Active Managers: Multiplying bonus '{stat}' by {m}"
        #print(debug_str)
    
    # Station bonus
    station_bonuses = {}
    for station, l in state.get("station",{}).items():
        if l == 0:
            continue
        sb = base["station"].get(station,{})
        stat = sb.get("boost",'')
        if not stat: continue
        if "ore_star" in stat: continue
        bonus = l * sb.get("per_level",0)
        if bonus < 0:
            bonus = (bonus/100)
        station_bonuses[stat] = station_bonuses.get(stat,1) + bonus
        debug_str = f"  Station {station}: modifying '{stat}' by {bonus}: {station_bonuses[stat]}"
        #print(debug_str)
    for stat, bonus in station_bonuses.items():
        global_bonuses[stat] *= bonus
        debug_str = f"  Station : Multiplying bonus '{stat}' by {bonus}"
        #print(debug_str)

    # Misc bonus
    for m_item in state.get("misc_bonuses", []):
        if m_item["target_type"] != "global": continue
        stat = m_item["stat"]
        if stat == '__': continue
        bonus = m_item["bonus"]
        global_bonuses[stat] *= bonus
    
        
def _get_misc_bonus(target_type: str, target: str, stat: str, state:dict):
    total = 1
    debug_str = f"{target_type}; {target}; {stat}"
    m_bonuses = state.get("misc_bonuses", [])
    for m_item in m_bonuses:
        if m_item["target_type"] != target_type: continue
        if m_item["target"] != target: continue
        if m_item["stat"] != stat: continue
        total *= m_item["bonus"]
    debug_str += f"; {total:.2f}"
    #print(debug_str)
    return total

                
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
            gm = global_bonuses.get("manager_bonus", 1)
            mgr_bonus = (_MGR_PRIMARY[stat][stars - 1]) - 1
            return 1 + (gm * mgr_bonus)
    return 1.0

def manager_secondary_bonus(stat: str, state: dict) -> float:
    """Combined cumulative secondary bonus across all ASSIGNED managers for stat.
    Only managers with a planet assigned contribute.
    Returns a multiplier: sum of individual bonuses.
    """
    total = 1
    for mgr in state.get("managers", []):
        if not mgr.get("planet"):
            continue
        if mgr.get("secondary") == stat:
            probe_smb = state["planets"][mgr["planet"]]["probe"].get("smb",1)
            stars = max(1, min(7, mgr.get("stars", 1)))
            total = total + (_MGR_SECONDARY.get(stat, [0.0]*7)[stars - 1]) - 1
            total = ((total - 1) * probe_smb) +1
    gm = global_bonuses.get("manager_bonus", 1)        
    total = 1 + (gm * (total - 1))
    return total

# ── time helpers ───────────────────────────────────────────────────────────────
def total_smelt_time(name, cat, base, state):
    e   = base[cat][name]
    own = e["smelt_time"] if cat=="alloys" else 0.0
    t   = own / max(0.001, global_bonuses['smelt_speed'])
    for ing, qty in e.get("recipe",{}).items():
        c2 = "alloys" if ing in base["alloys"] else ("items" if ing in base["items"] else None)
        if c2: t += total_smelt_time(ing, c2, base, state) * qty
    return t

def total_craft_time(name, cat, base, state):
    e   = base[cat][name]
    own = e["craft_time"] if cat=="items" else 0.0
    t   = own / max(0.001, global_bonuses['craft_speed'])
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
    # check if prereqs for a project are met
    if not prereq: return True
    pr = state["projects"]
    if isinstance(prereq, list): return any(pr.get(p,{}).get("researched") for p in prereq)
    return pr.get(prereq,{}).get("researched",False)

def station_prereq_met(name: str, state, base):
    prereq = base["station"][name].get("prereq", "")
    if not prereq: return True
    sta = state.get("station",{})
    if isinstance(prereq, list):
        return any(sta.get(p,0) > 0 for p in prereq)
    return sta.get(prereq,0) > 0
        

def analyze(name, cat, base, state):
    e  = base[cat][name]
    ov = effective_price(name, base, state)
    tk = "smelt_time" if cat=="alloys" else "craft_time"
    t  = e.get(tk,1)
    adj_t = t / max(0.001, global_bonuses['smelt_speed'] if cat=="alloys" else global_bonuses['craft_speed'])
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
    
def get_vps(pid: str, state, base, level=-1) -> float:
    bd = base["planets"][pid]
    ps = state["planets"][pid]
    lvl = ps["levels"]["mining"] if level < 0 else level
    probe = ps["probe"]
    colony = ps["colony"]
    bm = beacon_bonus(pid,"mining",base,state)
    mm = manager_primary_bonus(pid,"mining",state)
    gm=global_bonuses["mining"]
    mb = probe["m"]*colony["m"]*bm*mm*gm
    mr = _mining_rate(lvl,mb)
    vps = 0
    ore_p = _planet_ore_pri(pid, state, base)
    for i, (o,p) in enumerate(bd["resources"].items()):
        ore_state = state["ores"][o]
        mkt = ore_state.get("market",0)
        stars = ore_state.get("stars",0)
        bp = base["ores"][o]["base_price"]
        #rp = bp * [0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars)
        rp = effective_price(o, base, state)
        if (_proj(state, "Ore Targeting")) and (i == ore_p):
            p += 15
        vps += rp * mr * p / 100
    return vps

def _get_ast_vps(base: dict, state: dict):
    a_time = 3600 #default time between asteroid is 10 minutes
    a_time *= global_bonuses.get("ast_time",1)
    # from the wiki:
    # * No ore backlog
    # * Only the base value of the ores from that planet are considered (no stars, no market, no ships, etc).
    base_tvps = 0
    for pid, pb in base["planets"].items():
        ps = state["planets"].get(pid,{})
        if not ps["owned"]: continue
        lvl = ps["levels"]["mining"]
        probe = ps["probe"]
        colony = ps["colony"]
        bm = beacon_bonus(pid,"mining",base,state)
        mm = manager_primary_bonus(pid,"mining",state)
        gm=global_bonuses["mining"]
        mb = probe["m"]*colony["m"]*bm*mm*gm
        mr = _mining_rate(lvl,mb)
        vps = 0
        ore_p = _planet_ore_pri(pid, state, base)
        for i, (o,p) in enumerate(pb["resources"].items()):
            ore_state = state["ores"][o]
            bp = base["ores"][o]["base_price"]
            if (_proj(state, "Ore Targeting")) and (i == ore_p):
                p += 15
            vps += bp * mr * p / 100
        base_tvps += vps
    # "The nominal size for an asteroid is roughly around 130x of your VPS"
    ast_base = base_tvps * 130
    ast_base *= global_bonuses["ast_val"] * global_bonuses["ast_and_deb_val"]
    debug_str = f"Base asteroid value: $ {fmt(ast_base)}"
    #print(debug_str)
    r_ast_base = 0
    if _proj(state, "Asteroid Refined Drilling"):
        # "10% chance of an asteroid containing 20x normal value worth of alloy"
        r_ast_base = ast_base * 20
    
    # Now that we have the *base* value, we need to adjust for the *actual* value (with stars, market, etc...)
    ore_price_ratios = []
    for ore, bd in base["ores"].items():
        if not ore_unlocked(ore, base, state):
            continue
        st = state["ores"][ore]
        stars = st.get("stars",0)
        mkt = st.get("market",0)
        ore_price_ratios.append([0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars))
    opr = 0
    for r in ore_price_ratios:
        opr += r / len(ore_price_ratios)
    ast_val = ast_base * opr
    debug_str = f"Actual avg asteroid value: $ {fmt(ast_val)}"
    #print(debug_str)
    
    return 2.9 * ast_val / a_time
    

def get_next_vps_per(pid: str, level: int, vps: float, base: dict, state: dict) -> float:
    bp = base["planets"][pid]["base_price"]
    l1 = level - 1
    l2 = level - 2
    next_vps = 0
    if level == 0:
        # Non-owned: amortized VPS/$ if bought and upgraded to level 9.
        # Peak level is always 9 regardless of ore prices (cost/rate curve property).
        # Total cost = bp + sum of upgrade costs for levels 1..8
        total_cost = bp + sum((bp/20) * (1.3**l) for l in range(8))
        return get_vps(pid, state, base, 9) / total_cost
    else:
        # Owned: marginal VPS/$ of the next mining level upgrade.
        next_cost = (bp/20) * (1.3**(level - 1))
        next_vps  = get_vps(pid, state, base, level + 1) - get_vps(pid, state, base, level)
        return next_vps / next_cost

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
                with dpg.tab(label="  Station    "): self._tab_station()
                with dpg.tab(label="  Misc       "): self._tab_misc()

        dpg.set_viewport_resize_callback(self._resize)
        dpg.create_viewport(title="Idle Planet Miner - Calculator",
                            width=1500, height=860, min_width=900, min_height=600)
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
                dpg.add_font_range(0x2000, 0x207F)
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
        
        for img_name in ["star_white", "star_black", "Arrow_up", "Arrow_down", "Edit"]:
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
                        
        for pid,pb in self.base["planets"].items():
            pname = pb["name"]
            img_path = f"{SCRIPT_DIR}/Images/Planet_{pname}.png"
            if not os.path.exists(img_path):
                img_path = f"{SCRIPT_DIR}/Images/Planet_Unknown.png"
            img = Image.open(img_path).convert("RGBA")
            w,h = img.size
            flat = [c / 255.0 for px in img.getdata() for c in px]
            with dpg.texture_registry():
                dpg.add_static_texture(
                        width=w, height=h, default_value=flat, tag=f"Planet_{pname}")


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
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding,     3, 3)
            with dpg.theme_component(dpg.mvImageButton, enabled_state=False):
                dpg.add_theme_color(dpg.mvThemeCol_Button,C_BTN_DIS)
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
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0,0,0,0))
                dpg.add_theme_style(dpg.mvStyleVar_FrameRounding,  0)
                dpg.add_theme_style(dpg.mvStyleVar_FramePadding,  0, 5)
                dpg.add_theme_style(dpg.mvStyleVar_WindowRounding,  0)
                dpg.add_theme_style(dpg.mvStyleVar_TabRounding,     0)
                dpg.add_theme_style(dpg.mvStyleVar_ItemSpacing,     0, 0)
                dpg.add_theme_style(dpg.mvStyleVar_CellPadding,     0, 0)
                
        with dpg.theme(tag="muted_input_text"):
            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_color(dpg.mvThemeCol_Text, C_MUTED)
                
        with dpg.theme(tag="muted_clear_input_text"):
            with dpg.theme_component(dpg.mvInputText):
                dpg.add_theme_color(dpg.mvThemeCol_Text, C_MUTED)
                dpg.add_theme_color(dpg.mvThemeCol_FrameBg, (0,0,0,0))
        
        with dpg.theme(tag="ore_priority"):
            with dpg.theme_component(dpg.mvImageButton):
                dpg.add_theme_style(dpg.mvStyleVar_FrameBorderSize, 2)
                dpg.add_theme_color(dpg.mvThemeCol_Border, C_GOLD)
                                
            

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
    def _bonus_strip(self, key, label, tag_comp, tag_manual, cb):
        dpg.add_text(f"{label}:", color=C_MUTED)
        dpg.add_text(f"×{global_bonuses[key]:.3f}", color=C_TEAL, tag=tag_comp)
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

        with dpg.group(horizontal=True):
            tvps = 0
            dpg.add_text("Total Ore VPS: ", color=C_TEXT)
            dpg.add_text(f"$ {fmt(tvps)}", color=C_TEAL, tag="dash_tvps")
            dpg.add_text("   Est. Asteroid VPS: ", color=C_TEXT)
            dpg.add_text(f"$ {0}", color=C_TEAL, tag="dash_ast_vps")

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
        tvps = 0
        for pid, ps in self.state["planets"].items():
            if ps["owned"]:
                vps = get_vps(pid, self.state, self.base)
                tvps += vps
        dpg.set_value("dash_tvps", f"$ {fmt(tvps)}")
        dpg.set_value("dash_ast_vps", f"$ {fmt(_get_ast_vps(self.base, self.state))}")
    
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
                        txt = f"$ {fmt(v)}"
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
                            ("Stars",80),("Market",90),("Real $",105),
                            ("Ore/s",82),("Safe sell rate", 60)]:
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)

    def _refresh_ores(self):
        dpg.delete_item("ores_tbl", children_only=True, slot=1)
        for ore, bd in self.base["ores"].items():
            st = self.state["ores"][ore]
            bp = bd["base_price"]
            stars = st.get("stars",0)
            mkt = st.get("market",0)
            rp = bp * [0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars)
            unl = ore_unlocked(ore, self.base, self.state)
            ors = ore_mining_rate(ore, self.base, self.state)
            ore_img = f"Ore_{ore}"
            ore_sell_rate = _ore_sell_rate(ore, self.base, self.state)
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
                dpg.add_text(f"{ors:.2f}" if ors else "—",
                             tag=f"ors_{ore}", color=C_MUTED)
                dpg.add_text(f"{ore_sell_rate:.0f} %" if ors else "—",
                             tag=f"ore_{ore}_sell", color=C_MUTED)

    # ── ALLOYS ─────────────────────────────────────────────────────────────────
    def _tab_alloys(self):
        with dpg.group(horizontal=True):
            self._bonus_strip("smelt_speed","Smelt Speed",
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
        self._refresh_all()

    def _refresh_alloys(self):
        dpg.delete_item("alloys_tbl", children_only=True, slot=1)
        ss = max(0.001, global_bonuses['smelt_speed'])
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
                
                # "Recipe"
                with dpg.group(horizontal=True):
                    for i,q in bd["recipe"].items():
                        if i in self.base["ores"]:
                            img_name = f"Ore_{i}"
                        elif i in self.base["alloys"]:
                            img_name = f"Alloy_{i}"
                        else:
                            img_name = f"Item_{i}"
                        debug_str = f"{i}: '{img_name}'"
                        #print(debug_str)
                        dpg.add_image(img_name)
                        txt = dpg.add_input_text(default_value=f"x{q}",
                                           readonly=True,
                                           width=60)
                        dpg.bind_item_theme(txt, "clear_button")
                

    # ── ITEMS ──────────────────────────────────────────────────────────────────
    def _tab_items(self):
        with dpg.group(horizontal=True):
            self._bonus_strip("craft_speed","Craft Speed",
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
        self._refresh_all()

    def _refresh_items(self):
        dpg.delete_item("items_tbl", children_only=True, slot=1)
        cs = max(0.001, global_bonuses['craft_speed'])
        dpg.set_value("itc_comp", f"×{cs:.3f}")
        for name, bd in self.base["items"].items():
            st = self.state["items"][name]
            bp = bd["base_price"]; stars = st.get("stars",0); mkt = st.get("market",0)
            rp = bp * [0.33,0.5,1,2,3,4,5][mkt+2] * (1+0.2*stars)
            unl = st.get("unlocked",False)
            at  = bd["craft_time"] / cs
            rec = ", ".join(f"{q:g}×{i}" for i,q in bd["recipe"].items())
            with dpg.table_row(parent="items_tbl"):
                # "Unlocked"
                dpg.add_checkbox(default_value=unl,
                                 user_data=("items",name,"unlocked"),
                                 callback=self._cb_unlocked)
                                 
                # "Item"
                with dpg.group(horizontal=True):
                    dpg.add_image(f"Item_{name}")
                    dpg.add_text(name)
                    
                # "Base $"
                dpg.add_text(fmt(bp), color=C_MUTED)
                
                # "Time"
                dpg.add_text(fmt_time(at), color=C_MUTED)
                
                # "Stars"
                with dpg.group(horizontal=True):
                    self._star_widget(f"ist_{name}", 
                                ud=("items",name,"stars"),
                                stars=stars)
                    dpg.add_button(label="+", width=22,
                                user_data=(("items",name,"stars"),1),
                                callback=self._cb_stars)
                
                # "Market"
                with dpg.group(horizontal=True):
                    self._market_widget(f"mkt_it_{name}", mkt, ("items",name,"market"))
                
                # "Real $"
                dpg.add_text(fmt(rp), tag=f"itp_{name}", color=C_TEAL)
                
                # "Recipe"
                with dpg.group(horizontal=True):
                    for i,q in bd["recipe"].items():
                        if i in self.base["ores"]:
                            img_name = f"Ore_{i}"
                        elif i in self.base["alloys"]:
                            img_name = f"Alloy_{i}"
                        else:
                            img_name = f"Item_{i}"
                        dpg.add_image(img_name)
                        txt = dpg.add_input_text(default_value=f"x{q}",
                                           readonly=True,
                                           width=60)
                        dpg.bind_item_theme(txt, "clear_button")

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
            dpg.add_spacer(width=30)
            dpg.add_checkbox(label="Show Researched",
                             default_value=self.prefs["projects_show_r"],
                             callback=self._show_proj_researched)
            dpg.add_checkbox(label="Show Locked",
                             default_value=self.prefs["projects_show_locked"],
                             callback=self._show_proj_locked)
        with dpg.table(tag="proj_tbl", header_row=True, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, scrollX=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=1):
            for lbl, w in [("",28),("Project",200),("Cost",110),("Time",82),
                            ("Ingredients",320),("Prereq",270)]:
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
            if not met and not self.prefs["projects_show_locked"]:
                continue
            done = self.state["projects"].get(name,{}).get("researched",False)
            if done and not self.prefs["projects_show_r"]:
                continue
            cost = sum(effective_price(i,self.base,self.state)*q for i,q in rec.items())
            st2=0; ct2=0
            for i,q in rec.items():
                c2 = "alloys" if i in self.base["alloys"] else ("items" if i in self.base["items"] else None)
                if c2:
                    st2 += total_smelt_time(i,c2,self.base,self.state)*q
                    ct2 += total_craft_time(i,c2,self.base,self.state)*q
            wt  = wall_time(st2,ct2,sm,cr)
            if wt == 1:
                # No smelting - ore-only recipe
                wt = 0
                for i,q in rec.items():
                    ors = ore_mining_rate(i, self.base, self.state)
                    if ors > 0:
                        wt += q/ors
            pre_str = (" OR ".join(pre) if isinstance(pre,list) else pre) or "—"
            rec_str = ", ".join(f"{q:g}×{i}" for i,q in rec.items())
            col = C_TEAL if done else ((85,85,112,255) if not met else C_TEXT)
            with dpg.table_row(parent="proj_tbl"):
                # col: Researched
                dpg.add_checkbox(default_value=done, user_data=name,
                                 callback=self._cb_proj_check)
                # col: Project
                dpg.add_text(name,    color=col)
                # col: Cost
                dpg.add_text(f"$ {fmt(cost)}",color=col)
                # col: Time
                dpg.add_text(fmt_time(wt) if wt > 0 else "—", color=col)
                
                # col: Ingredients
                #dpg.add_text(rec_str, color=col)
                with dpg.group(horizontal=True):
                    for i,q in bd["recipe"].items():
                        if i in self.base["ores"]:
                            img_name = f"Ore_{i}"
                        elif i in self.base["alloys"]:
                            img_name = f"Alloy_{i}"
                        else:
                            img_name = f"Item_{i}"
                        dpg.add_image(img_name,
                                      tint_color=(255,255,255,255) if met else (150,150,150,200))
                        # apply global bonus: proj_cost   
                        # this is standard rounding, not floor                        
                        q = max(1,round(q * global_bonuses["proj_cost"]))
                                      
                        txt = dpg.add_input_text(default_value=f"x{q}",
                                           readonly=True,
                                           width=60)
                        dpg.bind_item_theme(txt, "clear_button")
                        if not met:
                            dpg.bind_item_theme(txt, "muted_clear_input_text")
                # col: Prereq
                dpg.add_text(pre_str, color=col)
                

    def _cb_proj_check(self, s, v, ud):
        self.state["projects"][ud]["researched"] = v
        save_state(self.state)
        if v and ("Alchemy" in ud):
            self._proj_alchemy(ud)
         
        self._refresh_all()
    
    def _proj_alchemy(self, proj: str):
        vp_w = dpg.get_viewport_client_width()
        vp_h = dpg.get_viewport_client_height()
        dlg_w, dlg_h = 320, 340
        px = (vp_w - dlg_w) // 2
        py = (vp_h - dlg_h) // 2
        planet_items = self._col_owned_planet_items()

        # Determine upgrade step from project name
        if "Superior" in proj:
            step = 3
        elif "Advanced" in proj:
            step = 2
        else:
            step = 1

        with dpg.window(label=f"{proj}",
                        modal=True,
                        tag="proj_alchemy_dlg",
                        width=dlg_w, height=dlg_h, pos=(px, py)):
            dpg.add_text("Select planet:")
            dpg.add_combo(
                items=planet_items,
                default_value="",
                width=200,
                user_data=step,
                callback=self._cb_proj_alc_planet)
            # Placeholder child window — filled when planet is chosen
            with dpg.child_window(tag="proj_alchemy_options",
                                  height=-1, border=False):
                pass
    
    def _cb_proj_alc_planet(self, sender, value, user_data):
        """Called when the user picks a planet in the alchemy dialog."""
        step = user_data  # 1 / 2 / 3 depending on Alchemy tier

        # Clear and rebuild the options child window
        dpg.delete_item("proj_alchemy_options", children_only=True)

        if not value:
            return

        # Parse pid from "pid: Name"
        pid = value.split(":")[0].strip()
        planet_resources = list(self.base["planets"][pid]["resources"].keys())
        ore_list = list(self.base["ores"].keys())
        icon_sz = 32

        # Build valid (ore -> next_ore) pairs
        valid_options = []
        for ore in planet_resources:
            if ore not in ore_list:
                continue
            idx = ore_list.index(ore)
            next_idx = idx + step
            if next_idx < len(ore_list):
                valid_options.append((ore, ore_list[next_idx]))

        if not valid_options:
            dpg.add_text("No upgradeable resources on this planet.",
                         parent="proj_alchemy_options",
                         color=(200, 100, 100, 255))
            return

        # Track selection
        selected = [valid_options[0][0]]

        # Tags for image buttons
        ore_btn_tags  = {}   # ore -> tag of the ore image button (clickable)
        next_btn_tags = {}   # ore -> tag of the next_ore image button (decorative)

        def _apply_selection_visuals():
            for ore, _ in valid_options:
                is_sel = (ore == selected[0])
                tint = (255, 255, 255, 255) if is_sel else (150, 150, 150, 160)
                dpg.configure_item(ore_btn_tags[ore],  tint_color=tint)
                dpg.configure_item(next_btn_tags[ore], tint_color=tint)
                if is_sel:
                    dpg.bind_item_theme(ore_btn_tags[ore], "ore_priority")
                else:
                    dpg.bind_item_theme(ore_btn_tags[ore], 0)

        def _select(s, v, ud):
            selected[0] = ud
            _apply_selection_visuals()

        dpg.add_text("Select resource to transmute:",
                     parent="proj_alchemy_options")
        dpg.add_spacer(height=4, parent="proj_alchemy_options")

        for i, (ore, next_ore) in enumerate(valid_options):
            is_first = (i == 0)
            ore_tag  = f"proj_alc_ore_btn_{i}"
            next_tag = f"proj_alc_next_btn_{i}"
            ore_btn_tags[ore]  = ore_tag
            next_btn_tags[ore] = next_tag

            with dpg.group(horizontal=True, parent="proj_alchemy_options"):
                # Ore image button -- clicking this selects the row
                dpg.add_image_button(
                    texture_tag=f"Ore_{ore}",
                    tag=ore_tag,
                    width=icon_sz, height=icon_sz,
                    tint_color=(255, 255, 255, 255) if is_first else (150, 150, 150, 160),
                    user_data=ore,
                    callback=_select)
                if is_first:
                    dpg.bind_item_theme(ore_tag, "ore_priority")

                # Arrow
                if self._arrow_right is not None:
                    dpg.add_image(self._arrow_right,
                                  width=self._arrow_right_size[0],
                                  height=self._arrow_right_size[1])
                else:
                    dpg.add_text("->")

                # Next ore -- non-interactive, dims/brightens with selection
                dpg.add_image_button(
                    texture_tag=f"Ore_{next_ore}",
                    tag=next_tag,
                    width=icon_sz, height=icon_sz,
                    enabled=False,
                    tint_color=(255, 255, 255, 255) if is_first else (150, 150, 150, 160))

                dpg.add_text(f"  {ore} -> {next_ore}")

        dpg.add_spacer(height=6, parent="proj_alchemy_options")

        def _confirm(s, v, ud):
            chosen = selected[0]
            planet_name = self.base["planets"][pid]["name"]
            for ore, next_ore in valid_options:
                if ore == chosen:
                    print(f"changing {planet_name} resource '{ore}' to '{next_ore}'")
                    old_resources = self.base["planets"][pid]["resources"]
                    new_resources = {}
                    for k, v in old_resources.items():
                        if k == ore:
                            k = next_ore
                        if k in new_resources:
                            new_resources[k] += v
                        else:
                            new_resources[k] = v
                    print(old_resources)
                    print(new_resources)
                    path = ["planets", pid, "resources"]
                    update_base(self.base, path, "replace", new_resources)
                    self.state["base_updates"].append({
                            "path": path,
                            "op": "replace",
                            "value": new_resources,
                            "note": f"Project: Alchemy {step}"
                        })
                    save_state(self.state)
                    
                    # rebuild the relevant resource display on the Planets tab
                    dpg.delete_item(f"pla_{pid}_ores_group", children_only=True)
                    ore_p = _planet_ore_pri(pid, self.state, self.base)
                    with dpg.group(horizontal=True, parent=f"pla_{pid}_ores_group"):
                        enable_logistics = _proj(self.state, "Cargo Logistics")
                        for i, (k,v) in enumerate(new_resources.items()):
                            img_name = f"Ore_{k}"
                            dpg.add_image_button(texture_tag=img_name,
                                                 tag=f"pla_{pid}_ore{i}",
                                                 enabled=enable_logistics,
                                                 tint_color=(255,255,255,255) if enable_logistics else (150,150,150,200),
                                                 user_data=(pid,i),
                                                 callback=self._cb_planet_ore_priority)
                            dpg.add_text(f"{v}%",
                                         color=C_TEXT,
                                         tag=f"pla_{pid}_ore{i}_text")
                    
                    self._refresh_all()
                    break
            dpg.delete_item("proj_alchemy_dlg")

        with dpg.group(horizontal=True, parent="proj_alchemy_options"):
            dpg.add_button(label="Apply",  width=80, callback=_confirm)
            dpg.add_spacer(width=8)
            dpg.add_button(label="Cancel", width=80,
                           callback=lambda: dpg.delete_item("proj_alchemy_dlg"))
    
    def _show_proj_researched(self, s, v):
        self.prefs["projects_show_r"] = v
        save_prefs(self.prefs)
        self._refresh_all()
        
    def _show_proj_locked(self, s, v):
        self.prefs["projects_show_locked"] = v
        save_prefs(self.prefs)
        self._refresh_all()
        


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
        return f"x{add:.2f}"

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
                ("",85), ("Name",140), ("Planet",135), ("Stars",175),
                ("Primary",120), ("",80), ("Secondary",155), ("",80),
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
        max_idx = len(managers) - 1
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
                with dpg.group(horizontal=True):
                    x_button = dpg.add_button(label="X", 
                                   user_data=idx, callback=self._cb_mgr_delete)
                    dpg.add_image_button(texture_tag="Arrow_up",
                                         width=17, height=20,
                                         enabled=idx > 0,                                         
                                         user_data=(idx, -1), callback=self._cb_mgr_move)
                    dpg.add_image_button(texture_tag="Arrow_down", 
                                         width=17, height=20,                    
                                         enabled=idx < max_idx,                                         
                                         user_data=(idx, 1), callback=self._cb_mgr_move)
                dpg.bind_item_theme(x_button, "red_button_theme")
                
                dpg.add_input_text(default_value=name, width=135,
                                   tag=f"mgr_name_{idx}", user_data=idx,
                                   on_enter=True, callback=self._cb_mgr_name)
                # Planet Column
                dpg.add_combo(items=planet_opts, default_value=planet_display,
                              width=130, user_data=idx,
                              callback=self._cb_mgr_planet)
                # 7 star images
                with dpg.group(horizontal=True):
                    for si in range(1, 8):
                        tex = "star_white" if si <= stars else "star_black"
                        dpg.add_image_button(
                            texture_tag=tex,
                            width=19, height=19,
                            tag=f"mgr_star_{idx}_{si}",
                            user_data=(idx, si),
                            callback=self._cb_mgr_star_click)
                        dpg.bind_item_theme(f"mgr_star_{idx}_{si}", "clear_button")
                        
                dpg.add_combo(items=self._PRIMARY_OPTS,
                              default_value=self._mgr_primary_label(primary),
                              width=120, user_data=idx,
                              callback=self._cb_mgr_primary)
                dpg.add_text(f"x{pri_mult:.2f}", color=C_TEAL, tag=f"mgr_pri_eff_{idx}")
                dpg.add_combo(items=self._SECONDARY_OPTS,
                              default_value=self._mgr_secondary_label(secondary),
                              width=155, user_data=idx,
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
    
    def _cb_mgr_move(self, s, v, ud):
        idx, d = ud
        swap_idx = idx + d
        mgrs = self.state.get("managers", [])
        mgrs[idx], mgrs[swap_idx] = mgrs[swap_idx], mgrs[idx]
        self.state["managers"] = mgrs
        save_state(self.state)
        self._refresh_managers()
        

    def _cb_mgr_delete(self, s, v, ud):
        mgrs = self.state.get("managers", [])
        if 0 <= ud < len(mgrs): mgrs.pop(ud)
        save_state(self.state)
        self._refresh_all()

    def _cb_mgr_name(self, s, v, ud):
        self.state["managers"][ud]["name"] = v.strip() or f"Manager {ud+1}"
        save_state(self.state)

    def _cb_mgr_planet(self, s, v, ud):
        pid = v.split(":")[0].strip() if v else ""
        self._mgr_assign_planet(ud, pid)
        save_state(self.state)
        self._refresh_all()

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
        self._refresh_all()

    def _cb_mgr_primary(self, s, v, ud):
        try: key = self._PRIMARY_KEYS[self._PRIMARY_OPTS.index(v)]
        except: return
        self.state["managers"][ud]["primary"] = key
        stars = self.state["managers"][ud].get("stars", 1)
        if dpg.does_item_exist(f"mgr_pri_eff_{ud}"):
            dpg.set_value(f"mgr_pri_eff_{ud}", f"x{self._mgr_primary_mult(key,stars):.2f}")
        save_state(self.state)
        self._refresh_all()

    def _cb_mgr_secondary(self, s, v, ud):
        try: key = self._SECONDARY_KEYS[self._SECONDARY_OPTS.index(v)]
        except: return
        self.state["managers"][ud]["secondary"] = key
        stars = self.state["managers"][ud].get("stars", 1)
        sec_disp = self._mgr_secondary_display(key, stars)
        if dpg.does_item_exist(f"mgr_sec_eff_{ud}"):
            dpg.set_value(f"mgr_sec_eff_{ud}", sec_disp)
        save_state(self.state)
        self._refresh_all()

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
        self._refresh_all()

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
                dpg.add_text(f"$ {fmt(cost)}", color=C_TEAL)
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
        self._refresh_all()
        
        
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
            idx_map  = {"mining": "m",   "speed": "s",   "cargo": "c"}
            inc  = bonuses[stat]
            idx  = idx_map[stat]
            cur  = self.state["planets"][pid]["colony"][idx]
            self.state["planets"][pid]["colony"][idx] = round(cur + inc, 4)
            self.state["planets"][pid]["colony"]["lvl"] += 1
            # Remove this colony row
            self.state["colonies"].pop(orig_idx)
            save_state(self.state)
            self._refresh_all()

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
                dpg.add_text(f"{colony_state['m']:.2f}")
                dpg.add_image(self._arrow_right,
                        width=self._arrow_right_size[0],
                        height=self._arrow_right_size[1]
                        )
                dpg.add_text(f"{colony_state['m'] + 0.3:.2f}")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Ship Speed",
                            width=110,
                            user_data="speed",  callback=_apply)
                dpg.add_text(f"{colony_state['s']:.2f}")
                dpg.add_image(self._arrow_right,
                        width=self._arrow_right_size[0],
                        height=self._arrow_right_size[1]
                        )
                dpg.add_text(f"{colony_state['s'] + 0.6:.2f}")
            with dpg.group(horizontal=True):
                dpg.add_button(label="Ship Cargo",
                            width=110,
                            user_data="cargo",  callback=_apply)
                dpg.add_text(f"{colony_state['c']:.2f}")
                dpg.add_image(self._arrow_right,
                        width=self._arrow_right_size[0],
                        height=self._arrow_right_size[1]
                        )
                dpg.add_text(f"{colony_state['c'] + 0.3:.2f}")
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
        self._refresh_all()

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
        self._refresh_all()

    # ── PLANETS ────────────────────────────────────────────────────────────────
    def _tab_planets(self):
        with dpg.group(horizontal=True):
            for key, label, tc, tm in [
                ("mining","Mining Rate","gmc","gmm"),
                ("speed", "Ship Speed", "gsc","gsm"),
                ("cargo", "Ship Cargo", "gcc","gcm"),
            ]:
                self._bonus_strip(key, label, tc, tm, self._cb_planet_global)
        with dpg.table(tag="planet_tbl", header_row=False, row_background=True,
                       borders_innerH=True, borders_outerH=True,
                       borders_innerV=True, borders_outerV=True,
                       scrollY=True, scrollX=True, resizable=True,
                       policy=dpg.mvTable_SizingFixedFit, freeze_rows=2):
            # 19 columns: 11 main + 3 probe + 3 colony + 2 separator
            for w in [
                28, 105, 25, 27,    # #, Planet, Scope, Owned, 
                136,                    # Manager
                67, 55, 109,          # VPS, next_vps, Mining, 
                51,                     # Calculated transport speed
                104,                 # Speed
                104,                 # Cargo
                180,             # Probe: Mng, Spd, Crg
                160,             # Colony: Mng, Spd, Crg
                240,                    # Ores
            ]:
                dpg.add_table_column(label="", width_fixed=True, init_width_or_weight=w)
        
        # Build table with initial blank values
        with dpg.table_row(parent="planet_tbl"):
            for lbl in ["#","Planet"]:
                dpg.add_text(lbl, color=C_ACCENT)
            dpg.add_image(self._telescope, width=self._telescope_size[0], height=self._telescope_size[1])
            for lbl in [" ","Manager","VPS"]:
                dpg.add_text(lbl, color=C_ACCENT)
            
            # NextVPS header
            dpg.add_text("VPS/$", color=C_ACCENT)
            
            for lbl in ["Mining","","Speed","Cargo"]:
                dpg.add_text(lbl, color=C_ACCENT)
            # columns 11-13: "Probes" spanning — place in col 11, overflow right

            #dpg.add_text("<----", color=C_TEAL)
            dpg.add_text("        Probes", color=C_TEAL)
            #dpg.add_text("---->", color=C_TEAL)  
            # columns 14-16: "Colony" spanning
            #dpg.add_text("<----", color=C_TEAL)
            dpg.add_text("        Colony", color=C_TEAL)
            #dpg.add_text("---->", color=C_TEAL) 
            dpg.add_text("")
            
        # ── header row 2: sub-column labels ──────────────────────────────────
        with dpg.table_row(parent="planet_tbl"):
            # columns 0-10: plain labels, no group heading
            for lbl in ["","","","","",""]:
                dpg.add_text(lbl, color=C_ACCENT)
            nvps_pow = self.prefs.get("next_vps_pow",0)
            exp_str = fmt_super(f"{nvps_pow:+03d}")
            dpg.add_text(f"x10{exp_str}", 
                         color=C_MUTED,
                         tag="pla_nvps_exp")
            for lbl in ["","","",""]:
                dpg.add_text(lbl, color=C_ACCENT)
            for lbl in ["     M / S / C","     M / S / C"]:
                dpg.add_text(lbl, color=C_MUTED)
            dpg.add_text("Ores", color=C_ACCENT)
            
        for pid, bd in sorted(self.base["planets"].items(), key=lambda x:int(x[0])):
            ps    = self.state["planets"][pid]
            scope = str(bd["telescope"]) if bd["telescope"] else "—"
            ores  = ", ".join(f"{o} {p}%" for o,p in bd["resources"].items())
            col   = (85,85,112,255)

            def lvl_grp(stat):
                with dpg.group(horizontal=True):
                    dpg.add_input_text(default_value=0,
                                       on_enter=True,
                                       width=34,
                                       user_data=(pid,stat),
                                       tag=f"pla_{pid}_{stat}lvl",
                                       enabled=False,
                                       callback=self._cb_planet_lvl_edit)
                    dpg.add_button(label="+",
                                   width=16,
                                   user_data=(pid,stat,1),
                                   callback=self._cb_planet_lvl,
                                   tag=f"pla_{pid}_{stat}lvl_btn")

            with dpg.table_row(parent="planet_tbl"):
                dpg.add_text(pid, color=col, tag=f"pla_{pid}_pid")
                with dpg.group(horizontal=True):
                    dpg.add_image(f"Planet_{bd['name']}", tag=f"pla_{pid}_icon")
                    dpg.add_text(bd["name"], color=col, tag=f"pla_{pid}_name")
                dpg.add_text(scope, color=C_MUTED, tag=f"pla_{pid}_scope")
                dpg.add_checkbox(default_value=False, user_data=pid,
                                 callback=self._cb_planet_owned,
                                 tag=f"pla_{pid}_owned")

                # Manager column
                mgr_names = [""]
                dpg.add_combo(items=mgr_names, default_value="",
                              width=135, 
                              user_data=pid, 
                              enabled=False,
                              tag=f"pla_{pid}_manager",
                              callback=self._cb_planet_manager)
                              
                # "VPS" column
                vps = 0
                dpg.add_text(f"{fmt(vps)}",
                             tag=f"pla_{pid}_vps",
                             color=C_MUTED)
                
                # "Next VPS/$" 
                dpg.add_text("",
                             tag=f"pla_{pid}_nvps",
                             color=(0,0,0,255))
 
                # "Mining" column
                with dpg.group(horizontal=True):
                    lvl_grp("mining")
                    with dpg.group():
                        dpg.add_text("—",
                                     tag=f"pla_{pid}_ops",
                                     color=col)

                # "Transport" column
                dpg.add_text(f"", 
                             tag=f"pla_{pid}_trans",
                             color=C_TEAL)
                
                # Speed column
                with dpg.group(horizontal=True):
                    lvl_grp("speed")
                    with dpg.group():
                        dpg.add_text("—",
                                     tag=f"pla_{pid}_speed",
                                     color=col)
                                 
                # "Cargo" column
                with dpg.group(horizontal=True):
                    lvl_grp("cargo")
                    with dpg.group():
                        dpg.add_text("—", 
                                     tag=f"pla_{pid}_cargo",
                                     color=col)

                # Probe bonuses
                with dpg.group(horizontal=True):
                    dpg.add_button(label='',
                                   width=180,
                                   tag=f"pla_{pid}_probe",
                                   user_data=pid,
                                   callback=self._cb_planet_probe_set)
                                       
                                       
                                    
                # Colony bonuses (cols 14-16)
                with dpg.group(horizontal=True):
                    dpg.add_button(label='',
                                   width=160,
                                   tag=f"pla_{pid}_colony",
                                   user_data=pid,
                                   callback=self._cb_planet_colony_set)
                    
                #dpg.add_text(ores, color=col, tag=f"pla_{pid}_ores")
                with dpg.group(horizontal=True, tag=f"pla_{pid}_ores_group"):
                    for i, (k,v) in enumerate(bd["resources"].items()):
                        img_name = f"Ore_{k}"
                        dpg.add_image_button(texture_tag=img_name,
                                             tag=f"pla_{pid}_ore{i}",
                                             enabled=False,
                                             tint_color=(150,150,150,200),
                                             user_data=(pid,i),
                                             callback=self._cb_planet_ore_priority)
                        dpg.add_text(f"{v}%",
                                     color=col,
                                     tag=f"pla_{pid}_ore{i}_text")
                                    
    def _cb_planet_probe_set(self, s, v, ud):
        pid = ud
        ps = self.state["planets"].get(pid,{})
        pb = self.base["planets"].get(pid,{})
        probe = ps.get("probe",{})
        lvl = probe.get("lvl",0)
        m = probe.get("m",1)
        s = probe.get("s",1)
        c = probe.get("c",1)
        smb = probe.get("smb",1)
        name = pb.get("name","")
        
        def _cb_pla_pro_apply(sender):
            m = dpg.get_value("pla_pro_dlg_m")
            s = dpg.get_value("pla_pro_dlg_s")
            c = dpg.get_value("pla_pro_dlg_c")
            smb = dpg.get_value("pla_pro_dlg_smb")
            new_probe = {
                "m": m,
                "s": s,
                "c": c,
                "smb": smb}
            self.state["planets"][pid].update({"probe":new_probe})
            save_state(self.state)
            dpg.delete_item("pla_pro_dlg")
            self._refresh_all()
        
        with dpg.window(label=f"Set probe bonuses for {pid}:{name}",
                        modal=True,
                        pos=dpg.get_mouse_pos(local=False),
                        width=300,
                        tag="pla_pro_dlg"):
            with dpg.group(horizontal=True):
                dpg.add_text(" Mining Rate: ")
                dpg.add_input_float(default_value=m,
                                    on_enter=True,
                                    width=150,
                                    tag="pla_pro_dlg_m")
            with dpg.group(horizontal=True):
                dpg.add_text("  Ship Speed: ")
                dpg.add_input_float(default_value=s,
                                    on_enter=True,
                                    width=150,
                                    tag="pla_pro_dlg_s")
            with dpg.group(horizontal=True):
                dpg.add_text("       Cargo: ")
                dpg.add_input_float(default_value=c,
                                    on_enter=True,
                                    width=150,
                                    tag="pla_pro_dlg_c")
            with dpg.group(horizontal=True):
                dpg.add_text("Mgr Secondary: ")
                dpg.add_input_float(default_value=smb,
                                    on_enter=True,
                                    width=150,
                                    tag="pla_pro_dlg_smb")
            dpg.add_button(label="Apply",callback=_cb_pla_pro_apply)   


    def _cb_planet_colony_set(self, s, v, ud):
        pid = ud
        ps = self.state["planets"].get(pid,{})
        pb = self.base["planets"].get(pid,{})
        colony = ps.get("colony",{})
        lvl = colony.get("lvl",0)
        m = colony.get("m",0)
        s = colony.get("s",0)
        c = colony.get("c",0)
        name = pb.get("name","")
        
        def _cb_pla_col_apply(sender):
            lvl = dpg.get_value("pla_col_dlg_lvl")
            m = dpg.get_value("pla_col_dlg_m")
            s = dpg.get_value("pla_col_dlg_s")
            c = dpg.get_value("pla_col_dlg_c")
            new_col = {
                "lvl": lvl,
                "m": m,
                "s": s,
                "c": c}
            self.state["planets"][pid].update({"colony":new_col})
            save_state(self.state)
            dpg.delete_item("pla_col_dlg")
            self._refresh_all()
        
        with dpg.window(label=f"Set colony level for {pid}:{name}",
                        modal=True,
                        pos=dpg.get_mouse_pos(local=False),
                        width=300,
                        tag="pla_col_dlg"):
            with dpg.group(horizontal=True):
                dpg.add_text("Colony Level: ")
                dpg.add_input_int(default_value=lvl,
                                  min_value=0,
                                  width=150,
                                  min_clamped=True,
                                  on_enter=True,
                                  tag="pla_col_dlg_lvl")
            with dpg.group(horizontal=True):
                dpg.add_text(" Mining Rate: ")
                dpg.add_input_float(default_value=m,
                                    on_enter=True,
                                    width=150,
                                    tag="pla_col_dlg_m")
            with dpg.group(horizontal=True):
                dpg.add_text("  Ship Speed: ")
                dpg.add_input_float(default_value=s,
                                    on_enter=True,
                                    width=150,
                                    tag="pla_col_dlg_s")
            with dpg.group(horizontal=True):
                dpg.add_text("       Cargo: ")
                dpg.add_input_float(default_value=c,
                                    on_enter=True,
                                    width=150,
                                    tag="pla_col_dlg_c")
            dpg.add_button(label="Apply",callback=_cb_pla_col_apply)   
                                 
        

    def _cb_planet_ore_priority(self, s, v, ud):
        pid, i = ud
        self.state["planets"][pid].update({"ore_pri": i})
        save_state(self.state)
        self._refresh_all()
    
    def _cb_planet_global(self, s, v, ud):
        key = ud
        try: val = max(0.01, float(v))
        except: return
        self.state["globals"][key] = val
        tc_map = {"mining":"gmc","speed":"gsc","cargo":"gcc"}
        tm_map = {"mining":"gmm","speed":"gsm","cargo":"gcm"}
        dpg.set_value(tc_map[key], f"×{global_bonuses[key]:.3f}")
        dpg.set_value(tm_map[key], str(val))
        save_state(self.state)
        self._refresh_all()

    def _cb_planet_owned(self, s, v, ud):
        pid = ud
        self.state["planets"][pid]["owned"] = v
        if v:
            lvls = self.state["planets"][pid]["levels"]
            for k in lvls:
                if lvls[k] == 0: lvls[k] = 1
        else:
            lvls = self.state["planets"][pid]["levels"]
            for k in lvls:
                lvls[k] = 0
        save_state(self.state)
        self._refresh_all()

    def _cb_planet_lvl(self, s, v, ud):
        pid, stat, delta = ud
        cur = self.state["planets"][pid]["levels"][stat]
        self.state["planets"][pid]["levels"][stat] = max(1, cur+delta)
        save_state(self.state)
        self._refresh_all()

    def _cb_planet_lvl_edit(self, s, v, ud):
        pid, stat = ud
        self.state["planets"][pid]["levels"][stat] = max(1, int(v))
        save_state(self.state)
        self._refresh_all()

    def _cb_planet_bonus_val(self, s, v, ud):
        pid, group, idx = ud
        try: val = float(v)
        except: return
        self.state["planets"][pid][group][idx] = val
        save_state(self.state)
        self._refresh_all()
    
    def _refresh_single_planet(self, pid:str):
        bd = self.base["planets"][pid]
        ps = self.state["planets"][pid]
        owned = ps["owned"]; lvls = ps["levels"]
        # probe = ps["probes"]; colony = ps["colony"]
        probe = ps.get("probe",{"m":1, "s":1, "c":1})
        colony = ps.get("colony",{"lvl":0, "m":1, "s":1, "c":1})
        dist = self.base["planets"][pid]["distance"]
        next_vps_pow = self.prefs.get("next_vps_pow",0)
        max_nvps = self.prefs.get("max_nvps",100)
        
        gm=global_bonuses["mining"]
        gs=global_bonuses["speed"]
        gc=global_bonuses["cargo"]

        bm = beacon_bonus(pid,"mining",self.base,self.state)
        bs = beacon_bonus(pid,"speed", self.base,self.state)
        bc = beacon_bonus(pid,"cargo", self.base,self.state)
        mm = manager_primary_bonus(pid,"mining",self.state)
        ms = manager_primary_bonus(pid,"speed", self.state)
        mc = manager_primary_bonus(pid,"cargo", self.state)
        mb = probe["m"]*colony["m"]*bm*mm*gm*_get_misc_bonus("planets", pid, "mining", self.state)
        sb = probe["s"]*colony["s"]*bs*ms*gs*_get_misc_bonus("planets", pid, "speed", self.state)
        cb = probe["c"]*colony["c"]*bc*mc*gc*_get_misc_bonus("planets", pid, "cargo", self.state)
        #mr = _mining_rate(lvls["mining"],mb) if owned else 0
        mr = _planet_mining_rate(pid, self.base, self.state) if owned else 0
        sp = _ship_speed( lvls["speed"], sb) if owned else 0
        cg = _ship_cargo( lvls["cargo"], cb) if owned else 0
        col   = C_TEXT if owned else (85,85,112,255)
        
        # PID
        dpg.configure_item(f"pla_{pid}_pid", color=col)
        
        # Planet
        dpg.configure_item(f"pla_{pid}_icon", tint_color=(255,255,255,255) if owned else (150,150,150,200) )
        dpg.configure_item(f"pla_{pid}_name", color=col)
        
        # Scope
        scope = bd.get("telescope", 0)
        dpg.configure_item(f"pla_{pid}_scope", color=C_TEXT if self._beacon_unlocked(scope) else C_MUTED)
        
        # Owned
        dpg.set_value(f"pla_{pid}_owned", owned)
        
        # Manager
        mgr_names = [""] + [m["name"] for m in self.state.get("managers", [])]
        cur_mgr = next((m["name"] for m in self.state.get("managers", []) if m.get("planet")==pid), "")
        dpg.configure_item(f"pla_{pid}_manager",
                           enabled=owned,
                           items=mgr_names,
                           default_value=cur_mgr)
        
        # VPS
        vps = get_vps(pid, self.state, self.base) if owned else 0
        dpg.set_value(f"pla_{pid}_vps", f"$ {fmt(vps)}")
        dpg.configure_item(f"pla_{pid}_vps", color=col)
        
        # NVPS/$
        next_vps = get_next_vps_per(pid, lvls["mining"], vps, self.base, self.state)
        nvc = min(255, int(255 * next_vps / max_nvps))
        dpg.set_value(f"pla_{pid}_nvps", f"{next_vps/ (10**next_vps_pow):.2f}")
        dpg.configure_item(f"pla_{pid}_nvps", color=(nvc,nvc,nvc,255) if next_vps < 0.9*max_nvps else (200,255,200,255))
        
        # M.Lvl
        dpg.set_value(f"pla_{pid}_mininglvl", ps["levels"]["mining"])
        dpg.configure_item(f"pla_{pid}_mininglvl", enabled=owned)
        dpg.configure_item(f"pla_{pid}_mininglvl_btn", enabled=owned)
        
        # Ore/s
        dpg.set_value(f"pla_{pid}_ops", fmt(mr) if owned else "—")
        dpg.configure_item(f"pla_{pid}_ops", color=col)
        
        # Transport
        ts = _planet_transport(dist, sp, cg)
        ts_max = _planet_transport(bd.get("distance_min", 1000), sp, cg)
        ts_min = _planet_transport(bd.get("distance_max", 1e9), sp, cg)
        
        dpg.set_value(f"pla_{pid}_trans", fmt(ts) if owned else "—")
        if owned:
            dpg.configure_item(f"pla_{pid}_trans", 
                               color=C_TEAL if ts_min > mr else (C_WARN if ts_max < mr else C_GOLD))
        else:
            dpg.configure_item(f"pla_{pid}_trans", 
                               color=C_MUTED)
        
        # S.lvl
        dpg.set_value(f"pla_{pid}_speedlvl", ps["levels"]["speed"])
        dpg.configure_item(f"pla_{pid}_speedlvl", enabled=owned)
        dpg.configure_item(f"pla_{pid}_speedlvl_btn", enabled=owned)

        # Speed
        dpg.set_value(f"pla_{pid}_speed", fmt(sp) if owned else "—")
        dpg.configure_item(f"pla_{pid}_speed", color=col)
        
        # C.Lvl
        dpg.set_value(f"pla_{pid}_cargolvl", ps["levels"]["cargo"])
        dpg.configure_item(f"pla_{pid}_cargolvl", enabled=owned)
        dpg.configure_item(f"pla_{pid}_cargolvl_btn", enabled=owned)
        
        # Cargo
        dpg.set_value(f"pla_{pid}_cargo", fmt(cg) if owned else "—")
        dpg.configure_item(f"pla_{pid}_cargo", color=col)

        # Probes
        dpg.configure_item(f"pla_{pid}_probe", 
                           label=_get_probe_string(probe),
                           enabled=owned)
        #for idx in ["m","s","c"]:
        #    dpg.set_value(f"pla_{pid}_probe{idx}", f"{probe[idx]:.2f}")
        #    dpg.bind_item_theme(f"pla_{pid}_probe{idx}", "muted_input_text" if probe[idx] == 1 else 0)
                
        
        # Colony
        dpg.configure_item(f"pla_{pid}_colony", 
                           label=_get_col_string(colony),
                           enabled=owned)
        #for idx in ["m","s","c"]:
        #    dpg.set_value(f"pla_{pid}_colony{idx}", f"{colony[idx]:.2f}")
        #    dpg.bind_item_theme(f"pla_{pid}_colony{idx}", "muted_input_text" if colony[idx] == 1 else 0)
        
        # Ores
        ore_p = _planet_ore_pri(pid, self.state, self.base)
        for i, (k,v) in enumerate(bd["resources"].items()):
            enable_logistics = _proj(self.state, "Cargo Logistics") and owned
            dpg.configure_item(f"pla_{pid}_ore{i}", 
                               enabled=enable_logistics,
                               tint_color=(255,255,255,255) if enable_logistics else (150,150,150,200))
            if ore_p == i:
                dpg.bind_item_theme(f"pla_{pid}_ore{i}", "ore_priority")
            else:
                dpg.bind_item_theme(f"pla_{pid}_ore{i}", 0)
            
            dpg.configure_item(f"pla_{pid}_ore{i}_text", color=col)
                              

    def _refresh_planets(self):
        # find the maximum next_vps, for number shading
        max_nvps = 0
        for pid, bd in self.base["planets"].items():
            ps = self.state["planets"][pid]
            if not ps["owned"]:
                continue
            lvl = ps["levels"]["mining"]
            vps = get_vps(pid, self.state, self.base)
            nvps = get_next_vps_per(pid, lvl, vps, self.base, self.state)
            if nvps > max_nvps:
                max_nvps = nvps
        self.prefs.update({"max_nvps": max_nvps})
        # if the power changed, update the display
        old_pow = self.prefs.get("next_vps_pow",0)
        new_pow = math.floor(math.log10(max_nvps))
        if old_pow != new_pow:
            exp_str = fmt_super(f"{new_pow:+03d}")
            dpg.set_value("pla_nvps_exp", f"x10{exp_str}")
            
        self.prefs.update({"next_vps_pow": new_pow})
        save_prefs(self.prefs)
        
        # update global bonus strip
        dpg.set_value("gmc", f"×{global_bonuses['mining']:.3f}")
        dpg.set_value("gsc", f"×{global_bonuses['speed']:.3f}")
        dpg.set_value("gcc", f"×{global_bonuses['cargo']:.3f}")
        
        for pid, bd in self.base["planets"].items():
            self._refresh_single_planet(pid)
        
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
        self._refresh_all()

    def _cb_market(self, s, v, ud):
        cat, name, _ = ud
        self.state[cat][name]["market"] = int(v)
        save_state(self.state)
        self._update_price_label(cat, name)
        self._refresh_all()

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
        self._refresh_all()

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
            for cat in ("globals", "beacons", "rooms", "station", "misc_bonuses"):
                new_state[cat] = self.state[cat].copy()
                
            # Copy managers over (without planet assignments)
            for mgr in self.state["managers"]:
                mgr["planet"] = ""
                new_state["managers"].append(mgr.copy())
                
            # Reload base data
            self.base = load_base()
            
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
        # Rooms affect global bonuses — refresh everything that uses them
        self._refresh_all()

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
        self._refresh_all()

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
        self._refresh_all()

    
    # ── STATION ──────────────────────────────────────────────────────────────────
    
    def _tab_station(self):
        with dpg.group(horizontal=True):
            dpg.add_checkbox(label="Show Locked",
                             default_value=self.prefs.get("station_show_locked",True),
                             callback=self._show_station_locked)
            dpg.add_checkbox(label="Show Maxed",
                             default_value=self.prefs.get("station_show_maxed",True),
                             callback=self._show_station_maxed)
        with dpg.table(
            tag="station_tbl",
            header_row=True,
            row_background=True,
            borders_innerH=True, borders_outerH=True,
            borders_innerV=True, borders_outerV=True,
            scrollY=True, resizable=True,
            policy=dpg.mvTable_SizingFixedFit, freeze_rows=1,
        ):
            for lbl, w in [
                ("Name", 235),
                ("Level", 100),
                ("Max", 40),
                ("Per lvl", 60),
                ("Bonus", 60),
                ("Description", 300)
            ]:
                dpg.add_table_column(label=lbl,
                                     width_fixed=True,
                                     init_width_or_weight=w)
                                
    def _refresh_station(self):
        dpg.delete_item("station_tbl", children_only=True, slot=1)
        sta_state = self.state.get("station",{})
        for name, sta in self.base["station"].items():
            sl = sta_state.get(name,0)
            met = station_prereq_met(name, self.state, self.base)
            ml = sta.get("max_level",0)
            pl = sta.get("per_level",0)
            boost = sta.get("boost","")
            bonus = pl * sl
            desc = gb_descriptions.get(boost, "")
            if not desc: desc = boost
            col = C_TEAL if sl > 0 else ((85,85,112,255) if not met else C_TEXT)
            maxed = sl >= ml
            if maxed and not self.prefs.get("station_show_maxed",True):
                continue
            if (not met) and (not self.prefs.get("station_show_locked",True)):
                continue
            
            
            with dpg.table_row(parent="station_tbl"):
                # col: Name
                dpg.add_text(name, color=col)
                
                # col: Level
                with dpg.group(horizontal=True):
                    dpg.add_input_text(default_value=int(sl),
                                       on_enter=True,
                                       width=30,
                                       user_data=name,
                                       tag=f"sta_{name}_lvl",
                                       enabled=met,
                                       callback=self._cb_station_lvl_edit)
                    dpg.add_button(label="+",
                                   width=16,
                                   user_data=name,
                                   enabled=(not maxed) and met,
                                   callback=self._cb_station_lvl)
                                  

                # col: Max Level
                dpg.add_text(ml, color=col)

                # col: Per level
                pl_text = f"+{pl}" if pl > 0 else f"{pl}%"
                dpg.add_text(pl_text, color=col)

                # col: Bonus
                bonus_text = f"x{1 + bonus}" if bonus > 0 else (f"{bonus}%" if bonus < 0 else "-")
                dpg.add_text(bonus_text, color=col)

                # col: Description
                dpg.add_text(desc, color=col)
     
    def _cb_station_lvl(self, s, v, ud):
        cur = self.state["station"].get(ud,0)
        self.state["station"].update({ud:cur + 1})
        save_state(self.state)
        self._refresh_all()

    def _cb_station_lvl_edit(self, s, v, ud):
        lvl_max = self.base["station"].get(ud,{}).get("max_level",0)
        self.state["station"].update({ud:max(0, min(int(v),lvl_max))})
        save_state(self.state)
        self._refresh_all()
    
    def _show_station_locked(self, s, v):
        self.prefs.update({"station_show_locked":v})
        save_prefs(self.prefs)
        self._refresh_station()

    def _show_station_maxed(self, s, v):
        self.prefs.update({"station_show_maxed":v})
        save_prefs(self.prefs)
        self._refresh_station()
            
    # ──── MISC ─────────────────────        
    _MISC_TARGET_TYPES = ["","ores","alloys","items","planets","global"]
    
    def _tab_misc(self):
        with dpg.group(horizontal=True):
            dpg.add_button(label="+ Add Misc Bonus", callback=self._cb_misc_add)
        with dpg.table(
            tag="misc_tbl", header_row=True, row_background=True,
            borders_innerH=True, borders_outerH=True,
            borders_innerV=True, borders_outerV=True,
            scrollY=True, scrollX=True, resizable=True,
            policy=dpg.mvTable_SizingFixedFit, freeze_rows=1
        ):
            for lbl, w in [("",120), ("Name",300), 
                ("Target Type", 140), ("Target", 140),
                ("Stat", 120), ("Bonus",100)]:  
                dpg.add_table_column(label=lbl, width_fixed=True, init_width_or_weight=w)
                
    def _refresh_misc(self):
        dpg.delete_item("misc_tbl", children_only=True, slot=1)
        misc_items = self.state.get("misc_bonuses", [])
        max_idx = len(misc_items) - 1
        for idx, m_item in enumerate(misc_items):
            debug_str = f"{idx}: {m_item}  ::  '{m_item['name']}'"
            name = m_item.get("name", f"Misc bonus {idx}")
            target_type = m_item.get("target_type", "global")
            target = m_item.get("target", "global")
            stat = m_item.get("stat", "")
            bonus = m_item.get("bonus", 1)
            
            with dpg.table_row(parent="misc_tbl"):
                # order/delete
                with dpg.group(horizontal=True):
                    x_button = dpg.add_button(label="X", 
                        user_data=idx, callback=self._cb_misc_delete)
                    dpg.bind_item_theme(x_button, "red_button_theme")
                    dpg.add_image_button(texture_tag="Arrow_up",
                                         width=17, height=20,
                                         enabled=idx > 0,                                         
                                         user_data=(idx, -1), callback=self._cb_misc_move)
                    dpg.add_image_button(texture_tag="Arrow_down", 
                                         width=17, height=20,                    
                                         enabled=idx < max_idx,                                         
                                         user_data=(idx, 1), callback=self._cb_misc_move)
                    dpg.add_spacer(width=3)
                    dpg.add_image_button(texture_tag="Edit",
                                         width=17, height=20,
                                         user_data=idx, callback=self._cb_misc_edit)
                
                # name
                dpg.add_input_text(default_value=name,
                                   tag=f"misc_name_{idx}",
                                   user_data=idx,
                                   on_enter=True,
                                   callback=self._cb_misc_update_name)
                
                # Target Type
                dpg.add_combo(items=self._MISC_TARGET_TYPES,
                              default_value=target_type,
                              width=140,
                              user_data=idx,
                              tag=f"misc_type_{idx}",
                              callback=self._cb_misc_update_type)
                
                # Target
                dpg.add_input_text(default_value=target,
                                   tag=f"misc_target_{idx}",
                                   user_data=idx,
                                   on_enter=True,
                                   callback=self._cb_misc_update_target)
                
                # Stat
                dpg.add_combo(items=list(gb_descriptions.keys()),
                              default_value=stat,
                              width=140,
                              user_data=idx,
                              tag=f"misc_stat_{idx}",
                              callback=self._cb_misc_update_stat)
                
                # Bonus
                dpg.add_input_text(default_value=bonus,
                                   tag=f"misc_bonus_{idx}",
                                   user_data=idx,
                                   on_enter=True,
                                   callback=self._cb_misc_update_bonus)
                                   
    def _cb_misc_update_name(self, s, v, ud):
        self.state["misc_bonuses"][ud]["name"] = v.strip() or f"Misc bonus {ud}"
        save_state(self.state)
        self._refresh_misc()
            
    def _cb_misc_update_type(self, s, v, ud):
        self.state["misc_bonuses"][ud]["target_type"] = v or ""
        save_state(self.state)
        self._refresh_all()
            
    def _cb_misc_update_target(self, s, v, ud):
        self.state["misc_bonuses"][ud]["target"] = v.strip() or ""
        save_state(self.state)
        self._refresh_all()
            
    def _cb_misc_update_stat(self, s, v, ud):
        self.state["misc_bonuses"][ud]["stat"] = v or "__"
        save_state(self.state)
        self._refresh_all()
            
    def _cb_misc_update_bonus(self, s, v, ud):
        self.state["misc_bonuses"][ud]["bonus"] = float(v) or 1
        save_state(self.state)
        self._refresh_all()
            
    def _cb_misc_add(self, s, v, ud):
        self.state.setdefault("misc_bonuses", []).append({
            "name": f"Misc Bonus {len(self.state['misc_bonuses']) + 1}",
            "target_type": "",
            "target": "",
            "stat": "__",
            "bonus": 1
        })
        save_state(self.state)
        self._refresh_misc()
        
    def _cb_misc_delete(self, s, v, ud):
        m_items = self.state.get("misc_bonuses",[])
        if 0 <= ud < len(m_items):
            m_items.pop(ud)
        save_state(self.state)
        self._refresh_all()
        
    def _cb_misc_move(self, s, v, ud):
        idx, d = ud
        swap_idx = idx + d
        m_items = self.state.get("misc_bonuses",[])
        m_items[idx], m_items[swap_idx] = m_items[swap_idx], m_items[idx]
        self.state["misc_bonuses"] = m_items
        save_state(self.state)
        self._refresh_misc()
        
    def _cb_misc_edit(self, s, v, ud):
        pass
    
    # ─────────────────────────

    def _refresh_all(self):
        calculate_global_bonuses(self.base, self.state)
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
        self._refresh_station()
        self._refresh_misc()
        dpg.set_value("lbl_smelters", str(self.state.get("smelters",1)))
        dpg.set_value("lbl_crafters", str(self.state.get("crafters",1)))
        dpg.set_value("dash_filter",  self.prefs.get("dashboard_filter","All"))
        dpg.set_value("dash_sort",    self.prefs.get("dashboard_sort","vps_profit_ore"))
        dpg.set_value("proj_sort",    self.prefs.get("projects_sort","time"))

if __name__ == "__main__":
    App()