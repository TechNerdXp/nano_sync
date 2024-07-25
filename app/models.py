from datetime import datetime, timezone
from .extensions import db

class User(db.Model):
    """
    Model to store user information. Since authentication is via OAuth, 
    no password field is necessary.
    """
    id = db.Column(db.Integer, primary_key=True)
    email = db.Column(db.String(120), unique=True, nullable=False)  # User's email address
    name = db.Column(db.String(100), nullable=True)  # User's full name
    registered_on = db.Column(db.DateTime, default=datetime.now(timezone.utc))  # User registration timestamp

    def __repr__(self):
        return f'<User {self.email}>'

class Token(db.Model):
    """
    Model to store access tokens for users.
    """
    id = db.Column(db.Integer, primary_key=True)
    access_token = db.Column(db.String, nullable=False)  # OAuth access token
    expiry = db.Column(db.DateTime, nullable=False)  # Token expiry date and time
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Reference to user

    def __repr__(self):
        return f'<Token {self.access_token} for User {self.user_id}>'

class RefreshToken(db.Model):
    """
    Model to store refresh tokens to allow renewing access tokens automatically.
    """
    id = db.Column(db.Integer, primary_key=True)
    refresh_token = db.Column(db.String, nullable=False)  # OAuth refresh token
    user_id = db.Column(db.Integer, db.ForeignKey('user.id'), nullable=False)  # Reference to user

    def __repr__(self):
        return f'<RefreshToken {self.refresh_token} for User {self.user_id}>'
