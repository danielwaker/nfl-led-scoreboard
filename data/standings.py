import time
from datetime import datetime

import statsapi

import debug
from data import teams
from data.update import UpdateStatus
import data.headers
from espnapi import espnapi, groups, season, standings

STANDINGS_UPDATE_RATE = 15 * 60  # 15 minutes between standings updates


API_FIELDS = (
    "records,standingsType,teamRecords,team,id,abbreviation,division,league,nameShort,gamesBack,wildCardGamesBack,"
    "wildCardEliminationNumber,clinched,wins,losses"
)


class Standings:
    def __init__(self, config, playoffs_start_date: datetime):
        self.config = config
        self.date = self.config.parse_today()
        self.playoffs_start_date = playoffs_start_date.date()
        self.starttime = time.time()
        if config.preferred_divisions == ["ALL"]:
            self.preferred_divisions = groups.all_standings()
        else:
            self.preferred_divisions = config.preferred_divisions
        self.wild_cards = any("Wild" in division for division in config.preferred_divisions)
        self.current_division_index = 0

        self.standings = []
        self.leagues = {}

        self.update(True)


    def update(self, force=False) -> UpdateStatus:
        if force or self.__should_update():
            self.date = self.config.parse_today()
            debug.log("Refreshing standings for %s", self.date.strftime("%m/%d/%Y"))
            self.starttime = time.time()
            try:
                if not self.is_postseason():

                    # season_params = {
                    #     "standingsTypes": "regularSeason",
                    #     "leagueId": "103,104",
                    #     "hydrate": "division,team,league",
                    #     "season": self.date.strftime("%Y"),
                    #     "fields": API_FIELDS,
                    # }
                    # if self.date != datetime.today().date():
                    #     season_params["date"] = self.date.strftime("%m/%d/%Y")                        

                    standings = [(espnapi.get_standings(
                        groups.GroupType[division],
                        espnapi.StandingsType.PLAYOFF if "wild" in division.lower() else espnapi.StandingsType.OVERALL
                        ), division) for division in self.preferred_divisions]
                    # standings = [Division(map(bruh, standings, n)) for n in range(len(standings[0]))]
                    standings = [Division(division_data) for division_data in standings]
                    # divisons_data = statsapi.get("standings", season_params, request_kwargs={"headers": data.headers.API_HEADERS})
                    # standings = [Division(division_data) for division_data in divisons_data["records"]]

                    # if self.wild_cards:
                        # season_params["standingsTypes"] = "wildCard"
                        # wc_data = statsapi.get("standings", season_params, request_kwargs={"headers": data.headers.API_HEADERS})
                        # standings += [Division(data, wc=True) for data in wc_data["records"]]

                    self.standings = standings

                else:
                    standings = [(espnapi.get_standings(
                        groups.GroupType[division],
                        espnapi.StandingsType.PLAYOFF
                        ), division) for division in [groups.GroupType.AFC_WILD_CARD.name, groups.GroupType.NFC_WILD_CARD.name]]
                    standings = [Division(division_data) for division_data in standings]
                    
                    playoffs = espnapi.get_playoff_games()
                    self.leagues["AFC"] = League(standings[0], playoffs)
                    self.leagues["NFC"] = League(standings[1], playoffs)


            except:
                debug.exception("Failed to refresh standings.")
                return UpdateStatus.FAIL
            else:

                return UpdateStatus.SUCCESS

        return UpdateStatus.DEFERRED

    def __should_update(self):
        endtime = time.time()
        time_delta = endtime - self.starttime
        return time_delta >= STANDINGS_UPDATE_RATE

    def populated(self):
        return bool(self.standings) or (bool(self.leagues) and self.is_postseason())

    def is_postseason(self):
        # print("is postseason ", self.date, self.playoffs_start_date, self.date >= self.playoffs_start_date)
        return self.date >= self.playoffs_start_date

    def __standings_for(self, division_name):
        # print(division_name, self.standings[0].name)
        return next(division for division in self.standings if division.name == division_name)

    def current_standings(self):
        return self.__standings_for(self.preferred_divisions[self.current_division_index])

    def advance_to_next_standings(self):
        self.current_division_index = self.__next_division_index()
        return self.current_standings()

    def __next_division_index(self):
        counter = self.current_division_index + 1
        if counter >= len(self.preferred_divisions):
            counter = 0
        return counter


class Division:
    def __init__(self, data, wc=False):
        def bruh(ids, ws, ts, ls, gb, seed, clincher, i):
            # print(i)
            # print(s)
            return teams.TEAM_ID_ABBR[int(ids)], int(ws["value"]), int(ts["value"]), int(ls["value"]), gb["value"], seed["value"], clincher["displayValue"]

        self.name = data[1]
        
        x = len(data[0][0])
        
        # print(data[0])
        tms = map(bruh, data[0][0], data[0][1], data[0][2], data[0][3], data[0][4], data[0][5], data[0][6], range(x))
        self.teams = [Team(tm, wc) for tm in tms]

        # Fix GB for wild cards
        if "wild" in self.name.lower():
            teamz = self.teams
            seven = teamz[len(teamz) - (2 + 8)] # 7 out of 16
            # print("7", )
            eight = teamz[len(teamz) - (1 + 8)] # 8 out of 16
            wins = seven.w - eight.w
            losses = eight.l - seven.l
            gb = (wins + losses)/2
            teamz[len(teamz) - 9].gb = gb

        # print("GB2", self.teams[len(self.teams) - 1].gb)
        # if wc:
        #     self.name = data["league"]["abbreviation"] + " Wild Card"
        # else:
        #     self.name = data["division"]["nameShort"]
        # self.teams = [Team(team_data, wc) for team_data in data["teamRecords"][:5]]


class Team:
    def __init__(self, data, wc):
        # print(len(data))
        # print(data)
        self.team_abbrev = data[0]
        self.w = data[1]
        self.t = data[2]
        self.l = data[3]
        self.gb = data[4]
        self.seed = data[5]

        # self.team_abbrev = teams.TEAM_ID_ABBR[data["team"]["id"]]
        # self.w = data["wins"]
        # self.l = data["losses"]  # noqa: E741
        # if wc:
        #     self.gb = data["wildCardGamesBack"]
        # else:
        #     self.gb = data["gamesBack"]
        self.clinched = data[6].lower() in ["x","y","z"]
        self.elim = data[6].lower() == "e"

NL_IDS = {'wc36': 'F_3', 'wc45': 'F_4', 'wc27': 'F_5', 'dsA': 'D_3', 'dsB': 'D_4', 'cs': 'L_2' }
AL_IDS = {'wc36': 'F_1', 'wc45': 'F_2', 'wc27': 'F_6', 'dsA': 'D_1', 'dsB': 'D_2', 'cs': 'L_1' }

class League:
    """Grabs postseason bracket info for one league based on the schedule"""

    def __init__(self, data: Division, playoffs):
        self.name = data.name
        if self.name == 'NFC':
            ids = NL_IDS
        else:
            ids = AL_IDS

        self.wc3 = next((team for team in data.teams if team.seed == 3), None)
        self.wc4 = next((team for team in data.teams if team.seed == 4), None)
        self.wc5 = next((team for team in data.teams if team.seed == 5), None)
        self.wc6 = next((team for team in data.teams if team.seed == 6), None)
        self.wc7 = next((team for team in data.teams if team.seed == 7), None)

        self.ds_A_bye = next((team for team in data.teams if team.seed == 1), None)
        self.ds_B_bye = next((team for team in data.teams if team.seed == 2), None)

        # self.wc3, self.wc6 = self.get_seeds(data, ids['wc36'])
        # self.wc4, self.wc5 = self.get_seeds(data, ids['wc45'])

        # self.ds_A_bye, _ = self.get_seeds(data, ids['dsA'])
        # self.ds_B_bye, _ = self.get_seeds(data, ids['dsB'])

        self.wc36_winner = self.get_series_winner(self.wc3, self.wc6, playoffs, 1)
        self.wc45_winner = self.get_series_winner(self.wc4, self.wc5, playoffs, 1)
        self.wc27_winner = self.get_series_winner(self.ds_B_bye, self.wc7, playoffs, 1)
        self.mid1, self.mid2, self.bottom = sorted([self.wc27_winner,self.wc45_winner,self.wc36_winner], key=lambda x: x.seed)   
        self.l_two = self.get_series_winner(self.ds_A_bye, self.bottom, playoffs, 2)
        self.l_one = self.get_series_winner(self.mid1, self.mid2, playoffs, 2)
        sorted_teams_2 = sorted([self.l_one,self.l_two], key=lambda x: x.seed)
        self.champ = self.get_series_winner(sorted_teams_2[0], sorted_teams_2[1], playoffs, 3)

    def get_series_winner(self, higher, lower, playoffs, round):
        week = playoffs[round - 1]
        # [print(game) for game in week]
        game = next((game for game in week if game['hometeam'] == higher.team_abbrev), None)
        if game['homescore'] > game['awayscore']:
            return higher
        if game['awayscore'] > game['homescore']:
            return lower
        empty = lambda:None
        empty.team_abbrev = "TBD"
        empty.seed = -1
        return empty

    # def get_remaining_matchups(self, teams):
    #     lowest = teams[0]
    #     non_lowest = []
    #     if teams[1].seed > lowest:
    #         lowest = teams[1]
    #         non_lowest.append(teams[0])
    #     else:
    #         non_lowest.append(teams[1])
    #     if teams[2].seed > lowest:
    #         non_lowest.append(lowest)
    #         lowest = teams[2]
    #     else:
    #         non_lowest.append(teams[2])
    #     return non_lowest, lowest

    def __str__(self):
        return f"""{self.wc5} ---|
       |--- {self.wc45_winner} ---|
{self.wc6} ---|           | --- {self.l_two} ---|
            {self.ds_B_bye} ---|            |
{self.wc6} ---|                        | {self.champ}
       |--- {self.wc36_winner} ---|            |
{self.wc3} ---|           | --- {self.l_one} ---|
            {self.ds_A_bye} ---|
        """


def get_abbr(id, default="TBD"):
    return f"{teams.TEAM_ID_ABBR.get(id, default):>3}"
