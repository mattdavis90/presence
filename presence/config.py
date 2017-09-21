from configparser import ConfigParser


class Config(dict):
    def read(self, config_file):
        with open(config_file, 'rb') as f:
            d = {}
            exec (compile(f.read(), '<config-file>', 'exec'), d)
            self.update({k: v for k, v in d.items() if not k.startswith('_')})
