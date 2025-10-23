import asyncio
from app.db import SessionLocal
from app import models

async def main():
    async with SessionLocal() as db:
        db.add_all([
            models.Deal(name="AcmeSoft", industry="software", price=120.0, ebitda=10.0, currency="USD", org_id=1),
            models.Deal(name="WidgetCo", industry="manufacturing", price=60.0, ebitda=10.0, currency="USD", org_id=1),
        ])
        await db.commit()

if __name__ == "__main__":
    asyncio.run(main())
