import pyqrcode
from io import BytesIO
import sys, os
from datetime import datetime, timedelta
now = datetime.now

from http.server import BaseHTTPRequestHandler, HTTPServer

class myRequestHandler(BaseHTTPRequestHandler):
    def _set_headers(self):
        self.send_response(200)
        self.send_header('Content-type', 'text/html')
        self.end_headers()

    def do_GET(self):
        n=now()
        text, pickup, dropoff=self.getCurrentData(n)
        if 'full' in self.path or 'auto' in self.path:
            head=''
            intr=''
            if self.path.startswith('/auto'):
                try:
                    t=int(self.path[5:])
                except:
                    t=15
                head='<meta http-equiv="refresh" content="%s" >'%t
            intro='<h1>ROBOTOUR 2017</h1>last update %s<h2> WiFi SSID: robotour password: robotour address: 192.168.43.1:8888</h2>'%n.strftime("%H:%M:%S")
            header="<html><head>%s</head><body>%s<h1>%s<br>pickup: %s<br> dropoff: %s</h1>"%(head, intro, text, pickup, dropoff)
            footer="</body></html>"
            response = header+self.getQR(text+'\npickup: '+pickup+'\ndropoff: '+dropoff)+footer
        else:
            response = text+'\npickup: '+pickup+'\ndropoff: '+dropoff
        self._set_headers()
        self.wfile.write(response.encode('utf8'))


    def do_HEAD(self):
        self._set_headers()

    def do_POST(self):
        # Doesn't do anything with posted data
        self._set_headers()
        self.wfile.write("<html><body><h1>POST!</h1></body></html>")


    def getQR(self, data):
        if not self.server._lastdata or self.server._lastdata!= data:
                svg = BytesIO()
                qr = pyqrcode.create(data)
                qr.svg(svg, scale=18)
                self.server._svg = svg
                self.server._lastdata=data
        return self.server._svg.getvalue().decode('utf8')


    def getCurrentData(self, t):
        for i, (timestamp, text, pickup, dropoff) in enumerate(self.server._config):
            if timestamp<=t.time():
                if text=="":
                    return "Next round will start at %s"%self.server._config[i-1][0].strftime("%H:%M"),"", ""
                return text, self.server._points[pickup], self.server._points[dropoff]
        else:
            return "Round will start at %s"%self.server._config[-1][0].strftime("%H:%M"),"", ""

def readconfig(fn):
    with open(fn,'r') as f:
        config = []
        for line in f:
            t, text, pickup, dropoff = eval(line)
            t=datetime.strptime(t, "%H:%M").time()
            config.append((t, text, pickup, dropoff))
    return sorted(config, reverse=True)

def readPoints(fn):
    return eval(open(fn,'r').read())


def run(port=80):
    server_address = ('', port)
    httpd = HTTPServer(server_address, myRequestHandler)
    httpd._svg=None
    httpd._lastdata=None
    httpd._config=readconfig(os.path.join(os.path.split(os.path.abspath(__file__))[0],"rounds.txt"))
    httpd._points=readPoints(os.path.join(os.path.split(os.path.abspath(__file__))[0],"points.txt"))
    print('Starting httpd...')
    httpd.serve_forever()


testclock = 7,0
def test_now():
    global testclock
    d = datetime(year=2017, month=9, day=16, hour= testclock[0], minute = testclock[1])
    d+=timedelta(seconds=60*30)
    testclock=d.hour, d.minute
    return d

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        now=test_now
    run(port=8888)
