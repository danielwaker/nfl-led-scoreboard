import time
from typing import Callable, NoReturn
from data.screens import ScreenType

from data.teams import TEAM_ID_NAME
import debug
from data import Data, status
from data.scoreboard import Scoreboard
from data.scoreboard.postgame import Postgame
from data.scoreboard.pregame import Pregame
from renderers import network, offday, standings
from renderers.games import game as gamerender
from renderers.games import irregular
from renderers.games import postgame as postgamerender
from renderers.games import pregame as pregamerender
from renderers.games import teams

# NFL
from PIL import Image, ImageFont, ImageDraw
from datetime import datetime, timedelta
from rgbmatrix import graphics
import re
from utils import center_text
import time as t

# TODO(BMW) make configurable time?
STANDINGS_NEWS_SWITCH_TIME = 120


class MainRenderer:
    def __init__(self, matrix, data):
        self.matrix = matrix
        self.data: Data = data
        self.is_playoffs = False # TODO: self.data.schedule.date > self.data.headlines.important_dates.playoffs_start_date.date()
        self.canvas = matrix.CreateFrameCanvas()
        self.scrolling_text_pos = self.canvas.width
        self.game_changed_time = time.time()
        self.animation_time = 0
        self.standings_stat = "w"
        self.standings_league = "NL" # TODO: NFC/AFC

        # NFL
        # self.font = ImageFont.truetype("fonts/score_large.otf", 16)
        # self.font_mini = ImageFont.truetype("fonts/04B_24__.TTF", 8)
        # self.image = Image.new('RGB', (self.width, self.height))
        # self.draw = ImageDraw.Draw(self.image)

        # NFL attempt 2
        self.matrix = matrix
        self.data = data
        # self.screen_config = screenConfig("64x32_config")
        self.canvas = matrix.CreateFrameCanvas()
        self.width = 64
        self.height = 32
        # Create a new data image.
        self.image = Image.new('RGB', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        # Load the fonts
        self.font = ImageFont.truetype("fonts/score_large.otf", 16)
        self.font_mini = ImageFont.truetype("fonts/04B_24__.TTF", 8)


    def render(self):
        screen = self.data.get_screen_type()
        # display the news ticker
        if screen == ScreenType.ALWAYS_NEWS:
            True # TODO: self.__draw_news(permanent_cond)
        # display the standings
        elif screen == ScreenType.ALWAYS_STANDINGS:
            self.__render_standings()
        elif screen == ScreenType.LEAGUE_OFFDAY:
            self.__render_offday(team_offday=False)
        elif screen == ScreenType.PREFERRED_TEAM_OFFDAY:
            True # TODO: self.__render_offday(team_offday=True)
        # Playball!
        else:
            self.starttime = t.time()
            self.starttime_api = t.time()
            self.__render_game()

    def __render_offday(self, team_offday=True) -> NoReturn:

        news = False # TODO: remove this
        
        if team_offday:
            True # TODO
            # news = self.data.config.news_ticker_team_offday
            # standings = self.data.config.standings_team_offday
        else:
            # TODO: news = True
            standings = self.data.config.standings_mlb_offday

        if news and standings:
            while True:
                self.__draw_news(timer_cond(STANDINGS_NEWS_SWITCH_TIME))
                self.__draw_standings(timer_cond(STANDINGS_NEWS_SWITCH_TIME))
        elif news:
            self.__draw_news(permanent_cond)
        else:
            # self.__render_standings()
            while True:
                self.__render_standings()
                self.starttime = t.time()
                self.starttime_api = t.time()
                self.__render_game(False)

    def __render_standings(self) -> NoReturn:
        self.__draw_standings(permanent_cond)

        # Out of season off days don't always return standings so fall back on the news renderer
        # debug.error("No standings data.  Falling back to news.")
        # TODO some sort of fallback: self.__draw_news(permanent_cond)

    # Renders a game screen based on it's status
    # May also call draw_offday or draw_standings if there are no games
    def __render_gameday(self) -> NoReturn:
        refresh_rate = self.data.config.scrolling_speed
        while True:
            if not self.data.schedule.games_live():
                if self.data.config.news_no_games and self.data.config.standings_no_games:
                    self.__draw_news(all_of(timer_cond(STANDINGS_NEWS_SWITCH_TIME), self.no_games_cond))
                    self.__draw_standings(all_of(timer_cond(STANDINGS_NEWS_SWITCH_TIME), self.no_games_cond))
                    continue
                elif self.data.config.news_no_games:
                    self.__draw_news(self.no_games_cond)
                elif self.data.config.standings_no_games:
                    self.__draw_standings(self.no_games_cond)

            if self.game_changed_time < self.data.game_changed_time:
                self.scrolling_text_pos = self.canvas.width
                self.data.scrolling_finished = not self.data.config.rotation_scroll_until_finished
                self.game_changed_time = time.time()

            # Draw the current game
            self.__draw_game()

            time.sleep(refresh_rate)

    # Draws the provided game on the canvas
    def __draw_game(self):
        game = self.data.current_game
        bgcolor = self.data.config.scoreboard_colors.color("default.background")
        self.canvas.Fill(bgcolor["r"], bgcolor["g"], bgcolor["b"])
        scoreboard = Scoreboard(game)
        layout = self.data.config.layout
        colors = self.data.config.scoreboard_colors

        if status.is_pregame(game.status()):  # Draw the pregame information
            self.__max_scroll_x(layout.coords("pregame.scrolling_text"))
            pregame = Pregame(game, self.data.config.time_format)
            pos = pregamerender.render_pregame(
                self.canvas,
                layout,
                colors,
                pregame,
                self.scrolling_text_pos,
                self.data.config.pregame_weather,
                self.is_playoffs,
            )
            self.__update_scrolling_text_pos(pos, self.canvas.width)

        elif status.is_complete(game.status()):  # Draw the game summary
            self.__max_scroll_x(layout.coords("final.scrolling_text"))
            final = Postgame(game)
            pos = postgamerender.render_postgame(
                self.canvas, layout, colors, final, scoreboard, self.scrolling_text_pos, self.is_playoffs
            )
            self.__update_scrolling_text_pos(pos, self.canvas.width)

        elif status.is_irregular(game.status()):  # Draw game status
            short_text = self.data.config.layout.coords("status.text")["short_text"]
            if scoreboard.get_text_for_reason():
                self.__max_scroll_x(layout.coords("status.scrolling_text"))
                pos = irregular.render_irregular_status(
                    self.canvas, layout, colors, scoreboard, short_text, self.scrolling_text_pos
                )
                self.__update_scrolling_text_pos(pos, self.canvas.width)
            else:
                irregular.render_irregular_status(self.canvas, layout, colors, scoreboard, short_text)
                self.data.scrolling_finished = True

        else:  # draw a live game
            if scoreboard.homerun() or scoreboard.strikeout() or scoreboard.hit() or scoreboard.walk():
                self.animation_time += 1
            else:
                self.animation_time = 0

            if status.is_inning_break(scoreboard.inning.state):
                loop_point = self.data.config.layout.coords("inning.break.due_up")["loop"]
            else:
                loop_point = self.data.config.layout.coords("atbat")["loop"]

            self.scrolling_text_pos = min(self.scrolling_text_pos, loop_point)
            pos = gamerender.render_live_game(
                self.canvas, layout, colors, scoreboard, self.scrolling_text_pos, self.animation_time
            )
            self.__update_scrolling_text_pos(pos, loop_point)

        # draw last so it is always on top
        teams.render_team_banner(
            self.canvas,
            layout,
            self.data.config.team_colors,
            scoreboard.home_team,
            scoreboard.away_team,
            self.data.config.full_team_names,
            self.data.config.short_team_names_for_runs_hits,
            show_score=not status.is_pregame(game.status()),
        )

        # Show network issues
        if self.data.network_issues:
            network.render_network_error(self.canvas, layout, colors)

        self.canvas = self.matrix.SwapOnVSync(self.canvas)

    def __draw_news(self, cond: Callable[[], bool]):
        """
        Draw the news screen for as long as cond returns True
        """
        color = self.data.config.scoreboard_colors.color("default.background")
        while cond():
            self.canvas.Fill(color["r"], color["g"], color["b"])

            self.__max_scroll_x(self.data.config.layout.coords("offday.scrolling_text"))
            pos = offday.render_offday_screen(
                self.canvas,
                self.data.config.layout,
                self.data.config.scoreboard_colors,
                self.data.weather,
                self.data.headlines,
                self.data.config.time_format,
                self.scrolling_text_pos,
            )
            # todo make scrolling_text_pos something persistent/news-specific
            # if we want to show news as part of rotation?
            # not strictly necessary but would be nice, avoids only seeing first headline over and over
            self.__update_scrolling_text_pos(pos, self.canvas.width)
            # Show network issues
            if self.data.network_issues:
                network.render_network_error(self.canvas, self.data.config.layout, self.data.config.scoreboard_colors)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            time.sleep(self.data.config.scrolling_speed)

    def __draw_standings(self, cond: Callable[[], bool]):
        """
        Draw the standings screen for as long as cond returns True
        """
        if not self.data.standings.populated():
            return

        if self.data.standings.is_postseason() and self.canvas.width <= 32:
            return

        update = 1
        while cond():
            standings_index = self.data.standings.current_division_index

            if self.data.standings.is_postseason():
                standings.render_bracket(
                    self.canvas,
                    self.data.config.layout,
                    self.data.config.scoreboard_colors,
                    self.data.standings.leagues[self.standings_league],
                )
            else:
                standings.render_standings(
                    self.canvas,
                    self.data.config.layout,
                    self.data.config.scoreboard_colors,
                    self.data.standings.current_standings(),
                    self.standings_stat,
                )

            if self.data.network_issues:
                network.render_network_error(self.canvas, self.data.config.layout, self.data.config.scoreboard_colors)

            self.canvas = self.matrix.SwapOnVSync(self.canvas)

            if self.data.standings.is_postseason():
                if update % 20 == 0:
                    if self.standings_league == "NL":
                        self.standings_league = "AL"
                    else:
                        self.standings_league = "NL"
            elif self.canvas.width == 32 and update % 5 == 0:
                if self.standings_stat == "w":
                    self.standings_stat = "l"
                else:
                    self.standings_stat = "w"
                    self.data.standings.advance_to_next_standings()
            elif self.canvas.width > 32 and update % 10 == 0:
                self.data.standings.advance_to_next_standings()
            
            if standings_index != 0 and self.data.standings.current_division_index == 0:
                break

            time.sleep(1)
            update = (update + 1) % 100

    def __max_scroll_x(self, scroll_coords):
        scroll_max_x = scroll_coords["x"] + scroll_coords["width"]
        self.scrolling_text_pos = min(scroll_max_x, self.scrolling_text_pos)

    def __update_scrolling_text_pos(self, new_pos, end):
        """Updates the position of scrolling text"""
        pos_after_scroll = self.scrolling_text_pos - 1
        if pos_after_scroll + new_pos < 0:
            self.data.scrolling_finished = True
            if pos_after_scroll + new_pos < -10:
                self.scrolling_text_pos = end
                return
        self.scrolling_text_pos = pos_after_scroll

    def no_games_cond(self) -> bool:
        """A condition that is true only while there are no games live"""
        return not self.data.schedule.games_live()

    # NFL
    def __render_game(self, gameday=True):
        while True:
            game_index = self.data.nfl_data.current_game_index

            # If we need to refresh the overview data, do that
            if self.data.nfl_data.needs_refresh:
                # print("yes")
                self.data.nfl_data.refresh_games()

            # Draw the current game
            self.__draw_game(self.data.nfl_data.current_game())

            # Set the refresh rate
            refresh_rate = self.data.nfl_data.config.scrolling_speed
            t.sleep(refresh_rate)
            endtime = t.time()
            time_delta = endtime - self.starttime
            time_delta_api = endtime - self.starttime_api
            rotate_rate = self.__rotate_rate_for_game(self.data.nfl_data.current_game())

            # If we're ready to rotate, let's do it
            # fix this u idiot

            # TODO: lol ^ 12/21/25 monitor separate API refresh and rotation
            if time_delta_api >= self.data.config.api_refresh_rate: # rotate_rate:
                self.starttime_api = t.time()
                self.data.nfl_data.needs_refresh = True

                print(time_delta_api, self.data.config.api_refresh_rate)

                # print(self.__should_rotate_to_next_game(self.data.nfl_data.current_game()))
                # print(endtime - self.data.nfl_data.games_refresh_time >= self.data.config.api_refresh_rate, endtime - self.data.nfl_data.games_refresh_time, self.data.config.api_refresh_rate)
                # print(self.data.nfl_data.needs_refresh)

                if endtime - self.data.nfl_data.games_refresh_time >= self.data.config.api_refresh_rate:
                    self.data.nfl_data.refresh_games()

                if self.data.nfl_data.needs_refresh:
                    self.data.nfl_data.refresh_games()

            if time_delta >= rotate_rate:
                print(time_delta, rotate_rate)

                self.starttime = t.time()
                if self.__should_rotate_to_next_game(self.data.nfl_data.current_game()):
                    game = self.data.nfl_data.advance_to_next_game()
            
            if not gameday and self.data.nfl_data.current_game_index == 0 and game_index != 0:
                break

            # if time_delta >= rotate_rate:
            #     self.starttime = t.time()
            #     self.data.nfl_data.needs_refresh = True

            #     refresh = self.data.config.api_refresh_rate * 1000
            #     print(time_delta, rotate_rate)

            #     print(self.__should_rotate_to_next_game(self.data.nfl_data.current_game()))
            #     print(endtime - self.data.nfl_data.games_refresh_time >= refresh)
            #     print(self.data.nfl_data.needs_refresh)

            #     if self.__should_rotate_to_next_game(self.data.nfl_data.current_game()):
            #         game = self.data.nfl_data.advance_to_next_game()



            #     if endtime - self.data.nfl_data.games_refresh_time >= refresh:
            #         self.data.nfl_data.refresh_games()

            #     if self.data.nfl_data.needs_refresh:
            #         self.data.nfl_data.refresh_games()

    def __rotate_rate_for_game(self, game):
        rotate_rate = self.data.nfl_data.config.rotation_rates_live
        if game['state'] == 'pre':
            rotate_rate = self.data.nfl_data.config.rotation_rates_pregame
        if game['state'] == 'post':
            rotate_rate = self.data.nfl_data.config.rotation_rates_final
        if game['timeout'] == 'EH':
            rotate_rate = self.data.nfl_data.config.rotation_rates_half
        return rotate_rate

    def __should_rotate_to_next_game(self, game):
        # print("bello 2")
        # print(self.data.nfl_data.config.rotation_enabled, self.data.nfl_data.config.preferred_teams and not self.data.nfl_data.config.rotation_preferred_team_live_enabled)
        if self.data.nfl_data.config.rotation_enabled == False:
            return False
        
        # Rotate IF the current game doesn't include a preferred team
        # print(TEAM_ID_NAME[int(game['homeid'])], TEAM_ID_NAME[int(game['awayid'])], )
        if (TEAM_ID_NAME[int(game['homeid'])] not in self.data.nfl_data.config.preferred_teams
            and TEAM_ID_NAME[int(game['awayid'])] not in self.data.nfl_data.config.preferred_teams):
            return True

        # Rotate IF there are no preferred teams
        # OR if rotation is enabled for preferred team
        # OR if preferred team isn't live
        stay_on_preferred_team = (self.data.nfl_data.config.preferred_teams 
                                  and not self.data.nfl_data.config.rotation_preferred_team_live_enabled
                                  and not game['over']
                                  and not game['state'] == 'pre')
        return not stay_on_preferred_team

        # figure this out later heh
        # showing_preferred_team = self.data.nfl_data.config.preferred_teams[0] in [game.awayteam, game.hometeam]
        # if showing_preferred_team and game['status']:
        #     if self.data.nfl_data.config.rotation_preferred_team_live_mid_inning == True and Status.is_inning_break(overview.inning_state):
        #         return True
        #     return False

        # return True

    def __draw_game(self, game):
        time = self.data.nfl_data.get_current_date()
        gametime = datetime.strptime(game['date'], "%Y-%m-%dT%H:%MZ")
        if time < gametime - timedelta(hours=1) and game['state'] == 'pre':
            debug.info('Pre-Game State')
            self._draw_pregame(game)
        elif time < gametime and game['state'] == 'pre':
            debug.info('Countdown til gametime')
            self._draw_countdown(game)
        elif game['state'] == 'post':
            debug.info('Final State')
            self._draw_post_game(game)
        else:
            debug.info('Live State, checking every 5s')
            self._draw_live_game(game)
        debug.info('ping render_game')

    def _draw_pregame(self, game):
            time = self.data.nfl_data.get_current_date()
            gamedatetime = self.data.nfl_data.get_gametime()
            if gamedatetime.day == time.day:
                date_text = 'TODAY'
            else:
                date_text = gamedatetime.strftime('%A %-d %b').upper()
            gametime = gamedatetime.strftime("%-I:%M %p")
            # Center the game time on screen.                
            date_pos = center_text(self.font_mini.getbbox(date_text)[2], 32)
            gametime_pos = center_text(self.font_mini.getbbox(gametime)[2], 32)
            # Draw the text on the Data image.
            self.draw.text((date_pos, 0), date_text, font=self.font_mini)
            self.draw.multiline_text((gametime_pos, 6), gametime, fill=(255, 255, 255), font=self.font_mini, align="center")
            self.draw.text((25, 15), 'VS', font=self.font)
            # Put the data on the canvas
            self.canvas.SetImage(self.image, 0, 0)
            if self.data.nfl_data.helmet_logos:
                # Open the logo image file
                away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
                home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1).transpose(Image.FLIP_LEFT_RIGHT)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)
            else:
                # TEMP Open the logo image file
                away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
                home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)
                # awaysize = self.screen_config.team_logos_pos[game['awayteam']]['size']
                # homesize = self.screen_config.team_logos_pos[game['hometeam']]['size']
                # # Set the position of each logo
                # away_team_logo_pos = self.screen_config.team_logos_pos[game['awayteam']]['preaway']
                # home_team_logo_pos = self.screen_config.team_logos_pos[game['hometeam']]['prehome']
                # # Open the logo image file
                # away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((awaysize, awaysize), 1)
                # home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((homesize, homesize), 1)
                # # Put the images on the canvas
                # self.canvas.SetImage(away_team_logo.convert("RGB"), away_team_logo_pos["x"], away_team_logo_pos["y"])
                # self.canvas.SetImage(home_team_logo.convert("RGB"), home_team_logo_pos["x"], home_team_logo_pos["y"])
            # Load the canvas on screen.
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            # Refresh the Data image.
            self.image = Image.new('RGB', (self.width, self.height))
            self.draw = ImageDraw.Draw(self.image)

    def _draw_countdown(self, game):
        time = self.data.nfl_data.get_current_date()
        gametime = datetime.strptime(game['date'], "%Y-%m-%dT%H:%MZ")
        if time < gametime:
            gt = gametime - time
            # as beautiful as I am
            if gt > timedelta(hours=1):
                gametime = ':'.join(str(gametime - time).split(':')[:2])
            else:
                gametime = ':'.join(str(gametime - time).split(':')[1:]).split('.')[:1][0]
            # Center the game time on screen.
            gametime_pos = center_text(self.font_mini.getbbox(gametime)[2], 32)
            # Draw the text on the Data image.
            self.draw.text((29, 0), 'IN', font=self.font_mini)
            self.draw.multiline_text((gametime_pos, 6), gametime, fill=(255, 255, 255), font=self.font_mini, align="center")
            self.draw.text((25, 15), 'VS', font=self.font)
            # Put the data on the canvas
            self.canvas.SetImage(self.image, 0, 0)
            if self.data.nfl_data.helmet_logos:
                # Open the logo image file
                away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
                home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1).transpose(Image.FLIP_LEFT_RIGHT)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)
            else:
                # TEMP Open the logo image file
                away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
                home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
                # Put the images on the canvas
                self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 12)
                self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 12)
                # awaysize = self.screen_config.team_logos_pos[game['awayteam']]['size']
                # homesize = self.screen_config.team_logos_pos[game['hometeam']]['size']
                # # Set the position of each logo
                # away_team_logo_pos = self.screen_config.team_logos_pos[game['awayteam']]['preaway']
                # home_team_logo_pos = self.screen_config.team_logos_pos[game['hometeam']]['prehome']
                # # Open the logo image file
                # away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((awaysize, awaysize), 1)
                # home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((homesize, homesize), 1)
                # # Put the images on the canvas
                # self.canvas.SetImage(away_team_logo.convert("RGB"), away_team_logo_pos["x"], away_team_logo_pos["y"])
                # self.canvas.SetImage(home_team_logo.convert("RGB"), home_team_logo_pos["x"], home_team_logo_pos["y"])
            # Load the canvas on screen.
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            # Refresh the Data image.
            self.image = Image.new('RGB', (self.width, self.height))
            self.draw = ImageDraw.Draw(self.image)
            # t.sleep(1)

    def _draw_live_game(self, game):
        homescore = game['homescore']
        awayscore = game['awayscore']
        # print("home: ", homescore, "away: ", awayscore)
        # Refresh the data
        if self.data.nfl_data.needs_refresh:
            debug.info('Refresh game overview')
            self.data.nfl_data.refresh_games()
            self.data.nfl_data.needs_refresh = False
        # Use this code if you want the animations to run
        if game['homescore'] > homescore + 5 or game['awayscore'] > awayscore + 5:
            debug.info('should draw TD')
            self._draw_td()
        elif game['homescore'] > homescore + 2 or game['awayscore'] > awayscore + 2:
            debug.info('should draw FG')
            self._draw_fg()
        # Prepare the data
        # score = '{}-{}'.format(overview['awayscore'], overview['homescore'])
        if game['possession'] == game['awayid']:
            pos = game['awayteam']
        else:
            pos = game['hometeam']
        quarter = str(game['quarter'])
        time_period = game['time']
        # this is ugly but I want to replace the possession info with down info and spot info
        down = None
        spot = None
        game_info = None
        if game['down']:
            down = re.sub(r"[a-z]+", "", game['down']).replace(" ", "")
            info_pos = center_text(self.font_mini.getbbox(str(down))[2], 32)
            self.draw.multiline_text((info_pos, 19), str(down), fill=(255, 255, 255), font=self.font_mini, align="center")
        if game['spot']:
            spot = game['spot'].replace(" ", "")
            info_pos = center_text(self.font_mini.getbbox(spot)[2], 32)
            self.draw.multiline_text((info_pos, 25), spot, fill=(255, 255, 255), font=self.font_mini, align="center")
        pos_colour = (255, 255, 255)
        if game['redzone']:
            pos_colour = (255, 25, 25)
        # Set the position of the information on screen.
        homescore = '{0:02d}'.format(homescore)
        awayscore = '{0:02d}'.format(awayscore)
        home_score_size = self.font.getbbox(homescore)[2]
        home_score_pos = center_text(self.font.getbbox(homescore)[2], 16)
        away_score_pos = center_text(self.font.getbbox(awayscore)[2], 48)
        time_period_pos = center_text(self.font_mini.getbbox(time_period)[2], 32)
        # score_position = center_text(self.font.getbbox(score)[2], 32)
        quarter_position = center_text(self.font_mini.getbbox(quarter)[2], 32)
        info_pos = center_text(self.font_mini.getbbox(pos)[2], 32)
        self.draw.multiline_text((info_pos, 13), pos, fill=pos_colour, font=self.font_mini, align="center")
        self.draw.multiline_text((quarter_position, 0), quarter, fill=(255, 255, 255), font=self.font_mini, align="center")
        self.draw.multiline_text((time_period_pos, 6), time_period, fill=(255, 255, 255), font=self.font_mini, align="center")
        self.draw.multiline_text((6, 19), awayscore, fill=(255, 255, 255), font=self.font, align="center")
        self.draw.multiline_text((59 - home_score_size, 19), homescore, fill=(255, 255, 255), font=self.font, align="center")
        # Put the data on the canvas
        self.canvas.SetImage(self.image, 0, 0)
        if self.data.nfl_data.helmet_logos:
            # Open the logo image file
            away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
            home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1).transpose(Image.FLIP_LEFT_RIGHT)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        else:
            # TEMP Open the logo image file
            away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
            home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        # Set the position of each logo on screen.
        # awaysize = self.screen_config.team_logos_pos[game['awayteam']]['size']
        # homesize = self.screen_config.team_logos_pos[game['hometeam']]['size']
        # # Set the position of each logo
        # away_team_logo_pos = self.screen_config.team_logos_pos[game['awayteam']]['away']
        # home_team_logo_pos = self.screen_config.team_logos_pos[game['hometeam']]['home']
        # # Open the logo image file
        # away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((19, 19), 1)
        # home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((19, 19), 1)
        # Draw the text on the Data image.
        # self.draw.multiline_text((quarter_position, 0), quarter, fill=(255, 255, 255), font=self.font_mini, align="center")
        # self.draw.multiline_text((time_period_pos, 6), time_period, fill=(255, 255, 255), font=self.font_mini, align="center")
        # self.draw.multiline_text((6, 19), awayscore, fill=(255, 255, 255), font=self.font, align="center")
        # self.draw.multiline_text((59 - home_score_size, 19), homescore, fill=(255, 255, 255), font=self.font, align="center")
        # self.draw.multiline_text((score_position, 19), score, fill=(255, 255, 255), font=self.font, align="center")
        # Put the images on the canvas
        # self.canvas.SetImage(away_team_logo.convert("RGB"), away_team_logo_pos["x"], away_team_logo_pos["y"])
        # self.canvas.SetImage(home_team_logo.convert("RGB"), home_team_logo_pos["x"], home_team_logo_pos["y"])
        # Load the canvas on screen.
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        # Refresh the Data image.
        self.image = Image.new('RGB', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)
        # Check if the game is over
        if game['state'] == 'post':
            debug.info('GAME OVER')
        # Save the scores.
        # awayscore = game['awayscore']
        # homescore = game['homescore']

        # TODO: 12/18/25 Monitor this fix
        # self.data.nfl_data.needs_refresh = True

    def _draw_post_game(self, game):
        # Prepare the data
        score = '{}-{}'.format(game['awayscore'], game['homescore'])
        # Set the position of the information on screen.
        score_position = center_text(self.font.getbbox(score)[2], 32)
        # Draw the text on the Data image.
        self.draw.multiline_text((score_position, 19), score, fill=(255, 255, 255), font=self.font, align="center")
        self.draw.multiline_text((26, 0), "END", fill=(255, 255, 255), font=self.font_mini,align="center")
        # Put the data on the canvas
        self.canvas.SetImage(self.image, 0, 0)
        if self.data.nfl_data.helmet_logos:
            # Open the logo image file
            away_team_logo = Image.open('logos/{}H.png'.format(game['awayteam'])).resize((20, 20), 1)
            home_team_logo = Image.open('logos/{}H.png'.format(game['hometeam'])).resize((20, 20), 1).transpose(Image.FLIP_LEFT_RIGHT)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        else:
            # TEMP Open the logo image file
            away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((20, 20), Image.BOX)
            home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((20, 20), Image.BOX)
            # Put the images on the canvas
            self.canvas.SetImage(away_team_logo.convert("RGB"), 1, 0)
            self.canvas.SetImage(home_team_logo.convert("RGB"), 43, 0)
        # awaysize = self.screen_config.team_logos_pos[overview['hometeam']]['size']
        # homesize = self.screen_config.team_logos_pos[overview['awayteam']]['size']
        # awaysize = self.screen_config.team_logos_pos[game['awayteam']]['size']
        # homesize = self.screen_config.team_logos_pos[game['hometeam']]['size']
        # Set the position of each logo
        # away_team_logo_pos = self.screen_config.team_logos_pos[overview['hometeam']]['away']
        # home_team_logo_pos = self.screen_config.team_logos_pos[overview['awayteam']]['home']
        # away_team_logo_pos = self.screen_config.team_logos_pos[game['awayteam']]['away']
        # home_team_logo_pos = self.screen_config.team_logos_pos[game['hometeam']]['home']
        # Open the logo image file
        # away_team_logo = Image.open('logos/{}.png'.format(overview['hometeam'])).resize((awaysize, awaysize), 1)
        # home_team_logo = Image.open('logos/{}.png'.format(overview['awayteam'])).resize((homesize, homesize), 1)
        # away_team_logo = Image.open('logos/{}.png'.format(game['awayteam'])).resize((19, 19), 1)
        # home_team_logo = Image.open('logos/{}.png'.format(game['hometeam'])).resize((19, 19), 1)
        # Put the images on the canvas
        # self.canvas.SetImage(away_team_logo.convert("RGB"), away_team_logo_pos["x"], away_team_logo_pos["y"])
        # self.canvas.SetImage(home_team_logo.convert("RGB"), home_team_logo_pos["x"], home_team_logo_pos["y"])
        # Load the canvas on screen.
        self.canvas = self.matrix.SwapOnVSync(self.canvas)
        # Refresh the Data image.
        self.image = Image.new('RGB', (self.width, self.height))
        self.draw = ImageDraw.Draw(self.image)

    def _draw_td(self):
        debug.info('TD')
        # Load the gif file
        ball = Image.open("assets/td_ball.gif")
        words = Image.open("assets/td_words.gif")
        # Set the frame index to 0
        frameNo = 0
        self.canvas.Clear()
        # Go through the frames
        x = 0
        while x != 3:
            try:
                ball.seek(frameNo)
            except EOFError:
                x += 1
                frameNo = 0
                ball.seek(frameNo)
            self.canvas.SetImage(ball.convert('RGB'), 0, 0)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            frameNo += 1
            t.sleep(0.05)
        x = 0
        while x != 3:
            try:
                words.seek(frameNo)
            except EOFError:
                x += 1
                frameNo = 0
                words.seek(frameNo)
            self.canvas.SetImage(words.convert('RGB'), 0, 0)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            frameNo += 1
            t.sleep(0.05)

    def _draw_fg(self):
        debug.info('FG')
        # Load the gif file
        im = Image.open("assets/fg.gif")
        # Set the frame index to 0
        frameNo = 0
        self.canvas.Clear()
        # Go through the frames
        x = 0
        while x != 3:
            try:
                im.seek(frameNo)
            except EOFError:
                x += 1
                frameNo = 0
                im.seek(frameNo)
            self.canvas.SetImage(im.convert('RGB'), 0, 0)
            self.canvas = self.matrix.SwapOnVSync(self.canvas)
            frameNo += 1
            t.sleep(0.02)

def permanent_cond() -> bool:
    """A condition that is always true"""
    return True


def timer_cond(seconds) -> Callable[[], bool]:
    """Create a condition that is true for the specified number of seconds"""
    end = time.time() + seconds

    def cond():
        return time.time() < end

    return cond


def all_of(*conds) -> Callable[[], bool]:
    """Create a condition that is true if all of the given conditions are true"""

    def cond():
        return all(c() for c in conds)

    return cond
