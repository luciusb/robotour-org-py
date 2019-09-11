from flask import Flask, Response, redirect, request, abort, render_template, flash, send_from_directory  # url_for
from flask_login import LoginManager, login_required, logout_user, login_user, current_user
from flask_qrcode import QRcode
from datetime import datetime, timedelta
import os
from os.path import join as pjoin, exists
from data import reload, ll, User, reload_user, save_users, user_config, users_index, save_results, update_results
import logging
logging.basicConfig(level=logging.DEBUG)

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


@app.context_processor
def reloadContext():
    print("Reload context")
    return {"comp_name": user_config[None].name}

reload()
reloadContext()

@app.route('/delivery<int:round>')
@login_required
def delivery(round):
    config = user_config[None]
    event = config.events[round]
    return render_template("auto.html", name=event.name, qr="geo:%s,%s" % ll(config.points[event.dropoff], refresh=5))


@app.route('/pickup<int:round>')
def pickup(round):
    config = user_config[None]
    event = config.events[round]
    return render_template("auto.html", name=event.name, qr="geo:%s,%s" % ll(config.points[event.pickup], refresh=5))


@app.route('/')
def auto(user=None):
    now = datetime.utcnow() + timedelta(hours=user_config[user].utc_offset)
    for event in user_config[user].events:
        if event.start < now < event.end:
            config = user_config[user]
            return render_template("auto.html", name=event.name, qr="geo:%s,%s" % ll(config.points[event.pickup]), refresh=5)
    else:
        return render_template("program.html", events=user_config[user].events, refresh=15, now=now, additional="")


@app.route('/results')
def results(user=None):
    c = user_config[None]
    return render_template("results.html", results=c.results, rounds=[e.name for e in c.events], refresh=15)


@app.route('/resultse', methods=["GET", "POST"])
@login_required
def results_edit(user=None):
    if current_user.role in ('admin', 'referee'):
        c = user_config[None]
        if request.method == 'POST':
            for team in c.results:
                team["rounds"] = [request.form["i%03i%03i" % (team["id"], i)] for i in range(len(c.events))]
            c.results = update_results(c.results, len(c.events))
            save_results(c.results)
        r = []
        for i, res in enumerate(c.results):
            r.append({"name": res["name"],
                      "rounds": [("i%03i%03i" % (res["id"], j), r) for j, r in enumerate(res["rounds"])],
                      "id": res["id"],
                      "total": res["total"]
                      })
        return render_template("edit_results.html", results=r, rounds=[e.name for e in c.events], refresh=0)
    else:
        redirect('/results')


@app.route('/test')
@login_required
def test():
    if current_user.role in ('admin', 'referee'):
        user = None
    elif current_user.role == 'user':
        user = current_user.username
    else:
        flash("Testing is not accesible for %s role: %s" % (current_user.username, current_user.role))
        redirect('/')
    start, end = user_config[user].test()
    if not start:
        return render_template("program.html", events=user_config[user].events, refresh=0, now=end[0]-timedelta(minutes=1),
                               header="Till %s" % end[0].strftime("%d.%m.%Y %H:%M"))
    elif not end:
        return render_template("program.html", events=user_config[user].events, refresh=0, now=start[0]+timedelta(minutes=1),
                               header="after %s" % start[0].strftime("%d.%m.%Y %H:%M"))
    else:
        header = "from %s to %s" % (start[0].strftime("%d.%m.%Y %H:%M"), end[0].strftime("%d.%m.%Y %H:%M"))
        now = end[0]-timedelta(minutes=1)
        event = user_config[user].getEvent(now)
        if event:
            print(repr(user_config[user].points))
            pickup = ll(user_config[user].points[event.pickup])
            dropoff = ll(user_config[user].points[event.dropoff])
            return render_template("auto.html", name=event.name + " pickup", qr="geo:%s,%s" % pickup, refresh=0, header=header) + \
                render_template("auto.html", name=event.name + " dropoff", qr="geo:%s,%s" % dropoff, refresh=0, header=header)
        else:
            return render_template("program.html", events=user_config[user].events, refresh=0, now=now, header=header)


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
        <meta name="viewport" content="width=device-width, initial-scale=1.0">
        <form action="" method="post">
            <p><input type=text name=username>
            <p><input type=password name=password>
            <p><input type=submit value=Login>
        </form>
        ''')


@app.route("/register", methods=["GET", "POST"])
def register():
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
def config():
    if request.method == 'POST':
        if current_user.role == 'admin':
            cfdir = 'admin'
        else:
            cfdir = pjoin('users', current_user.username)
        need_reload = False
        for input_name in ('users', 'points', 'config', 'file', 'teams', 'results'):
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
                reloadContext()
            else:
                reload_user(current_user.username)
        return redirect(request.url)
    return render_template('config.html', admin=(current_user.role == 'admin'))


@app.route('/download/<filename>')
@login_required
def download(filename):
    if current_user.role == 'admin':
        if filename in ('config.json', 'points.json', 'users.json', 'results.json', 'teams.json'):
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
