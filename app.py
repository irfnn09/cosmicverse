from flask import Flask, render_template, request, redirect, url_for, flash, session
from werkzeug.security import generate_password_hash, check_password_hash
from dotenv import load_dotenv
from database import get_db, init_db
import os

load_dotenv()

app = Flask(__name__)
app.secret_key = os.getenv("SECRET_KEY")

#Buat database bila app start
with app.app_context():
    init_db()

# HOME

@app.route("/")
def home():
    db = get_db()

    #Ambil puisi terbaru
    puisi_terbaru = db.execute('''
        SELECT poems.*, users.username
        FROM poems
        JOIN users ON poems.user_id = users.id
        ORDER BY tarikh_Publish DESC
        LIMIT 6
    ''').fetchall()

     # Ambil puisi popular
    puisi_popular = db.execute('''
        SELECT poems.*, users.username, COUNT(likes.id) as jumlah_like
        FROM poems 
        JOIN users ON poems.user_id = users.id
        LEFT JOIN likes ON poems.id = likes.poem_id
        GROUP BY poems.id
        ORDER BY jumlah_like DESC
        LIMIT 6
    ''').fetchall()

    db.close()
    return render_template("home.html", 
                         puisi_terbaru=puisi_terbaru,
                         puisi_popular=puisi_popular)


# REGISTER

@app.route("/register", methods=["GET", "POST"])
def register():
    if request.method == "POST":
        username = request.form["username"]
        email = request.form["email"]
        kata_laluan = request.form["kata_laluan"]

        db = get_db()

        # Check kalau username atau email dah wujud
        user_sedia_ada = db.execute(
            "SELECT id FROM users WHERE username = ? OR email = ?",
            (username, email)
        ).fetchone()

        if user_sedia_ada:
            flash("Username atau email dah digunakan!", "error")
            return redirect(url_for("register"))

        # Encrypt password
        kata_laluan_hash = generate_password_hash(kata_laluan)

        # Simpan user baru
        db.execute(
            "INSERT INTO users (username, email, kata_laluan) VALUES (?, ?, ?)",
            (username, email, kata_laluan_hash)
        )
        db.commit()
        db.close()

        flash("Akaun berjaya didaftar! Sila login.", "success")
        return redirect(url_for("login"))
    
    return render_template("register.html")

    #LOGIN

@app.route("/login", methods=["GET", "POST"])
def login():
    if request.method == "POST":
        email = request.form["email"]
        kata_laluan = request.form["kata_laluan"]
        
        db = get_db()
        user = db.execute(
            "SELECT * FROM users WHERE email = ?", (email,)
        ).fetchone()
        db.close()

        if user and check_password_hash(user["kata_laluan"], kata_laluan):
            session["user_id"] = user["id"]
            session["username"] = user["username"]
            flash("Selamat datang, " + user["username"] + "!", "success")
            return redirect(url_for("home"))
        else:
            flash("Email atau kata laluan salah!", "error")

    return render_template("login.html")

#LOGOUT

@app.route("/logout")
def logout():
    session.clear()
    flash("Anda telah log keluar.", "success")
    return redirect(url_for("home"))


#TULIS PUISI

@app.route("/write", methods=["GET", "POST"])
def write():
    if not session.get("user_id"):
        flash("Sila log masuk dulu!", "error")
        return redirect(url_for("login"))

    if request.method == "POST":
        tajuk = request.form["tajuk"]
        isi = request.form["isi"]
        kategori = request.form["kategori"]
        tags = request.form["tags"]
        nama_penulis_asal = request.form["nama_penulis_asal"]
        sumber = request.form["sumber"]
        
        db = get_db()

        #SIMPAN PUISI
        db.execute('''
            INSERT INTO poems (tajuk, isi, kategori, nama_penulis_asal, sumber, user_id)
            VALUES (?, ?, ?, ?, ?, ?)
        ''', (tajuk, isi, kategori, nama_penulis_asal, sumber, session["user_id"]))

        poem_id = db.execute("SELECT last_insert_rowid()").fetchone()[0]

         # SIMPAN TAG
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            for tag in tag_list:
                if tag:
                    db.execute(
                        "INSERT INTO tags (nama_tag, poem_id) VALUES (?, ?)",
                        (tag.lower(), poem_id)
                    )

        db.commit()
        db.close()

        flash("Puisi berjaya diterbitkan!", "success")
        return redirect(url_for("poem", poem_id=poem_id))

    return render_template("write.html")

#BACA PUISI

@app.route("/poem/<int:poem_id>")
def poem(poem_id):
    db = get_db()

    # Ambil puisi
    puisi = db.execute('''
        SELECT poems.*, users.username
        FROM poems
        JOIN users ON poems.user_id = users.id
        WHERE poems.id = ?
    ''', (poem_id,)).fetchone()
    
    if not puisi:
        flash("Puisi tidak dijumpai!", "error")
        return redirect(url_for("home"))

    # Ambil penulis
    penulis = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (puisi["user_id"],)
    ).fetchone()
    
    # Ambil tags
    tags = db.execute(
        "SELECT * FROM tags WHERE poem_id = ?",
        (poem_id,)
    ).fetchall()

    # Ambil komen
    komen = db.execute('''
        SELECT comments.*, users.username
        FROM comments
        JOIN users ON comments.user_id = users.id
        WHERE comments.poem_id = ?
        ORDER BY comments.tarikh DESC
    ''', (poem_id,)).fetchall()
    
    # Kira likes
    jumlah_like = db.execute(
        "SELECT COUNT(*) FROM likes WHERE poem_id = ?",
        (poem_id,)
    ).fetchone()[0]

    # Check user dah like ke belum
    sudah_like = False
    if session.get("user_id"):
        like = db.execute(
            "SELECT id FROM likes WHERE user_id = ? AND poem_id = ?",
            (session["user_id"], poem_id)
        ).fetchone()
        sudah_like = like is not None
    
    db.close()

    return render_template("poem.html",
        puisi=puisi,
        penulis=penulis,
        tags=tags,
        komen=komen,
        jumlah_like=jumlah_like,
        sudah_like=sudah_like
    )

#LIKE PUISI

@app.route("/like/<int:poem_id>", methods=["POST"])
def like(poem_id):
    if not session.get("user_id"):
        flash("Sila log masuk dulu!", "error")
        return redirect(url_for("login"))
    
    db = get_db()

    #Check dh like atau tak
    sedia_ada = db.execute(
        "SELECT id FROM likes WHERE user_id = ? AND poem_id = ?",
        (session["user_id"], poem_id)
    ).fetchone()
    
    if sedia_ada:
        # Dah like — buang like (unlike)
        db.execute(
            "DELETE FROM likes WHERE user_id = ? AND poem_id = ?",
            (session["user_id"], poem_id)
        )
    else:
        #Belum like- nk like
        db.execute(
            "INSERT INTO likes (user_id, poem_id) VALUES (?, ?)",
            (session["user_id"], poem_id)
        )

    db.commit()
    db.close()
    
    return redirect(url_for("poem", poem_id=poem_id))

#KOMEN

@app.route("/comment/<int:poem_id>", methods=["POST"])
def comment(poem_id):
    if not session.get("user_id"):
        flash("Sila log masuk dulu!", "error")
        return redirect(url_for("login"))

    isi_komen = request.form["isi_komen"]
    
    if not isi_komen.strip():
        flash("Komen tidak boleh kosong!", "error")
        return redirect(url_for("poem", poem_id=poem_id))
    
    db = get_db()

    db.execute('''
        INSERT INTO comments (isi_komen, user_id, poem_id)
        VALUES (?, ?, ?)
    ''', (isi_komen, session["user_id"], poem_id))
    
    db.commit()
    db.close()
    
    flash("Komen dihantar!", "success")
    return redirect(url_for("poem", poem_id=poem_id))

 #PROFILE

@app.route("/profile/<username>")
def profile(username):
    db = get_db()
    
    # Ambil info user
    user = db.execute(
        "SELECT * FROM users WHERE username = ?",
        (username,)
    ).fetchone()

    if not user:
        flash("Pengguna tidak dijumpai!", "error")
        return redirect(url_for("home"))

     # Ambil semua puisi user ni
    puisi_user = db.execute('''
        SELECT * FROM poems
        WHERE user_id = ?
        ORDER BY tarikh_publish DESC
    ''', (user["id"],)).fetchall()
    
    # Kira jumlah like yang user ni dapat
    jumlah_like = db.execute('''
        SELECT COUNT(*) FROM likes
        JOIN poems ON likes.poem_id = poems.id
        WHERE poems.user_id = ?
    ''', (user["id"],)).fetchone()[0]
    
    db.close()

    return render_template("profile.html",
        user=user,
        puisi_user=puisi_user,
        jumlah_like=jumlah_like
    )

#EDIT PROFILE

@app.route("/edit-profile", methods=["GET", "POST"])
def edit_profile():
    if not session.get("user_id"):
        flash("Sila log masuk dulu!", "error")
        return redirect(url_for("login"))

    db = get_db()
    user = db.execute(
        "SELECT * FROM users WHERE id = ?",
        (session["user_id"],)
    ).fetchone()
    
    if request.method == "POST":
        bio = request.form["bio"]
        username = request.form["username"]

        # Check kalau username dah digunakan orang lain
        user_sedia_ada = db.execute(
            "SELECT id FROM users WHERE username = ? AND id != ?",
            (username, session["user_id"])
        ).fetchone()

        if user_sedia_ada:
            flash("Username dah digunakan!", "error")
            return redirect(url_for("edit_profile"))

        db.execute(
            "UPDATE users SET bio = ?, username = ? WHERE id = ?",
            (bio, username, session["user_id"])
        )

        # Update session username
        session["username"] = username

        db.commit()
        db.close()

        flash("Profil berjaya dikemaskini!", "success")
        return redirect(url_for("profile", username=session["username"]))

    db.close()
    return render_template("edit_profile.html", user=user)

#MEMBERS

@app.route("/members")
def members():
    cari = request.args.get("cari", "")
    
    db = get_db()

    if cari:
        users = db.execute('''
            SELECT users.*, COUNT(poems.id) as jumlah_puisi
            FROM users
            LEFT JOIN poems ON users.id = poems.user_id
            WHERE users.username LIKE ?
            GROUP BY users.id
            ORDER BY jumlah_puisi DESC
        ''', (f"%{cari}%",)).fetchall()
    else:
        users = db.execute('''
            SELECT users.*, COUNT(poems.id) as jumlah_puisi
            FROM users
            LEFT JOIN poems ON users.id = poems.user_id
            GROUP BY users.id
            ORDER BY jumlah_puisi DESC
        ''').fetchall()
    
    db.close()

    return render_template("members.html",
        users=users,
        cari=cari
    )

#SEARCH

@app.route("/search")
def search():
    query = request.args.get("q", "")

    puisi_result = []
    user_result = []
    tag_result = []
    
    if query:
        db = get_db()

        #Cari puisi
        puisi_result = db.execute('''
            SELECT poems.*, users.username
            FROM poems
            JOIN users ON poems.user_id = users.id
            WHERE poems.tajuk LIKE ?
            OR poems.isi LIKE ?
            OR poems.kategori LIKE ?
        ''', (f"%{query}%", f"%{query}%", f"%{query}%")).fetchall()
        
        # Cari user
        user_result = db.execute('''
            SELECT * FROM users
            WHERE username LIKE ?
        ''', (f"%{query}%",)).fetchall()
        
        # Cari tag
        tag_result = db.execute('''
            SELECT DISTINCT nama_tag FROM tags
            WHERE nama_tag LIKE ?
        ''', (f"%{query}%",)).fetchall()
        
        db.close()

    return render_template("search.html",
         query=query,
        puisi_result=puisi_result,
        user_result=user_result,
        tag_result=tag_result
    )

#KATEGORI
@app.route("/category/<nama>")
def category(nama):
    db = get_db()
    
    puisi_list = db.execute('''
        SELECT poems.*, users.username
        FROM poems
        JOIN users ON poems.user_id = users.id
        WHERE poems.kategori LIKE ?
        ORDER BY tarikh_publish DESC
    ''', (f"%{nama}%",)).fetchall()
    
    db.close()
    
    return render_template("category.html",
        nama_kategori=nama,
        puisi_list=puisi_list
    )

#TAG

@app.route("/tag/<nama>")
def tag(nama):
    db = get_db()
    
    puisi_list = db.execute('''
        SELECT poems.*, users.username
        FROM poems
        JOIN users ON poems.user_id = users.id
        JOIN tags ON poems.id = tags.poem_id
        WHERE tags.nama_tag = ?
        ORDER BY poems.tarikh_publish DESC
    ''', (nama,)).fetchall()
    
    db.close()
    
    return render_template("tag.html",
        nama_tag=nama,
        puisi_list=puisi_list
    )


# EDIT PUISI

@app.route("/edit-poem/<int:poem_id>", methods=["GET", "POST"])
def edit_poem(poem_id):
    if not session.get("user_id"):
        flash("Sila log masuk dulu!", "error")
        return redirect(url_for("login"))
    
    db = get_db()
    
    puisi = db.execute(
        "SELECT * FROM poems WHERE id = ?", (poem_id,)
    ).fetchone()
    
    # Pastikan hanya penulis boleh edit
    if not puisi or puisi["user_id"] != session["user_id"]:
        flash("Anda tidak dibenarkan edit puisi ini!", "error")
        return redirect(url_for("home"))
    
    if request.method == "POST":
        tajuk = request.form["tajuk"]
        isi = request.form["isi"]
        kategori = request.form["kategori"]
        tags = request.form["tags"]
        nama_penulis_asal = request.form["nama_penulis_asal"]
        sumber = request.form["sumber"]
        
        # Update puisi
        db.execute('''
            UPDATE poems
            SET tajuk=?, isi=?, kategori=?, nama_penulis_asal=?, sumber=?
            WHERE id=?
        ''', (tajuk, isi, kategori, nama_penulis_asal, sumber, poem_id))
        
        # Delete tags lama, replace dengan baru
        db.execute("DELETE FROM tags WHERE poem_id = ?", (poem_id,))
        
        if tags:
            tag_list = [t.strip() for t in tags.split(",")]
            for tag in tag_list:
                if tag:
                    db.execute(
                        "INSERT INTO tags (nama_tag, poem_id) VALUES (?, ?)",
                        (tag.lower(), poem_id)
                    )
        
        db.commit()
        db.close()
        
        flash("Puisi berjaya dikemaskini!", "success")
        return redirect(url_for("poem", poem_id=poem_id))
    
    # Ambil tags semasa
    current_tags = db.execute(
        "SELECT nama_tag FROM tags WHERE poem_id = ?", (poem_id,)
    ).fetchall()
    current_tags = ", ".join([t["nama_tag"] for t in current_tags])
    
    db.close()
    
    return render_template("edit_poem.html",
        puisi=puisi,
        current_tags=current_tags
    )


# DELETE PUISI

@app.route("/delete-poem/<int:poem_id>", methods=["POST"])
def delete_poem(poem_id):
    if not session.get("user_id"):
        flash("Sila log masuk dulu!", "error")
        return redirect(url_for("login"))
    
    db = get_db()
    
    puisi = db.execute(
        "SELECT * FROM poems WHERE id = ?", (poem_id,)
    ).fetchone()
    
    # Pastikan hanya penulis boleh delete
    if not puisi or puisi["user_id"] != session["user_id"]:
        flash("Anda tidak dibenarkan delete puisi ini!", "error")
        return redirect(url_for("home"))
    
    # Delete tags, likes, comments dulu baru delete puisi
    db.execute("DELETE FROM tags WHERE poem_id = ?", (poem_id,))
    db.execute("DELETE FROM likes WHERE poem_id = ?", (poem_id,))
    db.execute("DELETE FROM comments WHERE poem_id = ?", (poem_id,))
    db.execute("DELETE FROM poems WHERE id = ?", (poem_id,))
    
    db.commit()
    db.close()
    
    flash("Puisi berjaya dipadam!", "success")
    return redirect(url_for("home"))

if __name__ == "__main__":
    app.run(debug=True)
