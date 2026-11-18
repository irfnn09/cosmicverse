import sqlite3
from datetime import datetime

def get_db():
    conn = sqlite3.connect('cosmicverse.db')
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    conn = get_db()
    cursor = conn.cursor()

    #Table user
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            email TEXT UNIQUE NOT NULL,
            kata_laluan TEXT NOT NULL,
            bio TEXT,
            tarikh_join TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        ''')

    #Table poems
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS poems (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            tajuk TEXT NOT NULL,
            isi TEXT NOT NULL,
            kategori TEXT NOT NULL,
            nama_penulis_asal TEXT,
            sumber TEXT,
            user_id INTEGER NOT NULL,
            tarikh_publish TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id)
            )
        ''')
    
    #Table tags
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS tags (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            nama_tag TEXT NOT NULL,
            poem_id INTEGER NOT NULL,
            FOREIGN KEY (poem_id) REFERENCES poems (id)
            )
        ''')
    
    #Table likes
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS likes (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            user_id INTEGER NOT NULL,
            poem_id INTEGER NOT NULL,
            tarikh TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (poem_id) REFERENCES poems (id)
            )
        ''')

    #Table comments
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS comments (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            isi_komen TEXT NOT NULL,
            user_id INTEGER NOT NULL,
            poem_id INTEGER NOT NULL,
            tarikh TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
            FOREIGN KEY (user_id) REFERENCES users (id),
            FOREIGN KEY (poem_id) REFERENCES poems (id)
            )
        ''')

    conn.commit()
    conn.close()
    print("Database berjaya dibuat!")

if __name__ == "__main__":
    init_db()
