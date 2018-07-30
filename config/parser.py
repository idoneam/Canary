import configparser


class Parser:
    def __init__(self):
        self.configfile = './config/config.ini'

        config = configparser.ConfigParser()
        config.read(self.configfile)

        self.discord_key = config['Discord']['Key']

        self.welcome = config['Greetings']['Welcome'].split('\n')
        self.goodbye = config['Greetings']['Goodbye'].split('\n')

        self.db_path = config['DB']['Path']
