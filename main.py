import pyqrcode
from io import BytesIO
import sys, os
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
        data=self.getCurrentData(now())
        if 'full' in self.path or 'auto' in self.path:
            head=''
            intr=''
            if self.path.startswith('/auto'):
                try:
                    t=int(self.path[5:])
                except:
                    t=15
                head='<meta http-equiv="refresh" content="%s" >'%t
            intro='<h1>ROBOTOUR 2017</h1>last update %s<br><h2> WiFi SSID: robotour password: robotour</h2><br><h2>address: 192.168.43.1:8888</h2><br><br>'%now().strftime("%H:%M:%S")
            header="<html><head>%s</head><body>%s<h1>%s</h1><br>"%(head, intro, data.replace('\n','<br>'))
            footer="</body></html>"
            response = header+self.getQR(data)+footer
        else:
            response=data
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
                qr.svg(svg, scale=20)
                self.server._svg = svg
                self.server._lastdata=data
        return self.server._svg.getvalue().decode('utf8')


    def getCurrentData(self, t):
        for timestamp, data in self.server._config:
            if timestamp<t.time():
                return data
        else:
            return "Comming soon"

def readconfig(fn):
    with open(fn,'r') as f:
        config = []
        for line in f:
            t, data = eval(line)
            t=datetime.strptime(t, "%H:%M").time()
            print(t)
            config.append((t,data))
    return sorted(config, reverse=True)

def run(port=80):
    server_address = ('', port)
    httpd = HTTPServer(server_address, myRequestHandler)
    httpd._svg=None
    httpd._lastdata=None
    httpd._config=readconfig(os.path.join(os.path.split(os.path.abspath(__file__))[0],"rounds.txt"))
    print('Starting httpd...')
    httpd.serve_forever()

if __name__ == "__main__":
    from sys import argv

    if len(argv) == 2:
        run(port=int(argv[1]))
    else:
        run(port=8888)
