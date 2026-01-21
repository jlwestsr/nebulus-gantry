from nebulus_gantry.database import Chat, Message, User


def test_create_conversation_with_metadata(client, db):
    # Seed User
    user = User(id=1, username="testuser", email="test@example.com")
    db.add(user)
    db.commit()

    metadata = {"project": "Nebula", "priority": "High"}
    response = client.post(
        "/api/conversations",
        json={"topic": "Metadata Chat", "user_id": 1, "metadata": metadata}
    )
    if response.status_code != 200:
        print(f"Create failed: {response.text}")
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"] == metadata

    chat = db.query(Chat).filter(Chat.id == data["id"]).first()
    assert chat.metadata_json == metadata


def test_update_conversation_metadata(client, db):
    # Setup
    chat_id = "test-uuid-meta-update"
    chat = Chat(id=chat_id, user_id=1, title="Original", metadata_json={"tag": "v1"})
    db.add(chat)
    db.commit()

    new_metadata = {"tag": "v2", "status": "active"}
    response = client.put(
        f"/api/conversations/{chat_id}",
        json={"topic": "Updated", "metadata": new_metadata}
    )
    assert response.status_code == 200
    data = response.json()
    assert data["metadata"] == new_metadata

    db.expire_all()
    chat = db.query(Chat).filter(Chat.id == chat_id).first()
    assert chat.metadata_json == new_metadata


def test_get_conversation_entities(client, db):
    # Setup
    chat_id = "test-uuid-entities"
    chat = Chat(id=chat_id, user_id=1, title="Entity Chat")
    entities = {"Person": ["Alice"], "Tool": ["Git"]}
    msg = Message(chat_id=chat_id, author="user",
                  content="Hi Alice, use Git", entities=entities)

    db.add(chat)
    db.add(msg)
    db.commit()

    response = client.get(f"/api/conversations/{chat_id}")
    assert response.status_code == 200
    data = response.json()
    messages = data["messages"]
    assert len(messages) == 1
    assert messages[0]["entities"] == entities
