import functools
import pdfkit

from flask import (
    Blueprint, flash, g, redirect, render_template, request, session, url_for,
    current_app, send_file
)
from werkzeug.security import check_password_hash, generate_password_hash
from pyvirtualdisplay import Display

from inman.db import get_db
from inman.log import log_entry

bp = Blueprint('index', __name__)


def get_data(db):
    table = db.execute(
        'SELECT inventory.id, asset_no,'
        ' asset_type.name AS asset_type,'
        ' company.name AS company,'
        ' location.name AS location,'
        ' status.name AS status FROM inventory'
        ' INNER JOIN asset_type ON asset_type.id=inventory.asset_type'
        ' INNER JOIN company ON company.id=inventory.company'
        ' INNER JOIN location ON location.id=inventory.location'
        ' INNER JOIN status ON status.id=inventory.status'
    ).fetchall()
    data = []
    for row in table:
        entry = {}
        entry['asset_info'] = row
        normal_services = db.execute(
            "SELECT service_date, DATE(service_date, '+1 Year') AS due_date, remarks FROM normal_service WHERE asset_id=? ORDER BY service_date DESC", (row['id'],)
        ).fetchall()
        normal_service = []
        for services in normal_services:
            normal_service.append(services)

        entry['normal_service'] = normal_service
            
        other_services = db.execute(
            "SELECT service_date, remarks FROM other_service WHERE asset_id=? ORDER BY service_date DESC", (row['id'],)
        ).fetchall()
        other_service = []
        for services in other_services:
            other_service.append(services)
        
        entry['other_service'] = other_service
        data.append(entry)

    return data


@bp.route('/', methods=('GET', 'POST'))
def index():
    db = get_db()
    access = db.execute(
        'SELECT * FROM access ORDER BY id desc'
    ).fetchall()
    user = db.execute(
        'SELECT * FROM user ORDER BY username asc'
    ).fetchall()
    asset = db.execute(
        'SELECT * FROM inventory ORDER BY id asc'
    ).fetchall()
    asset_type = db.execute(
        'SELECT * FROM asset_type ORDER BY name asc'
    ).fetchall()
    company = db.execute(
        'SELECT * FROM company ORDER BY name asc'
    ).fetchall()
    location = db.execute(
        'SELECT * FROM location ORDER BY name asc'
    ).fetchall()
    status = db.execute(
        'SELECT * FROM status ORDER BY name ASC'
    ).fetchall()
    data = get_data(db)

    return render_template('index.html', access=access, user=user, asset=asset, asset_type=asset_type, company=company, location=location, status=status, data=data)

@bp.route('/login', methods=['POST'])
def login():
    if request.method == 'POST':
        username = request.form['username']
        password = request.form['password']
        db = get_db()
        error = None
        user = db.execute(
            'SELECT * FROM user WHERE username = ?', (username,)
        ).fetchone()

        if user is None:
            error = 'Incorrect Username!'
        elif not check_password_hash(user['password'], password):
            error = 'Incorrect Password!'

        if error is None:
            session.clear()
            session['user_id'] = user['id']
            log_entry(str(username) + ' has logged in.')
            return redirect(url_for('index'))

        flash(error, category='error')
        return redirect(url_for('index'))

@bp.before_app_request
def load_logged_in_user():
    user_id = session.get('user_id')

    if user_id is None:
        g.user = None
    else:
        g.user = get_db().execute(
            'SELECT * FROM user WHERE id = ?', (user_id,)
        ).fetchone()

@bp.route('/logout')
def logout():
    session.clear()
    log_entry(str(g.user['username'] + ' has logged out.'))
    return redirect(url_for('index'))

def login_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None:
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view

def admin_required(view):
    @functools.wraps(view)
    def wrapped_view(**kwargs):
        if g.user is None or g.user['access'] != 1:
            return redirect(url_for('index'))

        return view(**kwargs)

    return wrapped_view


@bp.route('/download-log')
@admin_required
def download_log():
    path = current_app.config['LOG']
    return send_file(path, as_attachment=True)


@bp.route('/download-report')
@admin_required
def download_report():
    try:
        css = url_for('static', filename='bootstrap.min.css')
        with Display():
            pdfkit.from_file(current_app.config['REPORT_HTML'],
                             current_app.config['REPORT'],
                             css=css)
    finally:
        path = current_app.config['REPORT']
        return send_file(path, as_attachment=True)


@bp.route('/register', methods=['POST'])
@admin_required
def register():
    username = request.form['username']
    password = request.form['password']
    access = request.form['access']
    db = get_db()
    error = None
    
    if not username:
        error = 'Username is required!'
    elif not password:
        error = 'Password is required!'
    elif not access:
        error = 'Access rights must be specified!'
        
    if error is None:
        try:
            db.execute(
                'INSERT INTO user (username, password, access) VALUES (?, ?, ?)',
                (username, generate_password_hash(password), access),
            )
            db.commit()
        except db.IntegrityError:
            error = f"User {username} is already registered."
        else:
            l_access = db.execute(
                'SELECT * FROM access WHERE id = ?', (access,)
            ).fetchone()
            log_entry(str(g.user['username']) + ' added a new ' + l_access['name'] + ' user with username ' + str(username))
            flash('Successfully Registered ' + str(username) + ' as an ' + l_access['name'], 'message')
            return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/terminate', methods=['POST'])
@admin_required
def terminate():
    id = request.form['userid']
    db = get_db()

    error = None

    entry = db.execute(
        'SELECT * FROM user WHERE id=?', (id,)
    ).fetchone()

    if entry is None:
        error = "Didn't find the username you specified."

    if id is None:
        error = "You must choose a valid entry from the provided options."

    if error is None:
        username = entry['username']
        db.execute(
            'DELETE FROM user WHERE id=?', (id,)
        )
        db.commit()
        log_entry(str(g.user['username'] + ' deleted a user with username ' + username + '.'))
        flash('Successfully deleted a user.', 'message')
        return redirect(url_for('index'))
    else:
        flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/add-asset-type', methods=['POST'])
@admin_required
def add_asset_type():
    asset_type = request.form['asset_type']
    db = get_db()
    error = None
    
    if not asset_type:
        error = 'You have to provide a name for the Asset Type to be added!'
        
    if error is None:
        try:
            db.execute(
                'INSERT INTO asset_type VALUES (NULL, ?)',
                (asset_type,),
            )
            db.commit()
        except db.IntegrityError:
            error = f"The asset type {asset_type} is already registered."
        else:
            log_entry(str(g.user['username']) + ' added a new asset type called ' +  str(asset_type) + '.')
            flash('Successfully Registered ' + str(asset_type) + ' as a new asset type.', 'message')
            return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/delete-asset-type', methods=['POST'])
@admin_required
def delete_asset_type():
    id = request.form['asset_type_id']
    db = get_db()

    error = None

    asset_type = db.execute(
        'SELECT * FROM asset_type WHERE id=?', (id,)
    ).fetchone()

    if asset_type is None:
        error = "Didn't find the asset type you specified."

    if id is None:
        error = "You must choose a valid entry from the provided options."

    if error is None:
        asset_type_name = asset_type['name']
        db.execute(
            'DELETE FROM asset_type WHERE id=?', (id,)
        )
        db.commit()
        log_entry(str(g.user['username'] + ' deleted an asset type with name ' + asset_type_name + '.'))
        flash('Successfully deleted an asset type.', 'message')
        return redirect(url_for('index'))
    else:
        flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/add-company', methods=['POST'])
@admin_required
def add_company():
    name = request.form['company_name']
    db = get_db()
    error = None
    
    if not name:
        error = 'You have to provide a name for the company to be added!'
        
    if error is None:
        try:
            db.execute(
                'INSERT INTO company VALUES (NULL, ?)',
                (name,),
            )
            db.commit()
        except db.IntegrityError:
            error = f"The company {name} is already registered."
        else:
            log_entry(str(g.user['username']) + ' added a new company called ' +  str(name) + '.')
            flash('Successfully Registered ' + str(name) + ' as a new company.', 'message')
            return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/delete-company', methods=['POST'])
@admin_required
def delete_company():
    id = request.form['company_id']
    db = get_db()

    error = None

    company = db.execute(
        'SELECT * FROM company WHERE id=?', (id,)
    ).fetchone()

    if company is None:
        error = "Didn't find the company you specified."

    if id is None:
        error = "You must choose a valid entry from the provided options."

    if error is None:
        company_name = company['name']
        db.execute(
            'DELETE FROM company WHERE id=?', (id,)
        )
        db.commit()
        log_entry(str(g.user['username'] + ' deleted a company with name ' + company_name + '.'))
        flash('Successfully deleted a company.', 'message')
        return redirect(url_for('index'))
    else:
        flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/add-location', methods=['POST'])
@admin_required
def add_location():
    name = request.form['location_name']
    db = get_db()
    error = None
    
    if not name:
        error = 'You have to provide a name for the location to be added!'
        
    if error is None:
        try:
            db.execute(
                'INSERT INTO location VALUES (NULL, ?)',
                (name,),
            )
            db.commit()
        except db.IntegrityError:
            error = f"The location {name} is already registered."
        else:
            log_entry(str(g.user['username']) + ' added a new location called ' +  str(name) + '.')
            flash('Successfully Registered ' + str(name) + ' as a new location.', 'message')
            return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/delete-location', methods=['POST'])
@admin_required
def delete_location():
    id = request.form['location_id']
    db = get_db()

    error = None

    location = db.execute(
        'SELECT * FROM location WHERE id=?', (id,)
    ).fetchone()

    if location is None:
        error = "Didn't find the location you specified."

    if id is None:
        error = "You must choose a valid entry from the provided options."

    if error is None:
        location_name = location['name']
        db.execute(
            'DELETE FROM location WHERE id=?', (id,)
        )
        db.commit()
        log_entry(str(g.user['username'] + ' deleted a location with name ' + location_name + '.'))
        flash('Successfully deleted a location.', 'message')
        return redirect(url_for('index'))
    else:
        flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/add-status', methods=['POST'])
@admin_required
def add_status():
    name = request.form['status_name']
    db = get_db()
    error = None
    
    if not name:
        error = 'You have to provide a name for the status type to be added!'
        
    if error is None:
        try:
            db.execute(
                'INSERT INTO status VALUES (NULL, ?)',
                (name,),
            )
            db.commit()
        except db.IntegrityError:
            error = f"The status {name} is already registered."
        else:
            log_entry(str(g.user['username']) + ' added a new status type called ' +  str(name) + '.')
            flash('Successfully Registered ' + str(name) + ' as a new status type.', 'message')
            return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/delete-status', methods=['POST'])
@admin_required
def delete_status():
    id = request.form['status_id']
    db = get_db()

    error = None

    status = db.execute(
        'SELECT * FROM status WHERE id=?', (id,)
    ).fetchone()

    if status is None:
        error = "Didn't find the status you specified."

    if id is None:
        error = "You must choose a valid entry from the provided options."

    if error is None:
        status_name = status['name']
        db.execute(
            'DELETE FROM status WHERE id=?', (id,)
        )
        db.commit()
        log_entry(str(g.user['username'] + ' deleted a status type with name ' + status_name + '.'))
        flash('Successfully deleted a status type.', 'message')
        return redirect(url_for('index'))
    else:
        flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/add-entry', methods=['POST'])
@admin_required
def add_entry():
    asset_no = request.form['asset_no']
    asset_type_id = request.form['asset_type']
    company_id = request.form['company']
    location_id = request.form['location']
    status_id = request.form['status']
    db = get_db()
    error = None
    
    if not asset_no:
        error = 'You have to provide an asset number for the asset to be added!'
    if not asset_type_id or not company_id or not location_id or not status_id:
        error = 'Please choose all the valid response from the given modal form when pressing add entry.'
        
    if error is None:
        try:
            db.execute(
                'INSERT INTO inventory (asset_no, asset_type, company, location, status) VALUES (?, ?, ?, ?, ?)',
                (asset_no, asset_type_id, company_id, location_id, status_id),
            )
            db.commit()
        except db.IntegrityError:
            error = f"Either an asset with asset number {asset_no} already exists or you did some mistake while filling in the form."
        else:
            log_entry(str(g.user['username']) + ' added a new asset with asset number ' +  str(asset_no) + '.')
            flash('Successfully Registered a new asset with asset number ' + str(asset_no) + '.', 'message')
            return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/location-filter-applied', methods=['POST'])
def location_filter_applied():
    db = get_db()
    access = db.execute(
        'SELECT * FROM access ORDER BY id desc'
    ).fetchall()
    user = db.execute(
        'SELECT * FROM user ORDER BY username asc'
    ).fetchall()
    asset = db.execute(
        'SELECT * FROM inventory ORDER BY id asc'
    ).fetchall()
    asset_type = db.execute(
        'SELECT * FROM asset_type ORDER BY name asc'
    ).fetchall()
    company = db.execute(
        'SELECT * FROM company ORDER BY name asc'
    ).fetchall()
    location = db.execute(
        'SELECT * FROM location ORDER BY name asc'
    ).fetchall()
    status = db.execute(
        'SELECT * FROM status ORDER BY name ASC'
    ).fetchall()

    filter_location_id = request.form['filter_location']
    db = get_db()
    table = db.execute(
        'SELECT inventory.id, asset_no, asset_type.name AS asset_type, company.name AS company, location.name AS location, status.name AS status FROM inventory'
        ' INNER JOIN asset_type ON asset_type.id=inventory.asset_type'
        ' INNER JOIN company ON company.id=inventory.company'
        ' INNER JOIN location ON location.id=inventory.location'
        ' INNER JOIN status ON status.id=inventory.status'
        ' AND location.id LIKE ?',
        (filter_location_id,)
    ).fetchall()
    data = []
    for row in table:
        entry = {}
        entry['asset_info'] = row
        normal_services = db.execute(
            "SELECT service_date, DATE(service_date, '+1 Year') AS due_date, remarks FROM normal_service WHERE asset_id=? ORDER BY service_date DESC", (row['id'],)
        ).fetchall()
        normal_service = []
        for services in normal_services:
            normal_service.append(services)

        entry['normal_service'] = normal_service
            
        other_services = db.execute(
            "SELECT service_date, remarks FROM other_service WHERE asset_id=? ORDER BY service_date DESC", (row['id'],)
        ).fetchall()
        other_service = []
        for services in other_services:
            other_service.append(services)
        
        entry['other_service'] = other_service
        data.append(entry)

    return render_template('index.html', access=access, user=user, asset=asset, asset_type=asset_type, company=company, location=location, status=status, data=data)

@bp.route('/delete-entry', methods=['POST'])
@admin_required
def delete_entry():
    asset_no = request.form['asset_no']
    if asset_no is None:
        flash('No asset number was provided. Nothing was deleted!', 'error')
        return redirect(url_for('index'))

    db = get_db()
    db.execute(
        'DELETE FROM inventory WHERE asset_no=?'
        , (asset_no,)
    )
    db.commit()
    flash('Successfully deleted asset with asset number ' + str(asset_no) + '.', 'message')
    log_entry(str(g.user['username']) + ' deleted an asset with asset number ' +  str(asset_no) + '.')
    return redirect(url_for('index'))

@bp.route('/edit-asset-no/', methods=['POST'])
@admin_required
def edit_asset_no():
    asset_no = request.form["asset_no"]
    new_asset_no = request.form["new_asset_no"]
    db = get_db()
    error = None
    
    if not new_asset_no:
        error = 'You have to provide an asset number for the asset number to be updated!'
        
    if error is None:
        try:
            db.execute(
                'UPDATE inventory SET asset_no=? WHERE asset_no=?',
                (new_asset_no, asset_no),
            )
            db.commit()
        except db.IntegrityError:
            error = f"Either an asset with asset number {new_asset_no} already exists or you did some mistake while filling in the form."
        else:
            log_entry(str(g.user['username']) + ' updated asset number ' + str(asset_no) + ' with asset number ' +  str(new_asset_no) + '.')
            flash('Successfully updated asset number ' + str(asset_no) + ' with asset number ' + str(new_asset_no) + '.', 'message')
            return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/edit-asset-type', methods=['POST'])
@admin_required
def edit_asset_type():
    asset_no = request.form["asset_no"]
    new_asset_type = request.form["new_type"]
    db = get_db()
    error = None
    
    if not new_asset_type:
        error = 'You have to provide an asset type for the asset type to be updated!'
        
    if error is None:
        db.execute(
            'UPDATE inventory SET asset_type=? WHERE asset_no=?',
            (new_asset_type, asset_no),
        )
        db.commit()

        log_entry(str(g.user['username']) + ' updated asset type of an asset with asset number ' + str(asset_no) + '.')
        flash('Successfully updated asset type of an asset with asset number ' + str(asset_no) + '.', 'message')
        return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/edit-company', methods=['POST'])
@admin_required
def edit_company():
    asset_no = request.form["asset_no"]
    new_company = request.form["new_company"]
    db = get_db()
    error = None
    
    if not new_company:
        error = 'You have to provide a company name for the company to be updated!'
        
    if error is None:
        db.execute(
            'UPDATE inventory SET company=? WHERE asset_no=?',
            (new_company, asset_no),
        )
        db.commit()

        log_entry(str(g.user['username']) + ' updated company of an asset with asset number ' + str(asset_no) + '.')
        flash('Successfully updated company of an asset with asset number ' + str(asset_no) + '.', 'message')
        return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/edit-location', methods=['POST'])
@admin_required
def edit_location():
    asset_no = request.form["asset_no"]
    new_location = request.form["new_location"]
    db = get_db()
    error = None
    
    if not new_location:
        error = 'You have to provide a location name for the location to be updated!'
        
    if error is None:
        db.execute(
            'UPDATE inventory SET location=? WHERE asset_no=?',
            (new_location, asset_no),
        )
        db.commit()

        log_entry(str(g.user['username']) + ' updated location of an asset with asset number ' + str(asset_no) + '.')
        flash('Successfully updated location of an asset with asset number ' + str(asset_no) + '.', 'message')
        return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/edit-status', methods=['POST'])
@admin_required
def edit_status():
    asset_no = request.form["asset_no"]
    new_status = request.form["new_status"]
    db = get_db()
    error = None
    
    if not new_status:
        error = 'You have to provide a status name for the location to be updated!'
        
    if error is None:
        db.execute(
            'UPDATE inventory SET status=? WHERE asset_no=?',
            (new_status, asset_no),
        )
        db.commit()

        log_entry(str(g.user['username']) + ' updated status of an asset with asset number ' + str(asset_no) + '.')
        flash('Successfully updated status of an asset with asset number ' + str(asset_no) + '.', 'message')
        return redirect(url_for('index'))
        
    flash(error, 'error')

    return redirect(url_for('index'))

@bp.route('/edit-normal-service', methods=['POST'])
@admin_required
def edit_normal_service():
    asset_no = request.form["asset_no"]
    date = request.form["date"]
    remarks = request.form["remarks"]
    choice = request.form["choice"]
    db = get_db()
    asset_id = db.execute('SELECT id FROM inventory WHERE asset_no=?', (asset_no,)).fetchone()[0]
    next_date = None

    service_id = db.execute('SELECT id FROM normal_service WHERE asset_id=? ORDER BY service_date DESC', (asset_id,)).fetchone()
    if service_id != None:
        service_id = service_id[0]

    error = None
    if date == '' or date is None:
        db.execute('DELETE FROM normal_service WHERE asset_id=? AND id=?', (asset_id, service_id))
        db.commit()
    elif choice == 'add':
        db.execute('INSERT INTO normal_service (asset_id, service_date, remarks) VALUES (?, ?, ?)', (asset_id, date, remarks))
        db.commit()
    elif choice == 'update':
        db.execute('UPDATE normal_service SET remarks=? WHERE asset_id=? AND id=?', (remarks, asset_id, service_id))
        db.execute('UPDATE normal_service SET service_date=? WHERE asset_id=? AND id=?', (date, asset_id, service_id))
        db.commit()
    else:
        error = "Options provided is not understood by the server!"

    if error is None:
        log_entry(str(g.user['username']) + ' updated normal service date of an asset with asset number ' + str(asset_no) + ' to ' + str(date) + '.')
        flash('Successfully updated normal service date of an asset with asset number ' + str(asset_no) + '.', 'message')
        return redirect(url_for('index'))
    else:
        flash(error, 'error')
        return redirect(url_for('index'))

@bp.route('/add-normal-service', methods=['POST'])
@login_required
def add_normal_service():
    asset_no = request.form["asset_no"]
    date = request.form["andate"]
    remarks = request.form["anremarks"]
    db = get_db()
    asset_id = db.execute('SELECT id FROM inventory WHERE asset_no=?', (asset_no,)).fetchone()[0]

    service_id = db.execute('SELECT id FROM normal_service WHERE asset_id=? ORDER BY service_date DESC', (asset_id,)).fetchone()
    if service_id != None:
        service_id = service_id[0]

    db.execute('INSERT INTO normal_service (asset_id, service_date, remarks) VALUES (?, ?, ?)', (asset_id, date, remarks))
    db.commit()

    log_entry(str(g.user['username']) + ' added a normal service date of an asset with asset number ' + str(asset_no) + ' to ' + str(date) + '.')
    flash('Successfully updated a normal service date of an asset with asset number ' + str(asset_no) + '.', 'message')
    return redirect(url_for('index'))
    
@bp.route('/edit-other-service', methods=['POST'])
@admin_required
def edit_other_service():
    asset_no = request.form["asset_no"]
    date = request.form["odate"]
    remarks = request.form["oremarks"]
    choice = request.form["choice"]
    db = get_db()
    asset_id = db.execute('SELECT id FROM inventory WHERE asset_no=?', (asset_no,)).fetchone()[0]

    service_id = db.execute('SELECT id FROM other_service WHERE asset_id=? ORDER BY service_date DESC', (asset_id,)).fetchone()
    if service_id != None:
        service_id = service_id[0]

    error = None
    if date == '' or date is None:
        db.execute('DELETE FROM other_service WHERE asset_id=? AND id=?', (asset_id, service_id))
        db.commit()
    elif choice == 'add':
        db.execute('INSERT INTO other_service (asset_id, service_date, remarks) VALUES (?, ?, ?)', (asset_id, date, remarks))
        db.commit()
    elif choice == 'update':
        db.execute('UPDATE other_service SET remarks=? WHERE asset_id=? AND id=?', (remarks, asset_id, service_id))
        db.execute('UPDATE other_service SET service_date=? WHERE asset_id=? AND id=?', (date, asset_id, service_id))
        db.commit()
    else:
        error = "Options provided is not understood by the server!"

    if error is None:
        log_entry(str(g.user['username']) + ' updated other service date of an asset with asset number ' + str(asset_no) + ' to ' + str(date) + '.')
        flash('Successfully updated other service date of an asset with asset number ' + str(asset_no) + '.', 'message')
        return redirect(url_for('index'))
    else:
        flash(error, 'error')
        return redirect(url_for('index'))

@bp.route('/add-other-service', methods=['POST'])
@login_required
def add_other_service():
    asset_no = request.form["asset_no"]
    date = request.form["aodate"]
    remarks = request.form["aoremarks"]
    db = get_db()
    asset_id = db.execute('SELECT id FROM inventory WHERE asset_no=?', (asset_no,)).fetchone()[0]

    service_id = db.execute('SELECT id FROM other_service WHERE asset_id=? ORDER BY service_date DESC', (asset_id,)).fetchone()
    if service_id != None:
        service_id = service_id[0]

    db.execute('INSERT INTO other_service (asset_id, service_date, remarks) VALUES (?, ?, ?)', (asset_id, date, remarks))
    db.commit()

    log_entry(str(g.user['username']) + ' added a normal service date of an asset with asset number ' + str(asset_no) + ' to ' + str(date) + '.')
    flash('Successfully updated a normal service date of an asset with asset number ' + str(asset_no) + '.', 'message')
    return redirect(url_for('index'))

@bp.route('/generate-report', methods=['GET', 'POST'])
@admin_required
def generate_report():
    db = get_db()
    data = get_data(db)
    normal_table = db.execute(
        "SELECT strftime('%Y', service_date) as year, strftime('%m', service_date) as month, service_date, inventory.asset_no, remarks FROM normal_service INNER JOIN inventory ON inventory.id=normal_service.asset_id ORDER BY service_date").fetchall()

    other_table = db.execute(
        "SELECT strftime('%Y', service_date) as year, strftime('%m', service_date) as month, service_date, inventory.asset_no, remarks FROM other_service INNER JOIN inventory ON inventory.id=other_service.asset_id ORDER BY service_date").fetchall()

    print(normal_table)
    return render_template('report.html', data=data, normal_table=normal_table, other_table=other_table)
