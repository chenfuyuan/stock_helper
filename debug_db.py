import asyncio
from sqlalchemy import text
from src.shared.infrastructure.db.session import AsyncSessionLocal


async def check_stock():
    async with AsyncSessionLocal() as session:
        result = await session.execute(
            text("SELECT * FROM stock_info WHERE third_code = '000001.SZ'")
        )
        row = result.first()
        if row:
            print(f"Found stock: {row}")
        else:
            print("Stock 000001.SZ NOT FOUND in stock_info table")

        # Check count
        result = await session.execute(text("SELECT count(*) FROM stock_info"))
        count = result.scalar()
        print(f"Total stocks in DB: {count}")


if __name__ == "__main__":
    asyncio.run(check_stock())
