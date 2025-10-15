from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
import os
import random
import uuid
from datetime import datetime
import boto3

main = Blueprint("main", __name__)

# Helper functions to avoid circular imports
def get_models():
    from models import User, Employee, Document, db
    return User, Employee, Document, db

def get_s3_client():
    return boto3.client(
        "s3",
        aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
        aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
        region_name=os.getenv("AWS_REGION", "us-east-1")
    )

def get_s3_bucket():
    return os.getenv("S3_BUCKET_NAME")

# ---------- ROOT REDIRECT ----------
@main.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("main.admin_dashboard"))
        else:
            return redirect(url_for("main.dashboard"))
    return redirect(url_for("main.login"))

# ---------- LOGIN ----------
@main.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("main.admin_dashboard"))
        else:
            return redirect(url_for("main.dashboard"))
            
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        User, Employee, Document, db = get_models()
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            return redirect(url_for("main.admin_dashboard" if user.is_admin else "main.dashboard"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

# ---------- LOGOUT ----------
@main.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("main.login"))

# ---------- ADMIN: CREATE EMPLOYEE ----------
@main.route("/admin/create_account", methods=["GET", "POST"])
@login_required
def create_account():
    if not current_user.is_admin:
        flash("Unauthorized access.", "error")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        User, Employee, Document, db = get_models()

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for("main.create_account"))

        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_pw, is_admin=False)
        db.session.add(new_user)
        db.session.commit()

        new_employee = Employee(user_id=new_user.id, email=email)
        db.session.add(new_employee)
        db.session.commit()

        flash("Employee account created successfully!", "success")
        return redirect(url_for("main.admin_dashboard"))

    return render_template("create_account.html")

# ---------- ADMIN DASHBOARD ----------
@main.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Unauthorized access.", "error")
        return redirect(url_for("main.dashboard"))
    
    User, Employee, Document, db = get_models()
    employees = Employee.query.all()
    return render_template("admin_dashboard.html", employees=employees)

# ---------- EMPLOYEE DASHBOARD ----------
@main.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    User, Employee, Document, db = get_models()
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash("Employee record not found. Please contact administrator.", "error")
        return redirect(url_for("main.logout"))

    docs = Document.query.filter_by(employee_id=employee.id).all()
    return render_template("dashboard.html", employee=employee, docs=docs)

# ---------- PROFILE SETUP ----------
@main.route("/profile_setup", methods=["GET", "POST"])
@login_required
def profile_setup():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    User, Employee, Document, db = get_models()
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()

        if not name or not email or not department:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("main.profile_setup"))

        # Update employee data
        employee.name = name
        employee.email = email
        employee.department = department
        employee.is_submitted = True
        employee.submitted_at = datetime.utcnow()
        
        db.session.commit()
        
        flash("Your profile has been submitted successfully!", "success")
        return redirect(url_for("main.dashboard"))

    return render_template("profile_setup.html", employee=employee)

# ---------- RESET PROFILE ----------
@main.route("/reset_profile")
@login_required
def reset_profile():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    User, Employee, Document, db = get_models()
    
    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if employee:
        # Reset employee data
        employee.name = None
        employee.department = None
        employee.profile_image_url = None
        employee.is_submitted = False
        employee.submitted_at = None
        
        # Delete documents
        Document.query.filter_by(employee_id=employee.id).delete()
        
        db.session.commit()
    
    flash("Your profile has been reset. You can start over.", "info")
    return redirect(url_for("main.profile_setup"))