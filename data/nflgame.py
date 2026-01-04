from datetime import datetime, timedelta
import time as t
from espnapi import espnapi as nflparser
import debug

NETWORK_RETRY_SLEEP_TIME = 10.0

class NflData:
    def __init__(self, config):
        # Save the parsed config
        self.config = config

        # Flag to determine when to refresh data
        self.needs_refresh = True

        self.helmet_logos = self.config.helmet_logos
        self.debug = self.config.debug
        self.demo_date = self.config.demo_date
        self.demo_week = self.config.demo_week if self.debug else ""
        self.only_live_teams = self.config.only_live_teams
        
        # Parse today's date and see if we should use today or yesterday
        self.get_current_date()


        # TODO: 12/21/2025 monitor set games to empty to start
        self.games = []
        self.last_games = []

        # Fetch the teams info
        self.refresh_games()

        # self.playoffs = nflparser.is_playoffs()
        # self.games = nflparser.get_all_games()
        # self.game = self.choose_game()
        # self.gametime = self.get_gametime()

        # What game do we want to start on?
        self.current_game_index = 0
        self.current_division_index = 0
        # self.scores = {}

    def get_current_date(self):
        # print(self.demo_date)
        # print(datetime.fromisoformat(self.demo_date))
        return datetime.now() if not (self.demo_date and self.debug) else datetime.fromisoformat(self.demo_date)
    
    def refresh_game(self):
        self.game = self.choose_game()
        self.needs_refresh = False

    def refresh_games(self):
        attempts_remaining = 5
        while attempts_remaining > 0:
            # print(attempts_remaining)
            try:
                all_games = nflparser.get_all_games(self.demo_week)

                # TODO: 12/18/25 Continue to monitor if this fixes the refresh rate...
                self.needs_refresh = False

                if len(self.games) > 0:
                    self.last_games = self.games.copy()
                if self.config.rotation_only_preferred:
                    self.games = self.__filter_list_of_games(all_games, self.config.preferred_teams)
                # if rotation is disabled, only look at the first team in the list of preferred teams
                elif not self.config.rotation_enabled:
                    self.games = self.__filter_list_of_games(all_games, [self.config.preferred_teams[0]])
                else:
                    self.games = self.__filter_list_of_games(all_games, None)

                self.games_refresh_time = t.time()
                self.network_issues = False
                break
            except Exception as e:
                self.network_issues = True
                debug.error("Networking error while refreshing the master list of games. {} retries remaining.".format(attempts_remaining))
                debug.error("Exception: {}".format(e))
                attempts_remaining -= 1
                t.sleep(NETWORK_RETRY_SLEEP_TIME)
            except ValueError:
                self.network_issues = True
                debug.error("Value Error while refreshing master list of games. {} retries remaining.".format(attempts_remaining))
                debug.error("ValueError: Failed to refresh list of games")
                attempts_remaining -= 1
                t.sleep(NETWORK_RETRY_SLEEP_TIME)

    #     # If we run out of retries, just move on to the next game
        if attempts_remaining <= 0 and self.config.rotation_enabled:
            self.advance_to_next_game()

    def get_gametime(self):
        tz_diff = t.timezone if (t.localtime().tm_isdst == 0) else t.altzone
        gametime = datetime.strptime(self.games[self.current_game_index]['date'], "%Y-%m-%dT%H:%MZ") + timedelta(hours=(tz_diff / 60 / 60 * -1))
        return gametime

    def current_game(self):
        return self.games[self.current_game_index]
    
    def current_game_old(self):
        current_game_old = self.last_games[self.current_game_index]
        self.last_games[self.current_game_index] = None
        return current_game_old

    # def update_scores(self, homescore, awayscore):
    #     self.scores[self.current_game_index] = {'home': homescore, 'away': awayscore}

    # def get_current_scores(self):
    #     if self.scores[self.current_game_index]:
    #         return self.scores[self.current_game_index]
    #     else:
    #         return {'home': 0, 'away': 0}

    # def refresh_overview(self):
    #     attempts_remaining = 5
    #     while attempts_remaining > 0:
    #         try:
    #             self.__update_layout_state()
    #             self.needs_refresh = False
    #             self.print_overview_debug()
    #             self.network_issues = False
    #             break
    #         except URLError, e:
    #             self.network_issues = True
    #             debug.error("Networking Error while refreshing the current overview. {} retries remaining.".format(attempts_remaining))
    #             debug.error("URLError: {}".format(e.reason))
    #             attempts_remaining -= 1
    #             time.sleep(NETWORK_RETRY_SLEEP_TIME)
    #         except ValueError:
    #             self.network_issues = True
    #             debug.error("Value Error while refreshing current overview. {} retries remaining.".format(attempts_remaining))
    #             debug.error("ValueError: Failed to refresh overview for {}".format(self.current_game().game_id))
    #             attempts_remaining -= 1
    #             time.sleep(NETWORK_RETRY_SLEEP_TIME)

    #     # If we run out of retries, just move on to the next game
    #     if attempts_remaining <= 0 and self.config.rotation_enabled:
    #         self.advance_to_next_game()

    def advance_to_next_game(self):
        self.current_game_index = self.__next_game_index()
        return self.current_game()

    # def game_index_for_preferred_team(self):
    #     if self.config.preferred_teams:
    #         return self.__game_index_for(self.config.preferred_teams[0])
    #     else:
    #         return 0

    def __filter_list_of_games(self, games, teams):
        # gamez = list(game for game in games if set([game['awayteam'], game['hometeam']]).intersection(set(teams)))
        print("bello")
        # print(game for game in gamez)

        if self.config.only_live_teams:
            game_list = list(game for game in games if game['state'] == 'in' and (game['timeout'] not in ["EH", "Off TO"])) # end half or official timeout
        if teams is not None and len(game_list) > 0:
            game_list = list(game for game in games if set([game['awayteam'], game['hometeam']]).intersection(set(teams)))
        if len(game_list) == 0:
            game_list = games

        # TODO: 12/21/25 monitor current game index reset
        if len(game_list) < len(self.games):
            self.current_game_index += len(game_list) - len(self.games)
            if self.current_game_index < 0:
                self.current_game_index = 0

        print(len(game_list))
        print(len(self.games))
        return game_list

    # def __game_index_for(self, team_name):
    #     team_index = 0
    #     print(self.games)
    #     # team_idxs = [i for i, game in enumerate(self.games) if team_name in [game.awayteam, game.hometeam]]
    #     for game in enumerate(self.games):
    #         print(game)
    #     return team_index

    def __next_game_index(self):
        counter = self.current_game_index + 1
        if counter >= len(self.games):
            counter = 0
        return counter

    #
    # Debug info

    # def print_overview_debug(self):
    #     debug.log("Overview Refreshed: {}".format(self.overview.id))
    #     debug.log("Pre: {}".format(Pregame(self.overview, self.config.time_format)))
    #     debug.log("Live: {}".format(Scoreboard(self.overview)))
    #     debug.log("Final: {}".format(Final(self.current_game())))