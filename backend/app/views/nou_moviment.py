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


def get_unique_concepts(user_id):
    concepts = Transaction.query.filter_by(user_id=user_id).with_entities(Transaction.concepte).distinct().all()
    return sorted(concept[0] for concept in concepts)

@app.route('/nou_moviment')
@login_required
def new_transaction_page():
    unique_concepts = get_unique_concepts(session.get('user_id'))
    return render_template('nou_moviment.html', unique_concepts=unique_concepts)

@app.route('/nou_moviment', methods=['GET', 'POST'])
@login_required
def new_transaction():
    if request.method == 'POST':
        tipo = request.form['tipo']
        description = request.form['description']
        concepte = request.form['concepte'] if request.form['concepte'] != 'other' else request.form['new_concept']
        if tipo == 'Gast':
            amount = abs(float(request.form['amount']))*-1
        else:
            amount = abs(float(request.form['amount']))
        date = datetime.strptime(request.form['date'], "%Y-%m-%d")
        user_id = session.get('user_id')

        # Validación de datos
        if not description or not amount or not date or not user_id:
            # Error: datos no válidos
            return "Error: Datos no válidos", 400
        if len(description)>255:
            return "Error: descripció massa llarga", 400
        if len(description)>100:
            return "Error: concepte massa llarg", 400
    
        transaction = Transaction(tipo=tipo,description=description, concepte = concepte, amount=amount, date=date, user_id=user_id)
        db.session.add(transaction)
        db.session.commit()
        return redirect(url_for('inici'))

    return render_template('nou_moviment.html')


from app import app
