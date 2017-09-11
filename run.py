import pyqrcode
from StringIO import StringIO
import sys
from time import time as now

from BaseHTTPServer import BaseHTTPRequestHandler, HTTPServer



class myRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):

        if not self.server._svg:
            svg = StringIO()
            qr = pyqrcode.create('robotour')
            qr.svg(svg, scale=10)
            self.server._svg = svg.getvalue()
        response = "<html><body><h1>Robotour 2017</h1>\n%s\n</body></html>"%self.server._svg
        self._set_headers()
        self.wfile.write(response)

    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        # Doesn't do anything with posted data
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>")


def readconfig(fn):
    with open(fn,'r') as f:
        table = (eval(line) for line in f)
    return table

def run(port=80):
    server_address = ('', port)
    httpd = HTTPServer(server_address, myRequestHandler)
    httpd._svg=None
    print('Starting httpd...')
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run(port=8888)
