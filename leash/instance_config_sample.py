SQLALCHEMY_DATABASE_URI = ""  # connection info for your database
SQLALCHEMY_TRACK_MODIFICATIONS = False  # don't change this setting
SECRET_KEY = ""  # application secret for signing cookies, etc.
DEBUG = True  # set to False for production
BCRYPT_LOG_ROUNDS = 12  # recommended setting

MAIL_SERVER = ""  # SMTP server IP or URL
MAIL_PORT = 25  # assumed, but might be different depending on your setup
MAIL_USERNAME = ""  # SMTP server username
MAIL_PASSWORD = ""  # SMTP server password
MAIL_DEFAULT_SENDER = ""  # default 'From' email address for system messages
MAIL_SUPPRESS_SEND = True  # set to False when you're sure you're set

TEST_EMAIL = ""  # testing email recipient address

ADMIN_EMAIL = ""  # administrator account email
ADMIN_PASSWORD = ""  # administrator account password
