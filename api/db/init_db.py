from api.db.base import Base
from api.db.session import engine
from api.db import models


def init_db() -> None:
    Base.metadata.create_all(bind=engine)


if __name__ == "__main__":
    init_db()
