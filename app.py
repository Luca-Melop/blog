from datetime import datetime
from bs4 import BeautifulSoup
from flask import Flask, jsonify, render_template, request, redirect, url_for, session, flash
from flask_sqlalchemy import SQLAlchemy
from bleach.sanitizer import Cleaner
import os
from werkzeug.utils import secure_filename
import re
import html
from bleach.css_sanitizer import CSSSanitizer
from werkzeug.exceptions import RequestEntityTooLarge
from PIL import Image
from form import ContactForm 
from flask_mail import Mail, Message

ADMIN_USERNAME = os.environ.get('ADMIN_USERNAME')
ADMIN_PASSWORD = os.environ.get('ADMIN_PASSWORD')

def crop_to_aspect_ratio(image_path, output_path, aspect_width=3, aspect_height=2):
    image = Image.open(image_path)
    img_width, img_height = image.size

    # Calculate target height for a 16:9 aspect ratio based on the current width
    target_height = int((aspect_height / aspect_width) * img_width)

    if target_height > img_height:
        # If target height is greater than image height, calculate target width instead
        target_width = int((aspect_width / aspect_height) * img_height)
        offset = (img_width - target_width) // 2
        crop_box = (offset, 0, offset + target_width, img_height)
    else:
        # Otherwise, calculate offset for height
        offset = (img_height - target_height) // 2
        crop_box = (0, offset, img_width, offset + target_height)

    cropped_image = image.crop(crop_box)
    cropped_image.save(output_path)


# Define the allowed tags, attributes, and styles
allowed_tags = ['div', 'span', 'p', 'br', 'h1', 'h2', 'h3', 'h4', 'h5', 'h6', 
                'ul', 'ol', 'li', 'strong', 'em', 'u', 'strike', 'a', 'img',
                'blockquote', 'code', 'pre', 'table', 'thead', 'tbody', 'tr',
                'th', 'td']

allowed_attributes = {
    '*': ['class', 'id', 'style'],  # Allows attributes on all tags
    'a': ['href', 'title', 'target'], 
    'img': ['src', 'alt', 'title', 'width', 'height', 'style']
}


css_sanitizer = CSSSanitizer(allowed_css_properties=[
    'color', 'background-color', 'font-size', 'text-align', 
    'margin', 'padding', 'width', 'height', 'max-width', 'max-height', 'font-weight'
])
# Create a Cleaner instance with these settings
cleaner = Cleaner(tags=allowed_tags, attributes=allowed_attributes, css_sanitizer=css_sanitizer, strip=True)

ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif', 'webp'}
def allowed_file(filename):
    print(filename)
    print(filename.rsplit('.', 1)[1].lower())
    return '.' in filename and filename.rsplit('.', 1)[1].lower() in ALLOWED_EXTENSIONS



app = Flask(__name__)
app.secret_key = os.environ.get('SECRET_KEY', 'SECRETKEY')
app.config['SQLALCHEMY_DATABASE_URI'] = os.environ.get('DATABASE_URL', 'sqlite:///blog.db')

db = SQLAlchemy(app)


MB = 4 #MegaBytes Limit
app.config['MAX_CONTENT_LENGTH'] = MB * 1024 * 1024 
@app.errorhandler(RequestEntityTooLarge)
def handle_file_too_large(e):
    return f"File is too large, max {MB}Mb", 413

class BlogPost(db.Model):
    id = db.Column(db.Integer, primary_key=True)
    title = db.Column(db.String(100), nullable=False)
    content = db.Column(db.Text, nullable=False)
    preview_image = db.Column(db.String(400))
    created_at = db.Column(db.DateTime, default=datetime.utcnow)
    author = db.Column(db.String(100))
    views = db.Column(db.Integer, default=0)

with app.app_context():
    db.create_all()

# Mail configuration
app.config['MAIL_SERVER'] = 'smtp.gmail.com'
app.config['MAIL_PORT'] = 587
app.config['MAIL_USE_TLS'] = True
app.config['MAIL_USE_SSL'] = False
app.config['MAIL_USERNAME'] = os.environ.get('MAIL_USERNAME')
app.config['MAIL_PASSWORD'] = os.environ.get('MAIL_PASSWORD')
app.config['MAIL_DEFAULT_SENDER'] = 'lucamezger88@gmail.com'

mail = Mail(app)

@app.route('/')
def index():
    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('index.html', posts=posts)

@app.route('/post/<int:post_id>')
def post_detail(post_id):
    post = BlogPost.query.get_or_404(post_id)
    post.views += 1  #statistics
    db.session.commit()
    return render_template('post.html', post=post)


@app.route('/login', methods=['GET', 'POST'])
def login():
    if request.method == 'POST':
        # For simplicity, use a fixed username and password
        if request.form['username'] == ADMIN_USERNAME and request.form['password'] == ADMIN_PASSWORD:
            session['logged_in'] = True
            return redirect(url_for('admin_dashboard'))
        else:
            return 'Login Failed'
    return render_template('login.html')

@app.route('/add', methods=['GET', 'POST'])
def add_post():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    if request.method == 'POST':
        title = request.form['title'].strip()  # Remove any leading/trailing 
        author = request.form['author'].strip()  # Get the author from the form
        content = cleaner.clean(request.form['content'])

        # Check if the title is empty
        if not title:
            return "Title cannot be empty", 400  # Return an error message

        # Check if the title is unique
        existing_post = BlogPost.query.filter_by(title=title).first()
        if existing_post:
            return "A post with this title already exists", 400  # Return an error message

        # Handle the preview image
        preview_image_filename = ''
        if 'previewImage' in request.files:
            file = request.files['previewImage']
            if file.filename != '' and allowed_file(file.filename):
                # Sanitize and format the title for use in the filename
                sanitized_title = secure_filename(title).replace('_', '-')
                new_filename = f"{sanitized_title}_preview"
                file_extension = os.path.splitext(file.filename)[1]
                preview_image_filename = new_filename + file_extension
                file_path = os.path.join('static/images/preview', preview_image_filename)
                temp_path = file_path + "_temp"
                file.save(temp_path)

                # Crop the image to a 16:9 aspect ratio
                crop_to_aspect_ratio(temp_path, file_path)

                # Remove the temporary file
                os.remove(temp_path)

                preview_image_filename = os.path.basename(file_path)
            else:
                return f"Unsupported file type. Allowed types are: {ALLOWED_EXTENSIONS}", 400

        # Create and save the new post
        new_post = BlogPost(title=title, content=content, preview_image=preview_image_filename, author=author)
        db.session.add(new_post)
        db.session.commit()
        return redirect(url_for('index'))

    return render_template('add_post.html')


@app.route('/upload_embedded_image', methods=['POST'])
def upload_embedded_image():
    if not session.get('logged_in'):
        return jsonify(success=False)

    title = request.form.get('title', 'default')
    image_count = request.form.get('imageCount', 1) # Get the image count
    if 'embeddedImage' in request.files:
        file = request.files['embeddedImage']
        if file.filename != '' and allowed_file(file.filename):
            sanitized_title = secure_filename(title).replace('_', '-')
            new_filename = f"{sanitized_title}_{image_count}"
            file_extension = os.path.splitext(file.filename)[1]
            filename_with_extension = new_filename + file_extension
            file_path = os.path.join('static/images/embedded', filename_with_extension)
            file.save(file_path)
            return jsonify(success=True, url=url_for('static', filename='images/embedded/' + filename_with_extension))
        else:
            return f"Unsupported file type. Allowed types are: {ALLOWED_EXTENSIONS}", 400

    return jsonify(success=False)


@app.route('/admin')
def admin_dashboard():
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    posts = BlogPost.query.order_by(BlogPost.created_at.desc()).all()
    return render_template('admin_dashboard.html', posts=posts)

@app.route('/edit/<int:post_id>', methods=['GET', 'POST'])
def edit_post(post_id):
    # Ensure the user is logged in
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    post = BlogPost.query.get_or_404(post_id)
    if request.method == 'POST':
        post.title = request.form['title']
        post.content = request.form['content']
        db.session.commit()
        return redirect(url_for('admin_dashboard'))

    return render_template('edit_post.html', post=post)


@app.route('/delete/<int:post_id>')
def delete_post(post_id):
    if not session.get('logged_in'):
        return redirect(url_for('login'))

    post_to_delete = BlogPost.query.get_or_404(post_id)

    # Delete the preview image if it exists
    if post_to_delete.preview_image:
        preview_image_path = os.path.join('static/images/preview', post_to_delete.preview_image)
        if os.path.exists(preview_image_path):
            os.remove(preview_image_path)

    # Parse the content for embedded image URLs and delete them
    soup = BeautifulSoup(post_to_delete.content, 'html.parser')
    for img_tag in soup.find_all('img'):
        img_url = img_tag.get('src')
        if img_url and img_url.startswith('/static/images/embedded/'):
            img_path = os.path.join(app.root_path, img_url.lstrip('/'))
            if os.path.exists(img_path):
                os.remove(img_path)

    # Delete the post
    db.session.delete(post_to_delete)
    db.session.commit()

    return redirect(url_for('admin_dashboard'))

@app.route('/contact', methods=['GET', 'POST'])
def contact():
    form = ContactForm()
    if form.validate_on_submit():
        # Extract form data
        name = form.name.data
        email = form.email.data
        message = form.message.data

        # Create the message
        msg = Message(subject=f"RSI-Blog: Contact from {name}",
                      sender=app.config['MAIL_DEFAULT_SENDER'],
                      recipients=['lucamezger88@gmail.com'],  # Where you want to receive emails
                      body=f"Received a message from {name} ({email}):\n\n{message}")

        # Send the email
        mail.send(msg)

        flash('Message sent successfully!', 'success')
        return redirect(url_for('contact'))
    return render_template('contact.html', form=form)


#for strip filter
@app.template_filter('strip_tags')
def strip_tags(value):
    # Strip tags
    stripped = re.sub(r'<[^>]+>', '', value)
    # Unescape HTML entities
    unescaped = html.unescape(stripped)
    return unescaped


#security stuff
#@app.after_request
#def apply_caching(response):
#    response.headers["X-Frame-Options"] = "SAMEORIGIN"
 #   response.headers["Content-Security-Policy"] = "default-src 'self'"
#    response.headers["X-XSS-Protection"] = "1; mode=block"
#    response.headers["Strict-Transport-Security"] = "max-age=63072000; includeSubDomains"
#    response.headers["X-Content-Type-Options"] = "nosniff"
#    return response




if __name__ == '__main__':
    app.run(debug=True)
