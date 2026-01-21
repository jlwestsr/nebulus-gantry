import chromadb
from chromadb.config import Settings
import os


class LTMTool:
    def __init__(self):
        """
        Initialize connection to ChromaDB for LTM access.
        """
        self.host = os.getenv("CHROMA_HOST", "http://host.docker.internal:8000")
        # Parse host/port
        if "://" in self.host:
            base = self.host.split("://")[1]
        else:
            base = self.host

        if ":" in base:
            h, p = base.split(":")
            self.chroma_host = h
            self.chroma_port = int(p)
        else:
            self.chroma_host = base
            self.chroma_port = 8000

        try:
            self.client = chromadb.HttpClient(
                host=self.chroma_host,
                port=self.chroma_port,
                settings=Settings(allow_reset=False, anonymized_telemetry=False),
            )
            # We target the 'messages' collection which contains the chat history
            self.collection = self.client.get_or_create_collection("messages")
        except Exception as e:
            print(f"Error connecting to ChromaDB at {self.host}: {e}")
            self.client = None
            self.collection = None

    def search_chat_history(self, query: str, limit: int = 5) -> str:
        """
        Search the long-term chat history for semantic matches.

        Args:
            query: The semantic search query (e.g., "What did we say about Python?")
            limit: Number of results to return (default: 5)
        """
        if not self.collection:
            return "Error: LTM Database not connected."

        try:
            results = self.collection.query(
                query_texts=[query],
                n_results=limit
            )

            # Format results
            output = []
            if results["documents"]:
                docs = results["documents"][0]
                metadatas = results["metadatas"][0]

                for i, doc in enumerate(docs):
                    meta = metadatas[i]
                    sender = meta.get("sender", "unknown")
                    timestamp = meta.get("timestamp", "unknown")
                    output.append(f"[{timestamp}] {sender}: {doc}")

            if not output:
                return "No relevant history found."

            return "\n---\n".join(output)

        except Exception as e:
            return f"Error querying LTM: {str(e)}"


# Singleton
_ltm_tool = None


def get_ltm_tool():
    global _ltm_tool
    if not _ltm_tool:
        _ltm_tool = LTMTool()
    return _ltm_tool
