"""
Memory management abstraction layer for agent memory operations.

This module provides a backend-agnostic interface for memory management,
currently implemented with Mem0 cloud platform but designed to be swappable
with other solutions (langmem, custom implementations, etc.). The abstraction
allows the agent to remain independent of the specific memory backend.
"""

import json
import logging
import os
from typing import (
    Any,
    Dict,
    List,
    Optional,
)

from mem0 import MemoryClient


# Configure logging
logger = logging.getLogger(__name__)


class MemoryManager:
    """Abstract memory management that can be swapped with different backends.

    IMPORTANT: This class uses async/await patterns. All memory operations
    (insert, search, get_all, add_conversation, clear, export, get_stats)
    are async methods and must be awaited.
    """

    def __init__(
        self,
        api_key: str
    ):
        """Initialize the memory manager with Mem0 cloud platform.

        This creates a SINGLE multi-tenant MemoryManager that services all users
        and sessions. User identification and session context are passed as parameters
        to each method call, not stored as instance variables.

        Args:
            api_key: Mem0 API key for cloud platform access
        """
        if not api_key:
            raise ValueError("api_key is required for Mem0 cloud platform")

        logger.info("Initializing multi-tenant MemoryManager with Mem0 cloud platform")

        # Initialize Mem0 cloud client (synchronous initialization)
        self.memory = MemoryClient(api_key=api_key)

        logger.info("Mem0 cloud client initialized successfully")


    async def insert(
        self,
        user_id: str,
        content: str,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> Dict[str, Any]:
        """Insert memory asynchronously for a specific user/session.

        Args:
            user_id: User identifier (required for multi-tenant isolation)
            content: The information to store in memory
            agent_id: Agent identifier for multi-agent scenarios (optional)
            run_id: Session/conversation identifier (optional)
            metadata: Optional metadata dictionary (e.g., type, timestamp, tags)

        Returns:
            Dictionary with operation status and stored information
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not content or not content.strip():
            raise ValueError("Memory content cannot be empty")

        try:
            logger.info(
                f"Inserting memory for user={user_id}, agent={agent_id}, "
                f"session={run_id}: '{content[:100]}...'"
            )

            # Store in Mem0 cloud platform - only pass user_id.
            # Don't pass metadata or run_id as they can cause silent failures
            # in Mem0's background processing, making memories un-searchable.
            self.memory.add(
                content,
                user_id=user_id,
            )

            logger.info(f"Memory stored for user={user_id} with context (agent={agent_id}, session={run_id})")

            result = {
                "status": "success",
                "message": "Memory stored successfully",
                "content": content,
                "metadata": metadata,
                "user_id": user_id
            }

            logger.info("Memory inserted successfully")

            return result

        except Exception as e:
            logger.error(f"Error inserting memory: {e}")
            return {
                "status": "error",
                "message": str(e)
            }


    async def search(
        self,
        user_id: str,
        query: str,
        limit: int = 5,
        run_id: Optional[str] = None,
        agent_id: Optional[str] = None,
        metadata_filters: Optional[Dict[str, Any]] = None
    ) -> List[Dict[str, Any]]:
        """Search memories asynchronously for a specific user.

        Performs semantic search across stored memories using vector similarity.
        Searches across ALL sessions for the user (cross-session recall).

        Args:
            user_id: User identifier (required for multi-tenant isolation)
            query: Search query to find relevant memories
            limit: Maximum number of memories to return (default: 5)
            run_id: Provided for context but NOT used in search (cross-session recall)
            agent_id: Filter by specific agent (optional)
            metadata_filters: Filter by metadata (optional)

        Returns:
            List of memory dictionaries with content, scores, and metadata
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if not query or not query.strip():
            raise ValueError("Search query cannot be empty")

        if limit < 1 or limit > 100:
            raise ValueError("Limit must be between 1 and 100")

        try:
            logger.info(
                f"Searching memories for user={user_id}: '{query}' "
                f"(limit={limit}, searching across ALL sessions)"
            )

            # Use user_id filter with version="v2" for reliable cross-session recall.
            results = self.memory.search(
                query=query,
                filters={"user_id": user_id},
                version="v2",
                limit=limit
            )

            # Log raw results at INFO level for debugging
            logger.info(f"Raw Mem0 search response type: {type(results)}")

            # Handle Mem0 returning dict with 'results' key
            if isinstance(results, dict):
                results = results.get("results", [])

            logger.info(f"Search returned {len(results)} results for user={user_id}, query='{query}'")

            if not results:
                logger.info("No memories found for query")
                return []

            # Normalize results to consistent format
            memories = []
            for i, mem in enumerate(results):
                if isinstance(mem, dict):
                    memory_entry = {
                        "id": mem.get("id", "unknown"),
                        "memory": mem.get("memory", str(mem)),
                        "score": mem.get("score", 1.0),
                        "created_at": mem.get("created_at", ""),
                        "metadata": mem.get("metadata", {})
                    }
                    memories.append(memory_entry)
                    logger.info(f"  Memory {i}: {memory_entry['memory'][:80]}")
                else:
                    memories.append({
                        "id": "unknown",
                        "memory": str(mem),
                        "score": 1.0,
                        "created_at": "",
                        "metadata": {}
                    })

            logger.info(f"Found {len(memories)} relevant memories")

            return memories

        except Exception as e:
            logger.error(f"Error searching memories: {e}", exc_info=True)
            return []


    async def export(
        self,
        user_id: str,
        format: str = "json"
    ) -> Dict[str, Any]:
        """Export all memories to JSON format asynchronously.

        Args:
            user_id: User identifier (required for multi-tenant isolation)
            format: Export format (currently only "json" supported)

        Returns:
            Dictionary containing all memories and metadata
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        if format not in ["json"]:
            raise ValueError(f"Unsupported export format: {format}. Use 'json'")

        try:
            logger.info(f"Exporting memories for user={user_id} in {format} format")

            all_memories = self.memory.get_all(
                filters={"user_id": user_id},
                version="v2"
            )

            export_data = {
                "user_id": user_id,
                "format": format,
                "memory_count": len(all_memories),
                "memories": all_memories,
                "backend": "mem0_cloud"
            }

            logger.info(f"Exported {len(all_memories)} memories for user={user_id}")

            return export_data

        except Exception as e:
            logger.error(f"Error exporting memories for user={user_id}: {e}")
            return {
                "status": "error",
                "message": str(e),
                "user_id": user_id
            }


    async def get_all(
        self,
        user_id: str,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """Get all memories for a specific user asynchronously.

        Args:
            user_id: User identifier (required for multi-tenant isolation)
            limit: Optional maximum number of memories to return

        Returns:
            List of all memory dictionaries for the user
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        try:
            logger.info(f"Retrieving all memories for user={user_id}")

            result = self.memory.get_all(
                filters={"user_id": user_id},
                version="v2"
            )

            if isinstance(result, dict):
                all_memories = result.get("results", result.get("memories", []))
            else:
                all_memories = result if isinstance(result, list) else []

            if limit and limit > 0:
                all_memories = all_memories[:limit]

            logger.info(f"Retrieved {len(all_memories)} total memories for user={user_id}")

            return all_memories

        except Exception as e:
            logger.error(f"Error retrieving all memories for user={user_id}: {e}")
            return []


    async def clear(self, user_id: str) -> None:
        """Clear all memories for a specific user asynchronously.

        WARNING: This permanently deletes all stored memories.

        Args:
            user_id: User identifier (required for multi-tenant isolation)
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        try:
            logger.warning(f"Clearing all memories for user: {user_id}")

            result = self.memory.get_all(
                filters={"user_id": user_id},
                version="v2"
            )

            if isinstance(result, dict):
                all_memories = result.get("results", result.get("memories", []))
            else:
                all_memories = result if isinstance(result, list) else []

            memory_count = len(all_memories)

            for mem in all_memories:
                if isinstance(mem, dict):
                    memory_id = mem.get("id")
                    if memory_id:
                        self.memory.delete(memory_id=memory_id)

            logger.info(f"Cleared {memory_count} memories successfully")

        except Exception as e:
            logger.error(f"Error clearing memories: {e}")
            raise RuntimeError(f"Failed to clear memories: {e}") from e


    async def add_conversation(
        self,
        user_id: str,
        user_message: str,
        assistant_message: str,
        agent_id: Optional[str] = None,
        run_id: Optional[str] = None,
        metadata: Optional[Dict[str, Any]] = None
    ) -> None:
        """Add a conversation turn to memory asynchronously.

        Args:
            user_id: User identifier (required for multi-tenant isolation)
            user_message: User's message
            assistant_message: Assistant's response
            agent_id: Agent identifier (optional)
            run_id: Session/conversation identifier (optional)
            metadata: Optional metadata for the conversation turn
        """
        try:
            conversation_text = f"User: {user_message}\nAssistant: {assistant_message}"

            logger.debug(
                f"Adding conversation for user={user_id}, agent={agent_id}, session={run_id} "
                f"(user msg length: {len(user_message)})"
            )

            # Store in Mem0 cloud platform - only pass user_id.
            # Don't pass metadata or run_id as they can cause silent failures
            # in Mem0's background processing, making memories un-searchable.
            self.memory.add(
                conversation_text,
                user_id=user_id,
            )

            logger.debug(f"Conversation stored for user={user_id}")

        except Exception as e:
            logger.error(f"Error storing conversation: {e}")
            # Don't raise - conversation storage failure shouldn't break agent


    async def get_stats(self, user_id: str) -> Dict[str, Any]:
        """Get memory statistics for a specific user asynchronously.

        Args:
            user_id: User identifier (required for multi-tenant isolation)

        Returns:
            Dictionary containing memory count and other statistics
        """
        if not user_id or not user_id.strip():
            raise ValueError("user_id cannot be empty")

        try:
            result = self.memory.get_all(
                filters={"user_id": user_id},
                version="v2"
            )

            if isinstance(result, dict):
                all_memories = result.get("results", result.get("memories", []))
            else:
                all_memories = result if isinstance(result, list) else []

            stats = {
                "user_id": user_id,
                "total_memories": len(all_memories),
                "backend": "mem0_cloud"
            }

            logger.info(f"Memory stats for user={user_id}: {stats}")
            return stats

        except Exception as e:
            logger.error(f"Error getting memory stats for user={user_id}: {e}")
            return {
                "user_id": user_id,
                "error": str(e)
            }