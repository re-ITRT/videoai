import asyncio
from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
import os

async def main():
    db_url = os.environ.get("DATABASE_URL", "postgresql+asyncpg://postgres:postgres@localhost:5432/video_ai")
    engine = create_async_engine(db_url)
    async with engine.begin() as conn:
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS users (
                id SERIAL PRIMARY KEY,
                username VARCHAR(32) UNIQUE NOT NULL,
                hashed_password VARCHAR(128) NOT NULL,
                nickname VARCHAR(64),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS products (
                id SERIAL PRIMARY KEY,
                name VARCHAR(255) NOT NULL,
                description TEXT,
                category VARCHAR(100),
                brand VARCHAR(100),
                price NUMERIC(10,2),
                user_id INTEGER REFERENCES users(id),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS materials (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                product_id INTEGER REFERENCES products(id),
                material_type VARCHAR(20) DEFAULT 'product',
                input_type VARCHAR(10) NOT NULL,
                image_url TEXT,
                video_url TEXT,
                text_content TEXT,
                embedding vector(1024),
                tags TEXT[],
                source VARCHAR(20) DEFAULT 'upload',
                category VARCHAR(100),
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS material_slices (
                id SERIAL PRIMARY KEY,
                material_id INTEGER REFERENCES materials(id) ON DELETE CASCADE,
                slice_type VARCHAR(20) DEFAULT 'video_scene',
                scene_id INTEGER,
                time_range VARCHAR(50),
                description TEXT,
                script TEXT,
                image_url TEXT,
                embedding vector(1024),
                tags TEXT[],
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS scripts (
                id SERIAL PRIMARY KEY,
                user_id INTEGER REFERENCES users(id),
                product_id INTEGER REFERENCES products(id),
                mode VARCHAR(20) DEFAULT 'auto',
                strategy VARCHAR(100),
                factors JSONB,
                video_style VARCHAR(100),
                total_duration FLOAT DEFAULT 0,
                scenes JSONB DEFAULT '[]',
                reference_video_id INTEGER,
                template_id INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS video_tasks (
                id SERIAL PRIMARY KEY,
                script_id INTEGER REFERENCES scripts(id),
                user_id INTEGER REFERENCES users(id),
                state VARCHAR(30) DEFAULT 'created',
                current_step INTEGER DEFAULT 0,
                total_steps INTEGER DEFAULT 8,
                aspect_ratio VARCHAR(10) DEFAULT '9:16',
                auto_mode BOOLEAN DEFAULT TRUE,
                video_url TEXT,
                duration FLOAT,
                error_message TEXT,
                retry_count INTEGER DEFAULT 0,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        await conn.execute(text("""
            CREATE TABLE IF NOT EXISTS task_logs (
                id SERIAL PRIMARY KEY,
                task_id INTEGER REFERENCES video_tasks(id),
                step VARCHAR(50),
                model_name VARCHAR(100),
                tokens_used INTEGER DEFAULT 0,
                duration_ms INTEGER DEFAULT 0,
                detail JSONB,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        # 索引
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_materials_user ON materials(user_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_materials_product ON materials(product_id)"))
        await conn.execute(text("CREATE INDEX IF NOT EXISTS idx_slices_material ON material_slices(material_id)"))
    print('DB initialized OK')

asyncio.run(main())
