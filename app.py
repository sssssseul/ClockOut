import os
from flask import Flask, request, jsonify, render_template
import psycopg2
import psycopg2.extras

app = Flask(__name__)

# 데이터베이스 연결 설정 (환경 변수 사용)
DATABASE_URL = os.environ.get('DATABASE_URL')

def get_db():
    return psycopg2.connect(DATABASE_URL)

def init_db():
    if not DATABASE_URL:
        print("WARNING: DATABASE_URL not set, database functions won't work")
        return
    
    with get_db() as conn:
        with conn.cursor() as cur:
            # 방명록 테이블 생성 (has_siren 컬럼 포함)
            cur.execute('''
                CREATE TABLE IF NOT EXISTS guestbook (
                    id SERIAL PRIMARY KEY,
                    nickname TEXT NOT NULL,
                    text TEXT NOT NULL,
                    ts DOUBLE PRECISION NOT NULL,
                    has_siren BOOLEAN DEFAULT FALSE
                )
            ''')
            # 기존 테이블에 컬럼이 없을 경우를 대비해 안전하게 추가
            cur.execute('ALTER TABLE guestbook ADD COLUMN IF NOT EXISTS has_siren BOOLEAN DEFAULT FALSE;')
            
            # 일하기 싫다 카운터 테이블 생성
            cur.execute('''
                CREATE TABLE IF NOT EXISTS hate_count (
                    date TEXT PRIMARY KEY,
                    count INTEGER DEFAULT 0
                )
            ''')
        conn.commit()

# 앱 시작 시 DB 초기화
init_db()

@app.route('/')
def index():
    return render_template('index.html')

# 1. 방명록 조회 API (has_siren 포함)
@app.route('/api/guestbook', methods=['GET'])
def get_guestbook():
    with get_db() as conn:
        with conn.cursor(cursor_factory=psycopg2.extras.RealDictCursor) as cur:
            cur.execute('SELECT id, nickname, text, ts, has_siren FROM guestbook ORDER BY id DESC LIMIT 100')
            rows = cur.fetchall()
    
    messages = [dict(r) for r in rows]
    return jsonify({"messages": messages})

# 2. 방명록 작성 API
@app.route('/api/guestbook', methods=['POST'])
def add_guestbook():
    data = request.get_json(force=True)
    nickname = data.get('nickname', '').strip()
    text = data.get('text', '').strip()
    ts = data.get('ts')
    
    if not nickname or not text or ts is None:
        return jsonify({"error": "bad request"}), 400
        
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute(
                'INSERT INTO guestbook (nickname, text, ts, has_siren) VALUES (%s, %s, %s, FALSE)',
                (nickname, text, ts)
            )
        conn.commit()
    return jsonify({"ok": True})

# 3. ⭐ 신규: 🚨 경고 뱃지 등록 API (비밀번호: 0530)
@app.route('/api/guestbook/<int:msg_id>/siren', methods=['POST'])
def siren_guestbook(msg_id):
    pw = request.get_json(force=True).get('password', '')
    if pw != '0530':
        return jsonify({"error": "unauthorized"}), 401
        
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('UPDATE guestbook SET has_siren = TRUE WHERE id = %s', (msg_id,))
        conn.commit()
    return jsonify({"ok": True})

# 4. 방명록 삭제 API (비밀번호: 0530)
@app.route('/api/guestbook/<int:msg_id>', methods=['DELETE'])
def delete_guestbook(msg_id):
    pw = request.get_json(force=True).get('password', '')
    if pw != '0530':
        return jsonify({"error": "unauthorized"}), 401
        
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('DELETE FROM guestbook WHERE id = %s', (msg_id,))
        conn.commit()
    return jsonify({"ok": True})

# 5. 일하기 싫다 카운트 조회 API
@app.route('/api/hate', methods=['GET'])
def get_hate():
    date_str = request.args.get('date', '')
    if not date_str:
        return jsonify({"count": 0})
        
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('SELECT count FROM hate_count WHERE date = %s', (date_str,))
            row = cur.fetchone()
            
    count = row[0] if row else 0
    return jsonify({"count": count})

# 6. 일하기 싫다 카운트 증가 API
@app.route('/api/hate', methods=['POST'])
def increment_hate():
    data = request.get_json(force=True)
    date_str = data.get('date', '')
    if not date_str:
        return jsonify({"error": "bad request"}), 400
        
    with get_db() as conn:
        with conn.cursor() as cur:
            cur.execute('''
                INSERT INTO hate_count (date, count) VALUES (%s, 1)
                ON CONFLICT (date) DO UPDATE SET count = hate_count.count + 1
                RETURNING count
            ''', (date_str,))
            new_count = cur.fetchone()[0]
        conn.commit()
    return jsonify({"count": new_count})

if __name__ == '__main__':
    app.run(host='0.0.0.0', port=5000, debug=True)
