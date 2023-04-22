from flask import render_template, request, jsonify, redirect, url_for, session, flash, abort, make_response
from app import app, db
from app.models import User, Transaction
from google.oauth2 import id_token
from google.auth.transport import requests
from datetime import datetime
from functools import wraps
import os
import pandas as pd
from werkzeug.utils import secure_filename
import logging
from dateutil.relativedelta import relativedelta
import io

logging.basicConfig(level=logging.DEBUG)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Siusplau, inicia sessió per accedir a la pàgina")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/')
def index():
    return render_template('index.html')

@app.route('/api/login', methods=['POST'])
def login():
    # Obtener el token de ID enviado por el cliente
    token = request.json.get('id_token')

    try:
        # Verificar el token de ID y obtener la información del usuario
        idinfo = id_token.verify_oauth2_token(token, requests.Request(), app.config['GOOGLE_CLIENT_ID'])

        # Si la verificación es exitosa, buscar o crear al usuario en la base de datos
        user = User.query.filter_by(email=idinfo['email']).first()
        if not user:
            user = User(email=idinfo['email'])
            db.session.add(user)
            db.session.commit()

        # Guardar el ID de usuario en la sesión
        session['user_id'] = user.id

        # Redirigir al usuario a la pantalla de "Inici"
        return redirect(url_for('inici'))

    except ValueError as e:
        # Si la verificación falla, devolver un error
        return jsonify({"error": str(e)}), 401
    

from app import app
