from flask import Flask, send_file, request, jsonify
import random, time, os, datetime
import psycopg2
import psycopg2.extras

app = Flask(__name__)
DATABASE_URL = os.environ.get('DATABASE_URL')

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
    return ANIMAL_EMOJI[noun] + " " + adj + " " + noun

def get_db():
    return psycopg2.connect(DATABASE_URL, sslmode='require')

def get_kst_today():
    return (datetime.datetime.utcnow() + datetime.timedelta(hours=9)).strftime('%Y-%m-%d')

def init_db():
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not set")
        return
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        CREATE TABLE IF NOT EXISTS guestbook (
            id SERIAL PRIMARY KEY,
            nickname TEXT NOT NULL,
            text TEXT NOT NULL,
            ts DOUBLE PRECISION NOT NULL,
            has_siren BOOLEAN DEFAULT FALSE,
            has_boom BOOLEAN DEFAULT FALSE
        )
    ''')
    cur.execute('ALTER TABLE guestbook ADD COLUMN IF NOT EXISTS has_siren BOOLEAN DEFAULT FALSE;')
    # 🆕 붐업 컬럼 추가 알터 스크립트 활성화
    cur.execute('ALTER TABLE guestbook ADD COLUMN IF NOT EXISTS has_boom BOOLEAN DEFAULT FALSE;')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS hate_count (
            date TEXT PRIMARY KEY,
            count INTEGER DEFAULT 0
        )
    ''')
    cur.execute('''
        CREATE TABLE IF NOT EXISTS admin_notice (
            id INTEGER PRIMARY KEY,
            text TEXT NOT NULL,
            updated_at DOUBLE PRECISION NOT NULL
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
    # 🆕 조회 필드에 has_boom 연동 추가
    cur.execute('SELECT id, nickname, text, ts, has_siren, has_boom FROM guestbook ORDER BY id DESC LIMIT 100')
    rows = cur.fetchall()
    cur.close()
    conn.close()
    return jsonify({"messages": [dict(r) for r in rows]})

@app.route('/api/guestbook', methods=['POST'])
def post_guestbook():
    data = request.get_json(force=True)
    nickname = (data.get('nickname') or '익명').strip()[:20]
    text = (data.get('text') or '').strip()[:200]
    if not text:
        return jsonify({"error": "empty"}), 400
    conn = get_db()
    cur = conn.cursor()
    # 🆕 신규 입력 시 has_boom 기본값 FALSE 탑재
    cur.execute('INSERT INTO guestbook (nickname, text, ts, has_siren, has_boom) VALUES (%s, %s, %s, FALSE, FALSE)',
                (nickname, text, time.time()))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

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

# 🆕 관리자용 붐업 뱃지 부여 라우터 파이프라인 신설
@app.route('/api/guestbook/<int:msg_id>/boom', methods=['POST'])
def boom_guestbook(msg_id):
    pw = request.get_json(force=True).get('password', '')
    if pw != '0530':
        return jsonify({"error": "unauthorized"}), 401
    conn = get_db()
    cur = conn.cursor()
    cur.execute('UPDATE guestbook SET has_boom = TRUE WHERE id = %s', (msg_id,))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True})

@app.route('/api/hate', methods=['GET'])
def get_hate():
    conn = get_db()
    cur = conn.cursor()
    today = get_kst_today()
    cur.execute('SELECT count FROM hate_count WHERE date = %s', (today,))
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"count": row[0] if row else 0})

@app.route('/api/hate', methods=['POST'])
def post_hate():
    conn = get_db()
    cur = conn.cursor()
    today = get_kst_today()
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

@app.route('/api/notice', methods=['GET'])
def get_notice():
    conn = get_db()
    cur = conn.cursor()
    cur.execute('SELECT text FROM admin_notice WHERE id = 1')
    row = cur.fetchone()
    cur.close()
    conn.close()
    return jsonify({"text": row[0] if row else ""})

@app.route('/api/notice', methods=['POST'])
def post_notice():
    data = request.get_json(force=True)
    if data.get('password', '') != '0530':
        return jsonify({"error": "unauthorized"}), 401
    text = (data.get('text') or '').strip()[:100]
    conn = get_db()
    cur = conn.cursor()
    cur.execute('''
        INSERT INTO admin_notice (id, text, updated_at) VALUES (1, %s, %s)
        ON CONFLICT (id) DO UPDATE SET text = EXCLUDED.text, updated_at = EXCLUDED.updated_at
    ''', (text, time.time()))
    conn.commit()
    cur.close()
    conn.close()
    return jsonify({"ok": True, "text": text})

if __name__ == '__main__':
    app.run()
