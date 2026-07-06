from flask import Blueprint, render_template, g
from utils.auth import login_required

bp = Blueprint('manual', __name__)


@bp.route('/manual')
@login_required
def index():
    return render_template('manual.html', user=g.user)
