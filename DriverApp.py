from flask import Flask
from flask_sockets import Sockets
import json
import random

app = Flask(__name__)
sockets = Sockets(app)

@sockets.route('/')
def echo_socket(ws):
    while not ws.closed:
        message = json.loads(ws.receive())
        print(message)
        anomaly = (random.randint(0, 9) == 7)
        ws.send(json.dumps({"anomaly": anomaly}))

if __name__ == "__main__":
    from gevent import pywsgi
    from geventwebsocket.handler import WebSocketHandler
    server = pywsgi.WSGIServer(('', 8080), app, handler_class=WebSocketHandler)
    server.serve_forever()