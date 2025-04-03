import time
from datetime import datetime, timezone
import math

def calculate(nation_info, COSTS, MILITARY_COSTS):
    # Cost constants per turn (calculated from daily cost divided by 12 turns)
    COSTS = {
        "coal_power": 100,          # $100/turn
        "oil_power": 150,           # $150/turn
        "nuclear_power": 875,       # $875/turn
        "wind_power": 42,           # $42/turn
        "farm": 25,                 # $25/turn
        "uranium_mine": 417,        # $417/turn
        "iron_mine": 134,           # $134/turn
        "coal_mine": 34,            # $34/turn
        "oil_refinery": 334,        # $334/turn
        "steel_mill": 334,          # $334/turn
        "aluminum_refinery": 209,   # $209/turn
        "munitions_factory": 292,   # $292/turn
        "police_station": 63,       # $63/turn
        "hospital": 84,             # $84/turn
        "recycling_center": 209,    # $209/turn
        "subway": 271,              # $271/turn
        "supermarket": 50,          # $50/turn
        "bank": 150,                # $150/turn
        "shopping_mall": 450,       # $450/turn
        "stadium": 1013             # $1013/turn
    }

    MILITARY_COSTS = {
        "soldiers": 1.88 / 12,      # per soldier per turn
        "tanks": 75 / 12,           # per tank per turn
        "aircraft": 750 / 12,       # per aircraft per turn
        "ships": 5062.5 / 12        # per ship per turn
    }

    # Initialize totals for building upkeep and resource consumption per turn.
    total_building_upkeep = 0
    total_coal_consumption = 0.0      # from coal power plants and steel mills
    total_oil_consumption = 0.0       # from oil power plants and oil refineries
    total_uranium_consumption = 0.0   # from nuclear power plants
    total_steel_mill_iron = 0.0       # iron consumption in steel mills
    total_steel_mill_coal = 0.0       # additional coal consumption in steel mills
    total_aluminum_refinery_bauxite = 0.0  # bauxite consumption in aluminum refineries
    total_munitions_factory_lead = 0.0     # lead consumption in munitions factories
    total_food_consumption = 0.0       # food consumption in cities

    gasoline_preparedness = 0
    munitions_preparedness = 0
    steel_preparedness = 0
    aluminum_preparedness = 0


    for city in nation_info.get("cities", []):
        infra = city.get("infrastructure", 0)
        # Sum building upkeep per turn from all buildings in the city.
        building_upkeep = (
            city.get("coal_power", 0) * COSTS["coal_power"] +
            city.get("oil_power", 0) * COSTS["oil_power"] +
            city.get("nuclear_power", 0) * COSTS["nuclear_power"] +
            city.get("wind_power", 0) * COSTS["wind_power"] +
            city.get("farm", 0) * COSTS["farm"] +
            city.get("uranium_mine", 0) * COSTS["uranium_mine"] +
            city.get("iron_mine", 0) * COSTS["iron_mine"] +
            city.get("coal_mine", 0) * COSTS["coal_mine"] +
            city.get("oil_refinery", 0) * COSTS["oil_refinery"] +
            city.get("steel_mill", 0) * COSTS["steel_mill"] +
            city.get("aluminum_refinery", 0) * COSTS["aluminum_refinery"] +
            city.get("munitions_factory", 0) * COSTS["munitions_factory"] +
            city.get("police_station", 0) * COSTS["police_station"] +
            city.get("hospital", 0) * COSTS["hospital"] +
            city.get("recycling_center", 0) * COSTS["recycling_center"] +
            city.get("subway", 0) * COSTS["subway"] +
            city.get("supermarket", 0) * COSTS["supermarket"] +
            city.get("bank", 0) * COSTS["bank"] +
            city.get("shopping_mall", 0) * COSTS["shopping_mall"] +
            city.get("stadium", 0) * COSTS["stadium"]
        )
        total_building_upkeep += building_upkeep

        # Resource consumption per turn:
        # Coal power plants: 0.1 ton coal per 100 infra per turn.
        total_coal_consumption += city.get("coal_power", 0) * ((infra / 100) * 0.1)

        # Oil power plants: 0.1 ton oil per 100 infra per turn.
        total_oil_consumption += city.get("oil_power", 0) * ((infra / 100) * 0.1)

        # Nuclear power plants: 0.2 ton uranium per 1000 infra per turn.
        total_uranium_consumption += city.get("nuclear_power", 0) * ((infra / 1000) * 0.2)

        # Oil refineries: 0.25 ton oil per turn.
        total_oil_consumption += city.get("oil_refinery", 0) * 0.5

        # Steel mills: consume 0.25 ton iron and 0.25 ton coal per turn each.
        total_steel_mill_iron += city.get("steel_mill", 0) * 0.75

        # Aluminum refineries: consume 0.25 ton bauxite per turn.
        total_aluminum_refinery_bauxite += city.get("aluminum_refinery", 0) * 0.75

        # Munitions factories: consume 0.5 ton lead per turn.
        total_munitions_factory_lead += city.get("munitions_factory", 0) * 1.5

        # Food Consumption: 1 Per Base-Person Per Turn and 1 Per 750 Soldiers
        base_population = int(city.get("infrastructure", 0) * 100)
        date_format = "%Y-%m-%d"

        
        date1 = datetime.now(timezone.utc)
        date2 = datetime.strptime(city.get("date", "2025-01-01"), date_format).replace(tzinfo=timezone.utc)

        age = (date1 - date2).days

        city_age_modifier = 1 + max(math.log(max(age, 1)) / 15, 0)

        population = ((base_population ^ 2) / 125_000_000) + ((base_population * city_age_modifier - base_population) / 850)
        total_food_consumption += population * 1 + (nation_info.get("soldiers", 0) / 750)


        MMR_WEIGHT = 0.5
        aluminum_preparedness += (city.get("hangar", 0) * 3 * 5) * MMR_WEIGHT
        steel_preparedness += ((city.get("factory", 0) * 50 * 0.5) + (city.get("drydock", 0) * 30)) * MMR_WEIGHT

    # Military upkeep per turn (wartime rates).
    soldiers = nation_info.get("soldiers", 0)
    tanks = nation_info.get("tanks", 0)
    aircraft = nation_info.get("aircraft", 0)
    ships = nation_info.get("ships", 0)
    soldier_upkeep = soldiers * MILITARY_COSTS["soldiers"]
    tank_upkeep = tanks * MILITARY_COSTS["tanks"]
    aircraft_upkeep = aircraft * MILITARY_COSTS["aircraft"]
    ship_upkeep = ships * MILITARY_COSTS["ships"]
    total_military_upkeep = soldier_upkeep + tank_upkeep + aircraft_upkeep + ship_upkeep

    # print(f"Soldiers: {soldiers}, Tanks: {tanks}, Aircraft: {aircraft}, Ships: {ships}")
    total_upkeep_turn = total_building_upkeep + total_military_upkeep

    # Calculate required money for 5 days (60 turns).
    required_money = total_upkeep_turn * 60
    current_money = nation_info.get("money", 0)
    money_deficit = max(required_money - current_money, 0)

    # Calculate required resources over 60 turns (5 days).
    required_coal = (total_coal_consumption + total_steel_mill_coal) * 60
    required_oil = total_oil_consumption * 60
    required_uranium = total_uranium_consumption * 60
    required_iron = total_steel_mill_iron * 60
    required_bauxite = total_aluminum_refinery_bauxite * 60
    required_lead = total_munitions_factory_lead * 60


    required_gasoline = gasoline_preparedness * 60
    required_munitions = munitions_preparedness * 60
    required_steel = steel_preparedness * 5
    required_aluminum = aluminum_preparedness * 5


    required_food = total_food_consumption * 6
    required_credits = 1 - nation_info.get("credits", 0) 

    # Get current resource amounts.
    current_coal = nation_info.get("coal", 0)
    current_oil = nation_info.get("oil", 0)
    current_uranium = nation_info.get("uranium", 0)
    current_iron = nation_info.get("iron", 0)
    current_bauxite = nation_info.get("bauxite", 0)
    current_lead = nation_info.get("lead", 0)
    current_gasoline = nation_info.get("gasoline", 0)
    current_munitions = nation_info.get("munitions", 0)
    current_steel = nation_info.get("steel", 0)
    current_aluminum = nation_info.get("aluminum", 0)
    current_food = nation_info.get("food", 0)
    current_credits = nation_info.get("credits", 0)

    # Calculate deficits (if current >= required, deficit is 0).
    coal_deficit = max(required_coal - current_coal, 0)
    oil_deficit = max(required_oil - current_oil, 0)
    uranium_deficit = max(required_uranium - current_uranium, 0)
    iron_deficit = max(required_iron - current_iron, 0)
    bauxite_deficit = max(required_bauxite - current_bauxite, 0)
    lead_deficit = max(required_lead - current_lead, 0)
    gasoline_deficit = max(required_gasoline - current_gasoline, 0)
    munitions_deficit = max(required_munitions - current_munitions, 0)
    steel_deficit = max(required_steel - current_steel, 0)
    aluminum_deficit = max(required_aluminum - current_aluminum, 0)
    food_deficit = max(required_food - current_food, 0)
    credits_deficit = max(required_credits - current_credits, 0)

    result = {
        "money_deficit": money_deficit,
        "coal_deficit": coal_deficit,
        "oil_deficit": oil_deficit,
        "uranium_deficit": uranium_deficit,
        "iron_deficit": iron_deficit,
        "bauxite_deficit": bauxite_deficit,
        "lead_deficit": lead_deficit,
        "gasoline_deficit": gasoline_deficit,
        "munitions_deficit": munitions_deficit,
        "steel_deficit": steel_deficit,
        "aluminum_deficit": aluminum_deficit,
        "food_deficit": food_deficit,
        "credits_deficit": credits_deficit,
    }

    excess = {
        resource: abs(required - current) if required - current < 0 else 0
        for resource, (required, current) in {
            "money": (required_money, current_money),
            "coal": (required_coal, current_coal),
            "oil": (required_oil, current_oil),
            "uranium": (required_uranium, current_uranium),
            "iron": (required_iron, current_iron),
            "bauxite": (required_bauxite, current_bauxite),
            "lead": (required_lead, current_lead),
            "gasoline": (required_gasoline, current_gasoline),
            "munitions": (required_munitions, current_munitions),
            "steel": (required_steel, current_steel),
            "aluminum": (required_aluminum, current_aluminum),
            "food": (required_food, current_food),
        }.items()
    }


    return result, excess