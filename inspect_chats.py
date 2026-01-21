from nebulus_gantry.database import db_session, Chat, User


def inspect_chats():
    with db_session() as db:
        chats = db.query(Chat).all()
        print(f"Total Chats: {len(chats)}")
        for c in chats:
            u = db.query(User).filter(User.id == c.user_id).first()
            u_email = u.email if u else "UNKNOWN"
            print(f"Chat {c.id} | Title: {c.title} | UserID: {c.user_id} ({u_email})")


if __name__ == "__main__":
    inspect_chats()
