import json

class ModelBase():

    def load_json(self, value):
        if not value or len(value) == 0:
            return None
        else:
            return json.loads(value)

    def save_json(self, value):
        if not value:
            return ''
        else:
            return json.dumps(value)