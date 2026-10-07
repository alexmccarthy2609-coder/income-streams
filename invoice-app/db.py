"""Database setup and the tables (called "models") the app stores data in.

We use SQLite: the whole database is a single file (invoices.db) so there is
nothing extra to install. Later, when the app goes online, we can switch to
Postgres by changing DATABASE_URL — the rest of the code stays the same.
"""

import os
from datetime import date, datetime

from sqlalchemy import ForeignKey, String, Text, create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Mapped, Session, mapped_column, relationship

def database_url() -> str:
    url = os.environ.get("DATABASE_URL", "sqlite:///invoices.db")
    # Hosting services like Render give a "postgres://" or "postgresql://" address;
    # SQLAlchemy needs to be told to use the psycopg driver for it.
    for prefix in ("postgres://", "postgresql://"):
        if url.startswith(prefix):
            return "postgresql+psycopg://" + url[len(prefix):]
    return url


DATABASE_URL = database_url()
# pool_pre_ping checks a database connection still works before using it
# (online databases close idle connections).
engine = create_engine(DATABASE_URL, pool_pre_ping=True)


class Base(DeclarativeBase):
    pass


class User(Base):
    __tablename__ = "users"

    id: Mapped[int] = mapped_column(primary_key=True)
    email: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    password_hash: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    # Business details, used to pre-fill every new invoice.
    business_name: Mapped[str] = mapped_column(String(200), default="")
    business_details: Mapped[str] = mapped_column(Text, default="")
    default_currency: Mapped[str] = mapped_column(String(3), default="GBP")
    default_tax_rate: Mapped[float] = mapped_column(default=0)
    default_notes: Mapped[str] = mapped_column(Text, default="")
    payment_terms_days: Mapped[int] = mapped_column(default=14)

    # Plan and billing. Stripe handles the actual payments; we just remember the result.
    plan: Mapped[str] = mapped_column(String(10), default="free")  # "free" or "pro"
    stripe_customer_id: Mapped[str | None] = mapped_column(String(100), index=True, default=None)
    stripe_subscription_id: Mapped[str | None] = mapped_column(String(100), default=None)
    subscription_status: Mapped[str | None] = mapped_column(String(30), default=None)
    # How many invoices were created in which month (e.g. "2026-10"), for the free plan limit.
    usage_month: Mapped[str] = mapped_column(String(7), default="")
    usage_count: Mapped[int] = mapped_column(default=0)

    clients: Mapped[list["Client"]] = relationship(back_populates="user", cascade="all, delete-orphan")
    invoices: Mapped[list["Invoice"]] = relationship(back_populates="user", cascade="all, delete-orphan")


class Client(Base):
    __tablename__ = "clients"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    name: Mapped[str] = mapped_column(String(200))
    details: Mapped[str] = mapped_column(Text, default="")

    user: Mapped[User] = relationship(back_populates="clients")


class Invoice(Base):
    __tablename__ = "invoices"

    id: Mapped[int] = mapped_column(primary_key=True)
    user_id: Mapped[int] = mapped_column(ForeignKey("users.id"), index=True)
    client_id: Mapped[int | None] = mapped_column(ForeignKey("clients.id", ondelete="SET NULL"))
    created_at: Mapped[datetime] = mapped_column(default=datetime.now)

    number: Mapped[str] = mapped_column(String(50))
    invoice_date: Mapped[date]
    due_date: Mapped[date]
    currency: Mapped[str] = mapped_column(String(3))
    tax_rate: Mapped[float] = mapped_column(default=0)
    notes: Mapped[str] = mapped_column(Text, default="")
    status: Mapped[str] = mapped_column(String(20), default="unpaid")  # "unpaid" or "paid"
    paid_date: Mapped[date | None] = mapped_column(default=None)

    # A copy of the names/addresses at the time the invoice was made, so
    # editing a client later doesn't change invoices already sent.
    business_name: Mapped[str] = mapped_column(String(200))
    business_details: Mapped[str] = mapped_column(Text, default="")
    client_name: Mapped[str] = mapped_column(String(200))
    client_details: Mapped[str] = mapped_column(Text, default="")

    user: Mapped[User] = relationship(back_populates="invoices")
    items: Mapped[list["InvoiceItem"]] = relationship(
        back_populates="invoice", cascade="all, delete-orphan", order_by="InvoiceItem.position"
    )

    @property
    def is_overdue(self) -> bool:
        return self.status != "paid" and self.due_date < date.today()

    @property
    def days_overdue(self) -> int:
        return (date.today() - self.due_date).days if self.is_overdue else 0

    @property
    def display_status(self) -> str:
        """What to show the user: paid, overdue or unpaid."""
        return "overdue" if self.is_overdue else self.status

    @property
    def subtotal(self) -> float:
        return round(sum(i.amount for i in self.items), 2)

    @property
    def tax(self) -> float:
        return round(self.subtotal * self.tax_rate / 100, 2)

    @property
    def total(self) -> float:
        return round(self.subtotal + self.tax, 2)


class InvoiceItem(Base):
    __tablename__ = "invoice_items"

    id: Mapped[int] = mapped_column(primary_key=True)
    invoice_id: Mapped[int] = mapped_column(ForeignKey("invoices.id"), index=True)
    position: Mapped[int] = mapped_column(default=0)
    description: Mapped[str] = mapped_column(Text)
    quantity: Mapped[float]
    unit_price: Mapped[float]

    invoice: Mapped[Invoice] = relationship(back_populates="items")

    @property
    def amount(self) -> float:
        return round(self.quantity * self.unit_price, 2)


# Columns added after the first version. If your invoices.db was made by an
# older version of the app, they are added automatically when it starts.
NEW_COLUMNS = {
    "invoices": {"paid_date": "DATE"},
    "users": {
        "plan": "VARCHAR(10) NOT NULL DEFAULT 'free'",
        "stripe_customer_id": "VARCHAR(100)",
        "stripe_subscription_id": "VARCHAR(100)",
        "subscription_status": "VARCHAR(30)",
        "usage_month": "VARCHAR(7) NOT NULL DEFAULT ''",
        "usage_count": "INTEGER NOT NULL DEFAULT 0",
    },
}


def create_tables():
    Base.metadata.create_all(engine)
    existing = inspect(engine)
    with engine.begin() as conn:
        for table, columns in NEW_COLUMNS.items():
            if not existing.has_table(table):
                continue
            have = {c["name"] for c in existing.get_columns(table)}
            for name, sql_type in columns.items():
                if name not in have:
                    conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {sql_type}"))


def get_db():
    """Gives each web request its own database session, closed afterwards."""
    with Session(engine) as session:
        yield session
