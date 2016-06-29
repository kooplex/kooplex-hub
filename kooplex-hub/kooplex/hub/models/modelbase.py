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

    def get_from_dict(d, keys):
        if type(keys) is str:
            if not d or type(d) is not dict:
                return None
            else:
                return d[keys]
        elif hasattr(keys, '__iter__'):
            for k in keys:
                if not d or type(d) is not dict:
                    return None
                if k in d:
                    d = d[k]
            return d
        else:
            return None