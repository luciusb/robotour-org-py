from flask import Flask, Response, redirect, request, abort, render_template, flash, send_from_directory  # url_for
from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user, current_user
from flask_qrcode import QRcode
from datetime import datetime, timedelta
from collections import namedtuple
import os
from os.path import join as pjoin, exists
import json

app = Flask(__name__)
QRcode(app)

user_config = {}

# config
app.config.update(
    DEBUG=True,
    SECRET_KEY='secret_xxx'
)

# flask-login
login_manager = LoginManager(app)
login_manager.login_view = "login"


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
    for fn in ('users.json', 'points.json', 'config.json'):
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
    global users_index
    global user_config
    users, points, events = readConfig(cfdir='admin')
    events = [event(**e) for e in events]
    users_index = {u["username"]: User(**u) for u in users}
    user_config[None] = Competition(points=points, events=events)
    for user in users_index.values():
        if user.role == 'user':
            reload_user(user.username)


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
    def __init__(self, points, events):
        self.events = events
        self.points = points
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


def reload_user(username):
    global user_config
    _, points, events = readConfig(cfdir=pjoin('users', username))
    events = [event(**e) for e in events]
    user_config[username] = Competition(points=points, events=events)


reload()


@app.route('/delivery<int:round>')
@login_required
def delivery(round):
    return render_template("delivery.html", round=round)


@app.route('/pickup<int:round>')
def pickup(round):
    return render_template("pickup.html", round=round)


@app.route('/')
def auto(user=None):
    now = datetime.now()
    for event in user_config[user].events:
        if event.start < now < event.end:
            return render_template("auto.html", name=event.name, qr="geo:%s,%s" % ll(user_config[user].points[event.start], refresh=5))
    else:
        return render_template("program.html", events=user_config[user].events, refresh=5, now=now)


@app.route('/test')
@login_required
def test():
    global user_config
    if current_user.role in ('admin', 'referee'):
        user = None
    elif current_user.role == 'user':
        user = current_user.username
    else:
        flash("Testing is not accesible for %s role: %s" % (current_user.username, current_user.role))
        redirect('/')
    start, end = user_config[user].test()
    if not start:
        return render_template("program.html", events=user_config[user].events, refresh=5, now=end[0]-timedelta(minutes=1),
                               header="Till %s" % end[0].strftime("%d.%m.%Y %H:%M"))
    elif not end:
        return render_template("program.html", events=user_config[user].events, refresh=5, now=start[0]+timedelta(minutes=1),
                               header="after %s" % start[0].strftime("%d.%m.%Y %H:%M"))
    else:
        header = "from %s to %s" % (start[0].strftime("%d.%m.%Y %H:%M"), end[0].strftime("%d.%m.%Y %H:%M"))
        now = end[0]-timedelta(minutes=1)
        event = user_config[user].getEvent(now)
        if event:
            print(repr(user_config[user].points))
            pickup = ll(user_config[user].points[event.pickup])
            dropoff = ll(user_config[user].points[event.dropoff])
            return render_template("auto.html", name=event.name + " pickup", qr="geo:%s,%s" % pickup, refresh=5, header=header) + \
                render_template("auto.html", name=event.name + " dropoff", qr="geo:%s,%s" % dropoff, refresh=5, header=header)
        else:
            return render_template("program.html", events=user_config[user].events, refresh=5, now=now, header=header)


# somewhere to login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users_index and password == users_index[username].password:
            login_user(users_index[username])
            return redirect(request.args.get("next"))
        else:
            return abort(401)
    else:
        return Response('''
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
        ''')


def save_users(users):
    with open(pjoin('admin', 'users.json'), 'w') as f:
        data = [u._asdict() for u in users]
        json.dump(data, f, cls=DateTimeEncoder, indent=4)


@app.route("/register", methods=["GET", "POST"])
def register():
    global users_index
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        passconfirm = request.form['passconfirm']
        if username in users_index:
            flash("User already exists, please select another username")
            return redirect(request.url)
        if not password == passconfirm:
            flash("Password do not match")
            return redirect(request.url)
        new = User(username=username, password=password, role='user')
        users_index[new.username] = new
        login_user(new)
        save_users(users_index.values())
        return redirect('/config')
    else:
        return render_template('register.html')

# @app.route("/user")
# def user


# somewhere to logout
@app.route("/logout")
@login_required
def logout():
    logout_user()
    return Response('<p>Logged out</p>')


# handle login failed
@app.errorhandler(401)
def page_not_found(e):
    return Response('<p>Login failed</p>')


# callback to reload the user object
@login_manager.user_loader
def load_user(userid):
    return users_index.get(userid, None)


@app.route('/config', methods=['GET', 'POST'])
@login_required
def upload_file():
    if request.method == 'POST':
        if current_user.role == 'admin':
            cfdir = 'admin'
        else:
            cfdir = pjoin('users', current_user.username)
        need_reload = False
        for input_name in ('users', 'points', 'config', 'file'):
            # check if the post request has the file part
            if input_name in request.files:
                file = request.files[input_name]
                if file.filename.lower() == input_name+'.json':
                    if not exists(cfdir):
                        os.makedirs(cfdir)
                    file.save(pjoin(cfdir, input_name+'.json'))
                    flash('%s upadated' % input_name)
                    need_reload = True
                else:
                    flash('Wrong filename %s, for %s, expected %s' % (file.filename, input_name, input_name+'.json'))
        else:
            flash('No file selected')
        if need_reload:
            if current_user.role == 'admin':
                reload()
            else:
                reload_user(current_user.username)
        return redirect(request.url)
    return render_template('config.html', admin=(current_user.role == 'admin'))


@app.route('/download/<filename>')
@login_required
def download(filename):
    if current_user.role == 'admin':
        if filename in ('config.json', 'points.json', 'users.json'):
            if exists(pjoin('admin', filename)):
                dir = 'admin'
            else:
                dir = 'defaults'
            return send_from_directory(dir, filename)
    elif current_user.role == 'user':
        if filename in ('config.json', 'points.json'):
            if exists(pjoin('users', current_user.username, filename)):
                dir = pjoin('users', current_user.username)
            else:
                dir = 'defaults'
            return send_from_directory(dir, filename)
    return abort(401)


if __name__ == "__main__":
    app.run()
