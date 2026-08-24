from flask import Flask
import os
import socket

app = Flask(__name__)


@app.route("/")
def home():
    return {
        "status": "ok",
        "message": "EKS Learning Lab application",
        "hostname": socket.gethostname(),
        "version": os.getenv("APP_VERSION", "dev")
    }


@app.route("/health")
def health():
    return {"status": "healthy"}


@app.route("/ready")
def ready():
    return {"status": "ready"}


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=8080)
