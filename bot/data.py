import requests
import json
from typing import Dict, List, Optional, Any
from datetime import datetime, timezone
import pytz
from bot.handler import error
import time

def GET_ALLIANCE_MEMBERS(ALLIANCE_ID: int, API_KEY: str, max_retries: int = 3):
    """Get alliance members from the API with retry logic."""
    query = f"""{{
    nations(first:500, vmode: false, alliance_id:{ALLIANCE_ID}) {{data {{
        id
        nation_name
        leader_name
        soldiers
        tanks
        aircraft
        ships
        money
        oil
        uranium
        iron
        bauxite
        lead
        coal
        gasoline
        munitions
        steel
        aluminum
        food
        credits
        population
        defensive_wars_count
        last_active
        discord
        alliance_position
        spies

        military_research {{
            ground_capacity
            air_capacity
            naval_capacity
        }}

        alliance {{
            id
            name
        }}

        cities {{
            date
            infrastructure
            coal_power
            oil_power
            nuclear_power
            wind_power
            farm
            uranium_mine
            iron_mine
            coal_mine
            oil_refinery
            steel_mill
            aluminum_refinery
            munitions_factory
            police_station
            hospital
            recycling_center
            subway
            supermarket
            bank
            shopping_mall
            stadium
            barracks
            factory
            hangar
            drydock
        }}
    }}}}}}"""
    
    url = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}&query={query}"
    
    for attempt in range(max_retries):
        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            data = response.json()
            
            # Check for API errors
            if "errors" in data:
                error_msg = data["errors"][0] if isinstance(data["errors"], list) else data["errors"]
                error_type = error_msg.get("extensions", {}).get("category", "unknown")
                
                # If it's an internal server error, retry after a delay
                if error_type == "internal":
                    if attempt < max_retries - 1:
                        error(f"Internal server error, retrying... (Attempt {attempt + 1}/{max_retries})", tag="ALLIANCE_MEMBERS")
                        time.sleep(2 ** attempt)  # Exponential backoff
                        continue
                    else:
                        error(f"Internal server error after {max_retries} attempts", tag="ALLIANCE_MEMBERS")
                        return None
                else:
                    error(f"API Error: {error_msg}", tag="ALLIANCE_MEMBERS")
                    return None
            
            members = data.get("data", {}).get("nations", {}).get("data", [])
            if not members:
                error("No members found in the API response.", tag="ALLIANCE_MEMBERS")
                return None
                
            return members
            
        except requests.exceptions.RequestException as e:
            if attempt < max_retries - 1:
                error(f"API request failed, retrying... (Attempt {attempt + 1}/{max_retries}): {e}", tag="ALLIANCE_MEMBERS")
                time.sleep(2 ** attempt)  # Exponential backoff
                continue
            else:
                error(f"API request failed after {max_retries} attempts: {e}", tag="ALLIANCE_MEMBERS")
                return None
                
        except (ValueError, KeyError, TypeError) as e:
            error(f"Error parsing API response: {e}", tag="ALLIANCE_MEMBERS")
            return None
    
    return None


def GET_NATION_DATA(nation_id: int, api_key: str) -> Optional[Dict]:
    """Get nation data from the API."""
    query = """
    {
        nations(id: %d) { 
            data {
                last_active
                flag
                id
                score
                color
                population
                nation_name
                leader_name
                soldiers
                tanks
                aircraft
                ships
                money
                coal
                oil
                uranium
                iron
                bauxite
                lead
                gasoline
                munitions
                steel
                aluminum
                food
                credits
                continent
                discord
                spies_today
                
                alliance {
                    id
                    name
                }
                
                wars {
                    id
                    attacker {
                        id
                        nation_name
                        leader_name
                        soldiers
                        tanks
                        aircraft
                        ships
                        alliance {
                            id
                            name
                        }
                    }
                    defender {
                        id
                        nation_name
                        leader_name
                        soldiers
                        tanks
                        aircraft
                        ships
                        alliance {
                            id
                            name
                        }
                    }
                    war_type
                    turns_left
                    att_points
                    def_points
                    att_peace
                    def_peace
                    att_resistance
                    def_resistance
                    att_fortify
                    def_fortify
                    ground_control
                    air_superiority
                    naval_blockade
                }
            }
        }
    }
    """ % nation_id
    
    try:
        response = requests.post(
            "https://api.politicsandwar.com/graphql",
            json={"query": query, "variables": {"id": [nation_id]}},
            params={"api_key": api_key}
        )
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            error(f"API Error in GET_NATION_DATA: {data['errors']}", tag="NATION")
            return None
            
        nations = data.get("data", {}).get("nations", {}).get("data", [])
        return nations[0] if nations else None
        
    except Exception as e:
        error(f"Error fetching nation data: {e}", tag="NATION")
        return None


def GET_CITY_DATA(nation_id: int, api_key: str) -> Optional[List[Dict]]:
    """Get city data for a nation from the API."""
    query = """
    {
        nations(id:%d) { data {
            cities {
                name
                id
                date
                infrastructure
                land
                coal_power
                oil_power
                nuclear_power
                wind_power
                farm
                uranium_mine
                iron_mine
                coal_mine
                oil_refinery
                steel_mill
                aluminum_refinery
                munitions_factory
                police_station
                hospital
                recycling_center
                subway
                supermarket
                bank
                shopping_mall
                stadium
                barracks
                factory
                hangar
                drydock
            }
        }}
    }
    """ % nation_id
    
    try:
        response = requests.get(
            "https://api.politicsandwar.com/graphql",
            params={"api_key": api_key, "query": query}
        )
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print(f"API Error: {data['errors']}")
            return None
            
        nations = data.get("data", {}).get("nations", {}).get("data", [])
        return nations[0].get("cities", []) if nations else None
        
    except Exception as e:
        print(f"Error fetching city data: {e}")
        return None


def GET_PURGE_NATIONS(API_KEY: str):
    query = f'''
        {{
        nations(max_score: 2000, color: "purple") {{ data {{
            id
            score
            color
            nation_name
            leader_name
            alliance {{
                id
                name
                rank
            }}
        }}}}
        }}
    '''
    url = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}&query={query}"
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return

    try:
        nation = response.json()
        nation_list = nation.get("data", {}).get("nations", {}).get("data", [])
        if not nation_list:
            print("No nations found in the API response.")
            return

        return nation_list

    except Exception as e:
        print(f"Error parsing API response: {e}")
        return




def GET_GAME_DATA(API_KEY: str):
    query = f"""
    {{
    game_info {{
            game_date
        
        radiation {{
            global
            north_america
            south_america
            europe
            africa
            asia
            australia
            antarctica
        }}
    }}
    }}
    """
    url = f"https://api.politicsandwar.com/graphql?api_key={API_KEY}&query={query}"
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return
    
    try:
        game_info = response.json()
        game_data = game_info.get("data", {}).get("game_info", {})
    except Exception as e:
        print(f"Error parsing API response: {e}")
        return
    
    return game_data

def GET_WAR_DATA(war_id: int, api_key: str) -> Optional[Dict]:
    """Get war data from the API."""
    query = """
    {
        wars(id:%d) { data {
            id
            attacker {
                id
                nation_name
                leader_name
                soldiers
                tanks
                aircraft
                ships
                alliance {
                    id
                    name
                }
            }
            defender {
                id
                nation_name
                leader_name
                soldiers
                tanks
                aircraft
                ships
                alliance {
                    id
                    name
                }
            }
            war_type
            turns_left
            att_points
            def_points
            att_peace
            def_peace
            att_resistance
            def_resistance
            att_fortify
            def_fortify
            ground_control
            air_superiority
            naval_blockade
        }}
    }
    """ % war_id
    
    try:
        response = requests.get(
            "https://api.politicsandwar.com/graphql",
            params={"api_key": api_key, "query": query}
        )
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            print(f"API Error: {data['errors']}")
            return None
            
        wars = data.get("data", {}).get("wars", {}).get("data", [])
        return wars[0] if wars else None
        
    except Exception as e:
        print(f"Error fetching war data: {e}")
        return None

def GET_WARS(params: Dict, api_key: str) -> List[Dict]:
    """Get war data from the API."""
    query = """
    query Wars($id: [Int], $min_id: Int, $max_id: Int, $before: DateTime, $after: DateTime, 
              $ended_before: DateTime, $ended_after: DateTime, $attid: [Int], $defid: [Int], 
              $or_id: [Int], $days_ago: Int, $active: Boolean, $status: WarActivity, 
              $nation_id: [Int], $alliance_id: [Int], $orderBy: [QueryWarsOrderByOrderByClause!], 
              $first: Int, $page: Int) {
        wars(id: $id, min_id: $min_id, max_id: $max_id, before: $before, after: $after,
             ended_before: $ended_before, ended_after: $ended_after, attid: $attid, defid: $defid,
             or_id: $or_id, days_ago: $days_ago, active: $active, status: $status,
             nation_id: $nation_id, alliance_id: $alliance_id, orderBy: $orderBy,
             first: $first, page: $page) {
            data {
                id
                date
                end_date
                reason
                war_type
                ground_control
                air_superiority
                naval_blockade
                winner_id
                turns_left
                att_id
                att_alliance_id
                att_alliance_position
                def_id
                def_alliance_id
                def_alliance_position
                att_points
                def_points
                att_peace
                def_peace
                att_resistance
                def_resistance
                att_fortify
                def_fortify
                att_gas_used
                def_gas_used
                att_mun_used
                def_mun_used
                att_alum_used
                def_alum_used
                att_steel_used
                def_steel_used
                att_infra_destroyed
                def_infra_destroyed
                att_money_looted
                def_money_looted
                def_soldiers_lost
                att_soldiers_lost
                def_tanks_lost
                att_tanks_lost
                def_aircraft_lost
                att_aircraft_lost
                def_ships_lost
                att_ships_lost
                att_missiles_used
                def_missiles_used
                att_nukes_used
                def_nukes_used
                att_infra_destroyed_value
                def_infra_destroyed_value
                attacker {
                    id
                    leader_name
                    nation_name
                    alliance {
                        id
                        name
                    }
                }
                defender {
                    id
                    leader_name
                    nation_name
                    alliance {
                        id
                        name
                    }
                }
            }
        }
    }
    """
    
    try:
        response = requests.post(
            "https://api.politicsandwar.com/graphql",
            json={"query": query, "variables": params},
            params={"api_key": api_key}
        )
        response.raise_for_status()
        data = response.json()
        
        if "errors" in data:
            error(f"API Error: {data['errors']}", tag="WARS")
            return []
        
        return data["data"]["wars"]["data"]
    except Exception as e:
        error(f"Error fetching war data: {e}", tag="WARS")
        return []

def GET_ALL_NATIONS(api_key: str) -> Optional[List[Dict]]:
    """Get all nations from the API in chunks of 500."""
    all_nations = []
    page = 1
    
    while True:
        query = """
        {{
            nations(first: 500, page: %d) {{ 
                data {{
                    id
                    nation_name
                    leader_name
                    score
                    population
                    soldiers
                    tanks
                    aircraft
                    ships
                    alliance {{
                        id
                        name
                    }}
                    cities {{
                        infrastructure
                    }}
                }
            }}
        }}
        """ % page
        
        try:
            response = requests.get(
                "https://api.politicsandwar.com/graphql",
                params={"api_key": api_key, "query": query},
                timeout=30  # Add timeout
            )
            response.raise_for_status()
            data = response.json()
            
            if "errors" in data:
                error(f"API Error in GET_ALL_NATIONS: {data['errors']}", tag="NATIONS")
                return None
                
            nations = data.get("data", {}).get("nations", {}).get("data", [])
            if not nations:  # No more nations to fetch
                break
                
            all_nations.extend(nations)
            page += 1
            
            # Add a small delay between requests to avoid rate limiting
            time.sleep(0.5)
            
        except requests.exceptions.Timeout:
            error("Timeout while fetching nations data", tag="NATIONS")
            return None
        except requests.exceptions.RequestException as e:
            error(f"Request error while fetching nations: {e}", tag="NATIONS")
            return None
        except Exception as e:
            error(f"Unexpected error in GET_ALL_NATIONS: {e}", tag="NATIONS")
            return None
    
    return all_nations if all_nations else None