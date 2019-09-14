import sys
from flask_login import UserMixin
from collections import namedtuple
from datetime import datetime
from os.path import join as pjoin, exists
import json
from decimal import Decimal
import logging

user_config = {}
users_index = {}


class DateTimeEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, datetime):
            return o.strftime("%d.%m.%Y %H:%M")
        return json.JSONEncoder.default(self, o)


class DecimalEncoder(json.JSONEncoder):
    def default(self, o):
        if isinstance(o, Decimal):
            return str(o)
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


event = namedtuple('event', ('name', 'start', 'end', 'pickup', 'dropoff', 'notes'))


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
    users, points, config, results = readConfig(cfdir='admin')
    for u in users:
        users_index[u["username"]] = User(**u)
    name, utc_offset, events, meetings = parseEvents(config)
    user_config[None] = Competition(name=name, utc_offset=utc_offset, points=points, events=events, results=results, meetings=meetings)
    for user in users_index.values():
        if user.role == 'user':
            reload_user(user.username)
    print("Reload", users_index)


def reload_user(username):
    _, points, config, _2 = readConfig(cfdir=pjoin('users', username))
    name, utc_offset, events, meetings = parseEvents(config)
    user_config[username] = Competition(name=name, utc_offset=utc_offset, points=points, events=events, results=None, meetings=meetings)


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


def update_results(results, roundscnt):
    for team in results:
        total = Decimal()
        rounds = []
        for i in range(roundscnt):
            if i >= len(team["rounds"]):
                rounds.append("")
            else:
                rounds.append(team["rounds"][i])
                # ignore the 0.th round
                if i > 0:
                    try:
                        total += Decimal(team["rounds"][i])
                    except:
                        pass
        team["rounds"] = rounds
        team["total"] = total
    results.sort(key=lambda x: x["total"], reverse=True)
    return results


class Competition:
    def __init__(self, name, utc_offset, points, events, meetings, results=None):
        self.name = name
        self.utc_offset = utc_offset
        self.events = events
        self.meetings = meetings
        self.points = points
        if results:
            results = update_results(results, roundscnt=len(events))
        self.results = results
        self.times = list(timeranges(events))
        self.times_with_meetings = list(timeranges(events+meetings))
        self.testindex = 0
        self.printerindex = 0
        self.printer_pickup = True

    def getEvent(self, time, include_meetings=False):
        events = list(self.events)
        if include_meetings:
            events += self.meetings
        for event in sorted(events, key=lambda x: x.start):
            if event.start < time < event.end:
                return event
        else:
            return None

    def getEvents(self, include_meetings=False):
        aevents = list(self.events)
        if include_meetings:
            aevents += self.meetings
        return sorted(aevents, key = lambda x: x.start)

    def test(self, include_meetings=False):
        if include_meetings:
            times=self.times_with_meetings
        else:
            times=self.times
        t = times[self.testindex]
        self.testindex += 1
        if self.testindex >= len(times):
            self.testindex = 0
        return t

    def printer(self):
        if self.printerindex >= len(self.events):
            self.printerindex = 0
            return None, False
        result = self.events[self.printerindex], self.printer_pickup
        self.printer_pickup = not self.printer_pickup
        if self.printer_pickup:
            self.printerindex +=1
        return result


def parseEvents(config):
    events = []
    meetings = []
    for e in config["events"]:
        e["start"] = datetime.strptime(e["start"], "%d.%m.%Y %H:%M")
        e["end"] = datetime.strptime(e["end"], "%d.%m.%Y %H:%M")
        events.append(event(**e))
    for e in config["meetings"]:
        e["start"] = datetime.strptime(e["start"], "%d.%m.%Y %H:%M")
        e["end"] = datetime.strptime(e["end"], "%d.%m.%Y %H:%M")
        meetings.append(event(**e))
    return config["name"], config["utc_offset"], events, meetings


def save_results(results):
    with open(pjoin('admin', 'results.json'), 'w') as f:
        json.dump(results, f, cls=DecimalEncoder, indent=4)


def save_users(users):
    with open(pjoin('admin', 'users.json'), 'w') as f:
        data = [u._asdict() for u in users]
        json.dump(data, f, cls=DateTimeEncoder, indent=4)
