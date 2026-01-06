import os
import asyncpg
from datetime import datetime
from typing import Optional, List, Dict, Any
import json
import logging

logger = logging.getLogger(__name__)

DATABASE_URL = os.environ.get("DATABASE_URL")

_pool: Optional[asyncpg.Pool] = None

async def get_pool() -> asyncpg.Pool:
    global _pool
    if _pool is None:
        _pool = await asyncpg.create_pool(DATABASE_URL, min_size=1, max_size=10)
    return _pool

async def close_pool():
    global _pool
    if _pool:
        await _pool.close()
        _pool = None

async def get_user_vocabulary(user_id: int) -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT word_id, english, russian, transcription, picture_url, sound_url,
                   translate_id, repetitions, ease_factor, interval_hours, next_repetition_date
            FROM user_vocabulary
            WHERE user_id = $1
            ORDER BY english
            """,
            user_id
        )
        return [dict(row) for row in rows]

async def get_due_words(user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT word_id, english, russian, transcription, picture_url, sound_url,
                   translate_id, repetitions, ease_factor, interval_hours, next_repetition_date
            FROM user_vocabulary
            WHERE user_id = $1 AND next_repetition_date <= NOW()
            ORDER BY RANDOM()
            LIMIT $2
            """,
            user_id, limit
        )
        return [dict(row) for row in rows]

async def count_due_words(user_id: int) -> int:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            """
            SELECT COUNT(*) FROM user_vocabulary
            WHERE user_id = $1 AND next_repetition_date <= NOW()
            """,
            user_id
        )
        return result or 0

async def upsert_vocabulary_word(user_id: int, word_data: Dict[str, Any]) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_vocabulary (
                user_id, word_id, english, russian, transcription, picture_url,
                sound_url, translate_id, repetitions, ease_factor, interval_hours,
                next_repetition_date, updated_at
            ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
            ON CONFLICT (user_id, english) DO UPDATE SET
                russian = EXCLUDED.russian,
                transcription = EXCLUDED.transcription,
                picture_url = EXCLUDED.picture_url,
                sound_url = EXCLUDED.sound_url,
                translate_id = EXCLUDED.translate_id,
                updated_at = NOW()
            """,
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
            word_data.get('next_repetition_date', datetime.now())
        )

async def bulk_upsert_vocabulary(user_id: int, words: List[Dict[str, Any]]) -> int:
    pool = await get_pool()
    count = 0
    async with pool.acquire() as conn:
        async with conn.transaction():
            for word in words:
                await conn.execute(
                    """
                    INSERT INTO user_vocabulary (
                        user_id, word_id, english, russian, transcription, picture_url,
                        sound_url, translate_id, repetitions, ease_factor, interval_hours,
                        next_repetition_date, updated_at
                    ) VALUES ($1, $2, $3, $4, $5, $6, $7, $8, $9, $10, $11, $12, NOW())
                    ON CONFLICT (user_id, english) DO UPDATE SET
                        russian = EXCLUDED.russian,
                        transcription = EXCLUDED.transcription,
                        picture_url = EXCLUDED.picture_url,
                        sound_url = EXCLUDED.sound_url,
                        translate_id = EXCLUDED.translate_id,
                        updated_at = NOW()
                    """,
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
                    word.get('next_repetition_date', datetime.now())
                )
                count += 1
    return count

async def update_word_after_training(user_id: int, english: str, correct: bool) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT repetitions, ease_factor, interval_hours
            FROM user_vocabulary
            WHERE user_id = $1 AND english = $2
            """,
            user_id, english
        )
        
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
        next_rep_date = datetime.fromtimestamp(next_rep)
        
        await conn.execute(
            """
            UPDATE user_vocabulary
            SET repetitions = $3, ease_factor = $4, interval_hours = $5,
                next_repetition_date = $6, updated_at = NOW()
            WHERE user_id = $1 AND english = $2
            """,
            user_id, english, repetitions, ease_factor, interval_hours, next_rep_date
        )

async def get_word_status(user_id: int, search_term: str) -> List[Dict[str, Any]]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        rows = await conn.fetch(
            """
            SELECT english, russian, repetitions, ease_factor, interval_hours, next_repetition_date
            FROM user_vocabulary
            WHERE user_id = $1 AND (LOWER(english) LIKE $2 OR LOWER(russian) LIKE $2)
            LIMIT 5
            """,
            user_id, f"%{search_term.lower()}%"
        )
        return [dict(row) for row in rows]

async def get_vocabulary_page(user_id: int, offset: int, limit: int, sort_by: str = 'alpha', due_only: bool = False) -> tuple:
    pool = await get_pool()
    async with pool.acquire() as conn:
        where_clause = "WHERE user_id = $1"
        if due_only:
            where_clause += " AND next_repetition_date <= NOW()"
        
        if sort_by == 'alpha':
            order_clause = "ORDER BY english ASC"
        elif sort_by == 'date':
            order_clause = "ORDER BY next_repetition_date ASC"
        else:
            order_clause = "ORDER BY english ASC"
        
        count = await conn.fetchval(
            f"SELECT COUNT(*) FROM user_vocabulary {where_clause}",
            user_id
        )
        
        rows = await conn.fetch(
            f"""
            SELECT english, russian, next_repetition_date
            FROM user_vocabulary
            {where_clause}
            {order_clause}
            OFFSET $2 LIMIT $3
            """,
            user_id, offset, limit
        )
        
        return [dict(row) for row in rows], count or 0

async def save_user_cookies(user_id: int, cookies: str) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO user_cookies (user_id, cookies, updated_at)
            VALUES ($1, $2, NOW())
            ON CONFLICT (user_id) DO UPDATE SET cookies = $2, updated_at = NOW()
            """,
            user_id, cookies
        )

async def get_user_cookies(user_id: int) -> Optional[str]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        result = await conn.fetchval(
            "SELECT cookies FROM user_cookies WHERE user_id = $1",
            user_id
        )
        return result

async def save_training_results(user_id: int, training_type: str, results: Dict) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            """
            INSERT INTO training_results (user_id, training_type, results)
            VALUES ($1, $2, $3)
            """,
            user_id, training_type, json.dumps(results)
        )

async def get_pending_training_results(user_id: int, training_type: str) -> Optional[Dict]:
    pool = await get_pool()
    async with pool.acquire() as conn:
        row = await conn.fetchrow(
            """
            SELECT id, results FROM training_results
            WHERE user_id = $1 AND training_type = $2
            ORDER BY created_at DESC LIMIT 1
            """,
            user_id, training_type
        )
        if row:
            return {'id': row['id'], 'results': json.loads(row['results'])}
        return None

async def delete_training_results(result_id: int) -> None:
    pool = await get_pool()
    async with pool.acquire() as conn:
        await conn.execute(
            "DELETE FROM training_results WHERE id = $1",
            result_id
        )
