import logging

from flask import Blueprint, flash, jsonify, redirect, render_template, request, url_for
from flask_login import current_user, login_required

from nutri_app import db
from nutri_app.models import User, Recipe, Tag, Favorite
from nutri_app.forms import (
    ChangeUsernameForm,
    ChangePasswordForm,
    ForgotPasswordForm,
    SetNewPasswordForm,
)
from nutri_app.utils import generate_reset_token, verify_reset_token

bp = Blueprint("account", __name__, url_prefix="/account")
logger = logging.getLogger(__name__)


@bp.route("/profile")
def profile():
    """Display user profile"""
    if not current_user.is_authenticated:
        flash("Please log in to view your profile.", "error")
        return redirect(url_for("auth.login"))

    change_username_form = ChangeUsernameForm()
    change_password_form = ChangePasswordForm()
    recipe_count = (
        db.session.query(Recipe)
        .join(Recipe.tags)
        .filter(Tag.type == "my_recipe")
        .count()
    )
    favorite_count = Favorite.query.filter_by(user_id=current_user.id).count()

    return render_template(
        "auth/profile.html",
        user=current_user,
        user_recipe_count=recipe_count,
        favorite_count=favorite_count,
        change_username_form=change_username_form,
        change_password_form=change_password_form,
    )


@bp.route("/change-username", methods=["POST"])
@login_required
def change_username():
    """Change the username of the logged-in user"""
    form = ChangeUsernameForm()
    if form.validate_on_submit():
        current_user.username = form.new_username.data
        db.session.commit()
        flash("Username updated successfully!", "success")

    else:
        for err_list in form.errors.values():
            for err_msg in err_list:
                flash(f"An error occured: {err_msg}", category="error")

    return redirect(url_for("account.profile"))


@bp.route("/change-password", methods=["POST"])
@login_required
def change_password():
    """Change the password of the logged-in user"""
    form = ChangePasswordForm()
    if form.validate_on_submit():
        if current_user.check_password(form.current_password.data):
            current_user.set_password(form.new_password.data)
            db.session.commit()
            flash("Your password has been updated successfully!", "success")
        else:
            flash("Please enter a valid current password!", category="error")
    else:
        for err_list in form.errors.values():
            for err_msg in err_list:
                flash(f"An error occured: {err_msg}", category="error")

    return redirect(url_for("account.profile"))


@bp.route("/forgot-password", methods=("GET", "POST"))
def forgot_password():
    """Send password reset email"""
    form = ForgotPasswordForm()

    if request.method == "POST":
        if form.validate_on_submit():
            attempted_user = User.query.filter_by(email=form.email.data).first()
            if attempted_user:
                token = generate_reset_token(form.email.data)
                reset_url = url_for(
                    "account.reset_password", token=token, _external=True
                )
                print(
                    f"Password reset link: {reset_url}"
                )  # Only for debugging, remove in production
                flash(
                    "Password reset instructions have been sent to your email.",
                    "success",
                )
                return redirect(url_for("recipes.index"))
            else:
                flash("Email not found.", "error")
        else:
            for err_list in form.errors.values():
                for err_msg in err_list:
                    flash(f"An error occured: {err_msg}", category="error")

    return render_template("auth/forgot_password.html", form=form)


@bp.route("/reset-password/<token>", methods=("GET", "POST"))
def reset_password(token):
    """Reset password using token"""
    form = SetNewPasswordForm()

    email = verify_reset_token(token)
    if not email:
        flash("The password reset link is invalid or has expired.", "error")
        return redirect(url_for("auth.login"))

    if request.method == "POST":
        if form.validate_on_submit():
            user = User.query.filter_by(email=email).first()
            if user:
                user.set_password(form.password.data)
                db.session.commit()
                flash("Your password has been updated.", "success")
                return redirect(url_for("auth.login"))
        else:
            for err_list in form.errors.values():
                for err_msg in err_list:
                    flash(f"An error occured: {err_msg}", category="error")

    return render_template("auth/reset_password.html", form=form)


@bp.route("/check-email")
def check_email():
    """Check if an email is already registered"""
    email = request.args.get("email", "").strip()

    if not email:
        return jsonify({"exists": False, "error": "No email provided"}), 400

    exists = (
        db.session.execute(db.select(User).filter_by(email=email)).scalar_one_or_none()
        is not None
    )

    return jsonify({"exists": exists})
