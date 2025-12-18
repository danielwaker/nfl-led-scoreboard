import requests
import json
from espnapi.season import SeasonType
from espnapi.groups import GroupType
from espnapi.standings import StandingsType

STANDINGS_URL = "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/"
SCOREBOARD_URL = "http://site.api.espn.com/apis/site/v2/sports/football/nfl/scoreboard"

default_clincher = {
              "name": "clincher",
              "displayValue": ""
            }

def get_standings(
        group_type: GroupType,
        standings_type: StandingsType = StandingsType.PLAYOFF, # playoff records come back alphabetical...
        season_type: SeasonType = SeasonType.REGULAR_SEASON
    ):
    url = f"{STANDINGS_URL}seasons/2025/types/{season_type.value}/groups/{group_type.value}/standings/{standings_type.value}?lang=en&region=us"
    print(url)
    data = requests.get(url)
    data = data.json()
    # print(data)

    teams = [team["team"] for team in data["standings"]]
    # for team in teams:
    #     print(team)
    team_ids = [team['$ref'][82:84].strip("?") for team in teams]
    # print(team_ids)

    recordIndex = 0
    if standings_type is StandingsType.PLAYOFF:
        recordIndex = 1
    # records = [record["records"][0] for record in data["standings"]] # 0 is overall
    records2 = [record["records"][recordIndex] for record in data["standings"]]
    # records3 =[next((record for stat in record["stats"] if stat["name"] == "playoffSeed"), None) for record in records]
    records4 = [next((record for stat in record["stats"] if stat["name"] == "playoffSeed"), None) for record in records2]
    # records5 = records3 + records4
    records = [x for x in records4 if x is not None]

    X, Y = [], []

    # Region: zip records and teams to sort
    # if standings_type is StandingsType.PLAYOFF:
    new_list = []

    for x, y in zip(records, team_ids):
        new_list.append((x, y))

    new_list.sort(key=lambda record: (next((stat for stat in record[0]["stats"] if stat["name"] == "playoffSeed"), None))["value"])


    for x, y in new_list:
        X.append(x)
        Y.append(y)
    
    records = X
    team_ids = Y

    # print(records[0])
    wins = [next((stat for stat in record["stats"] if stat["name"] == "wins"), None) for record in records]
    ties = [next((stat for stat in record["stats"] if stat["name"] == "ties"), None) for record in records]
    losses = [next((stat for stat in record["stats"] if stat["name"] == "losses"), None) for record in records]
    gamesBehind = [next((stat for stat in record["stats"] if stat["name"] == "gamesBehind"), None) for record in records]
    playoffSeed = [next((stat for stat in record["stats"] if stat["name"] == "playoffSeed"), None) for record in records]
    clincher = [next((stat for stat in record["stats"] if stat["name"] == "clincher"), default_clincher) for record in records]


    test = team_ids, wins, ties, losses, gamesBehind, playoffSeed, clincher

    # print(test)
    return team_ids, wins, ties, losses, gamesBehind, playoffSeed, clincher

def get_all_games(week):
    print("ESPN API CALL")
    # for i in range(5):
    try:
        res = requests.get(SCOREBOARD_URL+'?week='+week)
        res = res.json()
        games = []
        # i = 0
        for g in res['events']:
            info = g['competitions'][0]
            game = {'name': g['shortName'], 'date': g['date'],
                    'hometeam': info['competitors'][0]['team']['abbreviation'], 'homeid': info['competitors'][0]['id'], 'homescore': int(info['competitors'][0]['score']),
                    'awayteam': info['competitors'][1]['team']['abbreviation'], 'awayid': info['competitors'][1]['id'], 'awayscore': int(info['competitors'][1]['score']),
                    'down': info.get('situation', {}).get('shortDownDistanceText'), 'spot': info.get('situation', {}).get('possessionText'),
                    'time': info['status']['displayClock'], 'quarter': info['status']['period'], 'over': info['status']['type']['completed'],
                    'redzone': info.get('situation', {}).get('isRedZone'), 'possession': info.get('situation', {}).get('possession'), 'state': info['status']['type']['state']}
            games.append(game)
            # i += 1
        # print("games", len(games))
        return games
    except requests.exceptions.RequestException as e:
        print("Error encountered getting game info, can't hit ESPN api, retrying")
        # if i < 4:
        #     t.sleep(1)
        #     continue
        # else:
        #     print("Can't hit ESPN api after multiple retries, dying ", e)
    except Exception as e:
        print("something bad?", e)
