import requests

def GET_ALLIANCE_MEMBERS(ALLIANCE_ID: int, API_KEY: str):
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

        bankrecs {{
            id
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
    
    try:
        response = requests.get(url, timeout=10)
        response.raise_for_status()
    except requests.exceptions.RequestException as e:
        print(f"API request failed: {e}")
        return
    
    try:
        data = response.json()
        members = data.get("data", {}).get("nations", {}).get("data", [])
        if not members:
            print("No members found in the API response.")
            return
    except (ValueError, KeyError, TypeError) as e:
        print(f"Error parsing API response: {e}")
        return
    
    return members


def GET_NATION_DATA(nation_id: int, API_KEY: str):
    query = f'''
    {{
      nations(id:{nation_id}) {{ data {{
        id
        score
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

        

        alliance {{
            id
            name
        }}
        
        wars {{
            id
            
            attacker {{
                id
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

                alliance {{
                    id
                    name
                }}
            }}

            defender {{
                id
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

                alliance {{
                    id
                    name
                }}
            }}
            
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
        # Extract the nation info from the nested structure.
        nation_list = nation.get("data", {}).get("nations", {}).get("data", [])
        if not nation_list:
            print("Nation not found in the API response.")
            return
        nation_info = nation_list[0]
    except Exception as e:
        print(f"Error parsing API response: {e}")
        return
    
    return nation_info