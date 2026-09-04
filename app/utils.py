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
import base64
from io import BytesIO
from datetime import datetime
from reportlab.lib.pagesizes import A4
from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Table, TableStyle
from reportlab.lib.styles import getSampleStyleSheet
from reportlab.lib import colors
from sib_api_v3_sdk import TransactionalEmailsApi, ApiClient, SendSmtpEmail, Configuration



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


def generate_logs_pdf(logs):
    """Logs array ko lekar ReportLab PDF BytesIO buffer return karta hai."""
    buffer = BytesIO()
    doc = SimpleDocTemplate(
        buffer, 
        pagesize=A4, 
        rightMargin=15, 
        leftMargin=15, 
        topMargin=20, 
        bottomMargin=20
    )
    elements = []

    # Title & Subtitle Styling
    styles = getSampleStyleSheet()
    title = Paragraph("<b><font size=16 color='#1e293b'>Traffic Requests Log Backup Report</font></b>", styles['Title'])
    elements.append(title)
    
    info_text = f"<font size=9 color='#64748b'>Generated on: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC | Total Records: {len(logs)}</font>"
    elements.append(Paragraph(info_text, styles['Normal']))
    elements.append(Spacer(1, 15))

    # Table Header Data
    data = [["ID", "Time (UTC)", "IP Address", "Method", "Path / Page", "Status"]]

    # Table Rows Data
    for log in logs:
        short_path = log.path if len(log.path) <= 35 else log.path[:32] + "..."
        data.append([
            str(log.id),
            log.timestamp.strftime('%Y-%m-%d %H:%M:%S'),
            log.ip_address,
            log.method,
            short_path,
            str(log.status_code)
        ])

    table = Table(data, colWidths=[35, 115, 95, 50, 220, 45])
    table.setStyle(TableStyle([
        ('BACKGROUND', (0, 0), (-1, 0), colors.HexColor("#1e293b")),
        ('TEXTCOLOR', (0, 0), (-1, 0), colors.whitesmoke),
        ('ALIGN', (0, 0), (-1, -1), 'LEFT'),
        ('FONTNAME', (0, 0), (-1, 0), 'Helvetica-Bold'),
        ('FONTSIZE', (0, 0), (-1, -1), 8),
        ('BOTTOMPADDING', (0, 0), (-1, 0), 6),
        ('GRID', (0, 0), (-1, -1), 0.5, colors.HexColor("#cbd5e1")),
        ('ROWBACKGROUNDS', (0, 1), (-1, -1), [colors.white, colors.HexColor("#f8fafc")])
    ]))

    elements.append(table)
    doc.build(elements)

    buffer.seek(0)
    return buffer


def send_logs_pdf_email(pdf_buffer, total_logs_count):
    api_instance = TransactionalEmailsApi(ApiClient(configuration))
    pdf_bytes = pdf_buffer.getvalue()
    base64_pdf = base64.b64encode(pdf_bytes).decode('utf-8')

    filename = f"traffic_logs_backup_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"

    send_smtp_email = SendSmtpEmail(
        sender={
            "name": "H-24 Blog",
            "email": "dhhardik242008@gmail.com"
        },
        to=[
            {
                "email": "hardikprajapati242008@gmail.com",
                "name": "H-24 Blog App"
            }
        ],
        subject=f"Traffic Logs Backup ({total_logs_count} Records) Before DB Clear",
        html_content=f"""
        <!DOCTYPE html>
        <html>
        <body style="font-family: Arial, sans-serif; background-color: #f4f7fb; padding: 20px;">
            <div style="max-width: 600px; background: #ffffff; padding: 25px; border-radius: 8px; border: 1px solid #e2e8f0;">
                <h2 style="color: #1e293b; margin-top: 0;">Database Logs Backup Report</h2>
                <p style="color: #475569;">Hello Admin,</p>
                <p style="color: #475569;">before Deleting <b>{total_logs_count} records</b> pdf is attached.</p>
                <hr style="border: none; border-top: 1px solid #e2e8f0; margin: 20px 0;">
                <p style="font-size: 12px; color: #94a3b8;">Timestamp: {datetime.utcnow().strftime('%Y-%m-%d %H:%M:%S')} UTC</p>
            </div>
        </body>
        </html>
        """,
        attachment=[
            {
                "content": base64_pdf,
                "name": filename
            }
        ]
    )

    try:
        api_instance.send_transac_email(send_smtp_email)
        print("Backup Email with PDF Sent Successfully!")
        return True
    except Exception as e:
        print("Error sending email:", e)
        return False