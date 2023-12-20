from shared import db  # Import db from shared.py

class Lobby(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    lobby_id = db.Column(db.String(80), unique=True, nullable=False)
    creator_name = db.Column(db.String(120), nullable=False)
    participants = db.relationship('Participant', backref='lobby', lazy=True)
    game_started = db.Column(db.Boolean, default=False)

class Participant(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(120), nullable=False)
    lobby_id = db.Column(db.Integer, db.ForeignKey('lobby.id'), nullable=False)
    user_token = db.Column(db.String(120), nullable=False)

    def __init__(self, name, lobby_id, user_token):
        self.name = name
        self.lobby_id = lobby_id
        self.user_token = user_token