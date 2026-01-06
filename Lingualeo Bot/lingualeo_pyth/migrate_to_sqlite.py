import asyncio
import os
import sys

os.environ["DATABASE_URL"] = os.environ.get("DATABASE_URL", "")

async def migrate():
    if not os.environ.get("DATABASE_URL", "").strip():
        print("DATABASE_URL not set. Nothing to migrate.")
        return
    
    print("Importing PostgreSQL module...")
    import db as pg_db
    
    print("Importing SQLite module...")
    import db_sqlite as sqlite_db
    
    print("Initializing SQLite database...")
    await sqlite_db.init_db()
    
    print("Getting PostgreSQL pool...")
    pool = await pg_db.get_pool()
    
    async with pool.acquire() as conn:
        print("Fetching all users from PostgreSQL...")
        user_ids = await conn.fetch("SELECT DISTINCT user_id FROM user_vocabulary")
        
        for user_row in user_ids:
            user_id = user_row['user_id']
            print(f"\nMigrating user {user_id}...")
            
            words = await pg_db.get_user_vocabulary(user_id)
            print(f"  Found {len(words)} words")
            
            if words:
                count = await sqlite_db.bulk_upsert_vocabulary(user_id, words)
                print(f"  Migrated {count} words to SQLite")
            
            cookies = await pg_db.get_user_cookies(user_id)
            if cookies:
                await sqlite_db.save_user_cookies(user_id, cookies)
                print(f"  Migrated cookies")
        
        print("\nMigrating training results...")
        training_users = await conn.fetch("SELECT DISTINCT user_id FROM training_results")
        for user_row in training_users:
            user_id = user_row['user_id']
            results = await pg_db.get_training_results(user_id)
            if results:
                await sqlite_db.save_training_results(user_id, results)
                print(f"  Migrated training results for user {user_id}")
    
    await pg_db.close_pool()
    print("\nMigration complete!")
    print(f"SQLite database saved to: {sqlite_db.DB_PATH}")

if __name__ == "__main__":
    asyncio.run(migrate())
