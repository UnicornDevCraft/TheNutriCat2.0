"""Authentication routes for the application."""

import logging

from flask import Blueprint, flash, redirect, render_template, request, url_for
from flask_login import login_user, logout_user

from nutri_app import db
from nutri_app.models import User
from nutri_app.forms import RegistrationForm, LoginForm



bp = Blueprint("auth", __name__, url_prefix="/auth")
logger = logging.getLogger(__name__)


@bp.route("/register", methods=("GET", "POST"))
def register():
    """Register user"""
    form = RegistrationForm()

    if request.method == "POST":
        if form.validate_on_submit():
            user = User(
                username=User.generate_random_username(), 
                email=form.email.data
                )
            user.set_password(form.password.data)
            db.session.add(user)
            db.session.commit()
            login_user(user)
            flash("Registration was successful.", "success")
            return redirect(url_for("recipes.index"))

        if form.errors != {}:
            for err_list in form.errors.values():
                for err_msg in err_list:
                    flash(f'An error occured: {err_msg}', category='error')
        
    return render_template("auth/register.html", form=form)


@bp.route("/login", methods=("GET", "POST"))
def login():
    """Log user in"""
    form = LoginForm()

    if request.method == "POST":
        if form.validate_on_submit():
            attempted_user = User.query.filter_by(email=form.email.data).first()
            if attempted_user and attempted_user.check_password(form.password.data):
                login_user(attempted_user)
                flash("You are successfully logged in!", "success")
                return redirect(url_for("recipes.index"))
            else:
                flash("Incorrect email or password.", "error")

    return render_template("auth/login.html", form=form)


@bp.route("/logout")
def logout():
    """Log user out"""
    logout_user()
    flash("You are successfuly logged out!", "success")
    return redirect(url_for("recipes.index"))