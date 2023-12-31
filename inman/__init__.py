import os

from flask import Flask


def create_app(test_config=None):
    # create and configure the app
    app = Flask(__name__, instance_relative_config=True)
    app.config.from_mapping(
        SECRET_KEY='dev',
        DATABASE=os.path.join(app.instance_path, 'inventory-manager.sqlite'),
        LOG=os.path.join(app.instance_path, 'log.txt'),
        REPORT_HTML=os.path.join(app.instance_path, 'report.html'),
        REPORT=os.path.join(app.instance_path, 'report.pdf'),
        CSS=os.path.join(app.root_path, 'static/bootstrap.min.css'),
    )

    if test_config is None:
        # load the instance config, if it exists, when not testing
        app.config.from_pyfile('config.py', silent=True)
    else:
        # load the test config if passed in
        app.config.from_mapping(test_config)

    # ensure the instance folder exists
    try:
        os.makedirs(app.instance_path)
    except OSError:
        pass

    from . import db
    db.init_app(app)

    from . import log
    log.init_app(app)

    from . import index
    app.register_blueprint(index.bp)
    app.add_url_rule('/', endpoint='index')

    from . import report
    app.register_blueprint(report.bp)
    app.add_url_rule('/', endpoint='report')

    return app
