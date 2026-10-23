import os
import socket

from flask import Flask, jsonify, request

app = Flask(__name__)


@app.route("/health")
def health():
    return jsonify(status="ok")


@app.route("/check")
def check():
    host = request.args.get("host")
    port_raw = request.args.get("port")

    if not host or not port_raw:
        return jsonify(error="parametres 'host' et 'port' requis"), 400

    try:
        port = int(port_raw)
    except ValueError:
        return jsonify(error="'port' doit etre un entier"), 400

    if port < 1 or port > 65535:
        return jsonify(error="'port' doit etre compris entre 1 et 65535"), 400

    is_open = _is_port_open(host, port)
    return jsonify(host=host, port=port, open=is_open)


def _is_port_open(host, port, timeout=2):
    try:
        with socket.create_connection((host, port), timeout=timeout):
            return True
    except OSError:
        return False


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.environ.get("PORT", 5000)))
