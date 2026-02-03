from nebulus_gantry.database import db_session, User, Chat, Message


def clear_users():
    with db_session() as db:
        print("Clearing users...")
        db.query(Message).delete()
        db.query(Chat).delete()
        db.query(User).delete()
        print("Users cleared.")


if __name__ == "__main__":
    clear_users()
