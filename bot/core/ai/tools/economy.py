from langchain_core.tools import tool
from sqlalchemy import select
from bot.core.database import AsyncSessionLocal
from bot.core.models import BankAccount, Transaction, User

async def get_or_create_account(session, user_id: int, lock: bool = False):
    """
    Fetches or creates a bank account.
    If lock=True, uses SELECT ... FOR UPDATE for ACID transaction safety.
    """
    stmt = select(BankAccount).where(BankAccount.user_id == user_id)
    if lock:
        stmt = stmt.with_for_update()

    result = await session.execute(stmt)
    account = result.scalar_one_or_none()

    if not account:
        # Create flow (usually no lock needed here as INSERT is atomic, but concurrency is rare here)
        # Ensure user exists in users table first
        user_result = await session.execute(select(User).where(User.discord_id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            user = User(discord_id=user_id)
            session.add(user)
            await session.flush()

        account = BankAccount(user_id=user_id, balance=0, currency_type="NC")
        session.add(account)
        await session.flush()
        # Refetch with lock if needed (unlikely for new account)

    return account

@tool
async def get_user_balance(user_id: int) -> str:
    """
    Get the balance of a user.
    """
    async with AsyncSessionLocal() as session:
        account = await get_or_create_account(session, user_id, lock=False)
        return f"{account.balance} {account.currency_type}"

@tool
async def transfer_money(sender_id: int, receiver_id: int, amount: int) -> str:
    """
    Transfer money from one user to another.
    """
    # 1. Sanity Checks
    if not isinstance(amount, int) or amount <= 0:
        return "Transaction Rejected: Amount must be a positive integer."

    if sender_id == receiver_id:
        return "Transaction Rejected: Self-transfer prohibited."

    async with AsyncSessionLocal() as session:
        async with session.begin(): # ACID Transaction Start

            # 2. Row Locking (Prevention of Double Spending)
            # We fetch both accounts with FOR UPDATE

            # Sender
            sender_account = await get_or_create_account(session, sender_id, lock=True)

            # Liquidity Check
            if sender_account.balance < amount:
                return f"Transaction Rejected: Insufficient liquidity. Balance: {sender_account.balance} NC."

            # Receiver
            receiver_account = await get_or_create_account(session, receiver_id, lock=True)

            # 3. Execution
            sender_account.balance -= amount
            receiver_account.balance += amount

            # 4. Audit Trail
            transaction = Transaction(
                sender_id=sender_id,
                receiver_id=receiver_id,
                amount=amount,
                reason=f"Wire Transfer from {sender_id}"
            )
            session.add(transaction)

            # Commit happens automatically here.

    return f"Transaction Confirmed: {amount} NC transferred to {receiver_id}. Ledger updated."
