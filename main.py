import pyqrcode
from io import BytesIO
import sys
from datetime import datetime
now = datetime.now

from http.server import BaseHTTPRequestHandler, HTTPServer

class myRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        data="robotour 2017 %s"%now().strftime("%H:%M")
        if self.path == '/raw':
            response=data
        else:
            head=''
            if self.path.startswith('/auto'):
                try:
                    t=int(self.path[5:])
                except:
                    t=15
                head='<meta http-equiv="refresh" content="'+t+'" >'
            header=u"<html><head>"+head+"</head><body><h1>"+data+"</h1><br>"
            footer=u"</body></html>"
            if not self.server._lastdata or self.server._lastdata!= data:
                svg = BytesIO()
                qr = pyqrcode.create('robotour')
                qr.svg(svg, scale=20)
                self.server._svg = svg
            response = header+str(self.server._svg.getvalue())+footer
        self._set_headers()
        self.wfile.write(response.encode('utf8'))

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
    httpd._lastdata=None
    print('Starting httpd...')
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run(port=8888)
