"""Quick script to check voice sessions in the database."""
import asyncio
import asyncpg
import ssl

async def check():
    # Disable SSL for internal network connection
    pool = await asyncpg.create_pool(
        'postgresql://mycosoft:REDACTED_DB_PASSWORD@192.168.0.189:5432/mindex',
        ssl=False
    )
    async with pool.acquire() as conn:
        rows = await conn.fetch('SELECT session_id, mode, created_at FROM memory.voice_sessions ORDER BY created_at DESC LIMIT 5')
        if rows:
            print("=== Voice Sessions ===")
            for row in rows:
                print(f'{row["session_id"][:8]}... | {row["mode"]} | {row["created_at"]}')
        else:
            print('No sessions found')
        
        turns = await conn.fetch("SELECT turn_id, speaker, LEFT(text, 50) as text_preview, created_at FROM memory.voice_turns ORDER BY created_at DESC LIMIT 5")
        if turns:
            print('\n=== Voice Turns ===')
            for t in turns:
                print(f'{t["speaker"]}: {t["text_preview"]}...')
        else:
            print('No turns found')
    await pool.close()

if __name__ == "__main__":
    asyncio.run(check())
