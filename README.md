# Blog Application

A simple blog application built with Flask, SQLAlchemy, and other essential libraries.

## Installation

1. Clone the repository:
    ```sh
    git clone https://github.com/Luca-Melop/blog.git
    cd blog
    ```

2. Create and activate a virtual environment:
    ```sh
    python -m venv venv
    source venv/bin/activate  # On Windows use `venv\Scripts\activate`
    ```

3. Install the dependencies:
    ```sh
    pip install -r requirements.txt
    ```

4. Set up environment variables:
    ```sh
    export SECRET_KEY='your_secret_key'
    export DATABASE_URL='sqlite:///blog.db'
    export MAIL_USERNAME='your_email@gmail.com'
    export MAIL_PASSWORD='your_email_password'
    ```

5. Initialize the database:
    ```sh
    flask db upgrade
    ```

6. Run the application:
    ```sh
    flask run
    ```

## Usage

- Homepage: `http://127.0.0.1:5000/`
- Admin dashboard: `http://127.0.0.1:5000/admin` (Login required)

## Routes

- `/` - Display all blog posts
- `/post/<int:post_id>` - Display a specific post
- `/login` - User login
- `/add` - Add a new blog post (Admin only)
- `/edit/<int:post_id>` - Edit an existing post (Admin only)
- `/delete/<int:post_id>` - Delete a post (Admin only)
- `/contact` - Contact form


## Contact

For any queries or issues, please contact `lucamezger88@gmail.com`.
