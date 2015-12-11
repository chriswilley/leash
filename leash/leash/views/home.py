import os
from flask import (
    flash,
    g,
    jsonify,
    redirect,
    render_template,
    request,
    send_from_directory,
    url_for
)
from flask.ext.login import login_required

from . import home, ts
from .. import db, app
from ..forms import PuppyProfileForm, PuppyForm, ShelterForm, UserForm
from ..models import Puppy, PuppyProfile, Shelter, puppy_adopter, User
from ..utils import find_item, save_uploaded_image


@home.route('/')
def leashHome():
    return render_template('index.html')


@home.route('/about/')
def aboutLeash():
    return render_template('about.html')


@home.route('/shelter/<int:shelter_id>/')
def showPuppies(shelter_id):
    shelters = Shelter.query.all()

    if (shelter_id == 0):
        shelter = shelters[0]
        shelter_id = shelter.id
    else:
        shelter = find_item(shelters, 'id', shelter_id)

    shelter_name = shelter.name
    puppies = Puppy.query.filter_by(shelter_id=shelter.id).all()

    return render_template(
        'shelters.html',
        puppies=puppies,
        shelter=shelter_name,
        shelter_id=shelter_id,
        shelters=shelters
    )


@home.route('/shelter/<int:shelter_id>/info/')
def shelterInfo(shelter_id):
    shelter = Shelter.query.filter_by(id=shelter_id).one()
    return jsonify(Shelter=shelter.serialize)


@home.route('/puppy/<int:puppy_id>/info/')
def puppyInfo(puppy_id):
    puppy = Puppy.query.filter_by(id=puppy_id).one()
    return jsonify(Puppy=puppy.serialize)


@home.route('/puppy/<int:puppy_id>/edit_profile/', methods=['GET', 'POST'])
@login_required
def editPuppyProfile(puppy_id):
    puppy = Puppy.query.filter_by(id=puppy_id).one()
    if (puppy.profile):
        profile = puppy.profile
        form = PuppyProfileForm(obj=profile)
    else:
        form = PuppyProfileForm()

    if (form.validate_on_submit()):
        if not (puppy.profile):
            profile = PuppyProfile(
                puppy_id=puppy_id,
                description=form.description.data,
                special_needs=form.special_needs.data
            )
            db.session.add(profile)
        else:
            puppy.profile.description = form.description.data
            puppy.profile.special_needs = form.special_needs.data
            db.session.add(puppy)

        db.session.commit()

        flash('Puppy info saved.')

        return redirect(url_for('auth.view_account'))

    return render_template('edit_puppy_profile.html', puppy=puppy, form=form)


@home.route('/puppy/<int:puppy_id>/adopt/')
def adoptPuppy(puppy_id):
    if (g.user is None or not g.user.is_authenticated):
        return redirect(url_for('auth.signup') + '?next=/puppy/' + str(
            puppy_id) + '/adopt/')
    elif not (g.user.email_confirmed):
        token = ts.dumps(g.user.email, salt='account-not-activated-salt')
        return render_template(
            'account_not_activated.html',
            token=token,
            next=url_for('home.adoptPuppy', puppy_id=puppy_id)
        )
    else:
        puppy = Puppy.query.filter_by(id=puppy_id).one()
        puppy.shelter_id = None
        db.session.add(puppy)
        db.session.execute(
            puppy_adopter.insert().values([puppy.id, g.user.id, ]))
        db.session.commit()
        return render_template('adopt.html', puppy=puppy)


@home.route('/site_admin/<admin_area>/')
@login_required
def siteAdmin(admin_area):
    if not (g.user.is_admin or g.user.is_operator):
        return redirect(url_for('home.leashHome'))

    obj_list = []

    if (admin_area == 'shelters'):
        if (g.user.is_operator):
            obj_list = Shelter.query.filter(
                Shelter.operator.contains(g.user)).all()
        else:
            obj_list = Shelter.query.all()
        col_list = [
            ('name', 1),
            ('address', 0),
            ('city', 1),
            ('state', 1),
            ('zip_code', 0),
            ('email', 0),
            ('website', 1),
            ('max_puppies', 0),
            ('puppy_count', 1)
        ]
        add_object = url_for('home.addShelter')
    elif (admin_area == 'puppies'):
        if (g.user.is_operator):
            obj_list = Puppy.query.join(Shelter).filter(
                Shelter.operator.contains(g.user)).all()
        else:
            obj_list = Puppy.query.all()
        col_list = [
            ('shelter', 1),
            ('name', 1),
            ('breed', 1),
            ('gender', 1),
            ('weight', 0),
            ('date_of_birth', 0),
        ]
        add_object = url_for('home.addPuppy')
    elif (admin_area == 'users'):
        if not (g.user.is_admin):
            return redirect(url_for('home.leashHome'))

        obj_list = User.query.all()
        col_list = [
            ('name', 1),
            ('email', 1),
            ('user_role', 1),
        ]
        add_object = url_for('home.addUser')

    return render_template(
        'site_admin.html',
        admin_area=admin_area,
        obj_list=obj_list,
        col_list=col_list,
        add_object=add_object
    )


@home.route('/shelter/<int:shelter_id>/edit/', methods=['GET', 'POST'])
@login_required
def editShelter(shelter_id):
    shelter = Shelter.query.filter_by(id=shelter_id).one()

    if not (g.user.is_admin):
        if not (g.user.is_operator and g.user in shelter.operator):
            return redirect(url_for('home.leashHome'))

    form = ShelterForm(obj=shelter)
    form_action = url_for('home.editShelter', shelter_id=shelter_id)
    form_header = 'Edit Shelter'

    if (form.validate_on_submit()):
        form.populate_obj(shelter)

        db.session.add(shelter)
        db.session.commit()

        flash('Shelter info saved.')

        return redirect(url_for('home.siteAdmin', admin_area='shelters'))

    return render_template(
        'edit_shelter.html',
        form=form,
        shelter=shelter,
        form_action=form_action,
        form_header=form_header
    )


@home.route('/shelter/add/', methods=['GET', 'POST'])
@login_required
def addShelter():
    if not (g.user.is_admin):
        return redirect(url_for('home.leashHome'))

    form = ShelterForm()
    form_action = url_for('home.addShelter')
    form_header = 'Add Shelter'

    if (form.validate_on_submit()):
        new_shelter = Shelter()
        form.populate_obj(new_shelter)

        db.session.add(new_shelter)
        db.session.commit()

        flash('Shelter info saved.')

        return redirect(url_for('home.siteAdmin', admin_area='shelters'))

    return render_template(
        'edit_shelter.html',
        form=form,
        form_action=form_action,
        form_header=form_header
    )


@home.route('/shelter/<int:shelter_id>/delete/')
@login_required
def deleteShelter(shelter_id):
    if not (g.user.is_admin):
        return redirect(url_for('home.leashHome'))

    shelter = Shelter.query.filter_by(id=shelter_id).one()

    db.session.delete(shelter)
    db.session.commit()

    flash('Shelter deleted.')

    return redirect(url_for('home.siteAdmin', admin_area='shelters'))


@home.route('/puppy/<int:puppy_id>/edit/', methods=['GET', 'POST'])
@login_required
def editPuppy(puppy_id):
    puppy = Puppy.query.filter_by(id=puppy_id).one()

    if not (g.user.is_admin):
        if not (g.user.is_operator and g.user in puppy.shelter.operator):
            return redirect(url_for('home.leashHome'))

    puppy_pic = puppy.picture
    form = PuppyForm(obj=puppy)
    form_action = url_for('home.editPuppy', puppy_id=puppy_id)
    form_header = 'Edit Puppy'
    pProfile = None
    breed_choices = app.config['DOG_BREEDS']
    if (puppy.profile):
        pProfile = puppy.profile

    if (form.validate_on_submit()):
        form.populate_obj(puppy)
        db.session.add(puppy)
        if (form.breed.data == ''):
            puppy.breed = None

        if (form.picture.data.filename):
            puppy.picture = save_uploaded_image(form.picture.data)
        else:
            puppy.picture = puppy_pic

        if (form.description.data or form.special_needs.data):
            if (pProfile):
                pProfile.description = form.description.data
                pProfile.special_needs = form.special_needs.data
            else:
                pProfile = PuppyProfile(
                    puppy=puppy,
                    description=form.description.data,
                    special_needs=form.special_needs.data
                )
            db.session.add(pProfile)

        db.session.commit()

        flash('Puppy info saved.')

        return redirect(url_for('home.siteAdmin', admin_area='puppies'))
    elif (pProfile):
        form.description.data = pProfile.description
        form.special_needs.data = pProfile.special_needs

    return render_template(
        'edit_puppy.html',
        form=form,
        puppy=puppy,
        form_action=form_action,
        form_header=form_header,
        breed_choices=breed_choices
    )


@home.route('/puppy/add/', methods=['GET', 'POST'])
@login_required
def addPuppy():
    if not (g.user.is_admin or g.user.is_operator):
        return redirect(url_for('home.leashHome'))

    form = PuppyForm()
    form_action = url_for('home.addPuppy')
    form_header = 'Add Puppy'
    breed_choices = app.config['DOG_BREEDS']

    if (form.validate_on_submit()):
        new_puppy = Puppy()
        form.populate_obj(new_puppy)
        if (form.breed.data == ''):
            new_puppy.breed = None

        if (form.picture.data):
            new_puppy.picture = save_uploaded_image(form.picture.data)

        db.session.add(new_puppy)

        if (form.description.data or form.special_needs.data):
            pProfile = PuppyProfile(
                puppy=new_puppy,
                description=form.description.data,
                special_needs=form.special_needs.data
            )
            db.session.add(pProfile)

        db.session.commit()

        flash('Puppy info saved.')

        return redirect(url_for('home.siteAdmin', admin_area='puppies'))

    return render_template(
        'edit_puppy.html',
        form=form,
        form_action=form_action,
        form_header=form_header,
        breed_choices=breed_choices
    )


@home.route('/puppy/<int:puppy_id>/delete/')
@login_required
def deletePuppy(puppy_id):
    if not (g.user.is_admin):
        return redirect(url_for('home.leashHome'))

    puppy = Puppy.query.filter_by(id=puppy_id).one()

    db.session.delete(puppy)
    db.session.commit()

    flash('Puppy deleted.')

    return redirect(url_for('home.siteAdmin', admin_area='puppies'))


@home.route('/user/<int:user_id>/edit/', methods=['GET', 'POST'])
@login_required
def editUser(user_id):
    if not (g.user.is_admin):
        return redirect(url_for('home.leashHome'))

    user = User.query.filter_by(id=user_id).one()
    user_pic = user.picture
    form = UserForm(obj=user)
    form_action = url_for('home.editUser', user_id=user_id)
    form_header = 'Edit User'

    # bypass email field Unique() validator
    form.is_edit = True

    if (form.validate_on_submit()):
        form.populate_obj(user)
        db.session.add(user)

        if (form.picture.data):
            user.picture = save_uploaded_image(form.picture.data)
        else:
            user.picture = user_pic

        if ('_picture_delete' in request.form):
            user.picture = None

        db.session.commit()

        flash('User info saved.')

        return redirect(url_for('home.siteAdmin', admin_area='users'))

    return render_template(
        'edit_user.html',
        form=form,
        user=user,
        form_action=form_action,
        form_header=form_header
    )


@home.route('/user/add/', methods=['GET', 'POST'])
@login_required
def addUser():
    if not (g.user.is_admin):
        return redirect(url_for('home.leashHome'))

    form = UserForm()
    form_action = url_for('home.addUser')
    form_header = 'Add User'

    if (form.validate_on_submit()):
        new_user = User()
        form.populate_obj(new_user)

        if (form.picture.data):
            new_user.picture = save_uploaded_image(form.picture.data)
        else:
            new_user.picture = None

        db.session.add(new_user)
        db.session.commit()

        flash('User saved.')

        return redirect(url_for('home.siteAdmin', admin_area='users'))

    return render_template(
        'edit_user.html',
        form=form,
        form_action=form_action,
        form_header=form_header
    )


@home.route('/user/<int:user_id>/delete/')
@login_required
def deleteUser(user_id):
    if (g.user.id == user_id or not g.user.is_admin):
        return redirect(url_for('home.leashHome'))

    user = User.query.filter_by(id=user_id).one()

    db.session.delete(user)
    db.session.commit()

    flash('User deleted.')

    return redirect(url_for('home.siteAdmin', admin_area='users'))


@home.route('/puppy/distribute/')
@login_required
def distributePuppies():
    if not (g.user.is_admin):
        return redirect(url_for('home.leashHome'))

    puppy_count = Puppy.query.filter(Puppy.shelter_id != None).count()
    shelter_count = Shelter.query.count()
    avg_puppies = round(float(puppy_count) / float(shelter_count))
    shelters = Shelter.query.all()
    for shelter in shelters:
        sPuppies = shelter.puppy_count
        if (sPuppies > avg_puppies):
            while sPuppies > avg_puppies:
                temp_puppy = Puppy.query.filter_by(
                    shelter_id=shelter.id).first()
                new_shelter = Shelter.query.filter(
                    Shelter.puppy_count < avg_puppies).first()
                temp_puppy.shelter_id = new_shelter.id
                db.session.add(temp_puppy)
                db.session.commit()
                sPuppies -= 1
            db.session.add(shelter)
            db.session.commit()

    flash('Puppies distributed. Consolatory chew toys have been provided.')

    return redirect(url_for('home.siteAdmin', admin_area='shelters'))


@home.route('/media/<path:filename>')
def media(filename):
    dirname = os.path.dirname
    media_path = os.path.join(
        dirname(dirname(__file__)), app.config['MEDIA_FOLDER'])
    return send_from_directory(media_path, filename)
