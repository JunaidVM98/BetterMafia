# if no environment has been created previously or you have recloned the solution, create a new environment:
# python -m venv game_env

# to load into the created environment (or to use an existing environment):
# game_env\Scripts\activate

# packages to install if not installed in current environment:
# pip install -r requirements.txt

# Run the solution:
# python app.py

from flask import Flask, render_template, request, redirect, url_for, session, make_response
from shared import db  # Import db from shared.py instead of creating it here (otherwise we get circular referencing)
from flask_socketio import SocketIO, emit
from flask_migrate import Migrate
import random
import uuid

app = Flask(__name__)
app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///game.db'
app.config['SECRET_KEY'] = 'secret!'  # Should be a random secret key
socketio = SocketIO(app)
db.init_app(app)
migrate = Migrate(app, db)

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
    
    # Perform an inital check when a user loads into the lobby to see if their user token matches a participant who has already joined (i.e. they are in the lobby)
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

    participants = Participant.query.filter_by(lobby_id=lobby.id).all()
    already_joined = any(p.user_token == user_token for p in participants)

    # Set or update the user token cookie
    response = make_response(render_template('lobby.html', lobby=lobby, participants=participants, is_creator=is_creator, already_joined=already_joined, game_started=lobby.game_started, user_token=user_token))
    response.set_cookie('user_token', user_token)
    return response

@socketio.on('join', namespace='/lobby')
def handle_join(data):
    lobby_id = data['lobby_id']
    participant_name = data['name']
    lobby = Lobby.query.filter_by(lobby_id=lobby_id).first()

    # Retrieve or assign a new user token
    user_token = request.cookies.get('user_token', str(uuid.uuid4()))

    # Check if the participant already exists in the lobby
    existing_participant = Participant.query.filter_by(name=participant_name, lobby_id=lobby.id).first()
    if existing_participant is None:
        new_participant = Participant(name=participant_name, lobby_id=lobby.id, user_token=user_token)
        db.session.add(new_participant)
        db.session.commit()
        emit('update_participants', {'name': participant_name, 'user_token': user_token}, broadcast=True, namespace='/lobby')
    else:
        emit('participant_already_joined', {'name': participant_name}, namespace='/lobby')

@app.route('/start_game/<lobby_id>', methods=['POST'])
def start_game(lobby_id):
    lobby = Lobby.query.filter_by(lobby_id=lobby_id).first_or_404()
    if 'creator_name' in session and session['creator_name'] == lobby.creator_name:
        lobby.game_started = True
        db.session.commit()
        socketio.emit('redirect_to_game', {'lobby_id': lobby_id}, namespace='/lobby')
        socketio.emit('lobby_closed', {'lobby_id': lobby_id}, namespace='/lobby')
    return '', 204

@app.route('/game/<lobby_id>', methods=['GET'])
def game(lobby_id):
    lobby = Lobby.query.filter_by(lobby_id=lobby_id).first_or_404()

    user_token = request.cookies.get('user_token')
    participant = Participant.query.filter_by(lobby_id=lobby.id, user_token=user_token).first()

    if not participant:
        return f"Sorry you're not a member of this lobby so cannot access this game! <br> Either wait until the participants <a href='../lobby/{lobby_id}'>return to the lobby</a> so you can join, or <a href='../'>start your own game</a>."

    participants = Participant.query.filter_by(lobby_id=lobby.id).all()
    is_creator = 'creator_name' in session and session['creator_name'] == lobby.creator_name

    return render_template('game.html', lobby=lobby, participants=participants, is_creator=is_creator)

if __name__ == '__main__':
    init_db()
    socketio.run(app, debug=True)