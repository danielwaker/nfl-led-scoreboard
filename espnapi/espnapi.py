import requests
import json
from espnapi.season import SeasonType
from espnapi.groups import GroupType
from espnapi.standings import StandingsType

URL = "http://sports.core.api.espn.com/v2/sports/football/leagues/nfl/"

def get_standings(
        group_type: GroupType,
        standings_type: StandingsType = StandingsType.OVERALL,
        season_type: SeasonType = SeasonType.REGULAR_SEASON
    ):
    url = f"{URL}seasons/2025/types/{season_type.value}/groups/{group_type.value}/standings/{standings_type.value}?lang=en&region=us"
    # print(url)
    data = requests.get(url)
    data = data.json()
    # print(data)

    teams = [team["team"] for team in data["standings"]]
    # for team in teams:
    #     print(team)
    team_ids = [team['$ref'][82:84].strip("?") for team in teams]
    # print(team_ids)

    records = [record["records"][0] for record in data["standings"]] # 0 is overall
    # print(records[0])
    wins = [next((stat for stat in record["stats"] if stat["name"] == "wins"), None) for record in records]
    ties = [next((stat for stat in record["stats"] if stat["name"] == "ties"), None) for record in records]
    losses = [next((stat for stat in record["stats"] if stat["name"] == "losses"), None) for record in records]
    gamesBehind = [next((stat for stat in record["stats"] if stat["name"] == "gamesBehind"), None) for record in records]

    return team_ids, wins, ties, losses, gamesBehind