#!/usr/bin/env python
import pika
import argparse
import sys
import uuid
import threading
from argparse import RawTextHelpFormatter
from flask import Flask, jsonify, make_response, request, abort

app = Flask(__name__)

class RpcClient(object):
    internal_lock = threading.Lock()
    queue = {}

    def __init__(self, rpc_queue, host, port):

        self.rpc_queue = rpc_queue
        self.credentials = pika.PlainCredentials('guest', 'guest')
        self.parameters = pika.ConnectionParameters(
            host, int(port), '/',  self.credentials)
        self.connection = pika.BlockingConnection(self.parameters)
        self.channel = self.connection.channel()
        result = self.channel.queue_declare(queue=self.rpc_queue, durable=True)

    def send_request(self, payload, queue):
        corr_id = str(uuid.uuid4())
        self.queue[corr_id] = None
        with self.internal_lock:
            self.channel.basic_publish(exchange='',
                                       routing_key=queue,
                                       properties=pika.BasicProperties(
                                          delivery_mode = 2
                                       ),
                                       body=payload)
        return corr_id

@app.route('/')
def test():
    return make_response(jsonify({'result': 'success'}), 200)

@app.route('/api/1.0/new_job', methods=['POST'])
def create_job():

    # TODO handle missing things better
    if not request.json or not 'language' in request.json:
        abort(400)

    rpc_client.send_request(request.get_data().decode("utf-8"), request.json["language"])

    return make_response(jsonify({'result': 'success, job sent for processing'}), 200)


@app.errorhandler(404)
def not_found(error):
    return make_response(jsonify({'error': 'requested resource does not exits'}), 404)

@app.errorhandler(500)
def not_found(error):
    return make_response(jsonify({'error': 'a server error has occured'}), 500)

if __name__ == '__main__':
    examples = sys.argv[0] + " -p 5672 -s rabbitmq -m 'Hello' "
    parser = argparse.ArgumentParser(formatter_class=RawTextHelpFormatter,
                                 description='Run recess_api.py',
                                 epilog=examples)
    parser.add_argument('-p', '--port', action='store', dest='port', help='The port to listen on.')
    parser.add_argument('-s', '--server', action='store', dest='server', help='The RabbitMQ server.')

    args = parser.parse_args()
    if args.port == None:
        print("Missing required argument: -p/--port")
        sys.exit(1)
    if args.server == None:
        print("Missing required argument: -s/--server")
        sys.exit(1)

    rpc_client = RpcClient('task_queue', args.server, args.port)
    app.run(threaded = False, port=4520, host='0.0.0.0')
