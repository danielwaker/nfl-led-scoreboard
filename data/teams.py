# NOTE:
#   Modifying abbreviations for teams might require you to update or create colors/teams.json.
#   Each abbreviation in the teams list needs to have a corresponding entry in colors/teams.json
#   in order to render colors correctly.

# These are special teams in the league and not present in the api/v1/teams endpoint.
_SPECIAL_TEAMS = {
    159: { "abbreviation": "AL",  "name": "American League All-Stars" },
    160: { "abbreviation": "NL",  "name": "National League All-Stars" },
}

# Run this file to retreive the latest team data from the MLB API.
#   From project root:
#       python data/teams.py
_TEAMS = _SPECIAL_TEAMS | {
    14: { "abbreviation": "LAR", "name": "Rams" },
    22: { "abbreviation": "ARI",  "name": "Cardinals" },
    33: { "abbreviation": "BAL", "name": "Ravens" },
    17: { "abbreviation": "NE", "name": "Patriots" },
    3: { "abbreviation": "CHI", "name": "Bears" },
    4: { "abbreviation": "CIN", "name": "Bengals" },
    5: { "abbreviation": "CLE", "name": "Browns" },
    7: { "abbreviation": "DEN", "name": "Broncos" },
    8: { "abbreviation": "DET", "name": "Lions" },
    34: { "abbreviation": "HOU", "name": "Texans" },
    12: { "abbreviation": "KC",  "name": "Chiefs" },
    24: { "abbreviation": "LAC", "name": "Chargers" },
    28: { "abbreviation": "WSH", "name": "Commanders" },
    20: { "abbreviation": "NVJ", "name": "Jets" },
    13: { "abbreviation": "LV", "name": "Raiders" },
    23: { "abbreviation": "PIT", "name": "Steelers" },
    30: { "abbreviation": "JAX",  "name": "Jaguars" },
    26: { "abbreviation": "SEA", "name": "Seahawks" },
    25: { "abbreviation": "SF",  "name": "49ers" },
    18: { "abbreviation": "NO", "name": "Saints" },
    27: { "abbreviation": "TB",  "name": "Buccaneers" },
    6: { "abbreviation": "DAL", "name": "Cowboys" },
    10: { "abbreviation": "TEN", "name": "Titans" },
    16: { "abbreviation": "MIN", "name": "Vikings" },
    21: { "abbreviation": "PHI", "name": "Eagles" },
    1: { "abbreviation": "ATL", "name": "Falcons" },
    11: { "abbreviation": "IND", "name": "Colts" },
    15: { "abbreviation": "MIA", "name": "Dolphins" },
    19: { "abbreviation": "NYG", "name": "Giants" },
    9: { "abbreviation": "GB", "name": "Packers" },
    29: { "abbreviation": "CAR", "name": "Panthers" },
    2: { "abbreviation": "BUF", "name": "Bills" },
}

# Convenience dictionaries for quick lookups
TEAM_ID_ABBR  = { ID: t["abbreviation"] for ID, t in _TEAMS.items() }
TEAM_ID_NAME  = { ID: t["name"] for ID, t in _TEAMS.items() }
_TEAM_NAME_ID = { t["name"]: ID for ID, t in _TEAMS.items() }

def get_team_id(team_name):
    try:
        return _TEAM_NAME_ID[team_name]
    except KeyError:
        # this function is only ever given user's config as input
        # so we provide a more exact error message
        raise ValueError(f"Unknown team name: {team_name}")
    
# TODO: Fix this to get team data from ESPN API: https://site.api.espn.com/apis/site/v2/sports/football/nfl/teams
# def _fetch_team_data():
#     import json, os, statsapi

#     SPORT_ID = "1"
#     _teams = statsapi.get("teams", { "sportId": SPORT_ID })["teams"]
#     _teams.sort(key=lambda t: t["id"])

#     teams = {}

#     for team in _teams:
#         teams[team["id"]] = {
#             "abbreviation": team["abbreviation"],
#             "name": team["name"],
#         }

#     log_path = os.path.join(os.path.dirname(__file__), "..", "logs", "teams.log")
#     norm_path = os.path.normpath(log_path)

#     with open(norm_path, "w") as f:
#         json.dump(teams, f, indent=4)
    
#     print(f"Team data written to {norm_path}")

#     return teams

# if __name__ == "__main__":
#     _fetch_team_data()
