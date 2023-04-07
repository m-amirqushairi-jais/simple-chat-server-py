from datetime import datetime
from flask import Flask, render_template, request, jsonify
from flask_jwt_extended import (
    JWTManager, jwt_required, create_access_token,
    create_refresh_token, get_jwt_identity
)
from flask_migrate import Migrate
from flask_sqlalchemy import SQLAlchemy
from flask_socketio import SocketIO, join_room, leave_room, emit
import redis
from werkzeug.security import generate_password_hash, check_password_hash

app = Flask(__name__)
app.config['SECRET_KEY'] = 'mysecretkey'
app.config['JWT_SECRET_KEY'] = 'myjwtsecretkey'
app.config['SQLALCHEMY_DATABASE_URI'] = 'mysql+pymysql://username:password@db/db_name'
app.config['SQLALCHEMY_TRACK_MODIFICATIONS'] = False
socketio = SocketIO(app, cors_allowed_origins='*',
                    message_queue='redis://redis:6379/0')

# jwt
jwt = JWTManager(app)

# db
db = SQLAlchemy(app)


class User(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(80), unique=True,
                         nullable=False, index=True)
    password = db.Column(db.String(120), nullable=False)


migrate = Migrate(app, db)

# cache
cache = redis.StrictRedis(host='redis', port=6379, db=1)
redis_instance = redis.Redis(host='redis', port=6379)


def create_database():
    with app.app_context():
        db.create_all()


username_to_sid = {}
sid_to_username = {}


def get_sid_from_username(username):
    return username_to_sid.get(username)


@app.route('/')
def index():
    return render_template('index.html')


@app.route('/login', methods=['POST'])
def login():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400

    user = User.query.filter_by(username=username).first()
    if user is None or not check_password_hash(user.password, password):
        return jsonify({"msg": "Incorrect username or password"}), 401

    access_token = create_access_token(identity=username)
    refresh_token = create_refresh_token(identity=username)
    return jsonify(access_token=access_token, refresh_token=refresh_token), 200


@app.route('/register', methods=['POST'])
def register():
    if not request.is_json:
        return jsonify({"msg": "Missing JSON in request"}), 400

    username = request.json.get('username', None)
    password = request.json.get('password', None)

    if not username or not password:
        return jsonify({"msg": "Missing username or password"}), 400

    if User.query.filter_by(username=username).first() is not None:
        return jsonify({"msg": "User already exists"}), 400

    user = User(username=username, password=generate_password_hash(password))
    db.session.add(user)
    db.session.commit()

    return jsonify({"msg": "User created"}), 201


@app.route('/refresh', methods=['POST'])
@jwt_required(refresh=True)
def refresh():
    current_user = get_jwt_identity()
    access_token = create_access_token(identity=current_user)
    return jsonify(access_token=access_token), 200


@app.route('/rooms/<room>')
def room(room):
    if not session.get('username'):
        return redirect(url_for('index'))
    room_exists = cache.sismember("rooms", room)
    if not room_exists:
        return "The requested room does not exist. Please try another room.", 404
    else:
        data = {
            'room': room,
            'username': session['username']
        }
        chat_history = cache.lrange(f"chat_history_{data['room']}", 0, 99)
        return render_template('room.html', data=data, chat_history=chat_history)


@socketio.on('join')
@jwt_required
def handle_join_room_event(data):
    app.logger.info(f"{data['username']} has joined the room {data['room']}")
    join_room(data['room'])
    chat_history = cache.lrange(f"chat_history_{data['room']}", 0, 99)
    chat_history = [{'username': msg.split('::')[0], 'message': msg.split(
        '::')[1], 'timestamp': msg.split('::')[2]} for msg in chat_history]
    chat_history = [{'username': msg.decode('utf-8').split('::')[0], 'message': msg.decode(
        'utf-8').split('::')[1], 'timestamp': msg.decode('utf-8').split('::')[2]} for msg in chat_history]

    emit('chat_history', chat_history)
    # emit('join_room_announcement', data, room=data['room'])
    emit('join_room_announcement', {
         'username': data['username']}, room=data['room'])

    username_to_sid[data['username']] = request.sid
    sid_to_username[request.sid] = data['username']


@socketio.on('leave')
@jwt_required
def handle_leave_room_event(data):
    app.logger.info(f"{data['username']} has left the room {data['room']}")
    leave_room(data['room'])
    # emit('leave_room_announcement', data, room=data['room'])
    emit('leave_room_announcement', {
         'username': data['username']}, room=data['room'])
    del username_to_sid[data['username']]
    del sid_to_username[request.sid]


@socketio.on('send_message')
@jwt_required
def handle_send_message_event(data):
    app.logger.info(
        f"{data['username']} in room {data['room']} says: {data['message']}")
    data['timestamp'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
    cache.lpush(f"chat_history_{data['room']}",
                f"{data['username']}::{data['message']}::{data['timestamp']}")
    # Limit chat history to the last 100 messages
    cache.ltrim(f"chat_history_{data['room']}", 0, 99)
    emit('receive_message', data, room=data['room'])


@socketio.on('send_private_message')
@jwt_required
def handle_send_private_message_event(data):
    recipient = data['recipient']
    recipient_sid = get_sid_from_username(recipient)

    if recipient_sid:
        data['timestamp'] = datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')
        emit('receive_private_message', data, room=recipient_sid)


if __name__ == '__main__':
    create_database()
    socketio.run(app, debug=True)
