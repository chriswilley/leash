# Where Should We Eat?

This project sets up a restaurant listing website.


## Table of contents

* [Base setup](#base-setup)
* [App config](#app-config)
* [Instance config](#create-instance-config-file)
* [Run setup](#run-setup)
* [Running Leash](#running-leash)
* [Testing Leash](#testing-leash)
* [Sample data](#sample-data)
* [Flask-Admin](#flask-admin)
* [Debug toolbar](#debug-toolbar)
* [Creator](#creator)
* [Copyright and license](#copyright-and-license)


## Base setup

For starters, you need [Python](https://www.python.org/downloads/). The program was written for Python 2.7, so that's what you should download and install. You may already have Python, especially if you're on a Mac or Linux machine. To check, open a Terminal window (on a Mac, use the Spotlight search and type in "Terminal"; on a PC go to Start > Run and type in "cmd") and type "python" at the prompt. You should get something that looks like this (run on my Mac):

```
Python 2.7.10 (v2.7.10:15c95b7d81dc, May 23 2015, 09:33:12)
[GCC 4.2.1 (Apple Inc. build 5666) (dot 3)] on darwin
Type "help", "copyright", "credits" or "license" for more information.
>>>
```

Note the version number (2.7.10 in this case). If it starts with "3.", you should download version 2.7. If you have questions about any of this, check Python's [excellent online documentation](https://www.python.org/doc/).

You'll also need a database for Leash to connect to. There are a number of options, basically anything [SQLAlchemy can work with](http://docs.sqlalchemy.org/en/rel_1_0/core/engines.html#supported-databases). One note of caution: SQLite has a problem with decimal fields, and if you use that database you'll get a lot of warning messages in the logs about it. The application will work fine with SQLite, however.

There are a number of Python module dependencies for this project. To install them all, run the following:

```
pip install -r requirements.txt
```

Finally, you'll need [git](http://git-scm.com/download) so that you can clone this project.


## App config

Setting up Leash is pretty straightforward. First you need to create the database, and then [create an instance config file](#create-instance-config-file).

Here are the steps to create the database in PostgreSQL:

In a Terminal window, type:

```
psql
```

This will put you in the PostgreSQL shell environment. Your prompt will look like this: '=>', and you'll see a message similar to:

```
psql (9.3.9)
Type "help" for help.
```

Now you can execute SQL commands and do all kinds of other neat stuff. To setup the application database, type the following:

```
CREATE USER username WITH PASSWORD password;
CREATE DATABASE leash WITH OWNER username;
\q
```

For 'username' above, pick any username you like. For 'password', make sure to create a complex password made up of letters, numbers, symbols, all that jazz. When you're done, hit Ctrl-D to exit from the psql shell. Make a note of the username, password and database name as you'll need them in the next section.


## Create instance config file

Leash requires some configuration items that are deployment dependent. There is a starter file called instance_config_sample.py in the root folder, which has all the config parameters listed and waiting to be filled in. Enter the following in a Terminal window:

```
mkdir instance
cp instance_config_sample.py instance/config.py
```

The table below explains the config parameters.

Paramater | Description
--- | ---
SQLALCHEMY_DATABASE_URI | This is the database connection information Leash needs to attach to the database. For PostgreSQL, this would look like: "postgresql://db_owner:db_owner_password@hostname/db_name".
SQLALCHEMY_TRACK_MODIFICATIONS | This must be set to False due to an issue with Flask-SQLAlchemy and signals.
SECRET_KEY | This is what Flask uses to sign cookies and handle sessions. This should be a long string of random characters to keep it safe. See below for more info.
DEBUG | If you're deploying this in a test or development environment, set this to True. Set it to False if you're deploying into a production environment.
BCRYPT_LOG_ROUNDS | This setting tells the bcrypt module how many times to encrypt a string. This should be set to 12 or higher, but be forewarned that the higher you set it the more your server's CPU will be used (and the longer the encryption will take). Bcrypt is used to encrypt user passwords.
MAIL_SERVER | Leash requires an email (SMTP) server in order to send system emails when a user registers, and for other purposes. This setting tells Leash where the mail server is located (IP address or URL).
MAIL_PORT | Probably 25, but could be 587 or even something else depending on how your email server is set up.
MAIL_USERNAME | This is the email server username for Flask-Mail to login as.
MAIL_PASSWORD | The email server login password.
MAIL_DEFAULT_SENDER | The email address that should show in the "From" line when Leash sends out an email.
MAIL_SUPPRESS_SEND | This is a safety valve so you can turn off email sending if there's a problem, or for testing. Set to False when you want emails to be sent.
TEST_EMAIL | The recipient email address when running Leash tests (some tests send emails).
ADMIN_EMAIL | When you first set up Leash, an administrator account is established. This is the email address used by that account for logging in.
ADMIN_PASSWORD | The password for the initial administrator account.

For the SECRET_KEY setting, you should use a nice, long set of random characters as this key will be used for signing cookies and handling sessions. You can use a variety of online sources to generate the key, or use a function like the following:

```
python -c 'import random; import string; print "".join([random.SystemRandom().choice("abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789!@#$%^&*(-_=+)") for i in range(100)])'
```

Note that there is a config.py file in the Leash root folder. Don't remove or change that file (or overwrite it with the instance_config_sample.py file).


## Run Setup

After the above steps are done, type the following in a Terminal window from the main leash folder:

```
python setup.py
```

If all the config items are correct, the database will be set up and an admin user created for your use. With that, the application is ready to go!


## Running Leash

If you're in a development or test environment, type the following in a Terminal window from the leash root folder:

```
python run.py
```

If you're in a production environment, you'll need to set up a proper web server or use a hosting provider that can handle Flask applications such as Heroku or dotCloud. There are lots of online resources that explain how to do both of those things; check out Flask's [documentation](http://flask.pocoo.org/docs/0.10/deploying/#deployment) for lots of options.


## Testing Leash

There are a number of unit tests in test.py. To run them, type the following in a Terminal window from the leash root folder:

```
python test.py
```


## Sample data

If you want to populate Leash with some starter puppies and shelters, use the puppypopulator.py module. To load the data, type the following in a Terminal window from the leash root folder:

```
python puppypopulator.py
```


## Flask Admin

Leash has Flask-Admin installed, which can only be accessed by a user with the "admin" role (such as the initial administor user set up above). To access it, go to "/admin" from the Leash root URL in a browser (if you're running it on a local server, this would be: http://localhost:5000/admin/).


## Debug Toolbar

Leash also has Flask-DebugToolbar installed, which will only be visible if you have "DEBUG = True" in your instance config (i.e.: on a test or development server). The utility is handy when troubleshooting problems. If you want to disable it, add an instance config parameter as follows:

```
DEBUG_TB_ENABLED = False
```

Other configuration info can be found in the [documentation](http://flask-debugtoolbar.readthedocs.org/en/latest/).


## Creator

This program was built by me, Chris Willey, as part of the Udacity Nanodegree program for [Full Stack Developer](https://www.udacity.com/course/full-stack-web-developer-nanodegree--nd004).


## Copyright and License

Code and documentation copyright 2015 Christopher Willey. Code released under the MIT license.