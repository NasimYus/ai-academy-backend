from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models.ticket import Ticket


async def list_tickets(db: AsyncSession, course_id: int) -> list[Ticket]:
    result = await db.execute(
        select(Ticket)
        .where(Ticket.course_id == course_id)
        .order_by(Ticket.order.asc(), Ticket.id.asc())
    )
    return list(result.scalars().all())


async def add_ticket(db: AsyncSession, course_id: int, data: dict) -> Ticket:
    next_order = await db.scalar(
        select(func.coalesce(func.max(Ticket.order), -1) + 1).where(Ticket.course_id == course_id)
    )
    ticket = Ticket(course_id=course_id, order=next_order or 0, **data)
    db.add(ticket)
    await db.commit()
    await db.refresh(ticket)
    return ticket


async def get_ticket(db: AsyncSession, ticket_id: int) -> Ticket | None:
    return await db.get(Ticket, ticket_id)


async def delete_ticket(db: AsyncSession, ticket: Ticket) -> None:
    await db.delete(ticket)
    await db.commit()
