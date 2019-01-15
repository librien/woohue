from pprint import pprint
from urllib import request
from optparse import OptionParser
from itertools import cycle
from rgbxy import Converter
import datetime
import json
import os
import re
import platform
import sys
import time
import requests
import socket 
import curses
import config

def run_once(f):
    def wrapper(*args, **kwargs):
        if not wrapper.has_run:
            wrapper.has_run = True
            return f(*args, **kwargs)
    wrapper.has_run = False
    return wrapper

def clear_screen():
    if platform.system() == 'Windows':
        os.system('cls')
    else:
        os.system('clear')

def activate_goal_light(woohue_config, team):
    team_colors = []
    team_colors.append(team['primary-color']) # Team primary color
    team_colors.append(team['secondary-color']) # Team secondary color
    existingState = []
    for light in woohue_config.goal_lights:
        existingState.append(config.Bridge(woohue_config.ip).get_light(light, 'xy'))

    converter = Converter()
    for i, item in enumerate(team_colors):
        xy_color = converter.hex_to_xy(item)
        team_colors[i] = xy_color
    c = cycle(team_colors)
    for i in range(9):
        team_color = next(c)
        try:
            config.Bridge(woohue_config.ip).set_light(woohue_config.goal_lights, 'xy', team_color, transitiontime=0)
        except Exception as e:
            print(e)
        time.sleep(.5)

    #Restore previous color values
    for i in range(2):
        config.Bridge(woohue_config.ip).set_light(woohue_config.goal_lights[i], 'xy', existingState[i])

class configuration:
    def __init__(self, config_obj):
        self.config = config_obj
        self.ip = self.config['Bridge']['ip']
        self.goal_lights = self.config['Goal_Lights']['Lights']
        self.teams = self.config['Teams']['Team']

try:
    woohue_config = configuration(config.open_config())
except Exception as e:
    print(e)
else:
    activate_goal_light(woohue_config, woohue_config.teams[0])

class game:
    def __init__(self, team):
        self.team = team
        self.initial_score = 0
        self.get_game()
        self.watch_game()

    @run_once
    def start_game(self):
        clear_screen()
        print("Game time!")
        self.chant()
        print(self.score_line)
        self.puck_in_play = False
        self.end_of_period = False
        self.beginning_of_period = False

    def chant(self):
        print("Let's go {}!".format(self.team['team-name']))
        print(self.team['chant'])

    def get_ice_time(self, time_remaining, current_period):
        if time_remaining == "END":
            self.puck_in_play = False
            self.ice_time = time_remaining + " of " +  current_period
            if self.end_of_period == False:
                print(self.ice_time)
                self.end_of_period = True
        
        elif time_remaining == "20:00" or (time_remaining == "05:00" and current_period == "OT"):
            self.end_of_period = False
            self.ice_time = "Start of " + current_period
            if self.beginning_of_period == False:
                print(self.ice_time)
                self.beginning_of_period = True

        elif time_remaining == "Final":
            self.puck_in_play = False
            self.ice_time = "Final"

        else:
            self.ice_time = time_remaining + " in " + current_period
            if self.puck_in_play == False:
                print(self.ice_time)
                self.puck_in_play = True
            self.end_of_period = False
            self.beginning_of_period = False
    
    def get_game(self):
        try:
            api_url = ("https://statsapi.web.nhl.com/api/v1/schedule?teamId="+str(self.team['id'])+"&expand=schedule.linescore")
            self.game = requests.get(api_url).json()['dates'][0]['games'][0]
            self.status = int(self.game['status']['statusCode'])
            self.game_id = self.game['gamePk']
            self.game_time = datetime.datetime.strptime(self.game['gameDate'], "%Y-%m-%dT%H:%M:%SZ")
            self.puck_in_play = None
            self.score_line = self.game['teams']['away']['team']['name'] + " " + str(self.game['linescore']['teams']['away']['goals']) + " " + self.game['teams']['home']['team']['name'] + " " + str(self.game['linescore']['teams']['home']['goals'])
            def home_or_away(self):
                if self.team['id'] == self.game['teams']['home']['team']['id']:
                    return "home"
                elif self.team['id'] == self.game['teams']['away']['team']['id']:
                    return "away"
            self.home_or_away = home_or_away(self)
            self.score = self.game['linescore']['teams'][self.home_or_away]['goals']
            self.initial_score = self.game['linescore']['teams'][home_or_away(self)]['goals']
        except IndexError:
            print("\rNo games scheduled for today")
            '''
            Todo: Figure out a way to sleep / rerun script next day when a game is scheduled.
            Implement offseason handling?
            '''
            input('Try running the program on gameday. Press enter to exit.')
            sys.exit()
        except Exception as e:
            print(e)
            #sys.exit()

    def update_game(self):
        try:
            api_url = ("https://statsapi.web.nhl.com/api/v1/schedule?teamId="+str(self.team['id'])+"&expand=schedule.linescore")
            self.game = requests.get(api_url).json()['dates'][0]['games'][0]
            self.status = int(self.game['status']['statusCode'])
            self.game_time = datetime.datetime.strptime(self.game['gameDate'], "%Y-%m-%dT%H:%M:%SZ")
            self.score = self.game['linescore']['teams'][self.home_or_away]['goals']
            self.score_line = self.game['teams']['away']['team']['name'] + " " + str(self.game['linescore']['teams']['away']['goals']) + " " + self.game['teams']['home']['team']['name'] + " " + str(self.game['linescore']['teams']['home']['goals'])

        except Exception as e:
            print(e)

    def watch_game(self):
        current_time = datetime.datetime.utcnow()
        #activate_goal_light(woohue_config, self.team) #test goal light on program start
        while True:
            self.update_game()
            '''
            NHL API Game status.statusCode legend:
            1 - 
            2 - Pregame
            3 - In Progress
            4 - In Progress - Critical (OT)
            5 - SO?
            6 - Final
            '''
            if (self.status < 2):
                self.ice_time = "Gameday"
                pause_time = self.game_time - current_time
                pause_time = pause_time.seconds
                for i in range(pause_time):
                    sys.stdout.write("\rGame starting in approximately {0}.".format(str(datetime.timedelta(seconds=pause_time))))
                    sys.stdout.flush()
                    pause_time -= 1
                    time.sleep(1)
            elif (self.status == 2):
                self.ice_time = "Pregame"
                #print("Pregame! Waiting for puckdrop...")
                time.sleep(30)
            elif (self.status > 2 and self.status < 6):
                '''
                Todo: Implement way to show ice_time changes only once (end of periods, beginning of periods)
                '''
                
                if (self.game['linescore']['currentPeriodTimeRemaining'] and self.game['linescore']['currentPeriodOrdinal']):
                    self.start_game()
                    self.get_ice_time(self.game['linescore']['currentPeriodTimeRemaining'], self.game['linescore']['currentPeriodOrdinal'])

                def watch_score():
                    if (self.score > self.initial_score):
                        print('GOAL!')
                        print(self.score_line)
                        '''
                        Time of goal is not always accurate. 
                        It just returns the current time when API is updated.
                        '''
                        print('Time of Goal: ' + self.ice_time)
                        try: 
                            activate_goal_light(woohue_config, self.team)
                        except Exception as e:
                            print(e)
                        self.initial_score = self.score
                        self.chant()

                watch_score()
                time.sleep(10)

            elif (self.status >= 6):
                self.ice_time = "Final"
                print("Game is over")
                #time.sleep(30)
                print(self.score_line)
                break

def main():
    
    clear_screen()

    for team in woohue_config.teams:
        new_game = game(team)
        print("------------")

def get_teams():
    '''
    Retrieves JSON object of NHL teams
    '''
    api_url = ("https://statsapi.web.nhl.com/api/v1/teams")
    teams = requests.get(api_url).json()
    return teams

if __name__ == "__main__":
    main()


#pprint(get_teams())
