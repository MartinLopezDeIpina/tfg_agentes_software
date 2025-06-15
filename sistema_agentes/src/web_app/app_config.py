import os

from config import BACKEND_PORT


class Config:
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'clave-muy-secreta'
    DEBUG = False
    HOST = '0.0.0.0'
    PORT = BACKEND_PORT

