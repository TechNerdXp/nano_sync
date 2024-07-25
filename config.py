from datetime import timedelta

class Config:
    SECRET_KEY = 'OurVeryVeryVeryMuchSecretKeyPlusPlusPlusAtTheRateOfSpeedOfLight'
    SESSION_PERMANENT = True
    PERMANENT_SESSION_LIFETIME = timedelta(days=30)
    SQLALCHEMY_DATABASE_URI = 'sqlite:///nano_sync.db'
