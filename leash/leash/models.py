from datetime import datetime
from flask import url_for
from sqlalchemy.ext.hybrid import hybrid_property

from . import app, db, bcrypt

# Save ourselves some typing...
Col = db.Column
String = db.String
Integer = db.Integer
Date = db.Date
DateTime = db.DateTime
Numeric = db.Numeric
Boolean = db.Boolean
ForeignKey = db.ForeignKey
Table = db.Table
relationship = db.relationship
Model = db.Model

puppy_adopter = Table(
    'puppy_adopter',
    Col(
        'puppy_id',
        Integer,
        ForeignKey('puppy.id')
    ),
    Col(
        'adopter_id',
        Integer,
        ForeignKey('user.id')
    )
)

shelter_operator = Table(
    'shelter_operator',
    Col(
        'shelter_id',
        Integer,
        ForeignKey('shelter.id')
    ),
    Col(
        'operator_id',
        Integer,
        ForeignKey('user.id')
    )
)


class User(Model):
    __tablename__ = 'user'
    name = Col(String(250))
    id = Col(Integer, primary_key=True)
    email = Col(String(250), nullable=False, unique=True)
    picture = Col(String(250))
    _password = Col(String(128))
    is_oauth = Col(Boolean, default=False)
    email_confirmed = Col(Boolean, default=False)
    date_created = Col(DateTime, default=datetime.now)
    role = Col(String(25), default='default')

    __mapper_args__ = {
        'order_by': email
    }

    def __unicode__(self):
        if (self.name):
            return self.name
        else:
            return self.email

    @hybrid_property
    def password(self):
        return self._password

    @password.setter
    def _set_password(self, plaintext):
        self._password = bcrypt.generate_password_hash(plaintext)

    def is_correct_password(self, plaintext):
        return bcrypt.check_password_hash(self._password, plaintext)

    @property
    def is_active(self):
        return True

    @property
    def is_authenticated(self):
        return True

    @property
    def is_anonymous(self):
        return False

    @property
    def is_operator(self):
        return self.role == 'operator'

    @property
    def is_admin(self):
        return self.role == 'admin'

    @property
    def user_role(self):
        return app.config['USER_ROLES'][self.role]

    def get_id(self):
        return unicode(self.id)


class Puppy(Model):
    __tablename__ = 'puppy'
    name = Col(String(250), nullable=False)
    id = Col(Integer, primary_key=True)
    date_of_birth = Col(Date)
    breed = Col(String(80))
    picture = Col(String)
    gender = Col(String(6), nullable=False)
    weight = Col(Numeric(10))
    shelter_id = Col(Integer, ForeignKey('shelter.id'))
    shelter = relationship('Shelter')
    profile = relationship('PuppyProfile', uselist=False, backref='puppy')
    adopter = relationship(
        'User', secondary=puppy_adopter, backref=db.backref('puppies'))

    __mapper_args__ = {
        'order_by': shelter_id
    }

    def __unicode__(self):
        return self.name

    @property
    def serialize(self):
        # Returns object data in JSON
        specialNeeds = ''
        desc = ''
        if (self.profile):
            specialNeeds = self.profile.special_needs
            desc = self.profile.description

        if (self.date_of_birth):
            dob = datetime.strftime(self.date_of_birth, '%m/%d/%Y')
        else:
            dob = None

        return {
            'name': self.name,
            'dob': dob,
            'id': self.id,
            'breed': self.breed,
            'picture': url_for('home.media', filename=self.picture),
            'gender': self.gender,
            'weight': self.weight,
            'needs': specialNeeds,
            'description': desc
        }


class Shelter(Model):
    __tablename__ = 'shelter'
    name = Col(String(80), nullable=False)
    address = Col(String(250))
    city = Col(String(100))
    state = Col(String(20))
    zip_code = Col(String(10))
    email = Col(String(256))
    website = Col(String)
    max_puppies = Col(Integer)
    id = Col(Integer, primary_key=True)
    operator = relationship(
        'User', secondary=shelter_operator, backref=db.backref('shelters'))
    puppy_count = db.column_property(
        db.select(
            [db.func.count(Puppy.id)]
        ).where(Puppy.shelter_id == id).correlate_except(Puppy))

    __mapper_args__ = {
        'order_by': name
    }

    @property
    def serialize(self):
        # Returns object data in JSON
        return {
            'name': self.name,
            'address': self.address,
            'id': self.id,
            'city': self.city,
            'state': self.state,
            'zip': self.zip_code,
            'email': self.email,
            'website': self.website
        }

    def __unicode__(self):
        return self.name


class PuppyProfile(Model):
    __tablename__ = 'puppy_profile'
    id = Col(Integer, primary_key=True)
    profile_picture = Col(String)
    special_needs = Col(String)
    description = Col(String)
    puppy_id = Col(Integer, ForeignKey('puppy.id'))
