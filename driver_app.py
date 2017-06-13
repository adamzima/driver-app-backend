from flask import Flask
from flask_sockets import Sockets
import json
import random
from gevent import pywsgi
from geventwebsocket.handler import WebSocketHandler
from keras.models import model_from_json
from sklearn.metrics import mean_squared_error
import collections
import numpy
import time


MODEL_FILENAME = 'model.json'
MODEL_WEIGHTS_FILENAME = 'model.h5'
LOOK_BACK = 5
MIN_VALUE, MAX_VALUE = -15, 15
ERROR_THRESHOLD = 0.01
ANOMALY_COOLDOWN = 4 # seconds

app = Flask(__name__)
sockets = Sockets(app)


@sockets.route('/')
def echo_socket(ws):
    ad = AnomalyDetector()
    timestamp = None
    while not ws.closed:
        message = json.loads(ws.receive())
        if timestamp:
            if time.time() - timestamp > ANOMALY_COOLDOWN:
                timestamp = None
                ws.send(json.dumps({ anomaly: True }))
            continue
        print "-> Got message:", message
        result = ad.process_sample(message)
        print "<- Sending result:", result
        if result['anomaly']:
            timestamp = time.time()
        ws.send(json.dumps(result))

class AnomalyDetector(object):
    def __init__(self):
        super(AnomalyDetector, self).__init__()
        self.model = self.load_model()
        self.samples_buffer = collections.deque(maxlen=LOOK_BACK * 2)
        self.predicts_buffer = collections.deque(maxlen=LOOK_BACK)
        self.ready = False

    def load_model(self):
        # load JSON and create model
        model_json = None
        with open(MODEL_FILENAME, 'r') as file:
            model_json = file.read()
        model = model_from_json(model_json)

        # load weights into new model
        model.load_weights(MODEL_WEIGHTS_FILENAME)
        print("Loaded model from disk")
        model.compile(loss='mean_squared_error', optimizer='adam', metrics=["accuracy"])
        return model

    def normalize_sample(self, sample):
        def normalize(i):
            d = float(MAX_VALUE - MIN_VALUE)
            if i < MIN_VALUE:
                i = MIN_VALUE
            elif i > MAX_VALUE:
                i = MAX_VALUE
            return (i - MIN_VALUE) / d
        x, y, z = sample
        return map(normalize, sample)

    # sample = { 'x': 6.20, 'y': 6.20, 'z': 6.20 }
    def process_sample(self, raw_sample):
        sample = numpy.array([raw_sample['x'], raw_sample['y'], raw_sample['z']])
        normalized = self.normalize_sample(sample)
        self.samples_buffer.append(normalized)

        anomaly = False
        if len(self.samples_buffer) >= LOOK_BACK:
            if self.ready:
                last_prediction = list(self.predicts_buffer)[-1]
                error = mean_squared_error(normalized, last_prediction)
                print "error:", error
                anomaly = bool(error > ERROR_THRESHOLD)

            listed = list(self.samples_buffer)
            x = numpy.array([numpy.array(listed[-LOOK_BACK:])])
            predicted = self.model.predict(x)[0]
            self.predicts_buffer.append(predicted)
            self.ready = True

        return { "anomaly": anomaly }



if __name__ == "__main__":
    print('Starting server...')
    server = pywsgi.WSGIServer(('', 8080), app, handler_class=WebSocketHandler)
    server.serve_forever()
