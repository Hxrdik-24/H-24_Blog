import queue
import threading
import time
from io import BytesIO
from datetime import datetime
from functools import wraps
from flask import render_template, request, redirect, url_for, send_file, flash
from flask_login import current_user, login_required
from app import app, db
from app.models import RequestLog
from app.utils import generate_logs_pdf, send_logs_pdf_email
import os
# ==========================================
# IN-MEMORY BATCH LOGGING QUEUE SETUP
# ==========================================
log_queue = queue.Queue()

def bg_log_worker():
    """Background worker thread jo logs ko queue se nikal kar batch me DB me insert karega"""
    with app.app_context():
        while True:
            batch = []
            # Queue se 50 logs tak ya timeout hone tak accumulate karein
            while len(batch) < 50:
                try:
                    log_data = log_queue.get(timeout=3)
                    batch.append(RequestLog(**log_data))
                    log_queue.task_done()
                except queue.Empty:
                    break

            if batch:
                try:
                    db.session.bulk_save_objects(batch)
                    db.session.commit()
                except Exception as e:
                    db.session.rollback()
                    print(f"[Logging Worker Error]: {e}")

            time.sleep(1)

# Start Background Thread
worker_thread = threading.Thread(target=bg_log_worker, daemon=True)
worker_thread.start()


# Specific Admin Access Decorator
def admin_required(f):
    @wraps(f)
    def decorated_function(*args, **kwargs):
        if not current_user.is_authenticated or current_user.email != f'{os.getenv("ADMIN_EMAIL")}':
            flash("Access Denied !", "danger")
            return redirect(url_for('home'))  
        return f(*args, **kwargs)
    return decorated_function


@app.after_request
def log_incoming_request(response):
    # Static files, favicon, aur internal assets ignore karein
    ignored_paths = ('/static', '/favicon.ico', '/robots.txt')
    if request.path.startswith(ignored_paths):
        return response

    ip = request.headers.get('X-Forwarded-For', request.remote_addr)
    if ip and ',' in ip:
        ip = ip.split(',')[0].strip()

    # Non-blocking Queue Push
    log_data = {
        'ip_address': ip,
        'method': request.method,
        'path': request.path,
        'status_code': response.status_code,
        'user_agent': request.user_agent.string[:255] if request.user_agent else 'Unknown'
    }
    
    # Direct DB Write ki jagah RAM Queue me push (Ultra Fast)
    log_queue.put(log_data)

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
# 2. PDF DOWNLOAD ROUTE (SAFE LIMIT)
# ==========================================
@app.route('/admin/logs/download-pdf')
@login_required
@admin_required
def download_pdf_logs():
    # Memory Crash se bachne ke liye latest 2000 logs limit karein
    logs = RequestLog.query.order_by(RequestLog.timestamp.desc()).limit(2000).all()
    
    buffer = generate_logs_pdf(logs)
    filename = f"traffic_logs_{datetime.utcnow().strftime('%Y%m%d_%H%M%S')}.pdf"
    
    return send_file(
        buffer,
        as_attachment=True,
        download_name=filename,
        mimetype='application/pdf'
    )


# ==========================================
# 3. CLEAR ALL LOGS ROUTE (OPTIMIZED DELETE)
# ==========================================
@app.route('/admin/logs/clear', methods=['POST'])
@login_required
@admin_required
def clear_logs():
    # Backup PDF ke liye top 2000 logs len
    logs = RequestLog.query.order_by(RequestLog.timestamp.desc()).limit(2000).all()

    if not logs:
        flash("Delete karne ke liye koi logs nahi hain!", "warning")
        return redirect(url_for('view_logs'))

    pdf_buffer = generate_logs_pdf(logs)
    email_status = send_logs_pdf_email(pdf_buffer, len(logs))

    if email_status:
        try:
            # Fast Table Delete
            db.session.query(RequestLog).delete(synchronize_session=False)
            db.session.commit()
            flash("Backup Email Delivered successfully and all logs cleared.", "success")
        except Exception as e:
            db.session.rollback()
            flash(f"Error deleting logs from DB: {e}", "danger")
    else:
        flash("Error sending backup email.", "danger")

    return redirect(url_for('view_logs'))