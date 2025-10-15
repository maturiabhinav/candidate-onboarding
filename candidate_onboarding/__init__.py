from flask import Flask
from flask_sqlalchemy import SQLAlchemy
from flask_login import LoginManager
from flask_mail import Mail
import boto3
import os

db = SQLAlchemy()
login_manager = LoginManager()
mail = Mail()

# Initialize S3 client
s3 = boto3.client(
    "s3",
    access_key_id=os.getenv("ACCESS_KEY_ID"),
    secret_access_key=os.getenv("SECRET_ACCESS_KEY"),
    region_name=os.getenv("REGION")
)

S3_BUCKET = os.getenv("S3_BUCKET_NAME")

def create_app():
    app = Flask(__name__)

    # Secret key
    app.config["SECRET_KEY"] = os.getenv("SECRET_KEY", "default_secret")

    # ✅ Use RDS connection instead of sqlite
    app.config["SQLALCHEMY_DATABASE_URI"] = os.getenv(
        "DATABASE_URL",
        "sqlite:///site.db"  # fallback for local dev
    )
    app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

    # Mail setup
    app.config["MAIL_SERVER"] = "smtp.gmail.com"
    app.config["MAIL_PORT"] = 587
    app.config["MAIL_USE_TLS"] = True
    app.config["MAIL_USERNAME"] = os.getenv("MAIL_USERNAME")
    app.config["MAIL_PASSWORD"] = os.getenv("MAIL_PASSWORD")

    db.init_app(app)
    login_manager.init_app(app)
    mail.init_app(app)

    from .routes import main
    app.register_blueprint(main)

    return app
