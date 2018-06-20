# vim: set fileencoding=utf-8 et sts=2 sw=2:
import sys, os
import traceback
INTERP = os.path.join(os.environ['HOME'], 'live.robotour.cz', 'env', 'bin', 'python')
if sys.executable != INTERP:
    os.execl(INTERP, INTERP, *sys.argv)
sys.path.append(os.getcwd())
from app import app as application
if __name__ == '__main__':
    application.run(debug=False)
