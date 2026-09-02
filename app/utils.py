from app import cache
from app.models import Post
from sqlalchemy.orm import joinedload

import os
from itsdangerous import URLSafeTimedSerializer
from app.extensions import mail
from flask_mail import Message
from app import configuration
from sib_api_v3_sdk import (
    ApiClient,
    TransactionalEmailsApi,
    SendSmtpEmail
)

def refresh_home_cache():
    latest_posts = (
        Post.query
        .options(joinedload(Post.author))   # Relationship eager load
        .order_by(Post.date_posted.desc())  # Sorting
        .limit(10)
        .all()
    )

    cache.set("latest_posts", latest_posts)

    return latest_posts

def UserPostCaching(current_user):
    cache_key = f"user_posts_{current_user.id}"
    user_posts = cache.get(cache_key)
    if user_posts is None:
        user_posts = current_user.posts
        cache.set(cache_key,user_posts,timeout=300)
    return user_posts
    

def sendEmail(userEmail, tokenLink):
    api_instance = TransactionalEmailsApi(ApiClient(configuration))

    send_smtp_email = SendSmtpEmail(
        sender={
            "name": "H-24 Blog",
            "email": "dhhardik242008@gmail.com"
        },
        to=[
            {
                "email": f"{userEmail}",
                "name": "H-24 Blog App User "
            }
        ],
        subject="Verify Your Profile ",
    
        html_content = f"""
    <!DOCTYPE html>
    <html lang="en">
    <head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>Verify Your Email</title>
    </head>

    <body style="margin:0;padding:0;background:#f4f7fb;font-family:Arial,Helvetica,sans-serif;">

    <table width="100%" cellpadding="0" cellspacing="0" style="background:#f4f7fb;padding:40px 15px;">
    <tr>
    <td align="center">

    <table width="600" cellpadding="0" cellspacing="0"
    style="background:#ffffff;border-radius:18px;overflow:hidden;box-shadow:0 10px 30px rgba(0,0,0,.08);">

    <tr>
    <td align="center"
    style="background:linear-gradient(135deg,#2563eb,#7c3aed);padding:35px;">

    <h1 style="margin:0;color:white;font-size:34px;">
    🚀 H-24 Blog
    </h1>

    <p style="margin-top:12px;color:#e8edff;font-size:16px;">
    Welcome to the H-24 Community
    </p>

    </td>
    </tr>

    <tr>
    <td style="padding:40px;">

    <h2 style="margin-top:0;color:#222;">
    Hello 👋
    </h2>

    <p style="color:#555;font-size:16px;line-height:28px;">
    Thank you for creating your account on
    <b>H-24 Blog</b>.
    </p>

    <p style="color:#555;font-size:16px;line-height:28px;">
    To activate your account and start exploring the community,
    please verify your email address by clicking the button below.
    </p>

    <div style="text-align:center;margin:40px 0;">

    <a href="{tokenLink}"
    style="
    background:#2563eb;
    color:white;
    text-decoration:none;
    padding:16px 40px;
    font-size:18px;
    font-weight:bold;
    border-radius:10px;
    display:inline-block;">
    ✅ Verify Email
    </a>

    </div>

    <p style="color:#666;font-size:14px;">
    If the button doesn't work, copy and paste this link into your browser:
    </p>

    <p style="word-break:break-all;">
    <a href="{tokenLink}" style="color:#2563eb;">
    {tokenLink}
    </a>
    </p>

    <hr style="border:none;border-top:1px solid #eee;margin:35px 0;">

    <p style="font-size:14px;color:#777;line-height:24px;">
    If you didn't create this account, you can safely ignore this email.
    Your account will remain inactive until verification.
    </p>

    </td>
    </tr>

    <tr>
    <td align="center"
    style="background:#f8fafc;padding:25px;">

    <p style="margin:0;color:#777;font-size:13px;">
    © 2026 H-24 Blog • Built with ❤️ by Hardik Prajapati
    </p>

    </td>
    </tr>

    </table>

    </td>
    </tr>
    </table>

    </body>
    </html>
    """
    )

    try:
        response = api_instance.send_transac_email(send_smtp_email)
        print("Email Sent Successfully!")
        return True
    except Exception as e:
        print("Error:", e)
        return False

SECRET_KEY =  os.getenv('SECRET_KEY')
SECURITY_SALT = os.getenv("SECURITY_SALT")

def genrate_verifactionToken(email):
    serializer = URLSafeTimedSerializer(secret_key=SECRET_KEY)
    return serializer.dumps(email, salt=SECURITY_SALT)

def verifyToken(token,expiration=1500):
    serializer = URLSafeTimedSerializer(secret_key=SECRET_KEY)
    try:
        email = serializer.loads(
            token,
            salt=SECURITY_SALT,
            max_age=expiration
        )
        return email
    except Exception as e:
        print(f'Toke Error {e}')
        return None