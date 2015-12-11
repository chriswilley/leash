import datetime
import logging
import os

from flask import Flask, g, redirect, url_for, request
from flask.ext.bcrypt import Bcrypt
from flask.ext.login import LoginManager
from flask.ext.sqlalchemy import SQLAlchemy
from flask_admin import Admin, AdminIndexView, expose
from flask_admin.contrib.sqla import ModelView
from flask_admin.form import SecureForm, ImageUploadField
from flask_debugtoolbar import DebugToolbarExtension
from flask_mail import Mail
from jinja2 import Markup
from logging import Formatter, getLogger
from logging.handlers import RotatingFileHandler
from wtforms import PasswordField, TextAreaField, SelectField
from wtforms.widgets import PasswordInput

app = Flask(__name__, instance_relative_config=True)

app.config.from_object('config')
app.config.from_pyfile('config.py')

db = SQLAlchemy(app)

bcrypt = Bcrypt(app)

mail = Mail(app)

upload_path = os.path.join(
    os.path.dirname(__file__), app.config['UPLOAD_FOLDER'])

from .models import User, Puppy, PuppyProfile, Shelter
from .utils import show_gravatar


class SecureAdminView(ModelView):
    form_base_class = SecureForm

    def is_accessible(self):
        if not (g.user.is_anonymous):
            return g.user.is_admin
        else:
            return False

    def inaccessible_callback(self, name, **kwargs):
        # redirect to login page if user doesn't have access
        return redirect(url_for('auth.login', next=request.url))


class DefaultAdminView(AdminIndexView):

    @expose('/')
    def index(self):
        if not (g.user.is_anonymous):
            if (g.user.is_admin):
                return self.render('admin/index.html')

        return redirect(url_for('auth.login', next=request.url))


class PuppyAdminView(SecureAdminView):
    def _list_thumbnail(view, context, model, name):
        if not model.picture:
            return ''

        return Markup(
            '<img src="%s" height="40">' % url_for(
                'home.media', filename=model.picture))

    def after_model_change(self, form, model, is_created):
        if (model.profile):
            pProfile = model.profile
            pProfile.description = form.description.data
            pProfile.special_needs = form.special_needs.data
        else:
            pProfile = PuppyProfile(
                puppy=model,
                description=form.description.data,
                special_needs=form.special_needs.data
            )
        db.session.add(pProfile)

        if (model.adopter and model.shelter):
            model.shelter = None
            db.session.add(model)
        db.session.commit()

    def on_form_prefill(self, form, id):
        puppy = Puppy.query.filter_by(id=id).one()
        if (puppy.profile):
            pProfile = puppy.profile
            form.description.data = pProfile.description
            form.special_needs.data = pProfile.special_needs

    column_formatters = {
        'picture': _list_thumbnail
    }

    column_filters = ['shelter.name']
    can_view_details = True
    form_overrides = {
        'picture': ImageUploadField,
        'gender': SelectField
    }
    form_args = {
        'picture': {
            'label': 'Puppy Image',
            'base_path': upload_path,
            'endpoint': 'home.media'
        },
        'gender': {
            'choices': [
                ('male', 'Male'), ('female', 'Female')
            ]
        }
    }
    form_excluded_columns = ('profile',)
    form_extra_fields = {
        'description': TextAreaField(),
        'special_needs': TextAreaField()
    }


class UserAdminView(SecureAdminView):
    def _list_thumbnail(view, context, model, name):
        if not model.picture:
            return Markup('<img src="%s">' % show_gravatar(model.email))

        return Markup(
            '<img src="%s" height="40" width="40">' % url_for(
                'home.media', filename=model.picture))

    column_exclude_list = ('_password',)
    column_formatters = {
        'picture': _list_thumbnail,
        'date_created': lambda v, c, m, p: datetime.datetime.strftime(
            m.date_created, '%b %d, %Y %I:%M %p')
    }
    roles = app.config['USER_ROLES']
    form_args = {
        'picture': {
            'label': 'User Image',
            'base_path': upload_path,
            'endpoint': 'home.media'
        }
    }
    form_choices = {
        'role': roles.items()
    }
    form_overrides = {
        'picture': ImageUploadField
    }
    form_widget_args = {
        'date_created': {
            'disabled': True
        }
    }
    form_extra_fields = {
        'password': PasswordField(
            'Password', widget=PasswordInput(hide_value=False))
    }

admin = Admin(
    app,
    name='leash',
    template_mode='bootstrap3',
    index_view=DefaultAdminView()
)

admin.add_view(UserAdminView(User, db.session))
admin.add_view(PuppyAdminView(Puppy, db.session))
admin.add_view(SecureAdminView(Shelter, db.session))

toolbar = DebugToolbarExtension(app)

login_manager = LoginManager()
login_manager.init_app(app)
login_manager.login_view = 'auth.login'

if not (app.debug):
    dirname = os.path.dirname
    logfile = os.path.join(dirname(dirname(__file__)), 'logs/app.log')
    handler = RotatingFileHandler(logfile, maxBytes=10240, backupCount=10)
    handler.setLevel(logging.WARNING)
    handler.setFormatter(Formatter(
        '%(asctime)s %(levelname)s %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    loggers = [app.logger, getLogger('sqlalchemy')]
    for l in loggers:
        l.addHandler(handler)


@login_manager.user_loader
def load_user(userid):
    return User.query.filter(User.id == int(userid)).first()

from leash.views.auth import auth
from leash.views.home import home

app.register_blueprint(auth)
app.register_blueprint(home)
