import asyncio
import sys
import argparse
from loguru import logger
from src.shared.config import settings
from src.modules.data_engineering.presentation.jobs.sync_scheduler import (
    sync_incremental_finance_job,
    sync_daily_data_job
)

async def main():
    parser = argparse.ArgumentParser(description="Stock Helper CLI")
    subparsers = parser.add_subparsers(dest="command", help="Available commands")
    
    # Sync Finance Command
    sync_finance_parser = subparsers.add_parser("sync_finance", help="Sync incremental finance data")
    sync_finance_parser.add_argument("--date", type=str, help="Specific date to sync (YYYYMMDD), defaults to today")

    # Sync Daily Bar Command
    sync_daily_parser = subparsers.add_parser("sync_daily", help="Sync incremental daily bar data")
    sync_daily_parser.add_argument("--date", type=str, help="Specific date to sync (YYYYMMDD), defaults to today")

    args = parser.parse_args()

    if args.command == "sync_finance":
        logger.info(f"Triggering sync_finance manually for date: {args.date or 'today'}")
        await sync_incremental_finance_job(target_date=args.date)
    elif args.command == "sync_daily":
        logger.info(f"Triggering sync_daily manually for date: {args.date or 'today'}")
        await sync_daily_data_job(target_date=args.date)
    else:
        parser.print_help()

if __name__ == "__main__":
    if sys.platform == 'win32':
        asyncio.set_event_loop_policy(asyncio.WindowsSelectorEventLoopPolicy())
        
    asyncio.run(main())
