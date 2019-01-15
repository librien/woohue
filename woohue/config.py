from phue import Bridge
from pprint import pprint
from pick import pick
from itertools import cycle
import json
import time
import toml
import requests

#config = configparser.ConfigParser()
config = {}

def main():
    open_config()

#def writeConfig():

def get_bridge_ip():
    try:
        input('Please press the round button on your Hue Bridge and then press enter to continue.')
        print('Searching for Hue Bridge...')
        
        '''
        Phue library not discovering correctly; retrieve IP address manually
        #bridge = Bridge(ip)
        #ip = bridge.get_ip_address()
        '''
        ip = requests.get("https://www.meethue.com/api/nupnp").json()[0]['internalipaddress']
        print('Hue Bridge discovered successfully.')
        print('Please ensure your lights are powered on and currently illuminated.  Press enter to continue.')
    except Exception as e:
        print('Unable to find Hue Bridge')
        print(e)
    else: 
        return ip
    
def config_lights(ip):
    print('Retrieving lights...')
    bridge = Bridge(ip)
    lights = []
    for light in bridge.lights:
        try:
            bridge.get_light(light.name, 'colormode')
        except KeyError:
            pass
        else: lights.append(light.name)
       
    try:     
        title = 'Please use the spacebar to select at least one light from the choices below: '
        selectedLights = pick(lights, title, multi_select=True, min_selection_count=1, indicator='->')
    except:
        print('Sorry, setup was unable to find any color capable hue lights connected to your bridge.')
        return
    else:
        goal_lights = {}
        goal_lights['Lights'] = []
        for light in selectedLights:
            goal_lights['Lights'].append(light[0])

    return goal_lights
          

def set_teams():
    
    with open('nhlteams.json') as data_file:
        data = json.loads(data_file.read())
    title = 'Please use the spacebar to select a team from the choices below: '
    options = data['teams']
    def get_name(option): 
        return option.get('team-name')
    team, teamIndex = pick(options, title, min_selection_count=1, indicator='->', options_map_func=get_name)
    teams = {}
    teams['Team'] = []
    teams['Team'].append(team)
    return teams

def open_config():
    print("Loading configuration...")
    for i in range(0,100):
        while True:
            try: 
                with open('config.toml') as configfile:
                    config = toml.loads(configfile.read())
                print('Configuration loaded succesfully...')
                return config
      
            except Exception as e: 
                input("Please read the README file before beginning.  Press enter to continue.")
                config = {}
                print('Unable to find existing configuration')
                print('Running woohue configuration setup...')
                ip = get_bridge_ip()
                config['Bridge'] = {'ip': ip}
                config['Goal_Lights'] = config_lights(ip)
                config['Teams'] = set_teams()
                try:
                    with open('config.toml', 'w') as configfile:
                        toml.dump(config, configfile)
                    print('Configuration saved successfully')
                except Exception as e:
                    print(e)

if __name__ == "__main__":
    main()


