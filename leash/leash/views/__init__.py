from flask import Blueprint, g
from flask.ext.login import current_user
from itsdangerous import URLSafeTimedSerializer

from .. import app
from ..utils import show_gravatar

auth = Blueprint('auth', __name__)
home = Blueprint('home', __name__)

ts = URLSafeTimedSerializer(app.config["SECRET_KEY"])


@home.before_app_request
@auth.before_app_request
def pre_request():
    g.user = current_user
    if not (g.user.is_anonymous):
        if (g.user.picture):
            media_path = '/' + app.config['MEDIA_FOLDER'] + '/'
            user_img = media_path + g.user.picture
        else:
            user_img = show_gravatar(g.user.email)

        g.img = '<img src="' + user_img + '" height="40" width="40" />'
