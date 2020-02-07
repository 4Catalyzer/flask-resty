import datetime as dt

from .models import Author, Book, db

if __name__ == "__main__":
    print("Initializing database with dummy data...")
    db.create_all()

    fred = Author(name="Fred Brooks")
    db.session.add(fred)
    db.session.add(
        Book(
            title="The Mythical Man-Month",
            author=fred,
            published_at=dt.datetime(1995, 8, 12),
        )
    )

    don = Author(name="Don Norman")
    db.session.add(don)
    db.session.add(
        Book(
            title="The Design of Everyday Things",
            author=don,
            published_at=dt.datetime(2013, 11, 5),
        )
    )
    db.session.add(
        Book(
            title="Living With Complexity",
            author=don,
            published_at=dt.datetime(2010, 10, 29),
        )
    )

    db.session.commit()
    print("Done.")
