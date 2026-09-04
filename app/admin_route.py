from io import BytesIO
from datetime import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, send_file, flash
from flask_login import current_user, login_required
from app import app, db
from app.models import RequestLog
from app.utils import generate_logs_pdf, send_logs_pdf_email

# Specific Admin Access Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        # Check: User logged in and User e mail matched 
        if not current_user.is_authenticated or current_user.email != 'hardikprajapati242008@gmail.com':
            flash("Access Denied! Aapko is page ko view karne ki permission nahi hai.", "danger")
            return redirect(url_for('home'))  
        return f(*args, **kwargs)
    return decorated_function


@app.after_request
def log_incoming_request(response):
    if request.path.startswith('/static'):
        return response

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()

    try:
        log_entry = RequestLog(
            ip_address=ip,
            method=request.method,
            path=request.path,
            status_code=response.status_code,
            user_agent=request.user_agent.string[:255] if request.user_agent else 'Unknown'
        )
        db.session.add(log_entry)
        db.session.commit()
    except Exception as e:
        db.session.rollback()

    return response


# ==========================================
# 1. VIEW LOGS ROUTE
# ==========================================
@app.route('/admin/logs')
@login_required
@admin_required
def view_logs():
    logs = RequestLog.query.order_by(RequestLog.timestamp.desc()).limit(100).all()
    total_requests = RequestLog.query.count()
    unique_ips = db.session.query(db.func.count(db.func.distinct(RequestLog.ip_address))).scalar()
    
    return render_template(
        'admin_logs.html', 
        logs=logs, 
        total_requests=total_requests, 
        unique_ips=unique_ips
    )


# ==========================================
# 2. PDF DOWNLOAD ROUTE
# ==========================================
@app.route('/admin/logs/download-pdf')
@login_required
@admin_required
def download_pdf_logs():
    logs = RequestLog.query.order_by(RequestLog.timestamp.desc()).all()
    
    buffer = generate_logs_pdf(logs)
    filename = f"traffic_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ==========================================
# 3. CLEAR ALL LOGS ROUTE
# ==========================================
@app.route('/admin/logs/clear', methods=['POST'])
@login_required
@admin_required
def clear_logs():
    logs = RequestLog.query.order_by(RequestLog.timestamp.desc()).all()

    if not logs:
        flash("Delete karne ke liye koi logs nahi hain!", "warning")
        return redirect(url_for('view_logs'))

    pdf_buffer = generate_logs_pdf(logs)
    email_status = send_logs_pdf_email(pdf_buffer, len(logs))

    if email_status:
        try:
            deleted_count = RequestLog.query.delete()
            db.session.commit()
            flash(f"Backup Email Delivered successfully and {deleted_count} logs successfully deleted.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting logs from DB: {e}", "danger")
    else:
        flash("Error sending backup email.", "danger")

    return redirect(url_for('view_logs'))   