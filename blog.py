from flask import (
    Blueprint, flash, g, redirect, render_template, request, url_for
)
from werkzeug.exceptions import abort

from flaskr.auth import login_required
from flaskr.db import get_db

bp = Blueprint('blog', __name__)

@bp.route('/')
def index():

    # option 1

    #     user_id = g.user['id'] if g.user else 0  # Use 0 if not logged in
    # posts = db.execute("""
    #     SELECT 
    #         p.id, p.title, p.body, p.created, 
    #         p.author_id, u.username,
    #         COUNT(l.id) AS like_count,
    #         MAX(CASE WHEN l.user_id = ? THEN 1 ELSE 0 END) AS user_liked
    #     FROM post p
    #     LEFT JOIN likes l ON p.id = l.post_id
    #     LEFT JOIN user u ON p.author_id = u.id
    #     GROUP BY p.id
    #     ORDER BY p.created DESC
    # """, (user_id,)).fetchall()  # Note the comma in (user_id,) to make it a tuple
    

    # python and sql option 2

    # if g.user is not None:
    # # First get all post IDs the user has liked (more efficient than checking one-by-one)
    # liked_post_ids = [row['post_id'] for row in 
    #     db.execute(
    #         'SELECT post_id FROM likes WHERE user_id = ?', 
    #         (g.user['id'],)
    #     .fetchall()
    # ]
    # # Add user_liked flag to each post
    # for post in posts:
    #     post['user_liked'] = post['id'] in liked_post_ids

    # option 3
    db = get_db()
    posts = db.execute("""
        SELECT 
            p.*,
            u.username,
            COUNT(l.id) AS like_count,
            EXISTS(
                SELECT 1 FROM likes 
                WHERE post_id = p.id AND user_id = ?
            ) AS user_liked
        FROM post p
        LEFT JOIN likes l ON p.id = l.post_id
        LEFT JOIN user u ON p.author_id = u.id
        GROUP BY p.id
        ORDER BY p.created DESC
    """, (g.user['id'] if g.user else 0,)).fetchall()
    
    # before adding user_liked

    # db = get_db()
    # posts = db.execute("""
    # SELECT 
    #     p.id, 
    #     p.title, 
    #     p.body, 
    #     p.created, 
    #     p.author_id, 
    #     u.username,
    #     COUNT(l.id) AS like_count,
    # FROM 
    #     post p
    # LEFT JOIN 
    #     user u ON p.author_id = u.id
    # LEFT JOIN 
    #     likes l ON p.id = l.post_id
    # GROUP BY 
    #     p.id, p.title, p.body, p.created, p.author_id, u.username
    # ORDER BY 
    #     p.created DESC;
    # """).fetchall()
    
    return render_template('blog/index.html', posts=posts)

@bp.route('/<int:id>/like', methods= ['POST'])
@login_required
def like(id):
    db = get_db()
    is_liked = db.execute(
        'SELECT 1 FROM likes WHERE user_id = ? AND post_id = ?',
        (g.user['id'], id)
    ).fetchone() is not None

    if not is_liked:
        db.execute(
            'INSERT INTO likes (user_id, post_id)'
            ' VALUES ( ? , ? )',
            (g.user['id'] , id)
        )
        db.commit()
    else:
        db.execute(
            'DELETE FROM likes WHERE user_id = ? AND post_id = ?',
        (g.user['id'], id)
        )
        db.commit()
    return redirect(url_for('blog.index'))

@bp.route('/create', methods=('GET', 'POST'))
@login_required
def create():
    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'INSERT INTO post (title, body, author_id)'
                ' VALUES (?, ?, ?)',
                (title, body, g.user['id'])
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/create.html')

def get_post(id, check_author=True):
    post = get_db().execute(
        'SELECT p.id, title, body, created, author_id, username'
        ' FROM post p JOIN user u ON p.author_id = u.id'
        ' WHERE p.id = ?',
        (id,)
    ).fetchone()

    if post is None:
        abort(404, f"Post id {id} doesn't exist.")

    if check_author and post['author_id'] != g.user['id']:
        abort(403)

    return post

@bp.route('/<int:id>/update', methods=('GET', 'POST'))
@login_required
def update(id):
    post = get_post(id)

    if request.method == 'POST':
        title = request.form['title']
        body = request.form['body']
        error = None

        if not title:
            error = 'Title is required.'

        if error is not None:
            flash(error)
        else:
            db = get_db()
            db.execute(
                'UPDATE post SET title = ?, body = ?'
                ' WHERE id = ?',
                (title, body, id)
            )
            db.commit()
            return redirect(url_for('blog.index'))

    return render_template('blog/update.html', post=post)

@bp.route('/<int:id>/detail', methods=('POST', 'GET'))
def detail(id):
    if g.user is not None:
        post = get_db().execute("""
            SELECT p.*, u.username,
            COUNT(l.id) AS like_count,
                EXISTS(
                    SELECT 1 FROM likes 
                    WHERE post_id = p.id AND user_id = ?
                ) AS user_liked
            FROM post p
            LEFT JOIN user u ON p.author_id = u.id
            LEFT JOIN likes l ON p.id = l.post_id
            WHERE p.id = ?
            GROUP BY p.id, u.username
        """,
        (g.user['id'],id)).fetchone()
    else:
        post = get_db().execute("""
            SELECT p.*, u.username,
            COUNT(l.id) AS like_count
            FROM post p
            LEFT JOIN user u ON p.author_id = u.id
            LEFT JOIN likes l ON p.id = l.post_id
            WHERE p.id = ?
            GROUP BY p.id, u.username
        """,
        (id,)).fetchone()
    
    return render_template('blog/detail.html', post=post)

@bp.route('/<int:id>/delete', methods=('POST',))
@login_required
def delete(id):
    get_post(id)
    db = get_db()
    db.execute('DELETE FROM post WHERE id = ?', (id,))
    db.commit()
    return redirect(url_for('blog.index'))