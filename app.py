import os
import secrets
import requests
from flask import Flask, request, jsonify, Response, abort

app = Flask(__name__)

@app.before_request
def service_identity():
    if request.path == '/health':
        return None
    key = os.environ.get('SERVICE_KEY', '')
    if not key:
        abort(503)
    if not secrets.compare_digest(request.headers.get('X-Service-Key', ''), key):
        abort(401)

@app.get('/health')
def health():
    return {'status': 'ready'}

def call(service, path, method='POST', **kwargs):
    headers = {'X-Service-Key': os.environ['SERVICE_KEY']}
    for key in ('X-User-Id', 'X-Tenant-Id'):
        if request.headers.get(key):
            headers[key] = request.headers[key]
    base = os.environ.get(service.upper() + '_URL', 'http://' + service + ':8080')
    return requests.request(method, base + path, headers=headers, timeout=10, **kwargs)

import base64
from pathlib import Path
from urllib.parse import unquote

def root():
    return Path(os.environ.get('ASSET_ROOT', '/srv/assets'))

@app.post('/store')
def store():
    stored = []
    for entry in request.json['entries']:
        target = root() / unquote(entry['key'])
        target.parent.mkdir(parents=True, exist_ok=True)
        target.write_bytes(base64.b64decode(entry['data'], validate=True))
        stored.append(entry['key'])
    return jsonify(stored=stored)

@app.post('/upload')
def upload():
    target = (root() / unquote(request.json['key'])).resolve()
    if not target.is_relative_to(root().resolve()):
        abort(400)
    target.parent.mkdir(parents=True, exist_ok=True)
    target.write_bytes(base64.b64decode(request.json['data'], validate=True))
    return {'stored': request.json['key']}
