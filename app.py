from flask import Flask, Response, redirect, request, abort, render_template
# from flask.ext.login import LoginManager, UserMixin, login_required, login_user, logout_user
from flask_login import LoginManager, UserMixin, login_required, logout_user, login_user
from flask_qrcode import QRcode
from datetime import datetime, timedelta
from collections import namedtuple

app = Flask(__name__)
QRcode(app)

# config
app.config.update(
    DEBUG=True,
    SECRET_KEY='secret_xxx'
)

# flask-login
login_manager = LoginManager(app)
login_manager.login_view = "login"


# silly user model
class User(UserMixin):

    def __init__(self, id, password):
        self.id = id
        self.name = id
        self.password = password

    def __repr__(self):
        return "%d/%s/%s" % (self.id, self.name, self.password)


users = []


event = namedtuple('event', ('name', 'start', 'end', 'pickup', 'dropoff'))


def readConfig():
    users = eval(open('users.txt').read())
    points = eval(open('points.txt').read())
    events = eval(open('config.txt').read())
    events.sort(key=lambda x: x.start)
    return users, points, events


def ll(latlon):
    lat, lon = latlon.split()
    lat = lat.split('=')[1]
    lon = lon.split('=')[1]
    return lat, lon


u, points, events = readConfig()
users = {id: User(id, password) for id, password in u}


# some protected url
@app.route('/delivery<int:round>')
@login_required
def delivery(round):
    return render_template("delivery.html", round=round)


@app.route('/pickup<int:round>')
def pickup(round):
    return render_template("pickup.html", round=round)


@app.route('/auto')
def auto():
    now = datetime.now()
    for event in events:
        if event.start < now < event.end:
            return render_template("auto.html", name=event.name, qr="geo:%s,%s" % ll(points[event.start], refresh=5))
    else:
        return render_template("program.html", events=events, refresh=5, now=now)


def timeranges(events):
    times = []
    for i, event in enumerate(events):
        times.append((event.start, 'start', i))
        times.append((event.end, 'end', i))
    times.sort()
    yield (None, times[0])
    for s, e in zip(times, times[1:]):
        yield (s, e)
    yield (times[-1], None)


times = list(timeranges(events))
testindex = 0


@app.route('/test')
@login_required
def test():
    global testindex
    start, end = times[testindex]
    testindex += 1
    if testindex >= len(times):
        testindex = 0
    if not start:
        return render_template("program.html", events=events, refresh=5, now=end[0]-timedelta(minutes=1), header="Till %s" % end[0].strftime("%d.%m.%Y %H:%M"))
    elif not end:
        return render_template("program.html", events=events, refresh=5, now=start[0]+timedelta(minutes=1),
                               header="after %s" % start[0].strftime("%d.%m.%Y %H:%M"))
    else:
        header = "from %s to %s" % (start[0].strftime("%d.%m.%Y %H:%M"), end[0].strftime("%d.%m.%Y %H:%M"))
        now = end[0]-timedelta(minutes=1)
        for event in events:
            if event.start < now < event.end:
                return render_template("auto.html", name=event.name + " pickup", qr="geo:%s,%s" % ll(points[event.pickup]), refresh=5, header=header) + \
                        render_template("auto.html", name=event.name + " dropoff", qr="geo:%s,%s" % ll(points[event.dropoff]), refresh=5, header=header)
        else:
            return render_template("program.html", events=events, refresh=5, now=now, header=header)


# somewhere to login
@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        if username in users and password == users[username].password:
            login_user(users[username])
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
    return users.get(userid, None)


if __name__ == "__main__":
    app.run()
