import asyncio
import logging
from sqlalchemy import text

from shared.database import init_db, engine, AsyncSessionLocal
import seeds.seed_zones as sz
import seeds.seed_riders as sr
import seeds.seed_policies as sp
import seeds.seed_baselines as sb

# Import models to register them with SQLAlchemy Base
import rider_service.models
import policy_service.models
import trigger_service.models
import claims_service.models
import manual_claims.models

# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("setup")

async def run_setup():
    logger.info("⏳ Waiting for database to be ready...")
    # Attempt to connect to ensure postgres is actually responding
    max_retries = 10
    for i in range(max_retries):
        try:
            async with engine.connect() as conn:
                await conn.execute(text("SELECT 1"))
                logger.info("✅ Database is ready.")
                break
        except Exception:
            logger.info(f"⌛ Database not ready (retry {i+1}/{max_retries})...")
            await asyncio.sleep(2)
    else:
        logger.error("❌ Database connection failed after multiple retries.")
        return

    # Initialize tables
    logger.info("🏗️ Initializing tables...")
    await init_db()
    logger.info("✅ Tables created.")

    # 🚨 ONLY seed mandatory operational data (Zones)
    # Registration will FAIL if there are no zones!
    logger.info("🌱 Seeding zones (Mandatory)...")
    await sz.seed()
    
    # Optional: Skip these if the user wants "REAL" only data
    # logger.info("🌱 Seeding demo riders...")
    # await sr.seed()
    
    # logger.info("🌱 Seeding demo policies...")
    # await sp.seed()
    
    # logger.info("🌱 Seeding demo baselines...")
    # await sb.seed()
    
    logger.info("✨ Operational setup completed successfully. Waiting for registrations...")

if __name__ == "__main__":
    asyncio.run(run_setup())
