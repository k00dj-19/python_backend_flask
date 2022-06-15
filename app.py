import jwt
import bcrypt

from flask import Flask, request, jsonify, g, current_app, Response
from sqlalchemy import create_engine
from util import *
from api import *
from functools import wraps
from flask import request, Response
from datetime import datetime, timedelta
from flask_cors import CORS


def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        access_token = request.headers.get('Authorization')
        if access_token is not None:
            try:
                payload = jwt.decode(access_token, current_app.config['JWT_SECRET_KEY'], 'HS256')
            except jwt.InvalidTokenError:
                payload = None

            if payload is None: return Response(status = 401)

            user_id = payload['user_id']
            g.user_id = user_id
            g.user = get_user(user_id) if user_id else None
        else:
            return Response(status = 401)

        return f(*args, **kwargs)
    return decorated_function


def create_app(test_config = None):
    app = Flask(__name__)

    CORS(app)

    app.json_encoder = CustomJSONEncoder

    if test_config is None:
        app.config.from_pyfile("config.py")
    else:
        app.config.update(test_config)

    database = create_engine(app.config['DB_URL'], encoding = 'utf-8', max_overflow = 0)
    app.database = database

    @app.route("/", methods=['GET'])
    def index():
        return "Hello Flask"


    @app.route("/ping", methods=['GET'])
    def ping():
        return "pong"


    @app.route("/sign-up", methods=['POST'])
    def sign_up():
        new_user     = request.json
        new_user['password'] = bcrypt.hashpw(new_user['password'].encode('UTF-8'), bcrypt.gensalt())
        new_user_id  = insert_user(new_user)
        new_user_info = get_user(new_user_id)

        return jsonify(new_user_info)
    
    @app.route('/login', methods=['POST'])
    def login():
        credential = request.json
        email = credential['email']
        password = credential['password']
        user_credential = get_user_id_and_password(email)

        if user_credential and bcrypt.checkpw(password.encode('UTF-8'), user_credential['hashed_password'].encode('UTF-8')):
            user_id = user_credential['id']
            payload = {
                'user_id' : user_id,
                'exp' : datetime.utcnow() + timedelta(seconds = 60 * 60 * 24)
            }
            token = jwt.encode(payload, app.config['JWT_SECRET_KEY'], 'HS256')

            return jsonify({
                'access_token' : token
            })
        else:
            return '', 401

    @app.route("/tweet", methods=['POST'])
    @login_required
    def tweet():
        user_tweet = request.json
        user_tweet['id'] = g.user_id
        tweet = user_tweet['tweet']

        if len(tweet) > 300:
            return "300자를 초과했습니다.", 400

        insert_tweet(user_tweet)

        return "", 200


    @app.route("/follow", methods=['POST'])
    @login_required
    def follow():
        payload = request.json
        payload['id'] = g.user_id

        insert_follow(payload)

        return '', 200


    @app.route("/unfollow", methods=['POST'])
    @login_required
    def unfollow():
        payload = request.json
        payload['id'] = g.user_id

        insert_unfollow(payload)

        return '', 200


    @app.route("/timeline/<int:user_id>", methods=['GET'])
    def timeline(user_id):
        return jsonify({
            'user_id' : user_id,
            'timeline' : get_timeline(user_id)
        })
    
    @app.route('/timeline', methods=['GET'])
    @login_required
    def user_timeline():
        user_id = g.user_id

        return jsonify({
            'user_id' : user_id,
            'timeline' : get_timeline(user_id)
        })

    return app
