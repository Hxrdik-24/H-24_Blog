from app import app , db , bcrypt , cache
from flask import render_template , flash , url_for , redirect ,send_from_directory
from app.forms import registration, LoginForm , UpdateProfile , createPost , UpdatePost ,OTPForm
from app.models import  User ,Post , RequestLog
from flask import request
from flask_login import login_user , current_user , logout_user , login_required
import random
import secrets
import os
import cloudinary.uploader
from app.utils import refresh_home_cache , UserPostCaching , sendEmail , genrate_verifactionToken , verifyToken
import logging
from flask import abort
from flask_limiter import Limiter
from flask_limiter.util import get_remote_address
from flask import request, jsonify
from flask import make_response
#---------------------------------------------

@app.route('/sitemap.xml')
def sitemap():
    base_url = request.host_url.rstrip('/') 
    pages = [
        {'loc': f'{base_url}/', 'priority': '1.0'},
        {'loc': f'{base_url}/about', 'priority': '0.8'},
        {'loc': f'{base_url}/login', 'priority': '0.8'},
        {'loc': f'{base_url}/register', 'priority': '0.8'},
      
    ]
    
    xml_content = '<?xml version="1.0" encoding="UTF-8"?>\n'
    xml_content += '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">\n'
    
    for page in pages:
        xml_content += '  <url>\n'
        xml_content += f"    <loc>{page['loc']}</loc>\n"
        xml_content += f"    <priority>{page['priority']}</priority>\n"
        xml_content += '  </url>\n'
        
    xml_content += '</urlset>'
    
    response = make_response(xml_content)
    response.headers["Content-Type"] = "application/xml"
    return response

logging.getLogger("werkzeug").disabled = True


# my fav cat's images
profile = ['draw_cat.png','toper_cat.png','smart_cat.png','dog.png','cat_default.png']


limiter = Limiter(
    get_remote_address,
    default_limits=[],
    storage_uri=os.getenv('REDIS_URL'),
    app=app
    )

#---------------------------------------------------------
# 404 - Page Not Found 
@app.errorhandler(404)
def page_not_found(e):
    return render_template('404.html'), 404


# 500 - Internal Server Error
@app.errorhandler(500)
def internal_server_error(e):
    return render_template('500.html'), 500

@app.errorhandler(429)
def ratelimit_handler(e):
    return render_template("429.html"), 429
#---------------------------------------------------------

@app.route("/post/<int:post_id>")
def post(post_id):
    post = Post.query.get_or_404(post_id)
    return render_template('post.html', title=post.title, post=post)

@app.after_request
def log_request(response):
    ip = request.headers.get("X-Forwarded-For", request.remote_addr)
    print(ip)
    
    print(
        f"[H-24] {request.remote_addr} | "
        f"{request.method} | "
        f"{request.path} | "
        f"{response.status_code}"
    )

    return response

@app.route("/searchuser",methods=["POST","GET"])
def searchuser():
    if request.method == "POST":
        profile_username = request.form.get('userName') 
        user = User.query.filter_by(username = profile_username).first()
        if user:
            posts = Post.query.filter_by(author=user)\
                      .order_by(Post.date_posted.desc())\
                      .all()
            profile = user.image_file
            if user.image_file == "default.png":
                    profile_cat = ['draw_cat.png','toper_cat.png','smart_cat.png','dog.png','cat_default.png']
                    image = url_for(
                        "static",
                        filename= f"profile_pics/{random.choice(profile_cat)}"
                    )
            else:
                    image = user.image_file
            print(image )
            return render_template('view_profile.html',title='profile',user=user,posts=posts,type = user.profile_type,profile_img=image)
    flash("User not found!", "danger")
    return redirect(url_for('home'))    
@app.route("/post/<int:post_id>/update", methods=["GET","POST"])
@login_required
def postUpdate(post_id):
    post = Post.query.get_or_404(post_id)
    if post.author != current_user:
            abort(403)
        
    form = UpdatePost()

    if form.validate_on_submit():

        post.title = form.title.data
        post.content = form.content.data
        if not form.tag.data:
            post.tag = "General"
        else:
            post.tag = form.tag.data    
        db.session.commit()
        refresh_home_cache()
        flash("Post Updated Successfully","success")

        return redirect(url_for("home", post_id=post.id))

    elif request.method == "GET":

        form.title.data = post.title
        form.content.data = post.content

    return render_template(
        "new_post.html",
        title="Update Post",
        form=form,
        post=post
    )
@app.route("/")
def home():
    posts = cache.get("latest_posts")
    if posts is None:
        refresh_home_cache()
        posts = cache.get('latest_posts')
    return render_template("index.html",posts = posts, title = "Home page")

@app.route("/about")
def about():
    return render_template("about.html")

@app.route("/contact")
def contact():
    return render_template("contact.html")

@app.route("/login",methods=["POST","GET"])
@limiter.limit('3 per minute')
def login():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
    form = LoginForm()
    if form.validate_on_submit():
        user = User.query.filter_by(email=form.email.data).first()
        if user and bcrypt.check_password_hash(user.password,form.password.data):
            login_user(user,remember=form.remember.data)
            next_page = request.args.get('next')
            flash(f"Log in ","success")
            return redirect(next_page) if next_page else redirect(url_for('home'))
        else:
            flash("Invalid email or password.", "danger")
    # elif request.method == "POST":
    #     flash("Invalid credentials", "danger")

    return render_template("login.html", title = "Log In " ,form = form)

@app.route("/register", methods=["GET", "POST"])
def register():
    if current_user.is_authenticated:
        return redirect(url_for('home'))
        
    form = registration()   
    
    if form.validate_on_submit():
        try:
            hashed_password = bcrypt.generate_password_hash(form.password.data).decode('utf-8')
            user = User(username=form.username.data, password=hashed_password, email=form.email.data)
            db.session.add(user)
            db.session.commit()

            token = genrate_verifactionToken(form.email.data)
            token_link = url_for('verify_email', token=token, _external=True)

            email_sent = sendEmail(form.email.data, tokenLink=token_link)
            if email_sent:
                flash("Registration successful! Please check your email to verify.", "success")
            else:
                flash("Account created, but failed to send verification email.", "warning")

            return redirect(url_for("login"))
            
        except Exception as e:
            db.session.rollback()  
            print(f"Database/Registration Error: {e}")
            flash(f"Error: {e}", "danger")
            
    elif request.method == "POST":
        
        print("Form Errors:", form.errors)
        flash("Something went wrong while creating your account. Check form fields.", "danger")
 
    return render_template("register.html", title="Registration", form=form)

@app.route('/logout')
def logout():
    logout_user()
    return redirect(url_for('home'))

def save_img(form_img):
    
    if current_user.public_id:
        cloudinary.uploader.destroy(current_user.public_id)
    random_hex = secrets.token_hex(8)
    response = cloudinary.uploader.upload(
        form_img,
        public_id = random_hex,
        asset_folder = "profile_pics",
        overwrite = True
    ) 
    
    return response
@app.route('/upload-image', methods=['POST'])
def upload_image():

    MAX_FILE_SIZE = 5 * 1024 * 1024  # 5 MB
    #MIN_FREE_STORAGE = 200 * 1024 * 1024  # 200 MB

    if 'image' not in request.files:
        return jsonify({
            'success': False,
            'message': 'No file part'
        })

    file = request.files['image']

    if file.filename == '':
        return jsonify({
            'success': False,
            'message': 'No selected file'
        })

    try:
        # Get actual file size
        file.seek(0, 2)
        file_size = file.tell()
        file.seek(0)

        # Individual file limit
        if file_size > MAX_FILE_SIZE:
            return jsonify({
                'success': False,
                'message': 'File too large. Maximum size is 5 MB.'
            })

        # TODO:
        # Yaha Cloudinary ki remaining storage check karni hai.
        # Agar remaining <= 200 MB:
        #     upload block karna hai.

        upload_result = cloudinary.uploader.upload(file)

        image_url = upload_result.get('secure_url')

        return jsonify({
            'success': True,
            'url': image_url
        })

    except Exception as e:
        return jsonify({
            'success': False,
            'message': str(e)
        })
@app.route('/account', methods=['GET', 'POST'])
@login_required
def account():
    form = UpdateProfile()

    if form.validate_on_submit():
        current_user.username = form.username.data
        current_user.bio = form.bio.data
        current_user.github_link  = form.github_link.data
        if form.profile_pic.data:
            response =  save_img(form_img=form.profile_pic.data)   
            current_user.public_id = response["public_id"]
            current_user.image_file = response["secure_url"]
        db.session.commit()
        flash("Profile Updated Successfully!", "success")
        return redirect(url_for("account"))

    elif request.method == "GET":
        form.username.data = current_user.username
        

    if current_user.image_file == "default.png":
        image = url_for(
            "static",
            filename=f"profile_pics/{random.choice(profile)}"
        )
    else:
        image = current_user.image_file
    posts = UserPostCaching(current_user)        
    return render_template(
        "account.html",
        title="Profile | My Account",
        profile=image,
        form=form,
        type = current_user.profile_type,
        posts = posts
    )
@app.context_processor
def inject_profile():
    if current_user.is_authenticated:
        if current_user.image_file == "default.png":
            image = url_for(
                "static",
                filename=f"profile_pics/{random.choice(profile)}"
            )
        else:
            image = current_user.image_file

    else:
        image = url_for(
            "static",
            filename="profile_pics/default.png"
        )

    return dict(profile_image=image)

@app.route('/post/new',methods = ["POST","GET"])
@login_required
def new_post():
    if current_user.is_verified == False:
        flash("Verify Your Email First !",'danger')
        return redirect(url_for('account'))
    form = createPost()

    if form.validate_on_submit():
        post  = Post(
            title = form.title.data,
            content=form.content.data,
            author= current_user
        )    
        db.session.add(post)
        db.session.commit()
        flash("Post Created Successfully!", "success")
        refresh_home_cache()
        return redirect(url_for("home"))

    return render_template('new_post.html',title="POST",form=form)
from itsdangerous import URLSafeTimedSerializer, SignatureExpired, BadSignature
from flask import current_app, render_template, redirect, url_for, flash

@app.route("/verify/<token>")
def verify_email(token):
    # Tumhare function ko call karke email nikal rahe hain
    email = verifyToken(token)

    if not email:
        flash("The verification link is invalid or has expired.", "danger")
        return redirect(url_for('login'))

    # Ab database se user dhoondo
    user = User.query.filter_by(email=email).first()

    if user:
        if user.is_verified:
            flash("Account already verified! Please log in.", "info")
        else:
            user.is_verified = True
            db.session.commit()
            flash("Your email has been verified! You can now log in.", "success")
    else:
        flash("User not found.", "danger")

    return redirect(url_for('login'))

@app.route('/sendverifaction')
def sendverif():
    token = genrate_verifactionToken(current_user.email)
    token_link = url_for('verify_email', token=token, _external=True)

    email_sent = sendEmail(current_user.email, tokenLink=token_link)
    if email_sent:
            flash(" Please check your email to verify.", "success")
    else:
            flash("Email failed to send.", "warning")
    return redirect(url_for('home'))

@app.after_request
def add_security_headers(response):
    response.headers["X-Frame-Options"] = "SAMEORIGIN"
    response.headers['Content-Security-Policy'] = "frame-ancestors 'self'"
    return response

@app.route('/2fa')
def Twofa():
    form = OTPForm()
    if form.validate_on_submit():
        print(form.otp.data)
    return render_template('2fa.html',form=form)

@app.route('/supportus')
def sup():
    return render_template('supportus.html')

@app.route('/helth')
def helth():
    return "OK" , 200
# @app.route('/google7c80791f63896477.html')
# def google_verification():
#     return  send_from_directory('.', 'google7c80791f63896477.html')
