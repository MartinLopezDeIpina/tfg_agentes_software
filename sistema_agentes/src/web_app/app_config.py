import os

class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-muy-secreta'
    DEBUG = True
    HOST = '0.0.0.0'
    PORT = 5000

