from flask import g
from flask_wtf import Form
from flask_wtf.file import FileField, FileAllowed, FileRequired
from wtforms import (
    DateField,
    DecimalField,
    StringField,
    PasswordField,
    TextAreaField,
    SelectField,
    IntegerField
)
from wtforms.ext.sqlalchemy.fields import QuerySelectField
from wtforms.validators import DataRequired, Email, Optional, URL
from wtforms.widgets import PasswordInput
from . import app
from .models import Shelter, User
from .validators import Unique


def get_shelters():
    if (g.user.is_operator):
        return Shelter.query.filter(
            Shelter.operator.contains(g.user)).all()
    else:
        return Shelter.query.all()


class EmailPasswordForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])
    password = PasswordField('Password', validators=[DataRequired()])


class EmailForm(Form):
    email = StringField('Email', validators=[DataRequired(), Email()])


class PasswordForm(Form):
    password = PasswordField('Password', validators=[DataRequired()])


class AccountForm(Form):
    name = StringField('Your Name')
    email = StringField(
        'Email Address',
        validators=[
            DataRequired(),
            Email(message='Please enter a valid email address.')
        ]
    )


class PuppyProfileForm(Form):
    description = TextAreaField('Description')
    special_needs = TextAreaField('Special Needs')


class ShelterForm(Form):
    state_choices = app.config['US_STATES']

    name = StringField('Name', validators=[DataRequired()])
    address = StringField('Address')
    city = StringField('City')
    state = SelectField('State', choices=state_choices)
    zip_code = StringField('Zip Code')
    email = StringField('Email', validators=[Email(), Optional()])
    website = StringField('Website', validators=[URL(), Optional()])
    max_puppies = IntegerField('Max # of Puppies')


class PuppyForm(PuppyProfileForm):
    shelter = QuerySelectField('Shelter', query_factory=get_shelters)
    name = StringField('Name', validators=[DataRequired()])
    date_of_birth = DateField('<nobr>Date of Birth</nobr>')
    breed = StringField('Breed')
    gender = SelectField(
        'Gender',
        choices=[('male', 'Male'), ('female', 'Female')],
        validators=[DataRequired()]
    )
    weight = DecimalField('<nobr>Weight (lbs.)</nobr>')
    picture = FileField('Puppy Image', validators=[
        FileRequired(),
        FileAllowed(['jpg', 'png'], 'Please only upload image files')
    ])


class UserForm(Form):
    user_roles = app.config['USER_ROLES']
    picture_msg = 'If you leave "Picture" blank, Leash will use the user\'s '
    picture_msg += 'email address to pull from gravatar'

    # without this parameter, the Unique() validator would prevent model edits
    is_edit = False

    name = StringField('<nobr>Full Name</nobr>')
    email = StringField(
        'Email',
        validators=[
            DataRequired(),
            Email(message='Please enter a valid email address.'),
            Unique(
                User,
                User.email,
                message='There is already an account with this email address.'
            )
        ]
    )
    picture = FileField('Picture', validators=[
        FileAllowed(['jpg', 'png'], 'Please only upload image files')
    ], description=picture_msg)
    password = PasswordField(
        'Password',
        widget=PasswordInput(hide_value=False),
        validators=[DataRequired()]
    )
    role = SelectField('Role', choices=user_roles.items())
