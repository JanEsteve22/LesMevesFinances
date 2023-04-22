# Importar las librerías y módulos necesarios
import logging
import collections
from datetime import datetime
from functools import wraps

from flask import (
    render_template, request, jsonify, redirect, url_for,
    session, flash, abort, make_response
)
from dateutil.relativedelta import relativedelta
from sqlalchemy import func

from app import app, db
from app.models import Transaction

# Configurar el registro
logging.basicConfig(level=logging.DEBUG)

# Decorador para requerir inicio de sesión
def login_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if 'user_id' not in session:
            flash("Siusplau, inicia sessió per accedir a la pàgina")
            return redirect(url_for('index'))
        return f(*args, **kwargs)
    return decorated_function

# Función para formatear números
def format_number(number):
    return format(number, ",.2f").replace(",", "X").replace(".", ",").replace("X", ".")

# Función para obtener datos de gasto por concepto
def get_expense_data_by_concept(transactions):
    expense_data = {}
    for t in transactions:
        if t.concepte not in expense_data:
            expense_data[t.concepte] = 0
        expense_data[t.concepte] += abs(t.amount)
    return expense_data

# Función para obtener datos de gasto por categoría
def get_expense_data_by_category(transactions):
    category_expense = collections.defaultdict(float)
    for t in transactions:
        if t.tipo == 'Gast':
            category_expense[t.category] += abs(t.amount)
    return [{'category': category, 'amount': round(amount, 2)} for category, amount in category_expense.items()]

# Ruta principal de la aplicación
@app.route('/inici')
@login_required
def inici():
    # Obtener información del mes actual
    current_month = datetime.now().month
    current_year = datetime.now().year

    # Calcular fechas límite para el mes actual
    first_day_of_month = datetime(current_year, current_month, 1)
    last_day_of_month = (first_day_of_month + relativedelta(months=1, days=-1)).replace(hour=23, minute=59, second=59)

    # Consultar las transacciones del mes actual
    transactions = db.session.query(Transaction).filter_by(user_id=session['user_id']).filter(
        (Transaction.tipo == 'Ingrés') | (Transaction.tipo == 'Gast')
    ).filter(
        Transaction.date >= first_day_of_month,
        Transaction.date <= last_day_of_month
    ).all()

    # Separar ingresos y gastos
    ingresos = [t for t in transactions if t.tipo == 'Ingrés']
    gastos = [t for t in transactions if t.tipo == 'Gast']

    # Calcular totales de ingresos y gastos del mes actual
    total_ingresos = round(sum([abs(t.amount) for t in ingresos]), 2)
    total_gastos = round(sum([abs(t.amount) for t in gastos]), 2)

    # Calcular promedio de gasto diario y ahorro mensual
    days_passed_in_month = (datetime.now() - first_day_of_month).days + 1
    gasto_promedio_diario_mensual = round(total_gastos / days_passed_in_month, 2)
    ahorro_mensual = round(total_ingresos - total_gastos, 2)

    # Obtener la fecha actual y la fecha de creación de la cuenta del usuario
    today = datetime.now()
    account_creation_date = db.session.query(db.func.min(Transaction.date)).filter_by(user_id=session['user_id']).scalar()

    if account_creation_date is None:
        account_creation_date = datetime.now() # Establecer una fecha/hora predeterminada en caso de que la consulta devuelva None

    # Calcular los meses transcurridos desde la creación de la cuenta
    months_passed = (today.year - account_creation_date.year) * 12 + today.month - account_creation_date.month

    # Calcular datos de balance mensual
    months_labels = []
    balance_data = []

    for i in range(months_passed):
        month_start = today.replace(day=1, hour=0, minute=0, second=0, microsecond=0) - relativedelta(months=i)
        month_end = (month_start + relativedelta(months=1, days=-1)).replace(hour=23, minute=59, second=59)

        transactions_month = db.session.query(Transaction).filter_by(user_id=session['user_id']).filter(
            (Transaction.tipo == 'Ingrés') | (Transaction.tipo == 'Gast')
        ).filter(
            Transaction.date >= month_start,
            Transaction.date <= month_end
        ).order_by(Transaction.date).all() 

        ingresos_month = [t for t in transactions_month if t.tipo == 'Ingrés']
        gastos_month = [t for t in transactions_month if t.tipo == 'Gast']
        total_ingresos_month = sum(abs(t.amount) for t in ingresos_month)
        total_gastos_month = sum(abs(t.amount) for t in gastos_month)
        balance_month = total_ingresos_month - total_gastos_month

        months_labels.append(month_start.strftime('%m-%Y'))
        balance_data.append(balance_month)

    # Invertir los datos para mostrarlos correctamente en el gráfico
    months_labels.reverse()
    balance_data.reverse()

    # Calcular totales de ingresos, gastos y ahorros
    total_transactions = db.session.query(Transaction).filter_by(user_id=session['user_id']).filter(
        (Transaction.tipo == 'Ingrés') | (Transaction.tipo == 'Gast')
    ).all()

    total_transactions_gast = db.session.query(Transaction).filter_by(user_id=session['user_id']).filter(
        (Transaction.tipo == 'Gast')
    ).all()

    total_ingresos_all = round(sum([abs(t.amount) for t in total_transactions if t.tipo == 'Ingrés']), 2)
    total_gastos_all = round(sum([abs(t.amount) for t in total_transactions if t.tipo == 'Gast']), 2)
    ahorro_total = round(total_ingresos_all - total_gastos_all, 2)

    # Calcular el gasto promedio diario total
    min_transaction_date = db.session.query(db.func.min(Transaction.date)).filter_by(user_id=session['user_id']).scalar()
    if min_transaction_date is None:
        min_transaction_date = datetime.now() 
    
    days_since_min_transaction_date = (datetime.now() - min_transaction_date).days + 1
    gasto_promedio_diario_total = round(total_gastos_all / days_since_min_transaction_date, 2)

        # Calcular los datos de gastos por concepto para el mes actual y el total acumulado
    expense_data_current_month = get_expense_data_by_concept(gastos)
    expense_data_total = get_expense_data_by_concept(total_transactions_gast)

    # Renderizar la plantilla HTML con los datos calculados
    return render_template(
        'inici.html',
        ahorro_mensual=format_number(ahorro_mensual),
        total_gastos=format_number(total_gastos),
        total_ingresos=format_number(total_ingresos),
        months_labels=months_labels,
        balance_data=balance_data,
        ahorro_total=format_number(ahorro_total),
        total_gastos_all=format_number(total_gastos_all),
        total_ingresos_all=format_number(total_ingresos_all),
        gasto_promedio_diario_mensual=format_number(gasto_promedio_diario_mensual),
        gasto_promedio_diario_total=format_number(gasto_promedio_diario_total),
        expense_data_current_month=expense_data_current_month,
        expense_data_total=expense_data_total
    )

# Incluir la importación de la aplicación en la parte inferior del archivo
from app import app


