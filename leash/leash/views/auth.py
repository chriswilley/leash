from flask import (
    abort,
    g,
    flash,
    redirect,
    render_template,
    request,
    url_for
)
from flask.ext.login import (
    login_user,
    logout_user,
    login_required
)

from . import auth, ts
from .. import db, app
from ..forms import EmailPasswordForm, EmailForm, PasswordForm, AccountForm
from ..models import User
from ..utils import send_email


@auth.route('/signup/', methods=['GET', 'POST'])
def signup():
    form = EmailPasswordForm()

    if (form.validate_on_submit()):
        user = User(email=form.email.data, password=form.password.data)
        db.session.add(user)
        db.session.commit()

        send_email_confirmation(user)

        return redirect(url_for('home.leashHome'))

    return render_template('signup.html', form=form)


@auth.route('/activate/<token>/')
def activate_account(token):
    try:
        email = ts.loads(
            token, salt="account-not-activated-salt", max_age=3600)
    except:
        abort(404)

    user = User.query.filter_by(email=email).first_or_404()
    send_email_confirmation(user)

    flash('Account activation email sent.')

    return redirect(url_for('home.leashHome'))


@auth.route('/confirm/<token>/')
def confirm_email(token):
    try:
        email = ts.loads(token, salt="email-confirm-salt", max_age=86400)
    except:
        abort(404)

    user = User.query.filter_by(email=email).first_or_404()

    user.email_confirmed = True

    db.session.add(user)
    db.session.commit()

    flash('Thanks! Your account has been activated.')

    return redirect(request.args.get('next') or url_for('auth.login'))


@auth.route('/login/', methods=['GET', 'POST'])
def login():
    form = EmailPasswordForm()

    if (form.validate_on_submit()):
        user = User.query.filter_by(email=form.email.data).first_or_404()

        if (user.is_correct_password(form.password.data)):
            login_user(user)
            next_page = request.args.get('next') or url_for('home.leashHome')
        else:
            next_page = request.args.get('next') or url_for('auth.login')

        if (next_page == 'None'):
            return redirect(url_for('home.leashHome'))
        else:
            return redirect(next_page)

    return render_template('login.html', form=form)


@auth.route('/logout/')
@login_required
def logout():
    logout_user()

    return redirect(url_for('home.leashHome'))


@auth.route('/change_password/', methods=['GET', 'POST'])
@login_required
def change_password():
    form = PasswordForm()

    if (form.validate_on_submit()):
        g.user.password = form.password.data

        db.session.add(g.user)
        db.session.commit()

        flash('Password changed successfully.')

        return redirect(url_for('auth.view_account'))

    return render_template('change_password.html', form=form)


@auth.route('/reset_password/', methods=['GET', 'POST'])
def reset_password():
    form = EmailForm()

    if (form.validate_on_submit()):
        user = User.query.filter_by(email=form.email.data).first_or_404()
        if not (user.email_confirmed):
            token = ts.dumps(user.email, salt='account-not-activated-salt')
            return render_template(
                'account_not_activated.html',
                token=token,
                next=url_for('auth.reset_password')
            )

        subject = 'Leash: Password reset request'
        token = ts.dumps(user.email, salt='password-reset-salt')

        reset_url = url_for(
            'auth.confirm_password_reset', token=token, _external=True)

        html = render_template(
            'email_reset_password.html', reset_url=reset_url)

        sender = app.config['MAIL_DEFAULT_SENDER']
        recipients = [user.email, ]

        send_email(sender, recipients, subject, html)

        return redirect(url_for('home.leashHome'))

    return render_template('reset_password.html', form=form)


@auth.route('/reset_confirm/<token>/', methods=['GET', 'POST'])
def confirm_password_reset(token):
    try:
        email = ts.loads(token, salt="password-reset-salt", max_age=86400)
    except:
        abort(404)

    form = PasswordForm()

    if (form.validate_on_submit()):
        user = User.query.filter_by(email=email).first_or_404()
        user.password = form.password.data

        db.session.add(user)
        db.session.commit()

        msg = 'Password changed successfully. Please '
        msg += 'login with your new password.'
        flash(msg)

        return redirect(url_for('auth.login'))

    return render_template('new_password.html', form=form, token=token)


@auth.route('/account/', methods=['GET', 'POST'])
@login_required
def view_account():
    form = AccountForm(obj=g.user)

    if (form.validate_on_submit()):
        g.user.name = form.name.data
        g.user.email = form.email.data

        db.session.add(g.user)
        db.session.commit()

        msg = 'Account info changed successfully.'
        flash(msg)

        return redirect(url_for('auth.view_account'))

    puppies = g.user.puppies
    return render_template('account_profile.html', form=form, puppies=puppies)


def send_email_confirmation(user):
    subject = 'Leash: Please confirm your email address'
    token = ts.dumps(user.email, salt='email-confirm-salt')

    confirm_url = url_for(
        'auth.confirm_email', token=token, _external=True)

    if (request.args.get('next')):
        next_url = request.args.get('next')
    else:
        next_url = url_for('auth.login')

    html = render_template(
        'email_activate.html',
        confirm_url=confirm_url,
        next=next_url
    )

    sender = app.config['MAIL_DEFAULT_SENDER']
    recipients = [user.email, ]

    return send_email(sender, recipients, subject, html)
