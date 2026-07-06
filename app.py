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

ANIMAL_EMOJI = {
    "돼지": "🐷", "다람쥐": "🐿️", "펭귄": "🐧", "햄스터": "🐹",
    "여우": "🦊", "고래": "🐳", "토끼": "🐰", "부엉이": "🦉",
    "거북이": "🐢", "수달": "🦦", "코알라": "🐨", "사자": "🦁",
    "너구리": "🦝", "오리": "🦆", "곰": "🐻", "강아지": "🐶",
    "물개": "🦭", "기린": "🦒", "판다": "🐼", "라마": "🦙"
}
NOUN = list(ANIMAL_EMOJI.keys())

def gen_nickname():
    adj = random.choice(ADJ)
    noun = random.choice(NOUN)
    emoji = ANIMAL_EMOJI[noun]
    return emoji + " " + adj + " " + noun

def get_db():
    conn = psycopg2.connect(DATABASE_URL, sslmode='require')
    return conn

def init_db():
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not set, guestbook won't work")
        return
    conn = get_db()
    cur = conn.cursor()
    # ⭐ has_siren 컬럼 포함하여 테이블 생성
    cur.execute('''
        CREATE TABLE IF NOT EXISTS guestbook (
            id SERIAL PRIMARY KEY,
            nickname TEXT NOT NULL,
            text TEXT NOT NULL,
            ts DOUBLE PRECISION NOT NULL,
            has_siren BOOLEAN DEFAULT FALSE
        )
    ''')
    # ⭐ 기존 DB 유저분들을 위해 컬럼이 없으면 안전하게 추가하는 쿼리 실행
    cur.execute('ALTER TABLE guestbook ADD COLUMN IF NOT EXISTS has_siren BOOLEAN DEFAULT FALSE;')
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
    # ⭐ has_siren 컬럼도 함께 SELECT 하도록 수정
    cur.execute('SELECT id, nickname, text, ts, has_siren FROM guestbook ORDER BY id DESC LIMIT 100')
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
    # ⭐ 신규 글 저장 시 기본값 FALSE로 명시적 저장
    cur.execute(
        'INSERT INTO guestbook (nickname, text, ts, has_siren) VALUES (%s, %s, %s, FALSE)',
        (nickname, text, time.time())
    )
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

# ⭐ 신규 추가: 관리자용 🚨 경고 뱃지 처리 API (비밀번호: 0530)
@app.route('/api/guestbook/<int:msg_id>/siren', methods=['POST'])
def siren_guestbook(msg_id):
    pw = request.get_json(force=True).get('password', '')
    if pw != '0530':
        return jsonify({"error": "unauthorized"}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE guestbook SET has_siren = TRUE WHERE id = %s', (msg_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

if __name__ == '__main__':
    app.run()

@app.route('/api/guestbook/<int:msg_id>', methods=['DELETE'])
def delete_guestbook(msg_id):
    pw = request.get_json(force=True).get('password', '')
    if pw != '0530':
        return jsonify({"error": "unauthorized"}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute('DELETE FROM guestbook WHERE id = %s', (msg_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

# --- 일하기 싫다 카운터 ---
@app.route('/api/hate', methods=['GET'])
def get_hate():
    conn = get_db()
    cur = conn.cursor()
    today = __import__('datetime').date.today().isoformat()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS hate_count (
            date TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    ''')
    conn.commit()
    cur.execute('SELECT count FROM hate_count WHERE date = %s', (today,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"count": row[0] if row else 0, "date": today})

@app.route('/api/hate', methods=['POST'])
def post_hate():
    conn = get_db()
    cur = conn.cursor()
    today = __import__('datetime').date.today().isoformat()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS hate_count (
            date TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    ''')
    cur.execute('''
        INSERT INTO hate_count (date, count) VALUES (%s, 1)
        ON CONFLICT (date) DO UPDATE SET count = hate_count.count + 1
    ''', (today,))
    conn.commit()
    cur.execute('SELECT count FROM hate_count WHERE date = %s', (today,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"count": row[0] if row else 1})
