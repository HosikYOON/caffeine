import asyncio
import sys
sys.path.append('/app')

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker
from app.db.database import init_db
from app.db.model.transaction import Anomaly, Transaction

async def find_large_tx():
    engine = await init_db()
    async_session = async_sessionmaker(bind=engine, class_=AsyncSession, expire_on_commit=False)
    
    async with async_session() as db:
        print("--- SEARCHING FOR 100M+ TRANSACTIONS ---")
        # Find transactions > 90,000,000
        result = await db.execute(select(Transaction).where(Transaction.amount >= 90000000).order_by(Transaction.transaction_time.desc()))
        txs = result.scalars().all()
        
        if not txs:
            print("No transactions found over 90,000,000")
        else:
            print(f"Found {len(txs)} large transactions:")
            for tx in txs:
                # Check anomaly
                anom_res = await db.execute(select(Anomaly).where(Anomaly.transaction_id == tx.id))
                anom = anom_res.scalar_one_or_none()
                
                print(f"ID: {tx.id}")
                print(f"Amount: {tx.amount}")
                print(f"Date: {tx.transaction_time}")
                print(f"Merchant: {tx.merchant_name}")
                if anom:
                    print(f"[ANOMALY FOUND] Status: {anom.is_resolved}, Reason: {anom.reason}, Severity: {anom.severity}")
                else:
                    print("[NO ANOMALY RECORD]")
                print("-" * 30)

if __name__ == "__main__":
    asyncio.run(find_large_tx())
