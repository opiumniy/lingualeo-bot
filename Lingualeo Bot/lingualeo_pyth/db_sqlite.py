import os
import aiosqlite
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

DB_PATH = os.path.join(os.path.dirname(__file__), "lingualeo.db")

async def init_db():
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_vocabulary (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                word_id INTEGER,
                english TEXT NOT NULL,
                russian TEXT,
                transcription TEXT,
                picture_url TEXT,
                sound_url TEXT,
                translate_id INTEGER,
                repetitions INTEGER DEFAULT 0,
                ease_factor REAL DEFAULT 2.5,
                interval_hours REAL DEFAULT 1.0,
                next_repetition_date TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP,
                UNIQUE(user_id, english)
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS user_cookies (
                user_id INTEGER PRIMARY KEY,
                cookies TEXT,
                updated_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("""
            CREATE TABLE IF NOT EXISTS training_results (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                user_id INTEGER NOT NULL,
                training_type TEXT NOT NULL,
                results TEXT,
                created_at TEXT DEFAULT CURRENT_TIMESTAMP
            )
        """)
        await db.execute("CREATE INDEX IF NOT EXISTS idx_vocab_user ON user_vocabulary(user_id)")
        await db.execute("CREATE INDEX IF NOT EXISTS idx_vocab_next_rep ON user_vocabulary(user_id, next_repetition_date)")
        await db.commit()

async def get_user_vocabulary(user_id: int) -> List[Dict[str, Any]]:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT word_id, english, russian, transcription, picture_url, sound_url,
                   translate_id, repetitions, ease_factor, interval_hours, next_repetition_date
            FROM user_vocabulary
            WHERE user_id = ?
            ORDER BY english
            """,
            (user_id,)
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get('next_repetition_date'):
                try:
                    d['next_repetition_date'] = datetime.fromisoformat(d['next_repetition_date'])
                except:
                    d['next_repetition_date'] = datetime.now()
            result.append(d)
        return result

async def get_due_words(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    await init_db()
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT word_id, english, russian, transcription, picture_url, sound_url,
                   translate_id, repetitions, ease_factor, interval_hours, next_repetition_date
            FROM user_vocabulary
            WHERE user_id = ? AND next_repetition_date <= ?
            ORDER BY RANDOM()
            LIMIT ?
            """,
            (user_id, now, limit)
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get('next_repetition_date'):
                try:
                    d['next_repetition_date'] = datetime.fromisoformat(d['next_repetition_date'])
                except:
                    d['next_repetition_date'] = datetime.now()
            result.append(d)
        return result

async def count_due_words(user_id: int) -> int:
    await init_db()
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            """
            SELECT COUNT(*) FROM user_vocabulary
            WHERE user_id = ? AND next_repetition_date <= ?
            """,
            (user_id, now)
        )
        row = await cursor.fetchone()
        return row[0] if row else 0

async def upsert_vocabulary_word(user_id: int, word_data: Dict[str, Any]) -> None:
    await init_db()
    now = datetime.now().isoformat()
    next_rep = word_data.get('next_repetition_date')
    if isinstance(next_rep, datetime):
        next_rep = next_rep.isoformat()
    elif next_rep is None:
        next_rep = now
    
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_vocabulary (
                user_id, word_id, english, russian, transcription, picture_url,
                sound_url, translate_id, repetitions, ease_factor, interval_hours,
                next_repetition_date, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            ON CONFLICT (user_id, english) DO UPDATE SET
                russian = excluded.russian,
                transcription = excluded.transcription,
                picture_url = excluded.picture_url,
                sound_url = excluded.sound_url,
                translate_id = excluded.translate_id,
                updated_at = ?
            """,
            (
                user_id,
                word_data.get('word_id'),
                word_data.get('english', ''),
                word_data.get('russian', ''),
                word_data.get('transcription', ''),
                word_data.get('picture_url', ''),
                word_data.get('sound_url', ''),
                word_data.get('translate_id'),
                word_data.get('repetitions', 0),
                word_data.get('ease_factor', 2.5),
                word_data.get('interval_hours', 1.0),
                next_rep,
                now,
                now
            )
        )
        await db.commit()

async def bulk_upsert_vocabulary(user_id: int, words: List[Dict[str, Any]]) -> int:
    await init_db()
    now = datetime.now().isoformat()
    count = 0
    async with aiosqlite.connect(DB_PATH) as db:
        for word in words:
            next_rep = word.get('next_repetition_date')
            if isinstance(next_rep, datetime):
                next_rep = next_rep.isoformat()
            elif next_rep is None:
                next_rep = now
            
            await db.execute(
                """
                INSERT INTO user_vocabulary (
                    user_id, word_id, english, russian, transcription, picture_url,
                    sound_url, translate_id, repetitions, ease_factor, interval_hours,
                    next_repetition_date, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT (user_id, english) DO UPDATE SET
                    russian = excluded.russian,
                    transcription = excluded.transcription,
                    picture_url = excluded.picture_url,
                    sound_url = excluded.sound_url,
                    translate_id = excluded.translate_id,
                    updated_at = ?
                """,
                (
                    user_id,
                    word.get('word_id'),
                    word.get('english', ''),
                    word.get('russian', ''),
                    word.get('transcription', ''),
                    word.get('picture_url', ''),
                    word.get('sound_url', ''),
                    word.get('translate_id'),
                    word.get('repetitions', 0),
                    word.get('ease_factor', 2.5),
                    word.get('interval_hours', 1.0),
                    next_rep,
                    now,
                    now
                )
            )
            count += 1
        await db.commit()
    return count

async def update_word_after_training(user_id: int, english: str, correct: bool) -> None:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT repetitions, ease_factor, interval_hours
            FROM user_vocabulary
            WHERE user_id = ? AND english = ?
            """,
            (user_id, english)
        )
        row = await cursor.fetchone()
        
        if not row:
            return
        
        repetitions = row['repetitions']
        ease_factor = row['ease_factor']
        interval_hours = row['interval_hours']
        
        if correct:
            repetitions += 1
            if repetitions == 1:
                interval_hours = 1.0
            elif repetitions == 2:
                interval_hours = 6.0
            else:
                interval_hours = interval_hours * ease_factor
            ease_factor = max(1.3, ease_factor + 0.1)
        else:
            repetitions = 0
            interval_hours = 0.5
            ease_factor = max(1.3, ease_factor - 0.2)
        
        next_rep = datetime.now().timestamp() + (interval_hours * 3600)
        next_rep_date = datetime.fromtimestamp(next_rep).isoformat()
        now = datetime.now().isoformat()
        
        await db.execute(
            """
            UPDATE user_vocabulary
            SET repetitions = ?, ease_factor = ?, interval_hours = ?,
                next_repetition_date = ?, updated_at = ?
            WHERE user_id = ? AND english = ?
            """,
            (repetitions, ease_factor, interval_hours, next_rep_date, now, user_id, english)
        )
        await db.commit()

async def get_word_status(user_id: int, search_term: str) -> List[Dict[str, Any]]:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT english, russian, repetitions, ease_factor, interval_hours, next_repetition_date
            FROM user_vocabulary
            WHERE user_id = ? AND (LOWER(english) LIKE ? OR LOWER(russian) LIKE ?)
            LIMIT 5
            """,
            (user_id, f"%{search_term.lower()}%", f"%{search_term.lower()}%")
        )
        rows = await cursor.fetchall()
        result = []
        for row in rows:
            d = dict(row)
            if d.get('next_repetition_date'):
                try:
                    d['next_repetition_date'] = datetime.fromisoformat(d['next_repetition_date'])
                except:
                    d['next_repetition_date'] = datetime.now()
            result.append(d)
        return result

async def get_vocabulary_page(user_id: int, offset: int, limit: int, sort_by: str = 'alpha', due_only: bool = False) -> tuple:
    await init_db()
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        
        where_clause = "WHERE user_id = ?"
        params = [user_id]
        if due_only:
            where_clause += " AND next_repetition_date <= ?"
            params.append(now)
        
        if sort_by == 'alpha':
            order_clause = "ORDER BY english ASC"
        elif sort_by == 'date':
            order_clause = "ORDER BY next_repetition_date ASC"
        else:
            order_clause = "ORDER BY english ASC"
        
        cursor = await db.execute(
            f"SELECT COUNT(*) FROM user_vocabulary {where_clause}",
            params
        )
        count_row = await cursor.fetchone()
        count = count_row[0] if count_row else 0
        
        cursor = await db.execute(
            f"""
            SELECT english, russian, next_repetition_date
            FROM user_vocabulary
            {where_clause}
            {order_clause}
            LIMIT ? OFFSET ?
            """,
            params + [limit, offset]
        )
        rows = await cursor.fetchall()
        
        result = []
        for row in rows:
            d = dict(row)
            if d.get('next_repetition_date'):
                try:
                    d['next_repetition_date'] = datetime.fromisoformat(d['next_repetition_date'])
                except:
                    d['next_repetition_date'] = datetime.now()
            result.append(d)
        
        return result, count

async def save_user_cookies(user_id: int, cookies: str) -> None:
    await init_db()
    now = datetime.now().isoformat()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO user_cookies (user_id, cookies, updated_at)
            VALUES (?, ?, ?)
            ON CONFLICT (user_id) DO UPDATE SET cookies = ?, updated_at = ?
            """,
            (user_id, cookies, now, cookies, now)
        )
        await db.commit()

async def get_user_cookies(user_id: int) -> Optional[str]:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        cursor = await db.execute(
            "SELECT cookies FROM user_cookies WHERE user_id = ?",
            (user_id,)
        )
        row = await cursor.fetchone()
        return row[0] if row else None

async def save_training_results(user_id: int, training_type: str, results: Dict) -> None:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            """
            INSERT INTO training_results (user_id, training_type, results)
            VALUES (?, ?, ?)
            """,
            (user_id, training_type, json.dumps(results))
        )
        await db.commit()

async def get_pending_training_results(user_id: int, training_type: str) -> Optional[Dict]:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        db.row_factory = aiosqlite.Row
        cursor = await db.execute(
            """
            SELECT id, results FROM training_results
            WHERE user_id = ? AND training_type = ?
            ORDER BY created_at DESC LIMIT 1
            """,
            (user_id, training_type)
        )
        row = await cursor.fetchone()
        if row:
            return {'id': row['id'], 'results': json.loads(row['results'])}
        return None

async def delete_training_results(result_id: int) -> None:
    await init_db()
    async with aiosqlite.connect(DB_PATH) as db:
        await db.execute(
            "DELETE FROM training_results WHERE id = ?",
            (result_id,)
        )
        await db.commit()

async def close_pool():
    pass

async def get_pool():
    return None
