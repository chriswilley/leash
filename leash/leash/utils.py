import datetime
import hashlib
import os
import time
import urllib

from flask_mail import Message
from werkzeug import secure_filename

from . import app, mail


def find_item(item_list, field, value):
    """
    find_item() allows us to perform a query on a model and return a list
    and a single record without hitting the database twice; for example,
    we often need a list of shelters to generate the sidebar nav and also
    the name of a single shelter to place in a heading
    """
    for i in item_list:
        if (getattr(i, field) == value):
            return i


def send_email(sender, recipients, subject, body):
    msg = Message(subject, sender=sender, recipients=recipients)
    msg.html = body
    mail.send(msg)
    return


def set_image_name(filename):
    epoch = int(time.mktime(time.localtime()))
    return str(epoch) + '_' + secure_filename(filename)


def save_uploaded_image(image):
    upload_path = os.path.join(
        os.path.dirname(__file__), app.config['UPLOAD_FOLDER'])
    filename = set_image_name(image.filename)
    image.save(upload_path + '/' + filename)
    return filename


def show_gravatar(email):
    size = 40
    rating = 'g'
    default = 'mm'
    gravatar_url = "http://www.gravatar.com/avatar/"
    gravatar_url += hashlib.md5(email.lower()).hexdigest() + "?"
    gravatar_url += urllib.urlencode({
        's': str(size),
        'r': rating,
        'd': default
    })
    return gravatar_url


@app.template_filter('apostrophe')
def apostrophe_filter(s):
    if (s.endswith('s')):
        return s + '\''
    else:
        return s + '\'s'


@app.template_filter('singularize')
def singularize_filter(s):
    if (s.endswith('ies')):
        return s[:-3] + 'y'
    else:
        return s[:-1]


@app.template_filter('agetext')
def agetext_filter(dob):
    """
    age calculation shout out to http://stackoverflow.com/a/16614616
    """
    today = datetime.date.today()
    years = today.year - dob.year
    months = today.month - dob.month
    if (today.day < dob.day):
        months -= 1

    while months < 0:
        months += 12
        years -= 1

    if (years == 0):
        yearStr = ''
    else:
        yearStr = str(years) + ' year' + pluralize_filter(years)

    if (months == 0):
        monthStr = ''
    else:
        monthStr = str(months) + ' month' + pluralize_filter(months)

    if (yearStr != ''):
        if (monthStr != ''):
            age = yearStr + ', ' + monthStr
        else:
            age = yearStr
    else:
        age = monthStr

    return age


@app.template_filter('pluralize')
def pluralize_filter(value, arg='s'):
    """
    Borrowed from Django (django.template.defaultfilters)
    """
    if ',' not in arg:
        arg = ',' + arg
    bits = arg.split(',')
    if len(bits) > 2:
        return ''
    singular_suffix, plural_suffix = bits[:2]

    try:
        if float(value) != 1:
            return plural_suffix
    except ValueError:  # Invalid string that's not a number.
        pass
    except TypeError:  # Value isn't a string or a number; maybe it's a list?
        try:
            if len(value) != 1:
                return plural_suffix
        except TypeError:  # len() of unsized object.
            pass
    return singular_suffix
