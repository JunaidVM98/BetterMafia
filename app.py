# if creating a new environment
# python -m venv virtual_environment_name (e.g. python -m venv mpg)

# if using an existing environment, load into it
# virtual_environment_name\Scripts\activate (e.g. mpg\Scripts\activate)

# packages to install if not installed in current environment
# pip install flask 

from flask import Flask, render_template, request, redirect, url_for, session, make_response
from shared import db  # Import db from shared.py instead of creating it here (otherwise we get circular referencing)
from flask_socketio import SocketIO, emit
from flask_migrate import Migrate
import random
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///game.db'
app.config['SECRET_KEY'] = 'secret!'  # You should use a random secret key
socketio = SocketIO(app)
db.init_app(app)  # Initialize db with the app
migrate = Migrate(app, db)

# Move these imports after db is initialized
from database import Lobby, Participant

def init_db():
    with app.app_context():
        db.create_all()

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/create_lobby', methods=['POST'])
def create_lobby():
    # Retrieve or assign a new user token
    user_token = str(uuid.uuid4())
    name = request.form['name']
    lobby_id = str(random.randint(1000, 9999))
    new_lobby = Lobby(lobby_id=lobby_id, creator_name=name)
    db.session.add(new_lobby)
    db.session.commit()

    # Add the creator as a participant
    new_participant = Participant(name=name, lobby_id=new_lobby.id, user_token=user_token)
    db.session.add(new_participant)
    db.session.commit()

    session['creator_name'] = name
    session['joined_lobby'] = lobby_id

    response = make_response(redirect(url_for('lobby', lobby_id=lobby_id)))
    response.set_cookie('user_token', user_token)
    return response

@app.route('/lobby/<lobby_id>', methods=['GET', 'POST'])
def lobby(lobby_id):
    lobby = Lobby.query.filter_by(lobby_id=lobby_id).first_or_404()
    participants = Participant.query.filter_by(lobby_id=lobby.id).all()
    is_creator = 'creator_name' in session and session['creator_name'] == lobby.creator_name

    # Retrieve or assign a new user token
    user_token = request.cookies.get('user_token', str(uuid.uuid4()))
    
    already_joined = any(p.user_token == user_token for p in participants)
    # Debugging
    print("Current User Token:", user_token)
    for participant in participants:
        print("Participant Name and Token:", participant.name, participant.user_token)
        if participant.user_token == user_token:
            print("Match found for:", participant.name)

    print("User token:", user_token)  # Debugging
    print("Already joined:", already_joined)  # Debugging

    if request.method == 'POST':
        participant_name = request.form['name']
        if not already_joined and all(p.name != participant_name for p in participants):
            new_participant = Participant(name=participant_name, lobby_id=lobby.id, user_token=user_token)
            db.session.add(new_participant)
            db.session.commit()
            already_joined = True

    # Set or update the user token cookie
    response = make_response(render_template('lobby.html', lobby=lobby, participants=participants, is_creator=is_creator, already_joined=already_joined))
    response.set_cookie('user_token', user_token)
    return response


@socketio.on('join', namespace='/lobby')
def handle_join(data):
    lobby_id = data['lobby_id']
    participant_name = data['name']
    lobby = Lobby.query.filter_by(lobby_id=lobby_id).first()

    # Check if the participant already exists in the lobby
    existing_participant = Participant.query.filter_by(name=participant_name, lobby_id=lobby.id).first()
    if existing_participant is None:
        new_participant = Participant(name=participant_name, lobby_id=lobby.id)
        db.session.add(new_participant)
        db.session.commit()
        emit('update_participants', {'name': participant_name}, broadcast=True, namespace='/lobby')
    else:
        emit('participant_already_joined', {'name': participant_name}, namespace='/lobby')


@app.route('/start_game/<lobby_id>', methods=['POST'])
def start_game(lobby_id):
    lobby = Lobby.query.filter_by(lobby_id=lobby_id).first_or_404()
    if 'creator_name' in session and session['creator_name'] == lobby.creator_name:
        lobby.game_started = True
        db.session.commit()
        emit('redirect_to_game', {'lobby_id': lobby_id}, broadcast=True, namespace='/lobby')
    return '', 204

@app.route('/game/<lobby_id>', methods=['GET'])
def game(lobby_id):
    lobby = Lobby.query.filter_by(lobby_id=lobby_id).first_or_404()

    # Check if the user has joined this lobby
    if 'joined_lobby' not in session or session['joined_lobby'] != lobby_id:
        return "You do not have access to this game."

    participants = Participant.query.filter_by(lobby_id=lobby.id).all()
    is_creator = 'creator_name' in session and session['creator_name'] == lobby.creator_name

    return render_template('game.html', lobby=lobby, participants=participants, is_creator=is_creator)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)