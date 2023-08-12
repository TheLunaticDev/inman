from inman.db import get_db
from flask import (
    Blueprint, render_template
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

    return render_template('report-normal-service.html', data=data)


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

    return render_template('report-other-service.html', data=data)
