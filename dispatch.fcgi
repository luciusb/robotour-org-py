#!/home/zbynek/live.robotour.cz/.venv/bin/python

from flup.server.fcgi_fork import WSGIServer
from app import app

if __name__ == '__main__':
    WSGIServer(app).run()
