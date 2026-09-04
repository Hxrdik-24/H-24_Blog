from app import db
from datetime import datetime
from app import login_manager
from flask_login import UserMixin

@login_manager.user_loader
def load_user(user_id):
     return User.query.get(int(user_id))

class User(db.Model,UserMixin):
    id = db.Column(db.Integer , primary_key = True)
    username = db.Column(db.String(20), unique = True , nullable = False)
    email = db.Column(db.String(80), unique = True , nullable = False)
    image_file = db.Column(db.String(500),nullable = False , default = 'default.png' ) # for profile  
    public_id = db.Column(db.String(255),nullable = True )
    is_verified = db.Column(db.Boolean, default=False, nullable=False)
    profile_type = db.Column(
    db.String(20),
    nullable=False,
    default="normal"
    )    
    password = db.Column(db.String(128))
    posts = db.relationship("Post",backref='author' , lazy = True)
    bio = db.Column(db.Text, nullable=True)
    github_link = db.Column(db.String(255), nullable=True)
    def __repr__(self):
        return f"User('{self.username}','{self.email}','{self.image_file}')"
    

class Post(db.Model):
    id = db.Column(db.Integer , primary_key = True)
    title = db.Column(db.String(80), nullable = False)
    date_posted  = db.Column(db.DateTime,nullable = False, default = datetime.utcnow)
    content = db.Column(db.Text, nullable = False)
    tag = db.Column(db.String(20),nullable=True,default="General")
    user_id = db.Column(db.Integer , db.ForeignKey("user.id") , nullable = False)
    def __repr__(self):
        return f"Post('{self.title}','{self.date_posted}'"

class RequestLog(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    ip_address = db.Column(db.String(45), nullable=False)
    method = db.Column(db.String(10), nullable=False)
    path = db.Column(db.String(500), nullable=False)
    status_code = db.Column(db.Integer, nullable=False)
    user_agent = db.Column(db.String(255), nullable=True)
    timestamp = db.Column(db.DateTime, default=datetime.utcnow)

