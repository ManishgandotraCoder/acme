from collections.abc import Iterator

from sqlalchemy import DDL, Engine, create_engine, event
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker


class Base(DeclarativeBase):
    pass


# Extensions the schema relies on (pg_trgm: indexed substring search). Created before any
# table by create_all (tests/dev); the initial Alembic migration does the same in production.
REQUIRED_EXTENSIONS = ("pg_trgm",)
for _extension in REQUIRED_EXTENSIONS:
    event.listen(
        Base.metadata, "before_create", DDL(f"CREATE EXTENSION IF NOT EXISTS {_extension}")
    )


def make_engine(database_url: str) -> Engine:
    # pool_pre_ping: transparently replace connections dropped by the server or a proxy.
    return create_engine(database_url, pool_pre_ping=True)


def make_session_factory(engine: Engine) -> sessionmaker[Session]:
    return sessionmaker(bind=engine, expire_on_commit=False)


def create_schema(engine: Engine) -> None:
    """Create all tables registered on ``Base`` (tests/dev only; production uses Alembic)."""
    Base.metadata.create_all(engine)


def session_scope(factory: sessionmaker[Session]) -> Iterator[Session]:
    with factory() as session:
        yield session
