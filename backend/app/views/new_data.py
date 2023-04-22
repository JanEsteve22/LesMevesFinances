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
import openpyxl  # Importa la librería openpyxl

logging.basicConfig(level=logging.DEBUG)

def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Siusplau, inicia sessió per accedir a la pàgina")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

@app.route('/new_data')
@login_required
def new_data_page():
    return render_template('new_data.html')



# Configuración de carga de archivos
ALLOWED_EXTENSIONS = {'txt', 'xlsx'}  # Agrega la extensión 'xlsx' a los archivos permitidos
app.config['UPLOAD_FOLDER'] = 'uploads/'
if not os.path.exists(app.config['UPLOAD_FOLDER']):
    os.makedirs(app.config['UPLOAD_FOLDER'])

def allowed_file(filename):
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS

@app.route('/process_file', methods=['POST'])
@login_required
def process_file():
    if 'data-file' not in request.files:
        flash('No se encontró el archivo')
        return redirect(request.url)

    file = request.files['data-file']

    if file.filename == '':
        flash('No se seleccionó ningún archivo')
        return redirect(request.url)

    if file and allowed_file(file.filename):
        filename = secure_filename(file.filename)
        filepath = os.path.join(app.config['UPLOAD_FOLDER'], filename)
        file.save(filepath)

        try:
            # Leer el archivo .txt separado por tabulaciones o el archivo .xlsx
            if file.filename.endswith('.txt'):
                data = pd.read_csv(filepath, sep='\t', encoding='utf-8')
            elif file.filename.endswith('.xlsx'):
                data = pd.read_excel(filepath, engine='openpyxl')

            # Verificar si las columnas coinciden con los nombres esperados
            expected_columns = {'tipo','concepte', 'description', 'amount', 'date'}
            if set(data.columns) != expected_columns:
                flash('Les capceleres han de ser tipo, concepte, description, amount i date')
                return redirect(url_for('new_data_page'))

            # Procesar y guardar los datos en la base de datos
            for index, row in data.iterrows():
                tipo = row['tipo']
                concepte = row['concepte']
                description = str(row['description']).replace(",",".")
                amount = float(row['amount'])
                date = pd.to_datetime(row['date'], format='%Y%m%d')
                user_id = session.get('user_id')

                # Validar los atributos
                if tipo not in ['Gast', 'Ingrés']:
                    flash(f'Error en la fila {index + 1}: El camp "{tipo}" no es vàlid. Ha de ser "Gast" o "Ingrés".')
                    return redirect(url_for('new_data_page'))
                if len(description) > 100:
                    flash(f'Error en la fila {index + 1}: La descripció es massa llarga (màxim 100 caràcters).')
                    return redirect(url_for('new_data_page'))
                if len(concepte) > 100:
                    flash(f'Error en la fila {index + 1}: El concepte és massa llarg (màxim 100 caràcters).')
                    return redirect(url_for('new_data_page'))

                transaction = Transaction(tipo=tipo, concepte=concepte, description=description, amount=amount, date=date, user_id=user_id)
                db.session.add(transaction)

            db.session.commit()

            flash('Dades carregades amb èxit')
            return redirect(url_for('inici'))

        except Exception as e:
            print(e)
            flash(f'Error al processar el fitxer: {str(e)}')
            return redirect(url_for('new_data_page'))

    else:
        flash('Arxiu no permès')
        return redirect(url_for('new_data_page'))
    

from app import app
