from nebulus_gantry.database import db_session, User


def list_users():
    with db_session() as db:
        users = db.query(User).all()
        print(f"Total Users: {len(users)}")
        for u in users:
            print(f"ID: {u.id} | Email: {u.email} | Username: {u.username}")


if __name__ == "__main__":
    list_users()
