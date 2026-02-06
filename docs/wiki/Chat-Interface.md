# Chat Interface

Guide to using Gantry's conversational UI, including keyboard shortcuts, conversation management, search, and advanced features.

---

## Overview

Gantry provides a **Claude.AI-inspired chat interface** with:

- ✨ **Dark-themed UI** - Professional, distraction-free design
- ⚡ **Real-time streaming** - See responses as they're generated
- 📝 **Markdown rendering** - Code blocks, tables, lists, formatting
- 🔍 **Search** - Find messages across all conversations (Ctrl+K)
- 📌 **Pin conversations** - Keep important chats at the top
- 📥 **Export** - Save conversations as JSON or PDF
- 📱 **Mobile responsive** - Works on desktop, tablet, and phone

---

## Getting Started

### Creating Your First Conversation

1. **Click** the **+ New Chat** button in the sidebar
2. **Type** your message in the input box at the bottom
3. **Press Enter** or click the send button
4. Watch the AI respond in real-time with **streaming text**

### Conversation Basics

**Send a message:**

- Type in the input box
- Press **Enter** to send (Shift+Enter for newline)
- Or click the **send icon** (→)

**View response:**

- Responses stream in real-time (typewriter effect)
- Markdown is rendered automatically
- Code blocks have syntax highlighting

**Continue conversation:**

- Simply type your next message
- Context from previous messages is remembered
- No need to re-explain what you're discussing

---

## Interface Layout

```text
┌─────────────────────────────────────────────────────────┐
│  [≡] Gantry                    [Search] [👤 Profile]    │ ← Header
├──────────────┬──────────────────────────────────────────┤
│              │  Conversation: "Project Planning"        │
│  Sidebar     │  ─────────────────────────────────────  │
│              │  👤 User                                 │
│  📌 Pinned   │  Can you help me plan...                │
│  • Meeting   │                                          │
│              │  🤖 Assistant                            │
│  📂 Recent   │  I'd be happy to help! Let's break...   │ ← Chat Area
│  • Project   │                                          │
│  • Research  │  👤 User                                 │
│  • Code      │  What about timeline?                   │
│              │                                          │
│  + New Chat  │  🤖 Assistant [streaming...]            │
│              │  For the timeline, I suggest...         │
│              │  ─────────────────────────────────────  │
│              │  [Type your message here...        ] [→] │ ← Input
└──────────────┴──────────────────────────────────────────┘
```

### Components

**Header:**

- App logo and menu toggle (mobile)
- Search button (Ctrl+K)
- Profile menu (settings, admin, logout)

**Sidebar:**

- Pinned conversations (stays at top)
- Recent conversations (sorted by update time)
- New chat button
- Collapse toggle (mobile)

**Chat Area:**

- Message history (scrollable)
- User and assistant messages
- Streaming responses
- Markdown rendering

**Input Box:**

- Multi-line text input
- Send button
- Character count (appears when typing)

---

## Keyboard Shortcuts

| Shortcut | Action |
|----------|--------|
| **Ctrl+K** (Cmd+K) | Open search |
| **Enter** | Send message |
| **Shift+Enter** | New line in message |
| **Esc** | Close search / modals |
| **↑** / **↓** | Navigate search results |
| **/** | Focus message input |

---

## Conversation Management

### Create New Conversation

**Click** the **+ New Chat** button in the sidebar.

**Keyboard:** Press **/** to focus the input in current or new conversation.

### Rename Conversation

1. **Hover** over conversation in sidebar
2. **Click** the conversation name
3. **Type** new name
4. **Press Enter** or click outside to save

**Auto-naming:** First message automatically becomes the conversation title (truncated to ~50 chars).

### Pin/Unpin Conversation

1. **Hover** over conversation in sidebar
2. **Click** the 📌 pin icon
3. Pinned conversations move to **Pinned** section at top
4. **Click** again to unpin

**Use case:** Keep important ongoing conversations accessible.

### Delete Conversation

1. **Open** the conversation
2. **Click** the **⋮** menu in chat header
3. **Select** "Delete conversation"
4. **Confirm** deletion

**Warning:** This is permanent and cannot be undone!

### Search Conversations

**Press Ctrl+K** (Cmd+K on Mac) to open the search modal.

**Features:**

- Searches across **all conversations**
- Matches message content and conversation titles
- Shows preview of matching messages
- Jump directly to conversation

**Usage:**

1. Press **Ctrl+K**
2. Type your search query
3. Navigate results with **↑** / **↓**
4. Press **Enter** to open conversation
5. Press **Esc** to close

---

## Message Features

### Markdown Rendering

Gantry renders **GitHub-flavored markdown** in assistant responses:

**Text formatting:**

```markdown
**bold** _italic_ ~~strikethrough~~ `code`
```

**Lists:**

```markdown
- Bullet point
- Another point
  - Nested point

1. Numbered item
2. Another item
```

**Links:**

```markdown
[Link text](https://example.com)
```

**Code blocks:**

````markdown
```python
def hello():
    print("Hello, world!")
```
````

**Tables:**

```markdown
| Column 1 | Column 2 |
|----------|----------|
| Data     | More     |
```

**Blockquotes:**

```markdown
> This is a quote
> spanning multiple lines
```

**Headings:**

```markdown
# Heading 1
## Heading 2
### Heading 3
```

### Code Block Features

**Syntax highlighting:**

- Automatic language detection
- Supports 100+ languages (Python, JavaScript, Java, C++, etc.)

**Copy button:**

- Hover over code block
- Click **copy icon** in top-right
- Code copied to clipboard

**Example:**

```python
def fibonacci(n):
    a, b = 0, 1
    for _ in range(n):
        yield a
        a, b = b, a + b

# Usage
for num in fibonacci(10):
    print(num)
```

### Copy Message

**Copy assistant response:**

1. Hover over message
2. Click **copy icon** (📋)
3. Full message text copied to clipboard

**Copy user message:**

- Same process as assistant messages
- Useful for re-sending or editing prompts

---

## Export Conversations

Export conversations to **JSON** or **PDF** for archival or sharing.

### Export as JSON

1. **Open** conversation
2. **Click** **⋮** menu in header
3. **Select** "Export as JSON"
4. Browser downloads `conversation-{id}.json`

**JSON structure:**

```json
{
  "id": 123,
  "title": "Project Planning",
  "created_at": "2026-02-06T10:30:00Z",
  "updated_at": "2026-02-06T11:45:00Z",
  "messages": [
    {
      "id": 456,
      "role": "user",
      "content": "Can you help me plan...",
      "created_at": "2026-02-06T10:30:15Z"
    },
    {
      "id": 457,
      "role": "assistant",
      "content": "I'd be happy to help!...",
      "created_at": "2026-02-06T10:30:22Z"
    }
  ]
}
```

**Use cases:**

- Backup important conversations
- Process with scripts or analysis tools
- Import into other systems

### Export as PDF

1. **Open** conversation
2. **Click** **⋮** menu in header
3. **Select** "Export as PDF"
4. Browser downloads `conversation-{id}.pdf`

**PDF includes:**

- Conversation title and metadata
- All messages with timestamps
- Formatted markdown (headings, lists, code)
- Page numbers and headers

**Use cases:**

- Share with non-technical users
- Print physical copies
- Include in reports or documentation

---

## Advanced Features

### Multi-line Input

**Add line breaks** in your message:

- Press **Shift+Enter** for newline
- Press **Enter** to send

**Example:**

```text
This is line 1  [Shift+Enter]
This is line 2  [Shift+Enter]
This is line 3  [Enter to send]
```

### Long Messages

Input box **auto-expands** as you type (up to 10 lines visible).

**For very long prompts:**

- Type or paste content
- Scroll within input box
- Box remains at bottom of screen

### Paste Content

**Paste text:**

- Press **Ctrl+V** (Cmd+V on Mac)
- Text appears in input box
- Formatting is preserved (plain text)

**Paste code:**

- Paste code directly
- Wrap in markdown code fences if needed:

  ````text
  ```python
  [paste code here]
  ```
  ````

### Streaming Responses

Responses appear **in real-time** as the LLM generates them:

**Benefits:**

- Immediate feedback (know AI is working)
- Read while waiting for completion
- Stop generation if going off-track

**How it works:**

- Backend uses **Server-Sent Events (SSE)**
- Frontend updates UI as chunks arrive
- Smooth typewriter effect

### Stop Generation

**Not yet implemented** (planned feature).

**Workaround:**

- Refresh the page to cancel
- Send a new message to interrupt

---

## Conversation Context

### How Context Works

**Context window:**

- Gantry sends **recent messages** to the LLM
- Default: Last **10 messages** (5 exchanges)
- Includes system prompt + conversation history

**Context injection:**

- **Long-term memory** - Relevant past messages (ChromaDB search)
- **Knowledge Vault** - Document chunks (if docs selected)
- **Graph entities** - Related knowledge graph nodes

**Result:** AI remembers context across session, even from previous conversations.

### Context Limits

**LLM context window:**

- Model dependent (4K, 8K, 32K, 128K tokens)
- Gantry automatically truncates to fit
- Oldest messages dropped first (keeps recent context)

**Tip:** For very long conversations, start a new chat and reference key points.

---

## Troubleshooting

### Messages Not Sending

**Issue:** Click send, nothing happens.

**Fixes:**

- Check input is not empty
- Verify backend is running: `curl http://localhost:8000/health`
- Check browser console for errors (F12 → Console tab)
- Try refreshing the page

### Streaming Stops Mid-Response

**Issue:** Response starts, then freezes.

**Fixes:**

- Check LLM server is running
- Check backend logs: `docker compose logs backend`
- Network interruption - refresh and try again
- LLM may have hit token limit - rephrase prompt to be shorter

### Markdown Not Rendering

**Issue:** Markdown shows as plain text (e.g., `**bold**` instead of **bold**).

**Fixes:**

- Only assistant messages render markdown (user messages show plain text)
- Check message role is "assistant" not "user"
- Refresh page - may be rendering bug

### Search Not Finding Messages

**Issue:** Ctrl+K search returns no results for known messages.

**Fixes:**

- Search is case-insensitive but requires exact substring match
- Try different keywords
- Check that conversation exists in sidebar
- Database may need re-indexing (backend restart)

### Sidebar Not Showing Conversations

**Issue:** Sidebar is empty or missing conversations.

**Fixes:**

- Check user is logged in (profile icon shows in header)
- Refresh the page
- Check backend logs for database errors
- Verify database file exists: `ls -lh data/gantry.db`

---

## Tips & Best Practices

### Writing Effective Prompts

**Be specific:**

❌ "Write code"
✅ "Write a Python function that validates email addresses using regex"

**Provide context:**

❌ "Fix this"
✅ "Fix this function - it should return True for even numbers but currently returns False"

**Break down complex tasks:**

Instead of: "Build a complete web app"

Use:

1. "Design the database schema for a task manager"
2. "Write the API endpoint for creating tasks"
3. "Create the frontend component to display tasks"

### Using Markdown in Prompts

**Format code in user messages** for better responses:

````text
Can you review this function?

```python
def calculate(x, y):
    return x + y
```
````

**Use lists for multiple questions:**

```text
I have three questions:

1. How do I handle errors?
2. What's the best way to validate input?
3. Should I use async or sync?
```

### Conversation Organization

**Strategy 1 - Topic per conversation:**

- One conversation for frontend work
- One for backend work
- One for debugging
- Pin active topics

**Strategy 2 - Task per conversation:**

- One conversation per feature
- One per bug fix
- Archive (unpin) when complete

**Strategy 3 - Session per conversation:**

- New conversation daily
- Name with date: "2026-02-06 - Sprint Planning"
- Export important conversations

---

## Mobile Usage

### Mobile Layout

**Sidebar:**

- Hidden by default
- Tap **≡** menu icon to open
- Swipe left to close

**Chat area:**

- Full screen when sidebar closed
- Optimized touch targets
- Pinch to zoom code blocks

**Input:**

- Sticky at bottom
- Auto-focus when tapping
- Virtual keyboard resizes view

### Mobile Shortcuts

**Gestures:**

- Swipe sidebar to close
- Tap message to show actions (copy, etc.)
- Long-press for context menu (future)

**No keyboard shortcuts:**

- Ctrl+K, Shift+Enter don't work on mobile
- Use on-screen buttons instead

---

## Accessibility

**Keyboard navigation:**

- Full interface accessible via keyboard
- Tab through interactive elements
- Enter to activate buttons

**Screen readers:**

- Semantic HTML structure
- ARIA labels on icons
- Alt text on images (future)

**Contrast:**

- Dark theme meets WCAG AA standards
- High contrast text on backgrounds
- Focus indicators on interactive elements

---

## Next Steps

- **[Knowledge Vault](Knowledge-Vault)** - Upload documents for RAG-powered answers
- **[Long-Term Memory](Long-Term-Memory)** - How context and memory work
- **[Admin Dashboard](Admin-Dashboard)** - Manage users and system settings

---

**[← Back to Home](Home)** | **[Configuration →](Configuration)**
