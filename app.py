from flask import Flask, render_template, request, redirect, url_for, flash, session
from flask_login import LoginManager, login_user, login_required, logout_user, current_user, UserMixin
from werkzeug.security import generate_password_hash, check_password_hash
from flask_mail import Mail
from flask_sqlalchemy import SQLAlchemy
import os
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.environ["SECRET_KEY"]
app.config["SQLALCHEMY_DATABASE_URI"] = os.environ["DATABASE_URL"]
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

# Email configuration
app.config["MAIL_SERVER"] = "smtp.gmail.com"
app.config["MAIL_PORT"] = 587
app.config["MAIL_USE_TLS"] = True
app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

# Initialize extensions
db = SQLAlchemy(app)
login_manager = LoginManager(app)
mail = Mail(app)

# Configure login manager
login_manager.login_view = 'login'
login_manager.login_message_category = 'info'

# Define models
class User(db.Model, UserMixin):
    id = db.Column(db.Integer, primary_key=True)
    username = db.Column(db.String(150), unique=True, nullable=False)
    password = db.Column(db.String(200), nullable=False)
    is_admin = db.Column(db.Boolean, default=False)
    is_active = db.Column(db.Boolean, default=True)

class Employee(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    user_id = db.Column(db.Integer, db.ForeignKey("user.id"), nullable=False)
    name = db.Column(db.String(150))
    email = db.Column(db.String(150), unique=True)
    department = db.Column(db.String(100))
    is_submitted = db.Column(db.Boolean, default=False)

class Document(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    employee_id = db.Column(db.Integer, db.ForeignKey("employee.id"), nullable=False)
    file_url = db.Column(db.String(300), nullable=False)

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Routes
@app.route("/")
def index():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("dashboard"))
    return redirect(url_for("login"))

@app.route("/login", methods=["GET", "POST"])
def login():
    if current_user.is_authenticated:
        if current_user.is_admin:
            return redirect(url_for("admin_dashboard"))
        else:
            return redirect(url_for("dashboard"))
            
    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        user = User.query.filter_by(username=username).first()
        if user and check_password_hash(user.password, password) and user.is_active:
            login_user(user)
            return redirect(url_for("admin_dashboard" if user.is_admin else "dashboard"))
        flash("Invalid credentials", "error")
    return render_template("login.html")

@app.route("/logout")
@login_required
def logout():
    logout_user()
    flash("You have been logged out successfully.", "info")
    return redirect(url_for("login"))

@app.route("/admin/dashboard")
@login_required
def admin_dashboard():
    if not current_user.is_admin:
        flash("Unauthorized access.", "error")
        return redirect(url_for("dashboard"))
    
    employees = Employee.query.all()
    return render_template("admin_dashboard.html", employees=employees)

@app.route("/admin/create_employee", methods=["GET", "POST"])
@login_required
def create_employee():
    if not current_user.is_admin:
        flash("Unauthorized access.", "error")
        return redirect(url_for("dashboard"))

    if request.method == "POST":
        username = request.form["username"]
        password = request.form["password"]
        email = request.form["email"]

        # Check if username exists
        if User.query.filter_by(username=username).first():
            flash("Username already exists.", "error")
            return redirect(url_for("create_employee"))

        # Create user
        hashed_pw = generate_password_hash(password, method="pbkdf2:sha256")
        new_user = User(username=username, password=hashed_pw, is_admin=False)
        db.session.add(new_user)
        db.session.commit()

        # Create employee record
        new_employee = Employee(user_id=new_user.id, email=email)
        db.session.add(new_employee)
        db.session.commit()

        flash(f"Employee account created for {username}!", "success")
        return redirect(url_for("admin_dashboard"))

    return render_template("create_employee.html")

@app.route("/dashboard")
@login_required
def dashboard():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    employee = Employee.query.filter_by(user_id=current_user.id).first()
    if not employee:
        flash("Employee record not found.", "error")
        return redirect(url_for("logout"))

    docs = Document.query.filter_by(employee_id=employee.id).all()
    return render_template("dashboard.html", employee=employee, docs=docs)

@app.route("/profile_setup", methods=["GET", "POST"])
@login_required
def profile_setup():
    if current_user.is_admin:
        return redirect(url_for("admin_dashboard"))

    employee = Employee.query.filter_by(user_id=current_user.id).first()
    
    if request.method == "POST":
        name = request.form.get("name", "").strip()
        email = request.form.get("email", "").strip()
        department = request.form.get("department", "").strip()

        if not name or not email or not department:
            flash("Please fill in all required fields.", "error")
            return redirect(url_for("profile_setup"))

        # Update employee data
        employee.name = name
        employee.email = email
        employee.department = department
        employee.is_submitted = True
        
        db.session.commit()
        
        flash("Your profile has been submitted successfully!", "success")
        return redirect(url_for("dashboard"))

    return render_template("profile_setup.html", employee=employee)

# Create tables and admin user
with app.app_context():
    try:
        # Try to create all tables
        db.create_all()
        
        # Check if admin user exists
        if not User.query.filter_by(username="admin").first():
            admin_user = User(
                username="admin",
                password=generate_password_hash("Admin@123", method="pbkdf2:sha256"),
                is_admin=True,
            )
            db.session.add(admin_user)
            db.session.commit()
            print("✅ Default admin account created: admin / Admin@123")
        else:
            print("✅ Admin user already exists")
            
        print("✅ Database connected:", app.config["SQLALCHEMY_DATABASE_URI"])
        
    except Exception as e:
        print(f"❌ Database error: {e}")
        print("💡 Try deleting the site.db file and restarting the app")

if __name__ == "__main__":
    app.run()