from inman.db import get_db
from flask import (
    Blueprint, render_template, request, flash, redirect, url_for, current_app
)

bp = Blueprint('report', __name__)


@bp.route('/report-normal-service', methods=('GET', 'POST'))
def normal_service():
    db = get_db()
    data = db.execute(
        "SELECT inventory.asset_no,"
        " asset_type.name AS asset_type_name,"
        " company.name AS company_name,"
        " location.name AS location_name,"
        " status.name AS status_name,"
        " service_date, remarks,"
        " DATE(service_date, '+1 Year') AS due_date"
        " FROM normal_service"
        " INNER JOIN inventory ON inventory.id = normal_service.asset_id"
        " INNER JOIN asset_type ON asset_type.id = inventory.asset_type"
        " INNER JOIN company ON company.id = inventory.company"
        " INNER JOIN location ON location.id = inventory.location"
        " INNER JOIN status ON status.id = inventory.status"
        " ORDER BY service_date DESC"
    ).fetchall()

    report = render_template('report-normal-service.html', data=data)
    with open(current_app.config['REPORT_HTML'], 'w') as f:
        f.write(report)
    return report


@bp.route('/report-other-service', methods=('GET', 'POST'))
def other_service():
    db = get_db()
    data = db.execute(
        "SELECT inventory.asset_no,"
        " asset_type.name AS asset_type_name,"
        " company.name AS company_name,"
        " location.name AS location_name,"
        " status.name AS status_name,"
        " service_date, remarks"
        " FROM other_service"
        " INNER JOIN inventory ON inventory.id = other_service.asset_id"
        " INNER JOIN asset_type ON asset_type.id = inventory.asset_type"
        " INNER JOIN company ON company.id = inventory.company"
        " INNER JOIN location ON location.id = inventory.location"
        " INNER JOIN status ON status.id = inventory.status"
        " ORDER BY service_date DESC"
    ).fetchall()

    report = render_template('report-other-service.html', data=data)
    with open(current_app.config['REPORT_HTML'], 'W') as f:
        f.write(report)
    return report


@bp.route('/report-for-an-asset', methods=('GET', 'POST'))
def asset_number():
    asset_no = request.form['report_asset_no']
    choice = request.form['report_asset_choice']
    db = get_db()
    error = None

    if asset_no is None:
        error = 'No Asset Number was provided!'

    asset_id = db.execute(
        'SELECT id FROM inventory WHERE asset_no=?',
        (asset_no,)
    ).fetchone()

    if asset_id is None:
        error = 'No Asset was found having the provided Asset Number!'

    if error:
        flash(error, category='error')
        return redirect(url_for('index'))

    asset_information = db.execute(
        "SELECT asset_no,"
        " asset_type.name AS asset_type_name,"
        " company.name AS company_name,"
        " location.name AS location_name,"
        " status.name AS status_name"
        " FROM inventory"
        " INNER JOIN asset_type ON asset_type.id = inventory.asset_type"
        " INNER JOIN company ON company.id = inventory.company"
        " INNER JOIN location ON location.id = inventory.location"
        " INNER JOIN status ON status.id = inventory.status"
        " WHERE inventory.id=?",
        (asset_id[0],)
    ).fetchone()

    normal_service = db.execute(
        "SELECT service_date, remarks,"
        " DATE(service_date, '+1 Year') AS due_date"
        " FROM normal_service"
        " WHERE asset_id=?"
        " ORDER BY service_date DESC",
        (asset_id[0],)
    ).fetchall()

    other_service = db.execute(
        "SELECT service_date, remarks"
        " FROM other_service"
        " WHERE asset_id=?"
        " ORDER BY service_date DESC",
        (asset_id[0],)
    ).fetchall()

    if choice == 'full':
        report = render_template('report-asset-number.html',
                                 asset_information=asset_information,
                                 normal_service=normal_service,
                                 other_service=other_service)
        with open(current_app.config['REPORT_HTML'], 'W') as f:
            f.write(report)
        return report
    elif choice == 'normal':
        report = render_template('report-asset-number-normal.html',
                                 asset_information=asset_information,
                                 normal_service=normal_service)
        with open(current_app.config['REPORT_HTML'], 'W') as f:
            f.write(report)
        return report
    elif choice == 'other':
        report = render_template('report-asset-number-other.html',
                                 asset_information=asset_information,
                                 other_service=other_service)
        with open(current_app.config['REPORT_HTML'], 'W') as f:
            f.write(report)
        return report
    else:
        flash('Could not understand request for report generation.',
              category='error')
        return redirect(url_for('index'))


@bp.route('/report-location', methods=('GET', 'POST'))
def location():
    location = request.form['report_location_id']
    location_name = None
    choice = request.form['report_location_choice']
    db = get_db()
    error = None

    if location is None:
        error = 'No location was provided!'

    if error:
        flash(error, category='error')
        return redirect(url_for('index'))

    location_name = db.execute(
        "SELECT name FROM location WHERE id=?",
        (location,)
    ).fetchone()[0]

    normal_data = db.execute(
        "SELECT inventory.asset_no AS asset_number,"
        " asset_type.name AS asset_type,"
        " company.name AS company,"
        " service_date, DATE(service_date, '+1 Year') AS due_date,"
        " remarks FROM normal_service"
        " INNER JOIN inventory ON inventory.id = normal_service.asset_id"
        " INNER JOIN asset_type ON asset_type.id = inventory.asset_type"
        " INNER JOIN company ON company.id = inventory.company"
        " AND asset_id IN ("
        " SELECT id FROM inventory WHERE"
        " location = ?)"
        " ORDER BY inventory.id, service_date DESC",
        (location,)
    ).fetchall()

    other_data = db.execute(
        "SELECT inventory.asset_no AS asset_number,"
        " asset_type.name AS asset_type,"
        " company.name AS company,"
        " service_date, remarks"
        " FROM other_service"
        " INNER JOIN inventory ON inventory.id = other_service.asset_id"
        " INNER JOIN asset_type ON asset_type.id = inventory.asset_type"
        " INNER JOIN company ON company.id = inventory.company"
        " AND asset_id IN ("
        " SELECT id FROM inventory WHERE"
        " location = ?)"
        " ORDER BY inventory.id, service_date DESC",
        (location,)
    ).fetchall()

    if choice == 'full':
        report = render_template('report-location.html',
                                 location_name=location_name,
                                 normal_data=normal_data,
                                 other_data=other_data)
        with open(current_app.config['REPORT_HTML'], 'W') as f:
            f.write(report)
        return report
    elif choice == 'normal':
        report = render_template('report-location-normal.html',
                                 location_name=location_name,
                                 normal_data=normal_data)
        with open(current_app.config['REPORT_HTML'], 'W') as f:
            f.write(report)
        return report
    elif choice == 'other':
        report = render_template('report-location-other.html',
                                 location_name=location_name,
                                 other_data=other_data)
        with open(current_app.config['REPORT_HTML'], 'W') as f:
            f.write(report)
        return report
    else:
        flash('Could not understand request for report generation.',
              category='error')
        return redirect(url_for('index'))
