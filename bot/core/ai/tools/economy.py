from langchain_core.tools import tool
from sqlalchemy import select
from bot.core.database import AsyncSessionLocal
from bot.core.models import BankAccount, Transaction, User

async def get_or_create_account(session, user_id: int):
    result = await session.execute(select(BankAccount).where(BankAccount.user_id == user_id))
    account = result.scalar_one_or_none()

    if not account:
        # Ensure user exists in users table first
        user_result = await session.execute(select(User).where(User.discord_id == user_id))
        user = user_result.scalar_one_or_none()
        if not user:
            # Create user if not exists
            user = User(discord_id=user_id)
            session.add(user)
            await session.flush()

        account = BankAccount(user_id=user_id, balance=0, currency_type="NC")
        session.add(account)
        await session.flush()

    return account

@tool
async def get_user_balance(user_id: int) -> str:
    """
    Get the balance of a user.
    """
    async with AsyncSessionLocal() as session:
        account = await get_or_create_account(session, user_id)
        return f"{account.balance} {account.currency_type}"

@tool
async def transfer_money(sender_id: int, receiver_id: int, amount: int) -> str:
    """
    Transfer money from one user to another.
    """
    if amount <= 0:
        return "Amount must be positive."

    if sender_id == receiver_id:
        return "You cannot pay yourself."

    async with AsyncSessionLocal() as session:
        async with session.begin():
            # Sender
            sender_account = await get_or_create_account(session, sender_id)
            if sender_account.balance < amount:
                return f"Insufficient funds. You have {sender_account.balance} NC."

            # Receiver
            receiver_account = await get_or_create_account(session, receiver_id)

            # Transfer
            sender_account.balance -= amount
            receiver_account.balance += amount

            # Record transaction
            transaction = Transaction(
                sender_id=sender_id,
                receiver_id=receiver_id,
                amount=amount,
                reason=f"Transfer from {sender_id}"
            )
            session.add(transaction)

            # session.begin() commits automatically on exit

    return f"Successfully transferred {amount} NC to user {receiver_id}."
