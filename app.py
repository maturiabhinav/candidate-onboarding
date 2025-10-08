from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
from werkzeug.security import generate_password_hash
import os
import boto3
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

app = Flask(__name__)

# Configuration
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "dev-secret-key")
app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv("DATABASE_URL")
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

# S3 Configuration
s3 = boto3.client(
    "s3",
    aws_access_key_id=os.getenv("AWS_ACCESS_KEY_ID"),
    aws_secret_access_key=os.getenv("AWS_SECRET_ACCESS_KEY"),
    region_name=os.getenv("AWS_REGION", "us-east-1")
)
S3_BUCKET = os.getenv("S3_BUCKET_NAME")

# Import models after db initialization
from models import User, Employee, Document

# Import and register routes
from routes import main
app.register_blueprint(main)

# Configure login manager
login_manager.login_view = 'main.login'
login_manager.login_message_category = 'info'

@login_manager.user_loader
def load_user(user_id):
    return User.query.get(int(user_id))

# Create tables and admin user
with app.app_context():
    db.create_all()
    if not User.query.filter_by(username="admin").first():
        admin_user = User(
            username="admin",
            password=generate_password_hash("Admin@123", method="pbkdf2:sha256"),
            is_admin=True,
        )
        db.session.add(admin_user)
        db.session.commit()
        print("✅ Default admin account created: admin / Admin@123")
        print("✅ Database connected:", app.config["SQLALCHEMY_DATABASE_URI"])
        print("✅ S3 Bucket:", S3_BUCKET)

if __name__ == "__main__":
    app.run(debug=True)