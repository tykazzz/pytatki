# -*- coding: utf-8 -*-
"""Obsluga uzytkownika"""

__author__ = "Patryk Niedzwiedzinski"


from dbconnect import connection
from pymysql import escape_string
import re
import gc
from passlib.hash import sha256_crypt
from flask_mail import Message
from flask import render_template, redirect, flash, request, url_for
from flask_login import login_user, logout_user, current_user
from main import APP, MAIL
from config import CONFIG
from pytatki.models import User
from pytatki.view_manager import login_manager, login_required
from itsdangerous import URLSafeTimedSerializer


ts = URLSafeTimedSerializer(CONFIG.secret_key)


def valid_password(password):
    """Validation of password"""
    return re.search('[0-9]', password) and re.search('[A-Z]', password) \
        and re.search('[a-z]', password)


def valid_username(username):
    """Validation of username"""
    return " " in username and username == username.lower()


@APP.route('/user/<username>/')
@login_manager
def user_info(username):
    """User info"""
    con, conn = connection()
    con.execute("SELECT iduser, login FROM user WHERE login = %s", escape_string(username))
    user = con.fetchone()
    con.close()
    conn.close()
    if user:
        con, conn = connection()
        con.execute("SELECT idnote, title, note_type FROM note_view WHERE creator_id = %s", escape_string(str(user['iduser'])))
        notes = con.fetchall()
        con.execute("SELECT idusergroup, name FROM usergroup_membership WHERE iduser = %s", escape_string(str(user['iduser'])))
        groups = con.fetchall()
        con.close()
        conn.close()
        return render_template('user.html', user=user, notes=notes, groups=groups)
    flash('Nie ma takiego użytkownika', 'warning')
    return redirect('/')


def send_confirmation_email(email):
    token = ts.dumps(email, salt='email-confirm-key')
    msg = Message("Pytatki - Potwierdź swój adres email", sender=CONFIG.EMAIL, recipients=[email])
    msg.html = render_template('verify_email.html', token=token)
    MAIL.send(msg)


@APP.route('/user/send-confirmation-mail/')
def send_confirmation_view():
    """Send confirmation email"""
    send_confirmation_email(current_user['email'])
    flash("Wysłano ponownie wiadomość!", 'success')
    return redirect("/")


@APP.route('/user/confirm/<token>')
def confirm_email(token):
    try:
        email = ts.loads(token, salt="email-confirm-key", max_age=86400)
        con, conn = connection()
        con.execute(
            "UPDATE user SET email_confirm = 1 WHERE email = (%s)", escape_string(email))
        conn.commit()
        flash("Adres email zweryfikowany!", 'success')
        con.close()
        conn.close()
        gc.collect()
    except Exception as error:
        flash("Blad" + str(error), 'danger')
    return redirect('/')


@APP.route('/user/update-email/', methods=['POST'])
def update_email():
    try:
        if not current_user['email'] == request.form['email']:
            con, conn = connection()
            con.execute("UPDATE user SET email_confirm = 0, email = %s WHERE iduser = %s", (escape_string(str(request.form['email'])), escape_string(str(current_user['iduser']))))
            conn.commit()
            con.close()
            conn.close()
            send_confirmation_email(request.form['email'])
    except Exception as e:
        flash('Blad: ' + str(e), 'danger')
    return redirect(request.args.get('next') if 'next' in request.args else '/')


@APP.route('/user/update-password/', methods=['POST'])
@login_manager
def update_password():
    if current_user.check_password(request.form['password']):
        con, conn = connection()
        password = sha256_crypt.encrypt((str(request.form['new-password'])))
        con.execute("UPDATE user SET password = %s WHERE iduser = %s", (escape_string(password), escape_string(str(current_user['iduser']))))
        conn.commit()
        con.close()
        conn.close()
    return redirect(request.args.get('next') if 'next' in request.args else '/')


@APP.route('/register/', methods=["POST"])
def register_post():
    """Function for registration a new user"""
    #try:
    if not current_user.is_authenticated:
        form = request.form
        try:
            con, conn = connection()
            if form['password'] == form['confirm'] and len(
                    form['password']) >= 8 and valid_password(form['password']):
                wrong_password = False
            else:
                wrong_password = True
        except KeyError:
            wrong_password = True
        try:
            accept = form['accept_tos']
        except KeyError:
            accept = ''
        con.execute("SELECT * FROM user WHERE login = (%s)",
                                    (escape_string(form['username'])))
        used_username = con.fetchone()
        if accept != 'checked' or used_username or '@' not in form['email'] \
                or wrong_password or valid_username(form['username']):
            return render_template(
                'register.html',
                form=form,
                not_accept=bool(accept != 'checked'),
                used_username=used_username,
                wrong_email=bool('@' not in form['email']),
                wrong_password=wrong_password,
                wrong_username=bool(' ' in form['username']),
                upper=bool(not form['username'] == form['username'].lower()),
            )
        con.execute("SELECT idstatus FROM status WHERE name = \"active\"")
        active = con.fetchone()
        con.execute("INSERT INTO user (login, password, email, status_id) VALUES "
                        "(%s, %s, %s, %s)", (escape_string(form['username']), sha256_crypt.encrypt(escape_string(form['password'])),
                                             escape_string(form['email']), escape_string(str(active['idstatus']))))
        conn.commit()
        flash("Zarejestrowano pomyslnie!", 'success')
        con.close()
        conn.close()
        gc.collect()
        send_confirmation_email(form['email'])
        return redirect(url_for('login_get', next=request.args.get('next'), username=form['username']))
    else:
        flash("Jestes juz zalogowany!", 'warning')
    return redirect(request.args.get('next') if 'next' in request.args else '/')
    #except Exception as error:
    #    flash('Blad: '+str(error), 'danger')
    #    return redirect('/')


@APP.route('/register/', methods=["GET"])
def register_get():
    """Registration a new user"""
    if not current_user.is_authenticated:
        return render_template('register.html')
    flash("Jestes juz zalogowany!", 'warning')
    return redirect(request.args.get('next') if 'next' in request.args else '/')


@APP.route('/login/', methods=["POST"])
def login_post():
    try:
        if current_user.is_authenticated:
            flash('Już jesteś zalogowany!', 'warning')
            if request.args.get('next'):
                return redirect(request.args.get('next'))
            return redirect('/')
        con, conn = connection()
        con.execute("SELECT * FROM user WHERE email = %s OR login = %s",
                    (escape_string(request.form['username']), escape_string(request.form['username'])))
        user_dict = con.fetchone()
        user = User()
        if user_dict is not None:
            user.update(user_dict)
        con.close()
        conn.close()
        gc.collect()
        if user and sha256_crypt.verify(request.form['password'], user['password']):
            remember_me = request.form['remember'] if 'remember' in request.form else False
            login_user(user, remember=remember_me)
            return redirect(request.args.get('next') if 'next' in request.args else '/app/')
        return render_template('login.html')
    except Exception as error:
        flash('Błąd: ' + str(error), 'danger')
        return redirect('/')


@APP.route('/login/', methods=["GET"])
def login_get():
    """Login"""
    return render_template('login.html')


@APP.route("/logout/")
@login_required
def logout():
    """Logout"""
    logout_user()
    return redirect('/')
