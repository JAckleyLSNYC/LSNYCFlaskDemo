from flask import Flask
from flask import render_template

app = Flask(__name__)

#from app import routes
#from app import app

from app import Hyperlink
from app import BatchPAUpdaterGuardrails




@app.route('/')
@app.route('/index')
def index():
    return render_template('index.html')

@app.errorhandler(404)
def not_found_error(error):
    return render_template('404.html'), 404

@app.errorhandler(500)
def internal_error(error):
    #db.session.rollback()
    return render_template('500.html'), 500
