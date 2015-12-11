from leash import db, app
from leash.models import User

db.drop_all()
db.create_all()

admin_email = app.config['ADMIN_EMAIL']
admin_password = app.config['ADMIN_PASSWORD']
user = User(email=admin_email, password=admin_password, role='admin')
db.session.add(user)
db.session.commit()
