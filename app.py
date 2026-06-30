from flask import Flask, send_file, request, jsonify
import random, time, os
import psycopg2
import psycopg2.extras
from urllib.parse import urlparse

app = Flask(__name__)

DATABASE_URL = os.environ.get('DATABASE_URL')

# --- 익명 닉네임 생성용 단어 ---
ADJ = ["졸린", "배고픈", "신난", "지친", "느긋한", "용감한", "조용한", "엉뚱한",
       "행복한", "느린", "빠른", "수줍은", "단호한", "차분한", "엉성한", "튼튼한",
       "졸음많은", "커피사랑", "야근싫은", "퇴근직전"]
NOUN = ["돼지", "다람쥐", "펭귄", "햄스터", "여우", "고래", "토끼", "부엉이",
        "거북이", "수달", "코알라", "사자", "너구리", "오리", "곰", "강아지",
        "물개", "기린", "판다", "라마"]

def gen_nickname():
    return random.choice(ADJ) + " " + random.choice(NOUN)

def get_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not set, guestbook won't work")
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS guestbook (
            id SERIAL PRIMARY KEY,
            nickname TEXT NOT NULL,
            text TEXT NOT NULL,
            ts DOUBLE PRECISION NOT NULL
        )
    ''')
    conn.commit()
    cur.close()
    conn.close()

init_db()

@app.route('/')
def index():
    return send_file('index.html')

@app.route('/api/nickname')
def api_nickname():
    return jsonify({"nickname": gen_nickname()})

@app.route('/api/guestbook', methods=['GET'])
def get_guestbook():
    conn = get_db()
    cur = conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor)
    cur.execute('SELECT nickname, text, ts FROM guestbook ORDER BY id DESC LIMIT 100')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    messages = [dict(r) for r in rows]
    return jsonify({"messages": messages})

@app.route('/api/guestbook', methods=['POST'])
def post_guestbook():
    data = request.get_json(force=True)
    nickname = (data.get('nickname') or '익명').strip()[:20]
    text = (data.get('text') or '').strip()[:200]
    if not text:
        return jsonify({"error": "empty"}), 400
    conn = get_db()
    cur = conn.cursor()
    cur.execute(
        'INSERT INTO guestbook (nickname, text, ts) VALUES (%s, %s, %s)',
        (nickname, text, time.time())
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run()
