"""
Idle Planet Miner - Recipe Value Calculator
Calculates value/second for smelting and crafting recipes,
comparing output value vs input costs and vs raw ore value.

Data is persisted in ipm_data.json in the same folder as this script.
"""

import json
import os
import sys
import re
import tkinter as tk
from tkinter import ttk, messagebox, font as tkfont

# ── path helpers ─────────────────────────────────────────────────────────────
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
DATA_FILE   = os.path.join(SCRIPT_DIR, "ipm_data.json")

# ── default seed data ─────────────────────────────────────────────────────────
DEFAULT_DATA = {
    "ores": {
        "Copper":    {"base_price": 1, "unlocked":True},
        "Iron":      {"base_price": 2, "unlocked":False},
        "Lead":      {"base_price": 4, "unlocked":False},
        "Silicon":   {"base_price": 8, "unlocked":False},
        "Aluminum":  {"base_price": 17, "unlocked":False},
        "Silver":    {"base_price": 36, "unlocked":False},
        "Gold":      {"base_price": 75, "unlocked":False},
        "Diamond":   {"base_price": 160, "unlocked":False},
        "Platium":   {"base_price": 340, "unlocked":False},
        "Titanium":  {"base_price": 730, "unlocked":False},
        "Iridium":   {"base_price": 1600, "unlocked":False},
        "Palladium": {"base_price": 3500, "unlocked":False},
        "Osmium":    {"base_price": 7800, "unlocked":False},
        "Rhodium":   {"base_price": 17500, "unlocked":False},
        "Inerton":   {"base_price": 40000, "unlocked":False},
        "Quadium":   {"base_price": 92000, "unlocked":False},
        "Scrith":    {"base_price": 215000, "unlocked":False},
        "Uru":       {"base_price": 510000, "unlocked":False},
        "Vibranium": {"base_price": 1250000, "unlocked":False},
        "Aether":    {"base_price": 3200000, "unlocked":False},
        "Viterium":  {"base_price": 9000000, "unlocked":False},
        "Xynium":    {"base_price": 28000000, "unlocked":False},
        "Quolium":   {"base_price": 90000000, "unlocked":False},
        "Luterium":  {"base_price": 300000000, "unlocked":False},
        "Wraith":    {"base_price": 1100000000, "unlocked":False},
        "Aqualite":  {"base_price": 4300000000, "unlocked":False},
        "Opalite":   {"base_price": 18000000000, "unlocked":False},
    },
    "alloys": {
        "Copper Bar":     {"base_price": 1450,     "smelt_time": 20,  "recipe": {"Copper": 1000}, "unlocked":False},
        "Iron Bar":       {"base_price": 3000,     "smelt_time": 30,  "recipe": {"Iron": 1000}, "unlocked":False},
        "Lead Bar":       {"base_price": 6100,     "smelt_time": 40,  "recipe": {"Lead": 1000}, "unlocked":False},
        "Silicon Bar":    {"base_price": 12500,    "smelt_time": 60,  "recipe": {"Silicon": 1000}, "unlocked":False},
        "Aluminum Bar":   {"base_price": 27600,    "smelt_time": 80,  "recipe": {"Aluminum": 1000}, "unlocked":False},
        "Silver Bar":     {"base_price": 60000,    "smelt_time": 120,  "recipe": {"Silver": 1000}, "unlocked":False},
        "Gold Bar":       {"base_price": 120000,   "smelt_time": 180,  "recipe": {"Gold": 1000}, "unlocked":False},
        "Bronze Bar":     {"base_price": 234000,   "smelt_time": 240,  "recipe": {"Silver Bar": 2,"Copper Bar": 10}, "unlocked":False},
        "Steel Bar":      {"base_price": 340000,   "smelt_time": 480,  "recipe": {"Iron Bar": 15, "Lead Bar": 15}, "unlocked":False},
        "Platinum Bar":   {"base_price": 780000,   "smelt_time": 600,  "recipe": {"Gold Bar": 2,"Platinum":1000}, "unlocked":False},
        "Titanium Bar":   {"base_price": 1630000,  "smelt_time": 720,  "recipe": {"Bronze Bar":2,"Titanium": 1000}, "unlocked":False},
        "Iridium Bar":    {"base_price": 3110000,  "smelt_time": 840,  "recipe": {"Steel Bar": 2, "Iridium":1000}, "unlocked":False},
        "Palladium Bar":  {"base_price": 7000000,  "smelt_time": 960,  "recipe": {"Platinum Bar": 2, "Palladium":1000}, "unlocked":False},
        "Osmium Bar":     {"base_price": 14500000, "smelt_time": 1080,  "recipe": {"Titanium Bar": 2, "Osmium": 1000}, "unlocked":False},
        "Rhodium Bar":    {"base_price": 31000000, "smelt_time": 1200,  "recipe": {"Iridium Bar": 2, "Rhodium": 1000}, "unlocked":False},
        "Inerton Alloy":  {"base_price": 68000000, "smelt_time": 1440,  "recipe": {"Palladium Bar": 2, "Inerton": 1000}, "unlocked":False},
    },
    "items": {
        "Copper Wire":       {"base_price": 10000,        "craft_time": 60,    "recipe": {"Copper Bar": 5}, "unlocked":False},
        "Iron Nail":         {"base_price": 20000,        "craft_time": 120,   "recipe": {"Iron Bar": 5}, "unlocked":False},
        "Battery":           {"base_price": 70000,        "craft_time": 240,   "recipe": {"Copper Wire": 2, "Copper Bar": 10}, "unlocked":False},
        "Hammer":            {"base_price": 135000,       "craft_time": 480,   "recipe": {"Iron Nail": 2, "Lead Bar": 5}, "unlocked":False},
        "Glass":             {"base_price": 220000,       "craft_time": 720,   "recipe": {"Silicon Bar": 10}, "unlocked":False},
        "Circuit":           {"base_price": 620000,       "craft_time": 1200,  "recipe": {"Silicon Bar": 5, "Aluminum Bar": 5, "Copper Wire": 10}, "unlocked":False},
        "Lens":              {"base_price": 1100000,      "craft_time": 2400,  "recipe": {"Glass": 1, "Silver Bar": 5}, "unlocked":False},
        "Laser":             {"base_price": 3200000,      "craft_time": 3600,  "recipe": {"Gold Bar": 5, "Lens": 1, "Iron Bar": 10}, "unlocked":False},
		"Basic Computer":    {"base_price": 7600000,      "craft_time": 4800,  "recipe": {"Circuit":5,"Silver Bar":5},"unlocked":False},
		"Solar Panel":       {"base_price": 12500000,     "craft_time": 6000,  "recipe": {"Circuit":5,"Glass":10},"unlocked":False},
		"Laser Torch":       {"base_price": 31000000,     "craft_time": 7200,  "recipe": {"Bronze Bar":5,"Laser":2,"Lens":5},"unlocked":False},
		"Advanced Battery":  {"base_price": 35000000,     "craft_time": 9000,  "recipe": {"Steel Bar":20,"Battery":30},"unlocked":False},
		"Thermal Scanner":   {"base_price": 71500000,     "craft_time": 10800, "recipe": {"Platinum Bar":5,"Laser":2,"Glass":5},"unlocked":False},
		"Advanced Computer": {"base_price": 180000000,    "craft_time": 12600, "recipe": {"Titanium Bar":5,"Basic Computer":5},"unlocked":False},
		"Navigation Module": {"base_price": 1000000000,   "craft_time": 13500, "recipe": {"Thermal Scanner":1,"Laser Torch":2},"unlocked":False},
		"Plasma Torch":      {"base_price": 1150000000,   "craft_time": 15000, "recipe": {"Iridium Bar":15,"Laser Torch":5},"unlocked":False},
		"Radio Tower":       {"base_price": 1450000000,   "craft_time": 15600, "recipe": {"Platinum Bar":75,"Aluminum Bar":150,"Titanium Bar":50},"unlocked":False},
		"Telescope":         {"base_price": 2700000000,   "craft_time": 16800, "recipe": {"Lens":20,"Advanced Computer":1},"unlocked":False},
		"Satellite Dish":    {"base_price": 3400000000,   "craft_time": 18000, "recipe": {"Steel Bar":150,"Palladium Bar":30},"unlocked":False},
		"Motor":             {"base_price": 7000000000,   "craft_time": 19200, "recipe": {"Bronze Bar":500,"Hammer":200},"unlocked":False},
		"Accumulator":       {"base_price": 12000000000,  "craft_time": 20400, "recipe": {"Osmium Bar":20,"Advanced Battery":3},"unlocked":False},
		"Nuclear Capsule":   {"base_price": 26000000000,  "craft_time": 21000, "recipe": {"Rhodium Bar":5,"Plasma Torch":1},"unlocked":False},
		"Wind Turbine":      {"base_price": 140000000000, "craft_time": 21600, "recipe": {"Aluminum Bar":300,"Motor":1},"unlocked":False}
    },
    "projects": {
        "Management":                  {"Recipe": {"Copper":400,    "Iron":50},         "Prereq": "", "unlocked": True},
        "Asteroid Miner":              {"Recipe": {"Copper":400,    "Iron":10},         "Prereq": "", "unlocked": True},
        "Telescope 1":                 {"Recipe": {"Iron":1500,     "Copper Bar":5},    "Prereq": "", "unlocked": True},
        "Telescope 2":                 {"Recipe": {"Lead Bar":10,   "Silicon":500},     "Prereq": "Telescope 1"},
        "Telescope 3":                 {"Recipe": {"Iron Nail":10, "Silicon Bar":15},  "Prereq": "Telescope 2"},
        "Telescope 4":                 {"Recipe": {"Hammer":5,      "Aluminum Bar":20}, "Prereq": "Telescope 3"},
        "Telescope 5":                 {"Recipe": {"Circuit":3,     "Gold Bar":10},     "Prereq": "Telescope 4"},
        "Telescope 6":                 {"Recipe": {"Laser":3,       "Bronze Bar":25},   "Prereq": "Telescope 5"},
        "Telescope 7":                 {"Recipe": {"Solar Panel":3, "Platinum Bar":20}, "Prereq": "Telescope 6"},
        "Telescope 8":                 {"Recipe": {"Laser Torch":3, "Titanium Bar":10}, "Prereq": "Telescope 7"},
        "Beacon":                      {"Recipe": {"Iron Bar":15},                      "Prereq": "Telescope 1"},
        "Resource Details":            {"Recipe": {"Battery":3},         "Prereq": "Telescope 2"},
        "Bottleneck Optimizations":    {"Recipe": {"Titanium Bar":5, "Platinum Bar":25, "Steel Bar": 50}, "Prereq": "Resource Details"},
        "Cargo Logistics":             {"Recipe": {"Aluminum Bar": 10, "Circuit": 3}, "Prereq": "Telescope 4"},
        "Ore Targeting":               {"Recipe": {"Hammer": 100, "Battery": 50}, "Prereq": "Cargo Logistics"},
        "Advanced Ore Targeting":      {"Recipe": {"Basic Computer": 100, "Thermal Scanner": 15}, "Prereq": "Ore Targeting"},
        "Alchemy":                     {"Recipe": {"Gold Bar": 50, "Lens": 6}, "Prereq": "Telescope 4"},
        "Advanced Alchemy":            {"Recipe": {"Silver": 50000, "Titanium": 25000, "Basic Computer": 6}, "Prereq": "Alchemy"},
        "Superior Alchemy":            {"Recipe": {"Palladium Bar": 400, "Osmium Bar": 200, "Advanced Computer": 5}, "Prereq": "Advanced Alchemy"},
        "Asteroid Refined Drilling":   {"Recipe": {"Silicon Bar": 40, "Lead Bar": 80}, "Prereq": "Telescope 3"},
        "Asteroid Harvester":          {"Recipe": {"Iron Bar": 400, "Circuit": 5}, "Prereq": "Asteroid Refined Drilling"},
        "Advanced Asteroid Harvester": {"Recipe": {"Space Probe": 1, "Plasma Torch": 50}, "Prereq": "Asteroid Harvester"},
        "Superior Asteroid Harvester": {"Recipe": {"Nuclear Reactor": 10, "Scrith Alloy": 300, "Inerton Alloy": 600}, "Prereq": "Advanced Asteroid Harvester"},
        "Debris Scanner":              {"Recipe": {"Collider": 1, "Gravity Chamber": 8}, "Prereq": "Superior Asteroid Harvester"},
        "Smelter":              {"Recipe": {"Copper": 600, "Iron": 250}, "Prereq": "Asteroid Miner"},
        "Crafter":              {"Recipe": {"Lead": 5000, "Iron Bar": 5}, "Prereq": "Smelter"},
        "Advanced Crafter":  {"Recipe": {"Lens": 5, "Gold Bar": 50}, "Prereq": "Crafter"},
        "Crafting Efficiency":  {"Recipe": {"Solar Panel": 30}, "Prereq": "Advanced Crafter"},
        "Superior Crafting":  {"Recipe": {"Thermal Scanner": 2, "Advanced Battery": 10, "Laser Torch":20}, "Prereq": ["Crafting Efficiency","Advanced Item Value"]},
        "Advanced Item Value":  {"Recipe": {"Lens": 5, "Silver Bar": 8}, "Prereq": "Advanced Crafter"},
        "Crafting Specialist":  {"Recipe": {"Advanced Battery": 3, "Advanced Computer": 2}, "Prereq": "Advanced Item Value"},
        "Superior Item Value":  {"Recipe": {"Palladium Bar": 200, "Laser Torch": 25}, "Prereq": "Advanced Item Value"},
        "Advanced Furnace":  {"Recipe": {"Glass": 3, "Aluminum Bar": 10}, "Prereq": "Smelter"},
        "Smelting Efficiency":  {"Recipe": {"Bronze Bar": 200, "": 8}, "Prereq": ""},
        "Market Insight":  {"Recipe": {"Silver Bar": 20, "Hammer": 10}, "Prereq": "Telescope 4"},
        "Inside Trader":  {"Recipe": {"Steel Bar": 25, "Lens": 10}, "Prereq": "Market Insight"},
        "Market Manipulation":  {"Recipe": {"Diamond": 30000, "Gold Bar": 15000, "Basic Computer": 10}, "Prereq": "Inside Trader"},
        "Advanced Market Manipulation":  {"Recipe": {"Quadium Alloy": 100, "Advanced Computer": 10, "Telescope": 5}, "Prereq": "Market Manipulation"},
        "Market Accelerator":  {"Recipe": {"Iridium Bar": 400, "Motor": 1}, "Prereq": "Inside Trader"},
        "Advanced Market Accelerator":  {"Recipe": {"Inerton Alloy": 115, "Gravity Chamber": 1}, "Prereq": "Market Accelerator"},
        "Rover Advanced Logistics":  {"Recipe": {"Bronze Bar": 20, "Battery": 20, "Lens": 10}, "Prereq": "Telescope 5"},
        "Rover Scanning Module":  {"Recipe": {"Aluminum Bar": 100, "Basic Computer": 1}, "Prereq": "Rover Advanced Logistics"},
        "Rover Resupply":  {"Recipe": {"Platium Bar": 6, "Laser Torch": 1, "Solar Panel": 1}, "Prereq": "Rover Advanced Logistics"},
        "Advanced Rover Resupply":  {"Recipe": {"Advanced Battery": 10, "Plasma Torch": 6, "Rhodium Bar": 25}, "Prereq": "Rover Resupply"},
        "Manager Training":  {"Recipe": {"Laser Torch": 1, "Steel Bar": 50}, "Prereq": "Telescope 6"},
        "Contract Manager":  {"Recipe": {"Titanium Bar": 25, "Circuit": 20}, "Prereq": "Manager Training"},
        "Advanced Contract Manager":  {"Recipe": {"Advanced Computer": 10, "Thermal Scanner": 10}, "Prereq": "Contract Manager"},
        "Advanced Manager Training":  {"Recipe": {"Advanced Computer": 2, "Advanced Battery": 10}, "Prereq": "Manager Training"},
        "Superior Manager Training":  {"Recipe": {"Rhodium Bar": 200}, "Prereq": "Advanced Manager Training"},
        "Specialist University":  {"Recipe": {"Inerton Alloy": 300, "Motor": 3}, "Prereq": "Advanced Manager Training"},
        "Advanced Specialist University":  {"Recipe": {"Accumulator": 2, "Scrith Allow": 100}, "Prereq": "Specialist University"},
        "Colonization":  {"Recipe": {"Copper Bar": 20, "Iron Bar": 10}, "Prereq": "Management"},
        "Colonization Scouting":  {"Recipe": {"Iron Nail": 15}, "Prereq": "Colonization"},
        "Colonization Advanced Scouting":  {"Recipe": {"Silver Bar": 60}, "Prereq": "Colonization Scouting"},
        "Colonization Superior Scouting":  {"Recipe": {"Diamond": 50000}, "Prereq": "Colonization Advanced Scouting"},
        "Colonization Efficiency":  {"Recipe": {"Silver Bar": 15, "Hammer": 10}, "Prereq": "Colonization"},
        "Colony Renegotiation":  {"Recipe": {"Bronze Bar": 100, "Hammer": 400}, "Prereq": "Colonization Efficiency"},
        "Colonization Advanced Efficiency":  {"Recipe": {"Steel Bar": 40, "Laser": 10}, "Prereq": "Colonization Efficiency"},
        "Colonization Superior Efficiency":  {"Recipe": {"Palladium Bar": 50, "Laser Torch": 15}, "Prereq": "Colonization Advanced Efficiency"},
        "Colony Tax Incentives":  {"Recipe": {"Aluminum Bar": 60}, "Prereq": ["Colonization Scouting","Colonization Efficiency"]},
        "Colony Advanced Tax Incentives":  {"Recipe": {"Bronze Bar": 60}, "Prereq": "Colony Tax Incentives"},
        "Colony Superior Tax Incentives":  {"Recipe": {"Palladium Bar": 60}, "Prereq": "Colony Advanced Tax Incentives"},
        "Rover":  {"Recipe": {"Copper Wire": 10}, "Prereq": "Asteroid Miner"},
        "Advanced Mining":  {"Recipe": {"Battery": 5, "Aluminum Bar": 20}, "Prereq": "Rover"},
        "Advanced Thrusters":  {"Recipe": {"Glass": 2, "Gold Bar": 10}, "Prereq": "Advanced Mining"},
        "Advanced Cargo Handling":  {"Recipe": {"Hammer": 5, "Silver Bar": 25}, "Prereq": "Advanced Mining"},
        "Superior Mining":  {"Recipe": {"Laser Torch": 10, "Platinum Bar": 25}, "Prereq": ["Advanced Thrusters","Advanced Cargo Handling"]},
        "Superior Thrusters":  {"Recipe": {"Advanced Battery": 4}, "Prereq": "Superior Mining"},
        "Superior Cargo Handling":  {"Recipe": {"Titanium Bar": 50}, "Prereq": "Superior Mining"},
#        "Smelter":  {"Recipe": {"": 1, "": 1}, "Prereq": ""},
#        "Smelter":  {"Recipe": {"": 1, "": 1}, "Prereq": ""},
#        "Smelter":  {"Recipe": {"": 1, "": 1}, "Prereq": ""},
#        "Smelter":  {"Recipe": {"": 1, "": 1}, "Prereq": ""},
#        "Smelter":  {"Recipe": {"": 1, "": 1}, "Prereq": ""},
#        "Smelter":  {"Recipe": {"": 1, "": 1}, "Prereq": ""},
    },
    "planets": {
        1: {"Name": "Balor", "BasePrice": 100, "Telescope": 0, "Resources": {"Copper": 100}, "Distance": 10, "Levels": {"Mining": 0, "Speed": 0, "Cargo": 0}},
        2: {"Name": "Drasta", "BasePrice": 200, "Telescope": 0, "Resources": {"Copper": 80, "Iron": 20}, "Distance": 12, "Levels": {"Mining": 0, "Speed": 0, "Cargo": 0}},
    }
}
BASE_MINING_RATE = 0.25
# ── persistence helpers ───────────────────────────────────────────────────────

def load_data() -> dict:
    if os.path.exists(DATA_FILE):
        try:
            with open(DATA_FILE, "r") as f:
                tempData = json.load(f)
        except Exception:
            pass
    else:
        tempData = json.loads(json.dumps(DEFAULT_DATA))   # deep copy
    
    # Ensure flags are present
    for category in ["ores", "alloys", "items"]:
        for i in tempData[category]:
            item = tempData[category][i]
            if "unlocked" not in item.keys():
                item["unlocked"] = False
            if "stars" not in item.keys():
                item["stars"] = 0
            if "market" not in item.keys():
                item["market"] = 0
            if "realPrice" not in item.keys():
                item["realPrice"] = item["base_price"]
    for p in tempData["projects"]:
        project = tempData["projects"][p]
        if "unlocked" not in project.keys():
            project["unlocked"] = False
        if "Researched" not in project.keys():
            project["Researched"] = False
    for p in tempData["planets"]:
        planet = tempData["planets"][p]
        if "colony" not in planet.keys():
            planet["colony"] = [1,1,1]
        if "probes" not in planet.keys():
            planet["probes"] = [1,1,1]
            
    return tempData


def save_data(data: dict) -> None:
    with open(DATA_FILE, "w") as f:
        json.dump(data, f, indent=2)

# ── calculation helpers ───────────────────────────────────────────────────────

def effective_price(name: str, data: dict) -> float:
    """Return realPrice (stars+market adjusted) for any resource."""
    for cat in ("ores", "alloys", "items"):
        if name in data[cat]:
            e = data[cat][name]
            return float(e.get("realPrice", e["base_price"]))
    return 0.0

def getRealPrice(basePrice: float, stars: int, market: int, category: str = "") -> float:
    """Sell price adjusted for stars and market level (-2..4).
    category is preserved for future per-category bonus multipliers.
    """
    marketVar = [0.33, 0.5, 1, 2, 3, 4, 5][market + 2]
    starVar   = 1.0 + 0.2 * stars
    # TODO: apply category-specific bonuses here
    return basePrice * marketVar * starVar


def market_chevrons(market: int) -> str:
    """▲▲▲ green for positive, ▼▼ red for negative, — for zero."""
    if market > 0:  return "▲" * market
    if market < 0:  return "▼" * abs(market)
    return "—"

def effective_time(name: str, data: dict) -> float:
    """Return the current effective sell price for any resource."""
    if name in data["alloys"]:
        return data["alloys"][name]["smelt_time"]
    elif name in data["items"]:
        return data["items"][name]["craft_time"]
    return 0.0

def total_smelt_time_of_recipe(name: str, category: str, data: dict) -> float:
    """Recursive sum of all alloy smelt_times needed for this recipe (raw seconds)."""
    entry = data[category][name]
    total = entry["smelt_time"] if category == "alloys" else 0.0
    for ingredient, qty in entry.get("recipe", {}).items():
        if ingredient in data["alloys"]:
            total += total_smelt_time_of_recipe(ingredient, "alloys", data) * qty
        elif ingredient in data["items"]:
            total += total_smelt_time_of_recipe(ingredient, "items", data) * qty
    return total


def total_craft_time_of_recipe(name: str, category: str, data: dict) -> float:
    """Recursive sum of all item craft_times needed for this recipe (raw seconds)."""
    entry = data[category][name]
    total = entry["craft_time"] if category == "items" else 0.0
    for ingredient, qty in entry.get("recipe", {}).items():
        if ingredient in data["alloys"]:
            total += total_craft_time_of_recipe(ingredient, "alloys", data) * qty
        elif ingredient in data["items"]:
            total += total_craft_time_of_recipe(ingredient, "items", data) * qty
    return total


def total_wall_time(smelt_raw: float, craft_raw: float,
                    smelters: int, crafters: int) -> float:
    """Wall-clock time: smelting and crafting run in parallel.
    Each pool is divided by the number of machines.
    Returns max of the two lanes (bottleneck), minimum 1 to avoid /0.
    """
    smelt_wall = smelt_raw / max(1, smelters)
    craft_wall = craft_raw / max(1, crafters)
    return max(smelt_wall, craft_wall, 1.0)
	
def ore_cost_of_recipe(recipe: dict, data: dict) -> float:
    """Recursively expand a recipe all the way down to raw ore value."""
    total = 0.0
    for ingredient, qty in recipe.items():
        # Is it an ore?
        if ingredient in data["ores"]:
            total += effective_price(ingredient, data) * qty
        # Is it an alloy?
        elif ingredient in data["alloys"]:
            sub = data["alloys"][ingredient]
            sub_ore = ore_cost_of_recipe(sub["recipe"], data)
            total += sub_ore * qty
        # Is it an item?
        elif ingredient in data["items"]:
            sub = data["items"][ingredient]
            sub_ore = ore_cost_of_recipe(sub["recipe"], data)
            total += sub_ore * qty
        else:
            # unknown – treat as zero
            pass
    return total


def direct_input_cost(recipe: dict, data: dict) -> float:
    """Value of immediate inputs at their current sell prices."""
    total = 0.0
    for ingredient, qty in recipe.items():
        total += effective_price(ingredient, data) * qty
    return total


def project_cost(recipe: dict, data: dict) -> float:
    """Value of project ingredients using sell prices (ore > alloy > item lookup)."""
    total = 0.0
    for ingredient, qty in recipe.items():
        total += effective_price(ingredient, data) * qty
    return total


def project_time(recipe: dict, data: dict,
                 smelters: int = 1, crafters: int = 1) -> float:
    """Total wall-clock time to produce all ingredients of a project recipe."""
    smelt_total = 0.0
    craft_total = 0.0
    for ingredient, qty in recipe.items():
        if ingredient in data["alloys"]:
            smelt_total += total_smelt_time_of_recipe(ingredient, "alloys", data) * qty
            craft_total += total_craft_time_of_recipe(ingredient, "alloys", data) * qty
        elif ingredient in data["items"]:
            smelt_total += total_smelt_time_of_recipe(ingredient, "items", data) * qty
            craft_total += total_craft_time_of_recipe(ingredient, "items", data) * qty
        # ores: no production time
    return total_wall_time(smelt_total, craft_total, smelters, crafters)


def project_prereq_met(prereqs, data: dict) -> bool:
    """
    prereqs can be:
      ""        -> always available
      "A"       -> project A must be Researched
      ["A","B"] -> project A OR project B must be Researched (either satisfies)
    """
    if not prereqs:
        return True
    projects = data.get("projects", {})
    if isinstance(prereqs, list):
        return any(projects.get(p, {}).get("Researched", False) for p in prereqs)
    return projects.get(prereqs, {}).get("Researched", False)


def analyze_recipe(name: str, category: str, data: dict,
                   smelters: int = 1, crafters: int = 1) -> dict:
    """Return a dict of metrics for one recipe."""
    entry    = data[category][name]
    recipe   = entry["recipe"]
    out_val  = effective_price(name, data)
    time_key = "smelt_time" if category == "alloys" else "craft_time"
    t        = entry.get(time_key, 1)

    smelt_raw  = total_smelt_time_of_recipe(name, category, data)
    craft_raw  = total_craft_time_of_recipe(name, category, data)
    wall_time  = total_wall_time(smelt_raw, craft_raw, smelters, crafters)

    direct_cost = direct_input_cost(recipe, data)
    ore_cost    = ore_cost_of_recipe(recipe, data)

    profit_vs_direct = out_val - direct_cost
    profit_vs_ore    = out_val - ore_cost

    vps_out       = out_val          / t
    vps_vs_direct = profit_vs_direct / t
    vps_vs_ore    = profit_vs_ore    / wall_time

    unlocked = bool(entry["unlocked"])

    return {
        "unlocked":         unlocked,
        "name":             name,
        "category":         category,
        "output_value":     out_val,
        "direct_cost":      direct_cost,
        "ore_cost":         ore_cost,
        "profit_direct":    profit_vs_direct,
        "profit_ore":       profit_vs_ore,
        "craft_time":       t,
        "smelt_raw":        smelt_raw,
        "craft_raw":        craft_raw,
        "total_time":       wall_time,
        "vps_output":       vps_out,
        "vps_profit_direct":vps_vs_direct,
        "vps_profit_ore":   vps_vs_ore,
    }


def analyze_all(data: dict, smelters: int = 1, crafters: int = 1) -> list:
    results = []
    for name in data["alloys"]:
        results.append(analyze_recipe(name, "alloys", data, smelters, crafters))
    for name in data["items"]:
        results.append(analyze_recipe(name, "items", data, smelters, crafters))
    return results
    
def mining_rate(level: int, bonus: float = 1) -> float:
    l = level - 1
    mining = bonus * (BASE_MINING_RATE + (0.1 * l) + (0.017 * (l ** 2)))
    return mining
    
def ship_speed(level: int, bonus: float = 1) -> float:
    l = level - 1
    speed = bonus * (1 + (0.2 * l) + ((l ** 2) / 75))
    return speed
    
def ship_cargo(level: int, bonus: float = 1) -> int:
    l = level - 1
    cargo = round(bonus * (5 + (2 * l) + (l ** 2)))
    return cargo
    

# ── number formatting ─────────────────────────────────────────────────────────
SUFFIXES = [
    (1e33, "D"),  (1e30, "N"),  (1e27, "O"),  (1e24, "Sp"),
    (1e21, "Sx"), (1e18, "Qi"), (1e15, "Q"),  (1e12, "T"),
    (1e9,  "B"),  (1e6,  "M"),  (1e3,  "K"),
]

def fmt(n: float, dp: int = 2) -> str:
    if n == 0:
        return "$0"
    neg = n < 0
    n = abs(n)
    for threshold, suffix in SUFFIXES:
        if n >= threshold:
            val = round(n / threshold, dp)
            return f"{'−' if neg else ''}${val:.1f}{suffix}"
    return f"{'−' if neg else ''}${round(n, dp):.2f}"

def get_price(inStr:str) -> float:
    if inStr == '':
        return 0
    n = float(re.search(r'[\d\.]+',inStr)[0])
    if inStr[-1] == 'k' or inStr[-1] == 'K':
        n = n * 1e3
    elif inStr[-1] == 'm' or inStr[-1] == 'M':
        n = n * 1e6
    elif inStr[-1] == 'b' or inStr[-1] == 'B':
        n = n * 1e9
    elif inStr[-1] == 't' or inStr[-1] == 'T':
        n = n * 1e12
    return n
       

# ── colours (must be defined before SpreadsheetGrid uses them as defaults) ────
DARK_BG     = "#1e1e2e"
PANEL_BG    = "#2a2a3e"
ACCENT      = "#7c6af7"
ACCENT2     = "#56cfb2"
TEXT        = "#e0e0f0"
MUTED       = "#888899"
GOOD        = "#56cfb2"
BAD         = "#e05c6a"
WARNING     = "#f0c040"
ROW_A       = "#252538"
ROW_B       = "#2a2a3e"
ENTRY_BG    = "#33334a"
BTN_BG      = "#4a3fbf"
BTN_HOVER   = "#5a4fcf"

REG_FONT = ("Segoe UI", 14)
BOLD_FONT = ("Segoe UI", 14, "bold")
FOOTER_FONT = ("Segoe UI", 9)


# ─────────────────────────────────────────────────────────────────────────────
# Spreadsheet grid widget
# ─────────────────────────────────────────────────────────────────────────────

class SpreadsheetGrid(ttk.Frame):
    """
    A lightweight inline-editable spreadsheet built from a Canvas + Entry overlay.
    Clicking a cell opens an Entry widget directly on top of it.
    Tab / Enter / arrow keys navigate between cells.
    Changes are committed on focus-out and propagated via on_change().
    """

    ROW_H   = 24
    HDR_H   = 26
    PAD_X   = 6

    def __init__(self, master, columns, accent=ACCENT, on_change=None,
                 dropdown_cols=None, checkbox_cols=None,
                 slider_cols=None, readonly_cols=None,
                 extra_widgets=None, **kw):
        """
        columns       : list of (header_label, width_px, anchor)
        on_change     : callable fired after any cell edit
        dropdown_cols : dict of {col_index: callable_returning_list}
        checkbox_cols : set of col_index values rendered as ☑/☐ toggles
        slider_cols   : dict of {col_index: (min_val, max_val)} integer sliders
        readonly_cols : set of col_index values that cannot be edited
        """
        super().__init__(master, style="Dark.TFrame", **kw)
        self._cols          = columns
        self._accent        = accent
        self._on_change     = on_change or (lambda: None)
        self._dropdown_cols = dropdown_cols or {}
        self._checkbox_cols = set(checkbox_cols or [])
        self._slider_cols   = slider_cols   or {}
        self._readonly_cols = set(readonly_cols or [])
        self._extra_widgets = extra_widgets or []
        self._data          = []
        self._sel           = None
        self._entry         = None
        self._entry_var     = tk.StringVar()

        self._build()

    # ── build ─────────────────────────────────────────────────────────────────
    def _build(self):
        # toolbar (extra_widgets injected by caller sit here)
        tb = ttk.Frame(self, style="Dark.TFrame")
        tb.pack(fill="x", pady=(0, 4))
        for w in (self._extra_widgets or []):
            w(tb)   # callable receives the toolbar frame
        self._status = ttk.Label(tb, text="Click a cell to edit", style="Muted.TLabel")
        self._status.pack(side="right", padx=8)

        # canvas + scrollbars
        cf = ttk.Frame(self, style="Dark.TFrame")
        cf.pack(fill="both", expand=True)

        self._canvas = tk.Canvas(cf, bg=DARK_BG, highlightthickness=0)
        vsb = ttk.Scrollbar(cf, orient="vertical",   command=self._canvas.yview)
        hsb = ttk.Scrollbar(cf, orient="horizontal",  command=self._canvas.xview)
        self._canvas.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        self._canvas.grid(row=0, column=0, sticky="nsew")
        cf.rowconfigure(0, weight=1)
        cf.columnconfigure(0, weight=1)

        self._canvas.bind("<Button-1>",     self._on_click)
        self._canvas.bind("<Configure>",    lambda e: self._redraw())
        self._canvas.bind("<MouseWheel>",   lambda e: self._canvas.yview_scroll(-1*(e.delta//120), "units"))
        self._canvas.bind("<Button-4>",     lambda e: self._canvas.yview_scroll(-1, "units"))
        self._canvas.bind("<Button-5>",     lambda e: self._canvas.yview_scroll(1, "units"))

    # ── total grid dimensions ─────────────────────────────────────────────────
    def _total_width(self):
        return sum(w for _, w, _ in self._cols) + 2

    def _col_x(self, col):
        return sum(self._cols[i][1] for i in range(col))

    # ── drawing ───────────────────────────────────────────────────────────────
    def _redraw(self):
        c = self._canvas
        c.delete("all")
        nrows = len(self._data)
        ncols = len(self._cols)
        H     = self.ROW_H
        HDR   = self.HDR_H

        total_h = HDR + nrows * H + 2
        total_w = self._total_width()
        c.configure(scrollregion=(0, 0, total_w, total_h))

        # header background
        c.create_rectangle(0, 0, total_w, HDR, fill=PANEL_BG, outline="")

        x = 0
        for ci, (label, w, anchor) in enumerate(self._cols):
            # header cell
            c.create_rectangle(x, 0, x+w, HDR, fill=PANEL_BG, outline=DARK_BG, width=1)
            c.create_text(x + self.PAD_X, HDR//2, text=label,
                          anchor="w", fill=self._accent,
                          font=("Segoe UI", 11, "bold"))
            #c.create_text(x + self.PAD_X, HDR//2, text=label,
            #              anchor=anchor, fill=self._accent,
            #              font=("Segoe UI", 11, "bold"))
            x += w

        # data rows
        for ri, row in enumerate(self._data):
            y = HDR + ri * H
            bg = ROW_A if ri % 2 == 0 else ROW_B
            # highlight selected row
            if self._sel and self._sel[0] == ri:
                bg = "#3a3a5a"

            x = 0
            for ci, (_, w, a) in enumerate(self._cols):
                cell_bg = bg
                if self._sel == (ri, ci):
                    cell_bg = "#4a3f7f"
                c.create_rectangle(x, y, x+w, y+H, fill=cell_bg, outline="#333348", width=1)
                val = row[ci] if ci < len(row) else ""
                if ci in self._checkbox_cols:
                    # Draw a checkbox glyph centred in the cell
                    checked = str(val).lower() in ("true", "1", "yes")
                    glyph = "☑" if checked else "☐"
                    glyph_color = self._accent if checked else MUTED
                    c.create_text(x + w//2, y + H//2, text=glyph,
                                  anchor="center", fill=glyph_color,
                                  font=("Segoe UI", 13))
                elif ci in self._slider_cols:
                    # Draw chevron indicator for market slider
                    try:
                        mv = int(float(str(val)))
                    except (ValueError, TypeError):
                        mv = 0
                    if mv > 0:
                        glyph, color = "▲" * mv, GOOD
                    elif mv < 0:
                        glyph, color = "▼" * abs(mv), BAD
                    else:
                        glyph, color = "—", MUTED
                    c.create_text(x + self.PAD_X, y + H//2,
                                  text=glyph, anchor="w",
                                  fill=color, font=("Segoe UI", 11))
                elif ci in self._readonly_cols:
                    # Read-only: draw with muted colour
                    tx = (x + w - self.PAD_X) if a != "w" else (x + self.PAD_X)
                    c.create_text(tx, y + H//2, text=str(val),
                                  anchor=a, fill=MUTED, font=REG_FONT)
                elif val != "" or self._sel != (ri, ci):
                    if a == "w":
                        c.create_text(x + self.PAD_X, y + H//2, text=str(val),
                                  anchor=a, fill=TEXT,
                                  font=REG_FONT)
                        
                    else:
                        c.create_text(x + w - self.PAD_X, y + H//2, text=str(val),
                                  anchor=a, fill=TEXT,
                                  font=REG_FONT)
                x += w

        # reposition active entry if visible
        if self._entry and self._sel:
            self._position_entry(*self._sel)

    # ── cell editing ──────────────────────────────────────────────────────────
    def _on_click(self, event):
        cx = self._canvas.canvasx(event.x)
        cy = self._canvas.canvasy(event.y)
        HDR = self.HDR_H
        if cy < HDR:
            return
        ri = int((cy - HDR) // self.ROW_H)
        if ri >= len(self._data):
            return
        # find column
        x = 0
        for ci, (_, w, _) in enumerate(self._cols):
            if x <= cx < x + w:
                if ci in self._checkbox_cols:
                    self._toggle_checkbox(ri, ci)
                elif ci in self._readonly_cols:
                    pass  # not editable
                elif ci in self._slider_cols:
                    self._open_slider(ri, ci)
                else:
                    self._open_cell(ri, ci)
                return
            x += w

    def _toggle_checkbox(self, ri, ci):
        """Flip the boolean value in a checkbox cell immediately."""
        self._commit_entry()
        while len(self._data[ri]) <= ci:
            self._data[ri].append("")
        cur = str(self._data[ri][ci]).lower() in ("true", "1", "yes")
        self._data[ri][ci] = "True" if not cur else "False"
        self._sel = (ri, ci)
        self._redraw()
        self._on_change()

    def _open_slider(self, ri, ci):
        """Overlay a horizontal Scale widget on a slider cell."""
        self._commit_entry()
        self._sel = (ri, ci)
        self._redraw()
        lo, hi = self._slider_cols[ci]
        raw = self._data[ri][ci] if ci < len(self._data[ri]) else 0
        try:
            ival = int(float(str(raw)))
        except (ValueError, TypeError):
            ival = 0
        sv = tk.IntVar(value=ival)

        def _slide(*_):
            while len(self._data[ri]) <= ci:
                self._data[ri].append("")
            self._data[ri][ci] = str(sv.get())
            self._redraw()
            self._on_change()

        scale = tk.Scale(self._canvas, from_=lo, to=hi,
                         orient="horizontal", variable=sv, command=_slide,
                         bg=ENTRY_BG, fg=TEXT, troughcolor=PANEL_BG,
                         highlightthickness=0, bd=0,
                         activebackground=self._accent,
                         sliderrelief="flat", showvalue=True,
                         font=("Segoe UI", 8))
        scale.bind("<FocusOut>", lambda e: self._dismiss_slider(scale))
        scale.bind("<Escape>",   lambda e: self._dismiss_slider(scale))
        self._entry = scale
        self._position_entry(ri, ci)
        scale.focus_set()
        self._status.configure(text=f"Row {ri+1} — drag or use ← → arrow keys")

    def _dismiss_slider(self, scale):
        if self._entry is scale:
            self._entry.destroy()
            self._entry = None
        self._sel = None
        self._redraw()

    def _open_cell(self, ri, ci):
        self._commit_entry()
        self._sel = (ri, ci)
        self._redraw()

        val = self._data[ri][ci] if ci < len(self._data[ri]) else ""
        self._entry_var.set(str(val))

        if ci in self._dropdown_cols:
            # Combobox (dropdown) cell
            choices = [""] + list(self._dropdown_cols[ci]())
            ent = ttk.Combobox(self._canvas, textvariable=self._entry_var,
                               values=choices, state="readonly",
                               font=REG_FONT)
            ent.option_add("*TCombobox*Listbox.background",      PANEL_BG)
            ent.option_add("*TCombobox*Listbox.foreground",      TEXT)
            ent.option_add("*TCombobox*Listbox.selectBackground", self._accent)
            ent.bind("<<ComboboxSelected>>", lambda e: self._nav(ri, ci, 0, 1))
            ent.bind("<Return>",    lambda e: self._nav(ri, ci, 0, 1))
            ent.bind("<Tab>",       lambda e: (self._nav(ri, ci, 0, 1), "break")[1])
            ent.bind("<Shift-Tab>", lambda e: (self._nav(ri, ci, 0, -1), "break")[1])
            ent.bind("<Escape>",    lambda e: self._cancel_entry())
            ent.bind("<FocusOut>",  lambda e: self._commit_entry())
            self._entry = ent
            self._position_entry(ri, ci)
            ent.focus_set()
            ent.after(50, ent.event_generate, "<Button-1>")
        else:
            # plain Entry cell
            ent = tk.Entry(self._canvas, textvariable=self._entry_var,
                           bg=ENTRY_BG, fg=TEXT, insertbackground=TEXT,
                           relief="flat", font=REG_FONT,
                           highlightthickness=1, highlightcolor=self._accent,
                           highlightbackground=self._accent)
            ent.bind("<Return>",    lambda e: self._nav(ri, ci, 1, 0))
            ent.bind("<Tab>",       lambda e: (self._nav(ri, ci, 0, 1), "break")[1])
            ent.bind("<Shift-Tab>", lambda e: (self._nav(ri, ci, 0, -1), "break")[1])
            ent.bind("<Up>",        lambda e: self._nav(ri, ci, -1, 0))
            ent.bind("<Down>",      lambda e: self._nav(ri, ci, 1, 0))
            ent.bind("<Escape>",    lambda e: self._cancel_entry())
            ent.bind("<FocusOut>",  lambda e: self._commit_entry())
            self._entry = ent
            self._position_entry(ri, ci)
            ent.focus_set()
            ent.select_range(0, "end")

        self._status.configure(
            text=f"Row {ri+1}, Col {ci+1} — " +
                 ("choose from list" if ci in self._dropdown_cols
                  else "Tab/Enter/arrows to navigate, Esc to cancel"))

    def _position_entry(self, ri, ci):
        if not self._entry:
            return
        HDR = self.HDR_H
        x0 = self._col_x(ci)
        y0 = HDR + ri * self.ROW_H
        w  = self._cols[ci][1]
        H  = self.ROW_H
        # offset by canvas scroll
        ox = self._canvas.canvasx(0)
        oy = self._canvas.canvasy(0)
        self._entry.place(x=x0 - ox, y=y0 - oy, width=w, height=H)

    def _commit_entry(self):
        if self._entry is None or self._sel is None:
            return
        # Scale widgets write through on every drag; just destroy
        if isinstance(self._entry, tk.Scale):
            self._entry.destroy()
            self._entry = None
            self._sel   = None
            self._redraw()
            return
        ri, ci = self._sel
        val = self._entry_var.get()
        while len(self._data[ri]) <= ci:
            self._data[ri].append("")
        self._data[ri][ci] = val
        self._entry.destroy()
        self._entry = None
        self._redraw()
        self._on_change()

    def _cancel_entry(self):
        if self._entry:
            self._entry.destroy()
            self._entry = None
        self._sel = None
        self._redraw()

    def _nav(self, ri, ci, dr, dc):
        self._commit_entry()
        nr = ri + dr
        nc = ci + dc
        ncols = len(self._cols)
        nrows = len(self._data)
        if nc >= ncols:
            nc = 0; nr += 1
        if nc < 0:
            nc = ncols - 1; nr -= 1
        nr = max(0, min(nr, nrows - 1))
        nc = max(0, min(nc, ncols - 1))
        self._open_cell(nr, nc)

    # ── row operations ────────────────────────────────────────────────────────
    def _add_row(self):
        self._commit_entry()
        self._data.append([""] * len(self._cols))
        self._sel = (len(self._data) - 1, 0)
        self._redraw()
        self._open_cell(len(self._data) - 1, 0)
        # scroll to bottom
        self._canvas.yview_moveto(1.0)
        self._on_change()

    def _del_row(self):
        self._commit_entry()
        if not self._data:
            return
        if self._sel:
            ri = self._sel[0]
        else:
            ri = len(self._data) - 1
        if messagebox.askyesno("Delete Row", f"Delete row {ri+1}?"):
            del self._data[ri]
            self._sel = None
            self._redraw()
            self._on_change()

    def _move_up(self):
        self._commit_entry()
        if not self._sel:
            return
        ri = self._sel[0]
        if ri <= 0:
            return
        self._data[ri-1], self._data[ri] = self._data[ri], self._data[ri-1]
        self._sel = (ri-1, self._sel[1])
        self._redraw()
        self._on_change()

    def _move_down(self):
        self._commit_entry()
        if not self._sel:
            return
        ri = self._sel[0]
        if ri >= len(self._data) - 1:
            return
        self._data[ri+1], self._data[ri] = self._data[ri], self._data[ri+1]
        self._sel = (ri+1, self._sel[1])
        self._redraw()
        self._on_change()

    # ── public API ────────────────────────────────────────────────────────────
    def append_row(self, values):
        row = [str(v) if v != "" else "" for v in values]
        # pad/trim to column count
        ncols = len(self._cols)
        row = row[:ncols] + [""] * max(0, ncols - len(row))
        self._data.append(row)
        self._redraw()

    def get_rows(self):
        """Return current data as list of lists of strings."""
        return [list(r) for r in self._data]

    def clear(self):
        self._data.clear()
        self._sel  = None
        self._entry = None
        self._redraw()


# ─────────────────────────────────────────────────────────────────────────────
# GUI
# ─────────────────────────────────────────────────────────────────────────────

COL_DEFS = [
    ("Name",           "name",              180, "w"),
    ("Type",           "category",           60, "center"),
    ("Output $",       "output_value",       120, "e"),
    ("Input Cost",     "direct_cost",        120, "e"),
    ("Ore Cost",       "ore_cost",           120, "e"),
    ("Profit/Input",   "profit_direct",      120, "e"),
    ("Profit/Ore",     "profit_ore",         120, "e"),
    ("Time(s)",        "craft_time",          90, "center"),
    ("Smelt Time",     "smelt_raw",           90, "center"),
    ("Craft Time",     "craft_raw",           90, "center"),
    ("Total Time",     "total_time",          90, "center"),
    ("$/s Output",     "vps_output",         120, "e"),
    ("$/s vs Input",   "vps_profit_direct",  120, "e"),
    ("$/s vs Ore",     "vps_profit_ore",     120, "e"),
]


class App(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title("Idle Planet Miner – Recipe Calculator")
        self.configure(bg=DARK_BG)
        self.minsize(1200, 700)
        self.data = load_data()

        self._smelters = tk.IntVar(value=1)
        self._crafters = tk.IntVar(value=1)
        self._build_styles()
        self._build_ui()
        self._refresh_table()

    # ── styles ────────────────────────────────────────────────────────────────
    def _build_styles(self):
        s = ttk.Style(self)
        s.theme_use("clam")

        s.configure("Dark.TFrame",       background=DARK_BG)
        s.configure("Panel.TFrame",      background=PANEL_BG)
        s.configure("Dark.TLabel",       background=DARK_BG,   foreground=TEXT)
        s.configure("Panel.TLabel",      background=PANEL_BG,  foreground=TEXT)
        s.configure("Muted.TLabel",      background=DARK_BG,   foreground=MUTED, font=REG_FONT)
        s.configure("Title.TLabel",      background=DARK_BG,   foreground=ACCENT, font=("Segoe UI", 16, "bold"))
        s.configure("Accent.TLabel",     background=PANEL_BG,  foreground=ACCENT2)
        s.configure("Dark.TButton",      background=BTN_BG,    foreground=TEXT, font=REG_FONT, borderwidth=0, focusthickness=0)
        s.map("Dark.TButton",            background=[("active", BTN_HOVER)])
        s.configure("Dark.TEntry",       fieldbackground=ENTRY_BG, foreground=TEXT, insertcolor=TEXT)
        s.configure("Dark.TCombobox",    fieldbackground=ENTRY_BG, foreground=TEXT, background=PANEL_BG)
        s.map("Dark.TCombobox",          fieldbackground=[("readonly", ENTRY_BG)])
        s.configure("Dark.TNotebook",    background=DARK_BG,  tabmargins=[2, 5, 2, 0])
        s.configure("Dark.TNotebook.Tab",background=PANEL_BG, foreground=MUTED, padding=[12, 4])
        s.map("Dark.TNotebook.Tab",      background=[("selected", DARK_BG)],
                                         foreground=[("selected", ACCENT)])

        s.configure("Treeview",
                     background=ROW_A, fieldbackground=ROW_A,
                     foreground=TEXT, rowheight=28, font=REG_FONT)
        s.configure("Treeview.Heading",
                     background=PANEL_BG, foreground=ACCENT,
                     font=REG_FONT, relief="flat")
        s.map("Treeview",
              background=[("selected", ACCENT)],
              foreground=[("selected", "#ffffff")])
        s.map("Treeview.Heading", background=[("active", BTN_BG)])

    # ── main UI ───────────────────────────────────────────────────────────────
    def _build_ui(self):
        # header
        hdr = ttk.Frame(self, style="Dark.TFrame", padding=(16, 10))
        hdr.pack(fill="x")
        ttk.Label(hdr, text="⛏  Idle Planet Miner", style="Title.TLabel").pack(side="left")
        ttk.Label(hdr, text="Recipe Value Calculator", style="Muted.TLabel").pack(side="left", padx=(8, 0), pady=(6, 0))
        ttk.Button(hdr, text="💾  Save", style="Dark.TButton",
                   command=self._save).pack(side="right", padx=4)
        ttk.Button(hdr, text="↺  Reset Defaults", style="Dark.TButton",
                   command=self._reset_defaults).pack(side="right", padx=4)
        ttk.Button(hdr, text="🌌  Sell Galaxy", style="Dark.TButton",
                   command=self._sell_galaxy).pack(side="right", padx=4)

        nb = ttk.Notebook(self, style="Dark.TNotebook")
        nb.pack(fill="both", expand=True, padx=12, pady=(0, 12))

        self._tab_dashboard(nb)
        self._tab_ores(nb)
        self._tab_alloys(nb)
        self._tab_items(nb)
        self._tab_projects(nb)

    # ── tab: dashboard ────────────────────────────────────────────────────────
    def _tab_dashboard(self, nb):
        frame = ttk.Frame(nb, style="Dark.TFrame")
        nb.add(frame, text="📊  Dashboard")

        # filter row
        flt = ttk.Frame(frame, style="Dark.TFrame", padding=(8, 6))
        flt.pack(fill="x")

        ttk.Label(flt, text="Show:", style="Dark.TLabel").pack(side="left", padx=(0, 6))
        self._filter_var = tk.StringVar(value="All")
        for val in ("All", "Alloys", "Items"):
            ttk.Radiobutton(flt, text=val, variable=self._filter_var, value=val,
                            command=self._refresh_table,
                            style="Dark.TLabel").pack(side="left", padx=4)

        ttk.Label(flt, text="Sort by:", style="Dark.TLabel").pack(side="left", padx=(20, 6))
        self._sort_var = tk.StringVar(value="vps_profit_ore")
        sort_opts = [(c[0], c[1]) for c in COL_DEFS if c[1] not in ("name", "category")]
        sort_combo = ttk.Combobox(flt, textvariable=self._sort_var,
                                  values=[o[1] for o in sort_opts],
                                  state="readonly", width=20, style="Dark.TCombobox")
        sort_combo.pack(side="left")
        sort_combo.bind("<<ComboboxSelected>>", lambda _: self._refresh_table())

        ttk.Label(flt, text="↑ higher = better", style="Muted.TLabel").pack(side="left", padx=6)
        ttk.Button(flt, text="⟳ Recalculate", style="Dark.TButton",
                   command=self._refresh_table).pack(side="right", padx=4)

        # tree
        tree_frame = ttk.Frame(frame, style="Dark.TFrame")
        tree_frame.pack(fill="both", expand=True, padx=8, pady=(0, 8))

        cols = [c[1] for c in COL_DEFS]
        self.tree = ttk.Treeview(tree_frame, columns=cols, show="headings", selectmode="browse")

        for label, key, width, anchor in COL_DEFS:
            self.tree.heading(key, text=label,
                              command=lambda k=key: self._sort_by(k))
            self.tree.column(key, width=width, anchor=anchor, stretch=False)

        vsb = ttk.Scrollbar(tree_frame, orient="vertical", command=self.tree.yview)
        hsb = ttk.Scrollbar(tree_frame, orient="horizontal", command=self.tree.xview)
        self.tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self.tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        tree_frame.rowconfigure(0, weight=1)
        tree_frame.columnconfigure(0, weight=1)

        self.tree.tag_configure("row_a",  background=ROW_A)
        self.tree.tag_configure("row_b",  background=ROW_B)
        self.tree.tag_configure("alloy",  foreground=ACCENT2)
        self.tree.tag_configure("item",   foreground="#c0a0ff")
        self.tree.tag_configure("bad",    foreground=BAD)

        # legend / footer
        leg = ttk.Frame(frame, style="Dark.TFrame", padding=(8, 2))
        leg.pack(fill="x")
        ttk.Label(leg, text="● Alloys (smelted)", foreground=ACCENT2,
                  background=DARK_BG, font=FOOTER_FONT).pack(side="left", padx=8)
        ttk.Label(leg, text="● Items (crafted)", foreground="#c0a0ff",
                  background=DARK_BG, font=FOOTER_FONT).pack(side="left", padx=8)
        ttk.Label(leg, text="● Negative profit", foreground=BAD,
                  background=DARK_BG, font=FOOTER_FONT).pack(side="left", padx=8)
        ttk.Label(leg,
                  text="Tip: $/s vs Ore = profit per second if you sold raw ore instead",
                  style="Muted.TLabel").pack(side="right", padx=8)

    # ── tab: ores ─────────────────────────────────────────────────────────────
    def _tab_ores(self, nb):
        frame = ttk.Frame(nb, style="Dark.TFrame", padding=8)
        nb.add(frame, text="🪨  Ores")
        cols = [
            ("Unlocked",       80, "w"),
            ("Name",          150, "w"),
            ("Base Price ($)", 100, "e"),
            ("Stars",          60, "e"),
            ("Market",        110, "w"),
            ("Real Price ($)", 110, "e"),
        ]
        grid = SpreadsheetGrid(frame, cols, accent=ACCENT,
                               on_change=lambda: self._commit_ores(grid),
                               checkbox_cols={0},
                               slider_cols={4: (-2, 4)},
                               readonly_cols={5})
        grid.pack(fill="both", expand=True)
        for name, entry in self.data["ores"].items():
            realPrice = getRealPrice(entry["base_price"], entry["stars"], entry["market"], "ores")
            grid.append_row([entry.get("unlocked", False), name, fmt(entry["base_price"]),
                             entry["stars"], entry["market"], fmt(realPrice)])
        self._ore_grid = grid

    def _commit_ores(self, grid):
        new_ores = {}
        for i, row in enumerate(grid._data):
            name = str(row[1]).strip()
            if not name:
                continue
            unlocked = str(row[0]).lower() in ("true", "1", "yes")
            try:
                price = get_price(row[2])
            except (ValueError, IndexError):
                price = 0.0
            try:    stars  = int(float(row[3]))
            except: stars  = 0
            try:    market = int(float(row[4]))
            except: market = 0
            rp = getRealPrice(price, stars, market, "ores")
            new_ores[name] = {"base_price": price, "unlocked": unlocked,
                              "stars": stars, "market": market, "realPrice": rp}
            # write back into grid._data so the canvas redraws correctly
            row[2] = fmt(price)
            row[5] = fmt(rp)
        self.data["ores"] = new_ores
        save_data(self.data)
        self._refresh_table()

    # ── tab: alloys ───────────────────────────────────────────────────────────
    def _tab_alloys(self, nb):
        frame = ttk.Frame(nb, style="Dark.TFrame", padding=8)
        nb.add(frame, text="⚙️  Alloys")
        # 0=Unlocked 1=Name 2=BasePrice 3=SmeltTime 4=Stars 5=Market 6=RealPrice 7..=recipe
        cols = [
            ("Unlocked",       80,  "w"),
            ("Name",          160,  "w"),
            ("Base Price ($)", 100,  "e"),
            ("Smelt Time (s)", 100,  "e"),
            ("Stars",           60,  "e"),
            ("Market",         110,  "w"),
            ("Real Price ($)", 110,  "e"),
            ("Ingredient 1",   150,  "w"),
            ("Qty 1",           60,  "e"),
            ("Ingredient 2",   150,  "w"),
            ("Qty 2",           60,  "e"),
            ("Ingredient 3",   150,  "w"),
            ("Qty 3",           60,  "e"),
        ]
        def alloy_ingredients():
            return sorted(self.data["ores"].keys())
        dropdown_cols = {7: alloy_ingredients, 9: alloy_ingredients, 11: alloy_ingredients}
        def _smelter_widget(tb):
            ttk.Label(tb, text="Smelters:", style="Muted.TLabel").pack(side="left", padx=(4, 2))
            ttk.Button(tb, text="−", style="Dark.TButton", width=2,
                       command=lambda: (self._smelters.set(max(0, self._smelters.get()-1)),
                                        self._refresh_table())).pack(side="left")
            ttk.Label(tb, textvariable=self._smelters, style="Dark.TLabel",
                      width=3, anchor="center").pack(side="left")
            ttk.Button(tb, text="+", style="Dark.TButton", width=2,
                       command=lambda: (self._smelters.set(self._smelters.get()+1),
                                        self._refresh_table())).pack(side="left")
        grid = SpreadsheetGrid(frame, cols, accent=ACCENT2,
                               on_change=lambda: self._commit_alloys(grid),
                               dropdown_cols=dropdown_cols,
                               checkbox_cols={0},
                               slider_cols={5: (-2, 4)},
                               readonly_cols={6},
                               extra_widgets=[_smelter_widget])
        grid.pack(fill="both", expand=True)
        for name, entry in self.data["alloys"].items():
            bp    = entry.get("base_price", 0)
            stars = entry.get("stars", 0)
            mkt   = entry.get("market", 0)
            rp    = getRealPrice(bp, stars, mkt)
            recipe_items = list(entry.get("recipe", {}).items())
            row = [entry.get("unlocked", False), name,
                   fmt(bp), f"{int(entry.get('smelt_time', 60))}s",
                   stars, mkt, fmt(rp)]
            for i in range(3):
                if i < len(recipe_items):
                    row += [recipe_items[i][0], int(recipe_items[i][1])]
                else:
                    row += ["", ""]
            grid.append_row(row)
        self._alloy_grid = grid

    def _commit_alloys(self, grid):
        new_alloys = {}
        for row in grid._data:   # direct reference so writes update the canvas
            name = str(row[1]).strip()
            if not name:
                continue
            unlocked = str(row[0]).lower() in ("true", "1", "yes")
            try:
                price = get_price(row[2])
            except (ValueError, IndexError):
                price = 0.0
            try:
                t = float(re.search(r'\d+', row[3])[0])
            except (TypeError, ValueError, IndexError):
                t = 999999
            try:    stars  = int(float(row[4]))
            except: stars  = 0
            try:    market = int(float(row[5]))
            except: market = 0
            rp = getRealPrice(price, stars, market, "alloys")
            row[6] = fmt(rp)   # write directly into grid._data → redraws correctly
            recipe = {}
            for slot in range(3):
                base = 7 + slot * 2
                try:
                    ing = str(row[base]).strip()
                    qty = float(row[base + 1])
                    if ing:
                        recipe[ing] = qty
                except (ValueError, IndexError):
                    pass
            new_alloys[name] = {"base_price": price, "smelt_time": t,
                                "recipe": recipe, "unlocked": unlocked,
                                "stars": stars, "market": market, "realPrice": rp}
        self.data["alloys"] = new_alloys
        save_data(self.data)
        self._refresh_table()

    # ── tab: items ────────────────────────────────────────────────────────────
    def _tab_items(self, nb):
        frame = ttk.Frame(nb, style="Dark.TFrame", padding=8)
        nb.add(frame, text="📦  Items")
        # 0=Unlocked 1=Name 2=BasePrice 3=CraftTime 4=Stars 5=Market 6=RealPrice 7..=recipe
        cols = [
            ("Unlocked",       80,  "w"),
            ("Name",          160,  "w"),
            ("Base Price ($)", 130,  "e"),
            ("Craft Time",     80,  "e"),
            ("Stars",           60,  "e"),
            ("Market",         110,  "w"),
            ("Real Price ($)", 110,  "e"),
            ("Ingredient 1",   150,  "w"),
            ("Qty 1",           60,  "e"),
            ("Ingredient 2",   150,  "w"),
            ("Qty 2",           60,  "e"),
            ("Ingredient 3",   150,  "w"),
            ("Qty 3",           60,  "e"),
        ]
        def item_ingredients():
            return sorted(list(self.data["ores"].keys()) +
                          list(self.data["alloys"].keys()) +
                          list(self.data["items"].keys()))
        dropdown_cols = {7: item_ingredients, 9: item_ingredients, 11: item_ingredients}
        def _crafter_widget(tb):
            ttk.Label(tb, text="Crafters:", style="Muted.TLabel").pack(side="left", padx=(4, 2))
            ttk.Button(tb, text="−", style="Dark.TButton", width=2,
                       command=lambda: (self._crafters.set(max(0, self._crafters.get()-1)),
                                        self._refresh_table())).pack(side="left")
            ttk.Label(tb, textvariable=self._crafters, style="Dark.TLabel",
                      width=3, anchor="center").pack(side="left")
            ttk.Button(tb, text="+", style="Dark.TButton", width=2,
                       command=lambda: (self._crafters.set(self._crafters.get()+1),
                                        self._refresh_table())).pack(side="left")
        grid = SpreadsheetGrid(frame, cols, accent="#c0a0ff",
                               on_change=lambda: self._commit_items(grid),
                               dropdown_cols=dropdown_cols,
                               checkbox_cols={0},
                               slider_cols={5: (-2, 4)},
                               readonly_cols={6},
                               extra_widgets=[_crafter_widget])
        grid.pack(fill="both", expand=True)
        for name, entry in self.data["items"].items():
            bp    = entry.get("base_price", 0)
            stars = entry.get("stars", 0)
            mkt   = entry.get("market", 0)
            rp    = getRealPrice(bp, stars, mkt)
            recipe_items = list(entry.get("recipe", {}).items())
            row = [entry.get("unlocked", False), name,
                   fmt(bp), f"{int(entry.get('craft_time', 120))}s",
                   stars, mkt, fmt(rp)]
            for i in range(3):
                if i < len(recipe_items):
                    row += [recipe_items[i][0], recipe_items[i][1]]
                else:
                    row += ["", ""]
            grid.append_row(row)
        self._item_grid = grid

    def _commit_items(self, grid):
        new_items = {}
        for row in grid._data:   # direct reference so writes update the canvas
            name = str(row[1]).strip()
            if not name:
                continue
            unlocked = str(row[0]).lower() in ("true", "1", "yes")
            try:
                price = get_price(row[2])
            except (ValueError, IndexError):
                price = 0
            try:
                t = float(re.search(r'\d+', row[3])[0])
            except (TypeError, ValueError, IndexError):
                t = 9999999
            try:    stars  = int(float(row[4]))
            except: stars  = 0
            try:    market = int(float(row[5]))
            except: market = 0
            rp = getRealPrice(price, stars, market, "items")
            row[6] = fmt(rp)   # write directly into grid._data → redraws correctly
            recipe = {}
            for slot in range(3):
                base = 7 + slot * 2
                try:
                    ing = str(row[base]).strip()
                    qty = int(row[base + 1])
                    if ing:
                        recipe[ing] = qty
                except (ValueError, IndexError):
                    pass
            new_items[name] = {"base_price": price, "craft_time": t,
                               "recipe": recipe, "unlocked": unlocked,
                               "stars": stars, "market": market, "realPrice": rp}
        self.data["items"] = new_items
        save_data(self.data)
        self._refresh_table()

    # ── tab: projects ────────────────────────────────────────────────────────────
    def _tab_projects(self, nb):
        frame = ttk.Frame(nb, style="Dark.TFrame", padding=8)
        nb.add(frame, text="🧪 Projects")

        # ── toolbar / sort controls ───────────────────────────────────────────
        tb = ttk.Frame(frame, style="Dark.TFrame")
        tb.pack(fill="x", pady=(0, 6))
        ttk.Label(tb, text="Sort by:", style="Dark.TLabel").pack(side="left", padx=(0, 6))
        self._proj_sort_var = tk.StringVar(value="name")
        for val, label in (("name", "Name"), ("cost", "Cost"), ("time", "Time")):
            ttk.Radiobutton(tb, text=label, variable=self._proj_sort_var, value=val,
                            command=self._refresh_projects,
                            style="Dark.TLabel").pack(side="left", padx=4)
        ttk.Button(tb, text="⟳ Refresh", style="Dark.TButton",
                   command=self._refresh_projects).pack(side="left", padx=8)
        ttk.Label(tb,
                  text='☑ Researched  ·  greyed = prereq not met  ·  prereq: single name, or ["A","B"] means A OR B',
                  style="Muted.TLabel").pack(side="right", padx=8)

        # ── project tree (read-only display + researched checkbox via click) ──
        proj_tree_frame = ttk.Frame(frame, style="Dark.TFrame")
        proj_tree_frame.pack(fill="both", expand=True)

        proj_cols = ("researched", "name", "cost", "time", "prereq", "recipe_display")
        self._proj_tree = ttk.Treeview(proj_tree_frame, columns=proj_cols,
                                       show="headings", selectmode="browse")
        self._proj_tree.heading("researched",     text="Done")
        self._proj_tree.heading("name",           text="Project",
                                command=lambda: self._proj_sort("name"))
        self._proj_tree.heading("cost",           text="Cost ($)",
                                command=lambda: self._proj_sort("cost"))
        self._proj_tree.heading("time",           text="Time",
                                command=lambda: self._proj_sort("time"))
        self._proj_tree.heading("prereq",         text="Prereq")
        self._proj_tree.heading("recipe_display", text="Ingredients")

        self._proj_tree.column("researched",     width=55,  anchor="center", stretch=False)
        self._proj_tree.column("name",           width=220, anchor="w",      stretch=False)
        self._proj_tree.column("cost",           width=120, anchor="e",      stretch=False)
        self._proj_tree.column("time",           width=100, anchor="e",      stretch=False)
        self._proj_tree.column("prereq",         width=200, anchor="w",      stretch=False)
        self._proj_tree.column("recipe_display", width=500, anchor="w",      stretch=True)

        vsb = ttk.Scrollbar(proj_tree_frame, orient="vertical",   command=self._proj_tree.yview)
        hsb = ttk.Scrollbar(proj_tree_frame, orient="horizontal", command=self._proj_tree.xview)
        self._proj_tree.configure(yscrollcommand=vsb.set, xscrollcommand=hsb.set)

        self._proj_tree.grid(row=0, column=0, sticky="nsew")
        vsb.grid(row=0, column=1, sticky="ns")
        hsb.grid(row=1, column=0, sticky="ew")
        proj_tree_frame.rowconfigure(0, weight=1)
        proj_tree_frame.columnconfigure(0, weight=1)

        # tag styles — row_a/row_b set background only so state foreground wins
        self._proj_tree.tag_configure("row_a",      background=ROW_A)
        self._proj_tree.tag_configure("row_b",      background=ROW_B)
        self._proj_tree.tag_configure("available",  foreground=TEXT)
        self._proj_tree.tag_configure("locked",     foreground="#555570")
        self._proj_tree.tag_configure("researched", foreground=ACCENT2)

        # clicking the Researched column toggles
        self._proj_tree.bind("<ButtonRelease-1>", self._proj_tree_click)

        self._refresh_projects()

    # ── project helpers ───────────────────────────────────────────────────────

    def _refresh_projects(self):
        """Rebuild the project treeview from self.data['projects']."""
        tree = self._proj_tree
        for item in tree.get_children():
            tree.delete(item)

        projects = self.data.get("projects", {})
        sort_key = self._proj_sort_var.get()

        def row_sort_key(item):
            name, entry = item
            if sort_key == "cost":
                return project_cost(entry.get("Recipe", {}), self.data)
            if sort_key == "time":
                return project_time(entry.get("Recipe", {}), self.data,
                                   max(1, self._smelters.get()),
                                   max(1, self._crafters.get()))
            return name.lower()

        rows = sorted(projects.items(), key=row_sort_key)

        for i, (name, entry) in enumerate(rows):
            prereqs  = entry.get("Prereq", "")
            recipe   = entry.get("Recipe", {})
            cost     = project_cost(recipe, self.data)
            met      = project_prereq_met(prereqs, self.data)
            researched = entry.get("Researched", False)

            # Format prereq display
            if isinstance(prereqs, list):
                prereq_str = " OR ".join(prereqs)
            else:
                prereq_str = prereqs or "—"

            # Format recipe display
            recipe_str = ",  ".join(
                f"{qty:,g} {ing}" for ing, qty in recipe.items()
            )

            done_glyph = "☑" if researched else "☐"
            cost_str   = fmt(cost) if cost > 0 else "?"
            t          = project_time(recipe, self.data,
                                      max(1, self._smelters.get()),
                                      max(1, self._crafters.get()))
            time_str   = f"{int(t)}s" if t > 1 else "—"

            base_tag = "row_a" if i % 2 == 0 else "row_b"
            if researched:
                tags = (base_tag, "researched")
            elif not met:
                tags = (base_tag, "locked")
            else:
                tags = (base_tag, "available")

            tree.insert("", "end", iid=name, tags=tags,
                        values=(done_glyph, name, cost_str, time_str, prereq_str, recipe_str))

    def _proj_sort(self, key: str):
        self._proj_sort_var.set(key)
        self._refresh_projects()

    def _proj_tree_click(self, event):
        """Toggle Researched when clicking the Done column."""
        col  = self._proj_tree.identify_column(event.x)
        item = self._proj_tree.identify_row(event.y)
        if item and col == "#1":
            self._proj_toggle_researched(item)

    def _proj_toggle_researched(self, name):
        proj = self.data["projects"].get(name)
        if proj is None:
            return
        proj["Researched"] = not proj.get("Researched", False)
        save_data(self.data)
        self._refresh_projects()

    def _commit_projects(self, grid):
        pass  # projects edited directly in JSON / future editor
    

    # ── table refresh ─────────────────────────────────────────────────────────
    def _refresh_table(self):
        results = analyze_all(self.data,
                              smelters=max(1, self._smelters.get()),
                              crafters=max(1, self._crafters.get()))
        flt     = self._filter_var.get()
        sort_k  = self._sort_var.get()

        # only show recipes whose output item is marked unlocked
        results = [r for r in results if r.get("unlocked", True)]

        if flt == "Alloys":
            results = [r for r in results if r["category"] == "alloys"]
        elif flt == "Items":
            results = [r for r in results if r["category"] == "items"]

        results.sort(key=lambda r: r.get(sort_k, 0), reverse=True)

        for row in self.tree.get_children():
            self.tree.delete(row)

        time_cols  = {"craft_time", "smelt_raw", "craft_raw", "total_time"}
        money_cols = {"output_value", "direct_cost", "ore_cost",
                      "profit_direct", "profit_ore",
                      "vps_output", "vps_profit_direct", "vps_profit_ore"}

        for i, r in enumerate(results):
            values = []
            for _, key, _, _ in COL_DEFS:
                v = r.get(key, "")
                if key == "category":
                    values.append("Alloy" if v == "alloys" else "Item")
                elif key in money_cols:
                    values.append(fmt(v))
                elif key in time_cols:
                    values.append(f"{int(v)}s")
                else:
                    values.append(v)

            tags = ["row_a" if i % 2 == 0 else "row_b"]
            if r["category"] == "alloys":
                tags.append("alloy")
            else:
                tags.append("item")
            if r.get("profit_ore", 0) < 0:
                tags.append("bad")

            self.tree.insert("", "end", values=values, tags=tags)

    def _sort_by(self, key: str):
        self._sort_var.set(key)
        self._refresh_table()


    # ── save / reset ──────────────────────────────────────────────────────────
    def _save(self):
        save_data(self.data)
        messagebox.showinfo("Saved", f"Data saved to:\n{DATA_FILE}")

    def _reset_defaults(self):
        if messagebox.askyesno("Reset", "Reset all data to defaults? This cannot be undone."):
            self.data = json.loads(json.dumps(DEFAULT_DATA))
            save_data(self.data)
            messagebox.showinfo("Reset", "Data reset. Please restart the app for full UI refresh.")

    def _sell_galaxy(self):
        """New galaxy: keep stars, reset market/unlocks/research."""
        if not messagebox.askyesno(
                "Sell Galaxy",
                "Start a new galaxy?\n\n"
                "• Stars are kept\n"
                "• Unlocks, market levels and project research are reset"):
            return
        for cat in ("ores", "alloys", "items"):
            for entry in self.data[cat].values():
                entry["unlocked"] = False
                entry["market"]   = 0
                entry["realPrice"] = getRealPrice(
                    entry["base_price"], entry.get("stars", 0), 0, cat)
                # stars intentionally NOT reset
        for proj in self.data["projects"].values():
            proj["Researched"] = False
        self._smelters.set(1)
        self._crafters.set(1)
        save_data(self.data)
        messagebox.showinfo("Sell Galaxy",
                            "Galaxy sold!\nRestart the app to refresh all grids.")


# ── entry point ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    app = App()
    app.mainloop()