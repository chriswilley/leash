import re
import unittest
import urllib

from flask.ext.testing import TestCase

from leash import app, db, mail, views
from leash.models import Puppy, Shelter, User
from leash.forms import (
    AccountForm,
    EmailForm,
    EmailPasswordForm,
    PasswordForm,
    PuppyForm,
    PuppyProfileForm,
    ShelterForm,
    UserForm
)

from StringIO import StringIO

test_email = app.config['TEST_EMAIL']


class LeashTestCase(TestCase):

    def create_app(self):
        app.testing = True
        app.config['SQLALCHEMY_DATABASE_URI'] = 'sqlite:///:memory:'
        app.config['PRESERVE_CONTEXT_ON_EXCEPTION'] = False
        app.config['DEBUG_TB_INTERCEPT_REDIRECTS'] = False
        app.config['WTF_CSRF_ENABLED'] = False
        with app.app_context():
            db.drop_all()
            db.create_all()
            self.db = db
            user = User(
                name='admin',
                email='admin@leash.com',
                password='password'
            )

            shelter = Shelter(
                name='Swell Friendly Place'
            )

            puppy = Puppy(
                name='Ralph',
                gender='female',
                picture='dog-187817_640.jpg',
                shelter=shelter
            )

            db.session.add(user)
            db.session.add(shelter)
            db.session.add(puppy)
            db.session.commit()
        return app

    def login(self, email, password, _next=None):
        url = '/login/'
        if _next:
            url += '?next=' + _next

        return self.client.post(
            url,
            data={
                'email': email,
                'password': password
            },
            follow_redirects=True
        )

    def test_get_user(self):
        with app.app_context():
            user = User.query.filter_by(email='admin@leash.com').one()
            self.assertTrue(user.is_correct_password('password'))

    def test_leash_home(self):
        response = self.client.get('/')
        self.assert_200(response)
        self.assert_template_used('index.html')

    def test_home_show_puppies(self):
        shelter = Shelter.query.first()

        response = self.client.get('/shelter/0/')

        self.assert_200(response)
        self.assert_template_used('shelters.html')
        self.assertEqual(self.get_context_variable('shelter'), shelter.name)
        self.assertEqual(self.get_context_variable('shelter_id'), shelter.id)

        p_list = self.get_context_variable('puppies')
        self.assertEqual(len(p_list), 1)

        s_list = self.get_context_variable('shelters')
        self.assertEqual(len(s_list), 1)

    def test_home_shelter_info(self):
        shelter = Shelter.query.first()

        url = '/shelter/' + str(shelter.id) + '/info/'
        response = self.client.get(url)

        self.assert_200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['Shelter']['name'], shelter.name)

    def test_home_puppy_info(self):
        puppy = Puppy.query.first()

        url = '/puppy/' + str(puppy.id) + '/info/'
        response = self.client.get(url)

        self.assert_200(response)
        self.assertEqual(response.content_type, 'application/json')
        self.assertEqual(response.json['Puppy']['name'], puppy.name)
        self.assertEqual(response.json['Puppy']['gender'], puppy.gender)

        puppy_pic = '/media/' + puppy.picture
        self.assertEqual(response.json['Puppy']['picture'], puppy_pic)

    def test_home_edit_puppy_profile(self):
        puppy = Puppy.query.first()

        url = '/puppy/' + str(puppy.id) + '/edit_profile/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_200(response)
            form = self.get_context_variable('form')
            self.assertEqual(self.get_context_variable('puppy'), puppy)
            self.assertEqual(type(form), PuppyProfileForm)

            desc = 'One helluva dog'
            needs = 'To be noted as one helluva dog'
            response = self.client.post(
                url,
                data={
                    'description': desc,
                    'special_needs': needs
                },
                follow_redirects=True
            )
            self.assertIn('Puppy info saved.', response.data)
            revised_puppy = Puppy.query.first()
            self.assertEqual(revised_puppy.profile.description, desc)
            self.assertEqual(revised_puppy.profile.special_needs, needs)
            self.client.get('/logout/')

    def test_home_adopt_puppy(self):
        puppy = Puppy.query.first()
        user = User.query.first()

        url = '/puppy/' + str(puppy.id) + '/adopt/'
        response = self.client.get(url)

        self.assert_redirects(response, '/signup/?next=' + url)

        with app.app_context():
            response = self.login(user.email, 'password', url)
            self.assert_template_used('account_not_activated.html')

            url2 = '/activate/bad-token/'
            response = self.client.get(url2)
            self.assert_404(response)

            url2 = '/activate/' + self.get_context_variable('token') + '/'
            with mail.record_messages() as outbox:
                response = self.client.get(url2)
                self.assert_redirects(response, '/')

                response = self.client.get('/')
                self.assertIn('Account activation email sent.', response.data)

                self.assertEqual(len(outbox), 1)
                email = str(outbox[0])
                link = re.search(r'/confirm/(.+)/\?next', email)

                url2 = '/confirm/' + link.group(1) + '/'
                response = self.client.get(url2)
                self.assert_redirects(response, '/login/')

                response = self.client.get('/login/')
                self.assertIn(
                    'Thanks! Your account has been activated.', response.data)

            self.client.get(url)
            self.assert_template_used('adopt.html')

            revised_puppy = Puppy.query.first()
            self.assertEqual(revised_puppy.adopter[0], user)
            self.assertEqual(self.get_context_variable('puppy'), revised_puppy)

            self.client.get('/logout/')

    def test_home_site_admin_shelter(self):
        user = User.query.first()
        shelter = Shelter.query.first()

        url = '/site_admin/shelters/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            shelter2 = Shelter(name='Puppies R Us', operator=[user, ])
            db.session.add(shelter2)

            response = self.login(user.email, 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('site_admin.html')
            self.assertEqual(
                self.get_context_variable('admin_area'), 'shelters')
            self.assertEqual(len(self.get_context_variable('obj_list')), 1)
            self.assertEqual(
                self.get_context_variable('obj_list')[0], shelter2)
            self.assertEqual(len(self.get_context_variable('col_list')), 9)
            self.assertEqual(
                self.get_context_variable('add_object'), '/shelter/add/')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assertEqual(len(self.get_context_variable('obj_list')), 2)
            self.assertEqual(
                self.get_context_variable('obj_list')[0], shelter2)
            self.assertEqual(self.get_context_variable('obj_list')[1], shelter)

            self.client.get('/logout/')

    def test_home_site_admin_puppy(self):
        user = User.query.first()
        puppy = Puppy.query.first()

        url = '/site_admin/puppies/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            shelter2 = Shelter(name='Puppies R Us', operator=[user, ])
            puppy2 = Puppy(
                name='Jake',
                gender='male',
                picture='chihuahua-621112_640.jpg',
                shelter=shelter2
            )
            db.session.add(shelter2)
            db.session.add(puppy2)

            response = self.login(user.email, 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('site_admin.html')
            self.assertEqual(
                self.get_context_variable('admin_area'), 'puppies')
            self.assertEqual(len(self.get_context_variable('obj_list')), 1)
            self.assertEqual(
                self.get_context_variable('obj_list')[0], puppy2)
            self.assertEqual(len(self.get_context_variable('col_list')), 6)
            self.assertEqual(
                self.get_context_variable('add_object'), '/puppy/add/')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assertEqual(len(self.get_context_variable('obj_list')), 2)
            self.assertEqual(self.get_context_variable('obj_list')[0], puppy)
            self.assertEqual(
                self.get_context_variable('obj_list')[1], puppy2)

            self.client.get('/logout/')

    def test_home_site_admin_user(self):
        user = User.query.first()

        url = '/site_admin/users/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login(user.email, 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('site_admin.html')
            self.assertEqual(
                self.get_context_variable('admin_area'), 'users')
            self.assertEqual(len(self.get_context_variable('obj_list')), 1)
            self.assertEqual(self.get_context_variable('obj_list')[0], user)
            self.assertEqual(
                self.get_context_variable('add_object'), '/user/add/')

            self.client.get('/logout/')

    def test_home_edit_shelter(self):
        shelter = Shelter.query.first()
        user = User.query.first()

        url = '/shelter/' + str(shelter.id) + '/edit/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            shelter.operator = [user, ]
            db.session.add(shelter)

            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('edit_shelter.html')
            form = self.get_context_variable('form')
            self.assertEqual(self.get_context_variable('shelter'), shelter)
            self.assertEqual(self.get_context_variable('form_action'), url)
            self.assertEqual(
                self.get_context_variable('form_header'), 'Edit Shelter')
            self.assertEqual(type(form), ShelterForm)

            city = 'Xanadu'
            state = 'CA'
            response = self.client.post(
                url,
                data={
                    'name': shelter.name,
                    'city': city,
                    'state': state
                },
                follow_redirects=True
            )
            self.assertIn('Shelter info saved.', response.data)
            revised_shelter = Shelter.query.first()
            self.assertEqual(revised_shelter.city, city)
            self.assertEqual(revised_shelter.state, state)

            self.client.get('/logout/')

    def test_home_add_shelter(self):
        user = User.query.first()

        url = '/shelter/add/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('edit_shelter.html')
            form = self.get_context_variable('form')
            self.assertEqual(self.get_context_variable('form_action'), url)
            self.assertEqual(
                self.get_context_variable('form_header'), 'Add Shelter')
            self.assertEqual(type(form), ShelterForm)

            s_name = 'Puppies R Us'
            city = 'Xanadu'
            state = 'CA'
            response = self.client.post(
                url,
                data={
                    'name': s_name,
                    'city': city,
                    'state': state
                },
                follow_redirects=True
            )
            self.assertIn('Shelter info saved.', response.data)
            revised_shelter = Shelter.query.first()
            self.assertEqual(revised_shelter.name, s_name)
            self.assertEqual(revised_shelter.city, city)
            self.assertEqual(revised_shelter.state, state)

            self.client.get('/logout/')

    def test_home_delete_shelter(self):
        user = User.query.first()
        shelter2 = Shelter(name='Puppies R Us')
        db.session.add(shelter2)
        db.session.commit()

        url = '/shelter/' + str(shelter2.id) + '/delete/'
        url2 = '/site_admin/shelters/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_redirects(response, url2)

            response = self.client.get(url2)
            self.assertIn('Shelter deleted.', response.data)

            shelters = Shelter.query.all()
            self.assertEqual(len(shelters), 1)
            self.assertNotEqual(shelters[0], shelter2)

            self.client.get('/logout/')

    def test_home_edit_puppy(self):
        puppy = Puppy.query.first()
        shelter = Shelter.query.first()
        user = User.query.first()

        url = '/puppy/' + str(puppy.id) + '/edit/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            shelter.operator = [user, ]
            db.session.add(shelter)

            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('edit_puppy.html')
            form = self.get_context_variable('form')
            self.assertEqual(self.get_context_variable('puppy'), puppy)
            self.assertEqual(self.get_context_variable('form_action'), url)
            self.assertEqual(
                self.get_context_variable('form_header'), 'Edit Puppy')
            self.assertEqual(
                self.get_context_variable('breed_choices'),
                app.config['DOG_BREEDS']
            )
            self.assertEqual(type(form), PuppyForm)

            weight = 7.2
            desc = 'A real peach'
            picture = (StringIO('Cute dog photo'), 'dog.png')
            needs = 'To ride in handbags'
            response = self.client.post(
                url,
                data={
                    'name': puppy.name,
                    'weight': weight,
                    'picture': picture,
                    'description': desc,
                    'special_needs': needs
                },
                follow_redirects=True
            )
            self.assertIn('Puppy info saved.', response.data)
            revised_puppy = Puppy.query.first()
            self.assertEqual(float(revised_puppy.weight), weight)
            self.assertEqual(revised_puppy.profile.description, desc)
            self.assertEqual(revised_puppy.profile.special_needs, needs)

            self.client.get('/logout/')

    def test_home_add_puppy(self):
        user = User.query.first()
        shelter = Shelter.query.first()
        shelter.operator = [user, ]
        db.session.add(shelter)

        url = '/puppy/add/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('edit_puppy.html')
            form = self.get_context_variable('form')
            self.assertEqual(self.get_context_variable('form_action'), url)
            self.assertEqual(
                self.get_context_variable('form_header'), 'Add Puppy')
            self.assertEqual(type(form), PuppyForm)

            p_name = 'Jake'
            gender = 'male'
            picture = (StringIO('Cute dog photo'), 'dog.png')
            response = self.client.post(
                url,
                data={
                    'name': p_name,
                    'gender': gender,
                    'picture': picture,
                    'shelter': shelter.id
                },
                follow_redirects=True
            )
            self.assertIn('Puppy info saved.', response.data)
            puppy = Puppy.query.filter_by(name='Jake').one()
            self.assertEqual(puppy.name, p_name)
            self.assertEqual(puppy.gender, gender)
            self.assertIn('_dog.png', puppy.picture)

            self.client.get('/logout/')

    def test_home_delete_puppy(self):
        user = User.query.first()
        puppy2 = Puppy(name='Balthasar', gender='female', picture='dog.png')
        db.session.add(puppy2)
        db.session.commit()

        url = '/puppy/' + str(puppy2.id) + '/delete/'
        url2 = '/site_admin/puppies/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_redirects(response, url2)

            response = self.client.get(url2)
            self.assertIn('Puppy deleted.', response.data)

            puppies = Puppy.query.all()
            self.assertEqual(len(puppies), 1)
            self.assertNotEqual(puppies[0], puppy2)

            self.client.get('/logout/')

    def test_home_edit_user(self):
        user = User.query.first()

        url = '/user/' + str(user.id) + '/edit/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('edit_user.html')
            form = self.get_context_variable('form')
            self.assertEqual(self.get_context_variable('user'), user)
            self.assertEqual(self.get_context_variable('form_action'), url)
            self.assertEqual(
                self.get_context_variable('form_header'), 'Edit User')
            self.assertEqual(type(form), UserForm)

            u_name = 'Robert Dobbs'
            response = self.client.post(
                url,
                data={
                    'name': u_name,
                    'email': user.email,
                    'password': 'password'
                },
                follow_redirects=True
            )
            self.assertIn('User info saved.', response.data)
            revised_user = User.query.first()
            self.assertEqual(revised_user.name, u_name)

            self.client.get('/logout/')

    def test_home_add_user(self):
        user = User.query.first()

        url = '/user/add/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('edit_user.html')
            form = self.get_context_variable('form')
            self.assertEqual(self.get_context_variable('form_action'), url)
            self.assertEqual(
                self.get_context_variable('form_header'), 'Add User')
            self.assertEqual(type(form), UserForm)

            u_name = 'John Galt'
            email = 'name@thename.com'
            password = 'jujube'
            role = 'default'
            picture = None
            response = self.client.post(
                url,
                data={
                    'name': u_name,
                    'email': email,
                    'password': password,
                    'role': role,
                    'picture': picture
                },
                follow_redirects=True
            )
            self.assertIn('User saved.', response.data)
            user2 = User.query.filter_by(name='John Galt').one()
            self.assertEqual(user2.name, u_name)
            self.assertEqual(user2.email, email)
            self.assertTrue(user2.is_correct_password('jujube'))

            self.client.get('/logout/')

    def test_home_delete_user(self):
        user = User.query.first()
        user2 = User(
            name='Hester Prynne', email='prynne@hawthorne.com', password='A')
        db.session.add(user2)
        db.session.commit()

        url = '/user/' + str(user2.id) + '/delete/'
        url2 = '/site_admin/users/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_redirects(response, url2)

            response = self.client.get(url2)
            self.assertIn('User deleted.', response.data)
            users = User.query.all()
            self.assertEqual(len(users), 1)
            self.assertEqual(users[0], user)
            self.assertNotEqual(users[0], user2)

            self.client.get('/logout/')

    def test_home_distribute_puppies(self):
        user = User.query.first()
        shelter2 = Shelter(name='Shiny Happy Place')
        shelter3 = Shelter(name='Super Awesome Place')

        puppy2 = Puppy(
            name='Alice',
            gender='female',
            picture='dog2.png',
            shelter=shelter2
        )
        puppy3 = Puppy(
            name='Benny',
            gender='male',
            picture='dog3.png',
            shelter=shelter2
        )
        puppy4 = Puppy(
            name='Cosmo',
            gender='male',
            picture='dog4.png',
            shelter=shelter2
        )
        puppy5 = Puppy(
            name='Diana',
            gender='female',
            picture='dog5.png',
            shelter=shelter2
        )
        puppy6 = Puppy(
            name='Elise',
            gender='female',
            picture='dog6.png',
            shelter=shelter2
        )
        db.session.add(shelter2)
        db.session.add(shelter3)
        db.session.add(puppy2)
        db.session.add(puppy3)
        db.session.add(puppy4)
        db.session.add(puppy5)
        db.session.add(puppy6)

        url = '/puppy/distribute/'
        url2 = '/site_admin/shelters/'
        response = self.client.get(url)

        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            response = self.login('admin@leash.com', 'password', url)
            self.assert_template_used('index.html')

            user.role = 'operator'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            response = self.client.get(url)
            self.assert_redirects(response, url2)

            msg = 'Puppies distributed. Consolatory chew toys '
            msg += 'have been provided.'
            response = self.client.get(url2)
            self.assertIn(msg, response.data)

            s = Shelter.query.filter_by(name='Swell Friendly Place').one()
            self.assertEqual(s.puppy_count, 2)

            s = Shelter.query.filter_by(name='Shiny Happy Place').one()
            self.assertEqual(s.puppy_count, 2)

            s = Shelter.query.filter_by(name='Super Awesome Place').one()
            self.assertEqual(s.puppy_count, 2)

            self.client.get('/logout/')

    def test_auth_signup(self):
        url = '/signup/'
        response = self.client.get(url)

        self.assert_template_used('signup.html')
        form = self.get_context_variable('form')
        self.assertEqual(type(form), EmailPasswordForm)

        response = self.client.post(
            url,
            data={
                'email': test_email,
                'password': 'password'
            },
            follow_redirects=True
        )
        self.assert_200(response)
        self.assert_template_used('index.html')
        u = User.query.filter_by(email=test_email).one()
        self.assertTrue(u.is_correct_password('password'))
        self.assertFalse(u.email_confirmed)

    def test_auth_send_email_confirmation(self):
        user = User(email=test_email, password='password')
        db.session.add(user)

        response = self.client.get('/confirm/bad-token/')
        self.assert_404(response)

        with mail.record_messages() as outbox:
            views.auth.send_email_confirmation(user)
            self.assertEqual(len(outbox), 1)
            email = str(outbox[0])
            link = re.search(r'/confirm/(.+)/\?next', email)
            url = '/confirm/' + link.group(1) + '/'
            response = self.client.get(url)
            self.assert_redirects(response, '/login/')
            response = self.client.get('/login/')
            self.assertIn(
                'Thanks! Your account has been activated.', response.data)

    def test_auth_login(self):
        user = User.query.first()

        url = '/login/'

        response = self.client.get(url)
        form = self.get_context_variable('form')
        self.assert_200(response)
        self.assertEqual(type(form), EmailPasswordForm)
        self.assert_template_used('login.html')

        response = self.client.post(
            url,
            data={
                'email': user.email,
                'password': 'iforgot'
            }
        )
        self.assert_redirects(response, '/login/')

        response = self.client.post(
            url,
            data={
                'email': user.email,
                'password': 'password'
            }
        )
        self.assert_redirects(response, '/')

        response = self.client.post(
            url + '?next=/shelter/0/',
            data={
                'email': user.email,
                'password': 'password'
            }
        )
        self.assert_redirects(response, '/shelter/0/')

    def test_auth_logout(self):
        user = User.query.first()

        with app.app_context():
            self.login(user.email, 'password')
            self.assert_template_used('index.html')

            user.role = 'admin'
            db.session.add(user)

            url = '/site_admin/shelters/'
            response = self.client.get(url)
            self.assert_200(response)
            self.assert_template_used('site_admin.html')

            response = self.client.get('/logout/')
            self.assert_redirects(response, '/')

            url = '/site_admin/shelters/'
            response = self.client.get(url)
            self.assert_redirects(
                response, '/login/?next=' + urllib.quote_plus(url))

    def test_auth_change_password(self):
        user = User.query.first()

        url = '/change_password/'
        response = self.client.get(url)
        self.assert_redirects(
            response, '/login/?next=' + urllib.quote_plus(url))

        with app.app_context():
            self.login(user.email, 'password')
            self.assert_template_used('index.html')

            response = self.client.get(url)
            form = self.get_context_variable('form')
            self.assert_200(response)
            self.assert_template_used('change_password.html')
            self.assertEqual(type(form), PasswordForm)

            response = self.client.post(
                url,
                data={
                    'password': 'Pass123!'
                },
                follow_redirects=True
            )
            self.assert_template_used('account_profile.html')
            self.assertIn('Password changed successfully.', response.data)

            self.client.get('/logout/')
            self.login(user.email, 'Pass123!')
            self.assert_template_used('index.html')

            self.client.get('/logout/')

    def test_auth_reset_password(self):
        user = User.query.first()

        url = '/reset_password/'
        response = self.client.get(url)
        form = self.get_context_variable('form')
        self.assert_200(response)
        self.assert_template_used('reset_password.html')
        self.assertEqual(type(form), EmailForm)

        response = self.client.post(
            url,
            data={
                'email': user.email
            },
            follow_redirects=True
        )
        self.assert_template_used('account_not_activated.html')

        user.email_confirmed = True
        db.session.add(user)

        with mail.record_messages() as outbox:
            response = self.client.post(
                url,
                data={
                    'email': user.email
                },
                follow_redirects=True
            )
            self.assertEqual(len(outbox), 1)
            email = str(outbox[0])
            link = re.search(r'/reset_confirm/(.+)/">', email)
            url = '/reset_confirm/' + link.group(1) + '/'

            response = self.client.get(url)
            form = self.get_context_variable('form')
            self.assert_template_used('new_password.html')
            self.assertEqual(type(form), PasswordForm)

            response = self.client.post(
                url,
                data={
                    'password': 'NewPassword'
                },
                follow_redirects=True
            )
            self.assert_template_used('login.html')
            msg = 'Password changed successfully. Please '
            msg += 'login with your new password.'
            self.assertIn(msg, response.data)

            self.login(user.email, 'NewPassword')
            self.assert_template_used('index.html')

            self.client.get('/logout/')

    def test_auth_confirm_password_reset(self):
        response = self.client.get('/reset_confirm/bad-token/')
        self.assert_404(response)

    def test_auth_view_account(self):
        user = User.query.first()
        puppy = Puppy.query.first()
        puppy.adopter = [user, ]
        db.session.add(puppy)

        with app.app_context():
            self.login(user.email, 'password')
            url = '/account/'

            response = self.client.get(url)
            form = self.get_context_variable('form')
            self.assert_200(response)
            self.assert_template_used('account_profile.html')
            self.assertEqual(type(form), AccountForm)
            self.assertEqual(form.name.data, user.name)
            self.assertEqual(form.email.data, user.email)
            p_list = self.get_context_variable('puppies')
            self.assertEqual(p_list[0], puppy)

            u_name = 'Admin User'
            u_email = 'administrator@leash.com'
            response = self.client.post(
                url,
                data={
                    'name': u_name,
                    'email': u_email
                },
                follow_redirects=True
            )
            form = self.get_context_variable('form')
            self.assert_template_used('account_profile.html')
            self.assertIn('Account info changed successfully.', response.data)
            self.assertEqual(form.name.data, u_name)
            self.assertEqual(form.email.data, u_email)
            revised_user = User.query.first()
            self.assertEqual(revised_user.name, u_name)
            self.assertEqual(revised_user.email, u_email)

            self.client.get('/logout/')


if __name__ == '__main__':
    unittest.main()
