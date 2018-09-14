from flask_login import UserMixin
from collections import namedtuple
from datetime import datetime
from os.path import join as pjoin, exists
import json
from decimal import Decimal

user_config = {}
users_index = {}


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%d.%m.%Y %H:%M")
        return json.JSONEncoder.default(self, o)


# silly user model
class User(UserMixin):
    def __init__(self, username, password, role='referee'):
        # self.id = username
        self.username = username
        self.password = password
        self.role = role

    def __repr__(self):
        return "User(username='%s', password='%s', role='%s')" % (self.username, self.password, self.role)

    def get_id(self):
        return self.username

    def _asdict(self):
        return self.__dict__


event = namedtuple('event', ('name', 'start', 'end', 'pickup', 'dropoff'))


# add_constructor(u'!User', User_constructor)


def readConfig(cfdir):
    """
    default configs are in defaults directory and they get updated from github
    user generated configs live in config directory and overide the default config

    """
    defaultsdir = 'defaults'
    result = []
    for fn in ('users.json', 'points.json', 'config.json', 'results.json'):
        if exists(pjoin(cfdir, fn)):
            fn = pjoin(cfdir, fn)
        else:
            fn = pjoin(defaultsdir, fn)
        with open(fn, 'r') as f:
            result.append(json.load(f))
    return result


def ll(latlon):
    lat, lon = latlon.split()
    lat = lat.split('=')[1]
    lon = lon.split('=')[1]
    return lat, lon


def reload():
    users, points, events, results = readConfig(cfdir='admin')
    for u in users:
        users_index[u["username"]] = User(**u)
    user_config[None] = Competition(points=points, events=parseEvents(events), results=results)
    for user in users_index.values():
        if user.role == 'user':
            reload_user(user.username)
    print("Reload", users_index)


def reload_user(username):
    _, points, events, _2 = readConfig(cfdir=pjoin('users', username))
    user_config[username] = Competition(points=points, events=parseEvents(events), results=None)


def timeranges(events):
    if not events:
        return
    times = []
    for i, event in enumerate(events):
        times.append((event.start, 'start', i))
        times.append((event.end, 'end', i))
    times.sort()
    yield (None, times[0])
    for s, e in zip(times, times[1:]):
        yield (s, e)
    yield (times[-1], None)


class Competition:
    def __init__(self, points, events, results=None):
        self.events = events
        maxrounds = len(events)
        self.points = points
        if results:
            # maxrounds = max((len(x["rounds"]) for x in results))
            # self.rounds = ["Round%i" % i for i in range(maxrounds)]
            team_id = 0
            for team in results:
                total = Decimal()
                rounds = []
                for i in range(maxrounds):
                    if i >= len(team["rounds"]):
                        rounds.append("")
                    else:
                        rounds.append(team["rounds"][i])
                        try:
                            total += Decimal(team["rounds"][i])
                        except:
                            pass
                team["id"] = team_id
                team_id += 1
                team["rounds"] = rounds
                team["total"] = total
            results.sort(key=lambda x: x["total"], reverse=True)
        self.results = results
        self.times = list(timeranges(events))
        self.testindex = 0

    def getEvent(self, time):
        for event in self.events:
            if event.start < time < event.end:
                return event
        else:
            return None

    def test(self):
        t = self.times[self.testindex]
        self.testindex += 1
        if self.testindex >= len(self.times):
            self.testindex = 0
        return t


def parseEvents(revents):
    events = []
    for e in revents:
        e["start"] = datetime.strptime(e["start"], "%d.%m.%Y %H:%M")
        e["end"] = datetime.strptime(e["end"], "%d.%m.%Y %H:%M")
        events.append(event(**e))
    return events


def save_users(users):
    with open(pjoin('admin', 'users.json'), 'w') as f:
        data = [u._asdict() for u in users]
        json.dump(data, f, cls=DateTimeEncoder, indent=4)
