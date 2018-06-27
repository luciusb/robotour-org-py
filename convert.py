import json
from os.path import join as pjoin
from app import User, event
from datetime import datetime


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%d.%m.%Y %H:%M")
        return json.JSONEncoder.default(self, o)


defaultsdir = 'defaults'
for fn in ('users.txt', 'points.txt', 'config.txt'):
    data = eval(open(fn, 'r').read())
    if fn in ('users.txt', 'config.txt'):
        data = [u._asdict() for u in data]
    with open(pjoin(defaultsdir, fn), 'w') as f:
        json.dump(data, f, cls=DateTimeEncoder, indent=4)
