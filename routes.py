from flask import Blueprint, render_template, request, redirect, url_for, flash, session
from flask_login import login_user, login_required, logout_user, current_user
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Message
import os
import random
import uuid
from datetime import datetime

# Import from app (circular import handled)
from flask import current_app
from models import User, Employee, Document

main = Blueprint("main", __name__)

def get_s3_client():
    import boto3
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
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password):
            login_user(user)
            next_page = request.args.get('next')
            if next_page:
                return redirect(next_page)
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

        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for("main.create_account"))

        if len(password) < 6:
            flash("Password must be at least 6 characters long.", "error")
            return redirect(url_for("main.create_account"))

        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_pw, is_admin=False)
        
        from models import db
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
    
    employees = Employee.query.all()
    return render_template("admin_dashboard.html", employees=employees)

# ---------- EMPLOYEE: PROFILE SETUP ----------
@main.route("/profile_setup", methods=["GET", "POST"])
@login_required
def profile_setup():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if not employee:
        flash("Employee record not found. Please contact administrator.", "error")
        return redirect(url_for("main.logout"))

    if employee.is_submitted:
        flash("Your profile has already been submitted.", "info")
        return redirect(url_for("main.dashboard"))

    if request.method == "POST":
        session.pop('employee_data', None)
        session.pop('uploaded_docs', None)
        
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()

        if not name or not email or not department:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("main.profile_setup"))

        session["employee_data"] = {
            "name": name,
            "email": email,
            "department": department
        }

        # Upload profile image to S3
        profile_image = request.files.get("profile_image")
        if profile_image and profile_image.filename:
            try:
                s3_client = get_s3_client()
                bucket_name = get_s3_bucket()
                
                file_extension = profile_image.filename.rsplit('.', 1)[1].lower() if '.' in profile_image.filename else ''
                filename = f"profiles/profile_{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
                
                s3_client.upload_fileobj(
                    profile_image, 
                    bucket_name, 
                    filename, 
                    ExtraArgs={
                        "ACL": "public-read",
                        "ContentType": profile_image.content_type
                    }
                )
                file_url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
                session["employee_data"]["profile_image_url"] = file_url
                flash("Profile image uploaded successfully", "success")
            except Exception as e:
                flash(f"Error uploading profile image: {str(e)}", "error")
                return redirect(url_for("main.profile_setup"))

        # Upload documents to S3
        uploaded_docs = []
        for file in request.files.getlist("documents"):
            if file and file.filename:
                try:
                    s3_client = get_s3_client()
                    bucket_name = get_s3_bucket()
                    
                    file_extension = file.filename.rsplit('.', 1)[1].lower() if '.' in file.filename else ''
                    original_name = file.filename
                    filename = f"documents/doc_{current_user.id}_{uuid.uuid4().hex}.{file_extension}"
                    
                    s3_client.upload_fileobj(
                        file, 
                        bucket_name, 
                        filename, 
                        ExtraArgs={
                            "ACL": "public-read",
                            "ContentType": file.content_type
                        }
                    )
                    file_url = f"https://{bucket_name}.s3.amazonaws.com/{filename}"
                    uploaded_docs.append({
                        "url": file_url,
                        "name": original_name,
                        "type": file_extension
                    })
                except Exception as e:
                    flash(f"Error uploading document {file.filename}: {str(e)}", "error")
                    return redirect(url_for("main.profile_setup"))

        session["uploaded_docs"] = uploaded_docs
        if uploaded_docs:
            flash(f"{len(uploaded_docs)} document(s) uploaded successfully", "success")
        
        return redirect(url_for("main.preview"))

    return render_template("profile_setup.html", employee=employee)

# ---------- PREVIEW ----------
@main.route("/preview")
@login_required
def preview():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    data = session.get("employee_data")
    docs = session.get("uploaded_docs", [])
    
    if not data:
        flash("Please complete your profile information first.", "error")
        return redirect(url_for("main.profile_setup"))

    return render_template("preview.html", data=data, docs=docs)

# ---------- SEND OTP ----------
@main.route("/send_otp", methods=["POST"])
@login_required
def send_otp():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    data = session.get("employee_data")
    if not data:
        flash("Session expired. Please complete your profile again.", "error")
        return redirect(url_for("main.profile_setup"))

    try:
        otp = str(random.randint(100000, 999999))
        session["otp"] = otp
        session["otp_attempts"] = 0

        from flask_mail import Mail
        from flask import current_app
        mail = Mail(current_app)
        
        msg = Message(
            "Your OTP Code - Candidate Onboarding",
            sender=os.getenv("MAIL_USERNAME"),
            recipients=[data.get("email")]
        )
        msg.body = f"""
        Hello {data.get('name')},
        
        Your OTP for profile submission is: {otp}
        
        This OTP is valid for 10 minutes.
        
        If you didn't request this, please ignore this email.
        
        Best regards,
        Candidate Onboarding System
        """
        mail.send(msg)
        flash("OTP sent to your registered email address.", "success")
        return render_template("verify_otp.html")
    
    except Exception as e:
        flash(f"Failed to send OTP: {str(e)}", "error")
        return redirect(url_for("main.preview"))

# ---------- VERIFY OTP ----------
@main.route("/verify_otp", methods=["POST"])
@login_required
def verify_otp():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    entered_otp = request.form.get("otp", "").strip()
    stored_otp = session.get("otp")
    data = session.get("employee_data")
    docs = session.get("uploaded_docs", [])
    
    if not stored_otp or not data:
        flash("Session expired. Please complete your profile again.", "error")
        return redirect(url_for("main.profile_setup"))

    session["otp_attempts"] = session.get("otp_attempts", 0) + 1
    if session["otp_attempts"] > 3:
        flash("Too many failed attempts. Please restart the process.", "error")
        session.clear()
        return redirect(url_for("main.profile_setup"))

    if entered_otp == stored_otp:
        try:
            from models import db
            employee = Employee.query.filter_by(user_id=current_user.id).first()
            if not employee:
                flash("Employee record not found.", "error")
                return redirect(url_for("main.profile_setup"))

            # Update employee data
            employee.name = data["name"]
            employee.email = data["email"]
            employee.department = data["department"]
            employee.profile_image_url = data.get("profile_image_url")
            employee.is_submitted = True
            employee.submitted_at = datetime.utcnow()
            
            # Add documents
            for doc in docs:
                new_doc = Document(
                    employee_id=employee.id, 
                    file_url=doc["url"],
                    file_name=doc["name"],
                    file_type=doc["type"]
                )
                db.session.add(new_doc)
            
            db.session.commit()
            
            # Clear session data
            session.clear()
            
            flash("Your details and documents have been submitted successfully!", "success")
            return redirect(url_for("main.dashboard"))

        except Exception as e:
            db.session.rollback()
            flash(f"Error saving data: {str(e)}", "error")
            return redirect(url_for("main.preview"))

    flash("Invalid OTP, please try again.", "error")
    return redirect(url_for("main.preview"))

# ---------- EMPLOYEE DASHBOARD ----------
@main.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("main.admin_dashboard"))

    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash("Employee record not found. Please contact administrator.", "error")
        return redirect(url_for("main.logout"))

    docs = Document.query.filter_by(employee_id=employee.id).all()
    return render_template("dashboard.html", employee=employee, docs=docs)