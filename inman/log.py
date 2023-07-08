from datetime import datetime

entries = []

def log_entry(text):
    global entries
    entries += [datetime.now().strftime('%Y-%m-%d %H:%M:%S') + ' ' + text]

def register_log(e=None):
    global entries
    with open(current_app.config['LOG'], 'a') as f:
        for entry in entries:
            print(entry, file=f)
        entries = []

def init_app(app):
    app.teardown_appcontext(register_log)
