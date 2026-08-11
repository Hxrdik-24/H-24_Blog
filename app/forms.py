from flask_wtf import FlaskForm
from wtforms  import StringField , PasswordField , SubmitField , BooleanField , FileField   , HiddenField
from wtforms.validators import DataRequired , Length , Email , EqualTo , ValidationError , Regexp
from app.models import User
from flask_wtf.file import FileAllowed 
from flask_login import current_user

class registration(FlaskForm):   # it is inher. Flask form 
    username = StringField("UserName",validators=[DataRequired(),Length(min=2,max=10) ]) # data is requried and min length is 2 or max len os 10 
    email = StringField("Useremail",validators=[DataRequired(),Email()]) 
    password = PasswordField(
        "Password",
        validators=[
            DataRequired(),
            Length(min=8, max=20)
        ]
    )

    Confirm_password = PasswordField(
        "Confirm Password",
        validators=[
            DataRequired(),
            Length(min=8, max=20),
            EqualTo("password", message="Passwords must match")
        ]
    )    
    submit = SubmitField("Sign Up")

    def validate_username(self,username):
        user = User.query.filter_by(username=username.data).first()
        if user :
            raise ValidationError(" Username is already taken. ")
    def validate_email(self,email):
            email = User.query.filter_by(email=email.data).first()
            if email :
                raise ValidationError("Email is already taken ")

class LoginForm(FlaskForm):
    email = StringField("UserEmail",validators=[DataRequired(),Email()])
    password = PasswordField("Password",validators=[DataRequired(),Length(min=8 , max= 20)])
    remember = BooleanField("Remember Me")
    submit = SubmitField("Log In ")



class UpdateProfile(FlaskForm):   # it is inher. Flask form 
    username = StringField("Username",validators=[DataRequired(),Length(min=2,max=10) ]) # data is requried and min length is 2 or max len os 10 
    profile_pic = FileField("Upload your Profile Pic ",validators=[FileAllowed(['png','jpeg','jpg'], 'Only JPG, JPEG, and PNG files are allowed.')])
    
    bio = StringField("Bio",validators=[Length(min=0,max=50) ])
    github_link = StringField("GitHub Profile ",validators=[Length(min=0,max=50) ])
    submit = SubmitField("Save Profile")
    def validate_username(self,username):
        if username.data != current_user.username:
            user = User.query.filter_by(username=username.data).first()
            if user :
                raise ValidationError(" Username is already taken. ")
            
class createPost(FlaskForm):
    title = StringField("Title",validators=[DataRequired(),Length(min=2,max=80) ])
    content =  HiddenField("POST CONTENT",validators=[DataRequired()])
    submit = SubmitField("POST")

      
class UpdatePost(FlaskForm):
    title = StringField("Title",validators=[DataRequired(),Length(min=2,max=80) ])
    content =  HiddenField("POST CONTENT",validators=[DataRequired()])
    submit = SubmitField("POST")

class OTPForm(FlaskForm):
    otp = StringField(
        "OTP",
        validators=[
            DataRequired(),
            Length(min=6, max=6),
            Regexp(r'^\d{6}$', message="OTP must be exactly 6 digits.")
        ]
    )

    submit = SubmitField("Verify")