from docker.client import Client
from kooplex.lib import get_settings
import re

class Docker:
    base_url = get_settings('docker', 'base_url')
    #FIXME: settings_py '^##PRFIX##-notebook-\w+$'
    pattern_imagename_notebook = r'^kooplex-notebook-(\w+):\w+$'

    def __init__(self):
        self.client = Client(base_url = self.base_url)

    def list_imagenames(self):
        for image in self.client.images(all = True):
            for tag in image['RepoTags']:
                if re.match(self.pattern_imagename_notebook, tag):
                    _, imagename, _ = re.split(self.pattern_imagename_notebook, tag)
                    yield imagename
 
