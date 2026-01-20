# Feature: LTM Threads & Entity Recognition

## 1. Overview
**Branch**: `feat/ltm-threads-entities`

This feature enhances the LTM system by adding "Thread" capabilities (via metadata) and context-aware "Entity Recognition". It enables the storage of arbitrary metadata for conversations (e.g., tags, context) and automatically extracts and stores entities (people, projects, concepts) from messages to improve retrieval accuracy.

## 2. Requirements
- [ ] **Schema Update**:
    - [ ] Add `metadata` (JSON) column to `Chat` table.
    - [ ] Add `entities` (JSON) column to `Message` table.
- [ ] **Entity Recognition**:
    - [ ] Implement a service (using the configured LLM) to extract entities from new user messages.
    - [ ] Store extracted entities in the `Message` table.
- [ ] **API Updates**:
    - [ ] Update `POST /api/conversations` to accept `metadata`.
    - [ ] Update `PUT /api/conversations/{id}` to accept `metadata` updates.
    - [ ] Update `GET /api/conversations/{id}` to include `metadata` and message `entities`.

## 3. Technical Implementation
- **Database**:
    - Use `sqlalchemy.types.JSON` (or `String` containing JSON if SQLite JSON1 extension issues arise, but JSON is preferred).
- **Services**:
    - `gantry/services/entity_extractor.py`: Function `extract_entities(text: str) -> dict`.
- **Integration**:
    - Call `extract_entities` in `chat.py` (async) when saving user messages.
    - Call `extract_entities` in `chat.py` (async) when saving AI messages (optional, maybe just user?). Requirement says "interaction between me and the user", usually user entities are key. Let's do both or just User for now to save latency. *Decision: User messages only for now to reduce latency.*

## 4. Verification Plan
**Automated Tests**:
- [ ] `tests/test_entity_extractor.py`: Mock LLM response and verify extraction logic.
- [ ] `tests/test_ltm_metadata.py`: Verify API CRUD with metadata.

**Manual Verification**:
- [ ] Start app.
- [ ] Send message "Remember usage for Project Nebula".
- [ ] Verify via API that message has entities `{"Project": "Nebula"}`.
- [ ] Update conversation metadata via API.
