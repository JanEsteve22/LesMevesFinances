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
    return sorted([concept[0] for concept in concepts])


@app.route('/transaccions')
@login_required
def transaccions():
    user_id = session.get('user_id')
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()
    unique_concepts = get_unique_concepts(user_id)  # Replace 'user_id' with the actual user ID variable
    return render_template('transaccions.html', transactions=transactions, unique_concepts=unique_concepts)


@app.route('/transaccions/editar/<int:transaction_id>', methods=['GET', 'POST'])
@login_required
def edit_transaction(transaction_id):
    logging.debug("edit_transaction called")
    transaction = Transaction.query.get_or_404(transaction_id)
    if transaction.user_id != session['user_id']:
        logging.debug("usuario incorrecto")
        abort(403)
        

    field_name = request.form['field_name']
    new_value = request.form['new_value']

    if field_name == 'data':
        transaction.date = datetime.strptime(new_value, "%d/%m/%Y")
        logging.debug(f"Updated date to {new_value}")
    elif field_name == 'tipus':
        transaction.tipo = new_value
        logging.debug(f"Updated tipo to {new_value}")
    elif field_name == 'descripció':
        transaction.description = new_value
        logging.debug(f"Updated description to {new_value}")
    elif field_name == 'import':
        transaction.amount = float(new_value.replace(' €', ''))
        logging.debug(f"Updated amount to {new_value}")
    elif field_name == 'concepte':
        transaction.concepte = new_value
        logging.debug(f"Updated concepte to {new_value}")

    db.session.commit()
    return jsonify(success=True)


@app.route('/delete_transaction/<int:transaction_id>', methods=['POST'])
def delete_transaction(transaction_id):
    # Elimina el registro de la base de datos
    try:
        Transaction.query.filter_by(id=transaction_id).delete()
        db.session.commit()
        return jsonify(success=True)
    except Exception as e:
        print(e)
        db.session.rollback()
        return jsonify(success=False), 500
    

@app.route('/download_transactions')
@login_required
def download_transactions():
    user_id = session.get('user_id')
    transactions = Transaction.query.filter_by(user_id=user_id).order_by(Transaction.date.desc()).all()

    output = io.StringIO()
    for transaction in transactions:
        transaction_data = f"{transaction.tipo}\t{transaction.concepte}\t{transaction.description}\t{transaction.amount}\t{transaction.date.strftime('%d-%m-%y')}\n"
        output.write(transaction_data)
    output.seek(0)
    response = make_response(output.getvalue(), 200)
    response.mimetype = "text/plain"
    response.headers["Content-Disposition"] = "attachment; filename=transactions.txt"
    return response

@app.route('/delete_all_transactions', methods=['POST'])
@login_required
def delete_all_transactions():
    user_id = session.get('user_id')
    
    try:
        # Filtra las transacciones del usuario actual y elimínalas todas
        Transaction.query.filter_by(user_id=user_id).delete()
        
        # Confirma los cambios en la base de datos
        db.session.commit()
        
        # Devuelve una respuesta JSON que indica el éxito de la operación
        return jsonify(success=True)
    except Exception as e:
        print(e)
        db.session.rollback()
        return jsonify(success=False), 500


from app import app
