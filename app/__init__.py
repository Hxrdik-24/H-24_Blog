from flask import Flask
import os
import dotenv
from flask_sqlalchemy import SQLAlchemy
from flask_bcrypt import Bcrypt
from flask_login import LoginManager
import cloudinary
from flask_caching import Cache
from flask_mail import Mail
from flask_login import AnonymousUserMixin
from sib_api_v3_sdk import (
    Configuration
)
#from sqlalchemy.orm import DeclarativeBase
dotenv.load_dotenv()

app = Flask(__name__)
app.config["SECRET_KEY"] = os.getenv("SECRET_KEY")
#------------------------------------------------------------------------
#Data Base Config. with SqlAlchemy
db_url = os.getenv("DB_URL")

if db_url and db_url.startswith("postgres://"):
    db_url = db_url.replace("postgres://", "postgresql://", 1)
app.config["SQLALCHEMY_DATABASE_URI"] = db_url
app.config["SQLALCHEMY_TRACK_MODIFICATIONS"] = False

app.config["SQLALCHEMY_ENGINE_OPTIONS"] = {
    "pool_recycle": 300,
    "pool_pre_ping": True
}
#------------------------------------------------------------------------
#cloudinary Storage for user profile pic 
cloudinary.config(
    cloud_name = os.getenv("CLOUDINARY_CLOUD_NAME"),
    api_key = os.getenv("CLOUDINARY_API_KEY"),
    api_secret = os.getenv("CLOUDINARY_API_SECRET")
    )


#----------------------------------------------------------------------
#cache 

cache  = Cache()

app.config["CACHE_TYPE"] = os.getenv("CACHE_TYPE")
app.config["CACHE_DEFAULT_TIMEOUT"] = int(
    os.getenv("CACHE_DEFAULT_TIMEOUT", "3600")
)
app.config["REMEMBER_COOKIE_HTTPONLY"] = True
app.config["REMEMBER_COOKIE_SECURE"] = True
app.config["REMEMBER_COOKIE_SAMESITE"] = "Lax"
cache.init_app(app)
db = SQLAlchemy(app)
bcrypt = Bcrypt(app)
login_manager = LoginManager(app)

login_manager.login_view = 'login'


#------------------------------------
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USERNAME'] = os.getenv('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.getenv('MAIL_PASSWORD')


mail = Mail(app)

# Custom anonymous class jisme is_verified ko False set kar diya
class AnonymousUser(AnonymousUserMixin):
    @property
    def is_verified(self):
        return False

# Flask-Login me isko set kar do
login_manager.anonymous_user = AnonymousUser
#------------------------------------
# Email api confi. for brevo 


configuration = Configuration()
configuration.api_key["api-key"] = os.getenv("BREVO_API")

#---------------------------------
from app import models
from app import routes
from app import admin_route