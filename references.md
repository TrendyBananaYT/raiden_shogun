# raiden_shogun
A bot for the Inazuma Shogunate alliance in the web game "Politics And War". Runs off of Graphql v3 API Endpoints and discord.py

# Politics and War Bot

## Game Mechanics Reference

### City Details
- Base Population = Infrastructure * 100
- Infra Unit Cost = [((Current Infra-10)^2.2) / 710] + 300
- Improvements = Infra/50
- Land Unit Cost = 0.002*(Current Land-20)^2 + 50
- Population = (Base Pop - ((Disease Rate * 100 * Infra)/100) - MAX((Crime Rate / 10) * (100*Infra) - 25, 0) * (1 + ln(CityAgeInDays)/15)

### Crime & Disease
- Crime (%) = ((103 - Commerce)^2 + (Infrastructure * 100))/(111111) - Police Modifier
  - Police Modifier = (# of Police Stations)*(2.5)
- Disease Rate = ((((Population Density^2) * 0.01) - 25)/100) + (Base Population/100000) + Pollution Modifier - Hospital Modifier
  - Hospital Modifier = Hospital Count * 2.5
  - Pollution Modifier = Pollution Index * 0.05

### Resource Production
- Food Production = Farm Count * (Land Area / 500)
  - Mass Irrigation: Farms * (Land Area / 400)
  - Summer: Food * 1.2
  - Winter: Food * 0.8
  - Final Food Prod = Food Production * (nation+continent+global rad index)/1000

### Commerce Improvements
- Supermarkets: +3%
- Banks: +5%
- Shopping Malls: +9%
- Stadiums: +12%
- Subways: +8%

### Continent Resources
- Africa: Oil, Bauxite, Uranium
- Antarctica: Oil, Coal, Uranium
- Asia: Oil, Iron, Uranium
- Australia: Coal, Bauxite, Lead
- Europe: Coal, Iron, Lead
- North America: Coal, Iron, Uranium
- South America: Oil, Bauxite, Lead

### Power Plants
- Coal Power Plant
  - Cost: $5,000
  - Power: 500 infrastructure
  - Usage: 1.2 coal/day per 100 infra
  - Cost: $1,200/day
  - Pollution: +8

- Oil Power Plant
  - Cost: $7,000
  - Power: 500 infrastructure
  - Usage: 1.2 oil/day per 100 infra
  - Cost: $1,800/day
  - Pollution: +6

- Nuclear Power Plant
  - Cost: $500,000 + 100
  - Power: 2,000 infrastructure
  - Usage: 2.4 uranium/day per 1,000 infra
  - Cost: $10,500/day
  - Pollution: 0

- Wind Power Plant
  - Cost: $30,000 + 25
  - Power: 250 infrastructure
  - Usage: None
  - Cost: $500/day
  - Pollution: 0

### Resource Buildings
- Coal Mine
  - Cost: $1,000
  - Production: 3 coal/day
  - Cost: $400/day
  - Max: 10 per city
  - Pollution: +12

- Iron Mine
  - Cost: $9,500
  - Production: 3 iron/day
  - Cost: $1,600/day
  - Max: 10 per city
  - Pollution: +12

- Uranium Mine
  - Cost: $25,000
  - Production: 3 uranium/day
  - Cost: $5,000/day
  - Max: 5 per city
  - Pollution: +20

- Farm
  - Cost: $1,000
  - Production: Land Area/500 food per turn
  - Cost: $300/day
  - Max: 20 per city
  - Pollution: +2

### Manufacturing
- Oil Refinery
  - Cost: $45,000
  - Production: 6 gasoline/day from 3 oil
  - Cost: $4,000/day
  - Max: 5 per city
  - Pollution: +32

- Steel Mill
  - Cost: $45,000
  - Production: 9 steel/day from 3 iron + 3 coal
  - Cost: $4,000/day
  - Max: 5 per city
  - Pollution: +40

- Aluminum Refinery
  - Cost: $30,000
  - Production: 9 aluminum/day from 3 bauxite
  - Cost: $2,500/day
  - Max: 5 per city
  - Pollution: +40

- Munitions Factory
  - Cost: $35,000
  - Production: 18 munitions/day from 6 lead
  - Cost: $3,500/day
  - Max: 5 per city
  - Pollution: +32

### Civil Improvements
- Police Station
  - Cost: $75,000 + 20
  - Effect: -2.5% crime
  - Cost: $750/day
  - Max: 5 per city
  - Pollution: +1

- Hospital
  - Cost: $100,000 + 25
  - Effect: -2.5% disease
  - Cost: $1,000/day
  - Max: 5 per city
  - Pollution: +4

- Recycling Center
  - Cost: $125,000
  - Effect: -70 pollution
  - Cost: $2,500/day
  - Max: 3 per city

- Subway
  - Cost: $250,000 + 50 + 25
  - Effect: +8% commerce, -45 pollution
  - Cost: $3,250/day
  - Max: 1 per city

### Commerce Improvements
- Supermarket
  - Cost: $5,000
  - Effect: +4% commerce
  - Cost: $600/day
  - Max: 4 per city

- Bank
  - Cost: $15,000 + 5 + 10
  - Effect: +6% commerce
  - Cost: $1,800/day
  - Max: 5 per city

- Shopping Mall
  - Cost: $45,000 + 20 + 25
  - Effect: +8% commerce
  - Cost: $5,400/day
  - Max: 4 per city
  - Pollution: +2

- Stadium
  - Cost: $100,000 + 40 + 50
  - Effect: +10% commerce
  - Cost: $12,150/day
  - Max: 3 per city
  - Pollution: +5

### Military Buildings
- Barracks
  - Cost: $3,000
  - Effect: +3,000 soldiers/day
  - Cost: $1.25/soldier/day (peace), $1.88/soldier/day (war)
  - Max: 5 per city

- Factory
  - Cost: $15,000 + 5
  - Effect: +250 tanks/day
  - Cost: $50/tank/day (peace), $75/tank/day (war)
  - Max: 5 per city

- Hangar
  - Cost: $100,000 + 10
  - Effect: +15 aircraft/day
  - Cost: $500/aircraft/day (peace), $750/aircraft/day (war)
  - Max: 5 per city

- Drydock
  - Cost: $250,000 + 20
  - Effect: +5 ships/day
  - Cost: $3,375/ship/day (peace), $5,062.5/ship/day (war)
  - Max: 3 per city
