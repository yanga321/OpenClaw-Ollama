#!/usr/bin/env python3
# =============================================================================
# Memory Palace - Hippocampus-Inspired AI Memory System
# =============================================================================
# Features:
#   - Short-term memory buffer (recent conversations)
#   - Long-term memory consolidation (during sleep/charging)
#   - Vector embeddings for semantic search
#   - Importance-based memory prioritization
#   - Sleep consolidation algorithm
# =============================================================================

import sqlite3
import json
import hashlib
import numpy as np
from datetime import datetime, timedelta
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass, asdict
from pathlib import Path
import logging

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger('MemoryPalace')


@dataclass
class Memory:
    """Represents a single memory unit"""
    content: str
    embedding: Optional[List[float]] = None
    importance: float = 0.5
    created_at: str = ""
    consolidated: bool = False
    access_count: int = 0
    last_accessed: str = ""
    tags: List[str] = None
    
    def __post_init__(self):
        if not self.created_at:
            self.created_at = datetime.now().isoformat()
        if not self.last_accessed:
            self.last_accessed = self.created_at
        if self.tags is None:
            self.tags = []


@dataclass
class Conversation:
    """Represents a conversation turn"""
    role: str  # 'user' or 'assistant'
    content: str
    context_id: str = ""
    timestamp: str = ""
    
    def __post_init__(self):
        if not self.timestamp:
            self.timestamp = datetime.now().isoformat()


class MemoryPalace:
    """
    Hippocampus-inspired memory system with sleep consolidation.
    
    Architecture:
    - Working Memory: Recent conversations (last 24h)
    - Short-term Memory: Important recent interactions
    - Long-term Memory: Consolidated memories with embeddings
    - Sleep Consolidation: Process and optimize during idle/charging
    """
    
    def __init__(self, db_path: str = "user_data/memory_palace/memories.db"):
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Working memory buffer (in-memory)
        self.working_memory: List[Conversation] = []
        self.short_term_buffer: List[Memory] = []
        
        # Initialize database
        self._init_database()
        
        logger.info(f"Memory Palace initialized at {self.db_path}")
    
    def _init_database(self):
        """Initialize SQLite database with schema"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Conversations table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS conversations (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp DATETIME DEFAULT CURRENT_TIMESTAMP,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                context_id TEXT,
                processed BOOLEAN DEFAULT FALSE
            )
        ''')
        
        # Memories table
        cursor.execute('''
            CREATE TABLE IF NOT EXISTS memories (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                content TEXT NOT NULL,
                embedding BLOB,
                importance REAL DEFAULT 0.5,
                created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
                consolidated BOOLEAN DEFAULT FALSE,
                access_count INTEGER DEFAULT 0,
                last_accessed DATETIME DEFAULT CURRENT_TIMESTAMP,
                tags TEXT
            )
        ''')
        
        # Create indexes for performance
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_conversations_timestamp 
            ON conversations(timestamp)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_importance 
            ON memories(importance)
        ''')
        cursor.execute('''
            CREATE INDEX IF NOT EXISTS idx_memories_consolidated 
            ON memories(consolidated)
        ''')
        
        conn.commit()
        conn.close()
        logger.debug("Database schema initialized")
    
    def add_conversation(self, role: str, content: str, context_id: str = "") -> int:
        """
        Add a conversation turn to working memory and database.
        
        Args:
            role: 'user' or 'assistant'
            content: The message content
            context_id: Optional context identifier
            
        Returns:
            Database ID of the inserted conversation
        """
        conversation = Conversation(role=role, content=content, context_id=context_id)
        self.working_memory.append(conversation)
        
        # Keep only last 100 turns in working memory
        if len(self.working_memory) > 100:
            self.working_memory.pop(0)
        
        # Save to database
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            INSERT INTO conversations (role, content, context_id, timestamp)
            VALUES (?, ?, ?, ?)
        ''', (conversation.role, conversation.content, 
              conversation.context_id, conversation.timestamp))
        
        conv_id = cursor.lastrowid
        conn.commit()
        conn.close()
        
        # Extract potential memories from important conversations
        if role == 'assistant' and len(content) > 100:
            self._extract_memory(content, source_type='conversation', source_id=conv_id)
        
        logger.debug(f"Added conversation (ID: {conv_id})")
        return conv_id
    
    def _extract_memory(self, content: str, source_type: str = 'conversation', 
                       source_id: Optional[int] = None):
        """
        Extract important information as a memory.
        
        Uses simple heuristics (can be enhanced with ML):
        - Length thresholds
        - Keyword detection
        - Factual statements
        """
        # Simple importance scoring (can be enhanced with ML model)
        importance = self._calculate_importance(content)
        
        if importance > 0.6:  # Only store moderately important memories
            memory = Memory(
                content=content,
                importance=importance,
                tags=self._extract_tags(content)
            )
            
            # Generate embedding (placeholder - use actual embedding model in production)
            memory.embedding = self._generate_embedding(content)
            
            self.short_term_buffer.append(memory)
            logger.info(f"Extracted memory with importance {importance:.2f}")
    
    def _calculate_importance(self, content: str) -> float:
        """
        Calculate importance score for content.
        
        Heuristics:
        - Length (longer often more detailed)
        - Presence of key phrases
        - Recency boost
        """
        base_score = min(len(content) / 500, 1.0) * 0.4
        
        # Keyword bonuses
        keywords = ['important', 'remember', 'key', 'critical', 'note', 
                   'fact', 'learn', 'discovered', 'conclusion']
        keyword_bonus = sum(0.05 for word in keywords if word in content.lower())
        
        # Question bonus (answers are often important)
        if '?' in content:
            keyword_bonus += 0.1
        
        return min(base_score + keyword_bonus, 1.0)
    
    def _extract_tags(self, content: str) -> List[str]:
        """Extract simple tags from content"""
        # Placeholder implementation
        tags = []
        
        # Detect topic categories
        if any(word in content.lower() for word in ['code', 'function', 'program']):
            tags.append('coding')
        if any(word in content.lower() for word in ['fact', 'history', 'science']):
            tags.append('knowledge')
        if any(word in content.lower() for word in ['feel', 'emotion', 'happy', 'sad']):
            tags.append('emotional')
        
        return tags
    
    def _generate_embedding(self, content: str) -> List[float]:
        """
        Generate vector embedding for content.
        
        In production: Use sentence-transformers, SBERT, or similar
        Here: Use simple hash-based placeholder
        """
        # Placeholder: Create deterministic pseudo-embedding
        hash_obj = hashlib.md5(content.encode())
        hash_bytes = hash_obj.digest()
        
        # Convert to 384-dimensional vector (matching common embedding models)
        embedding = []
        for i in range(384):
            byte_idx = i % len(hash_bytes)
            embedding.append((hash_bytes[byte_idx] / 255.0) * 2 - 1)  # Normalize to [-1, 1]
        
        return embedding
    
    def consolidate_memories(self, force: bool = False):
        """
        Consolidate short-term memories to long-term storage.
        
        Mimics hippocampal consolidation during sleep:
        - Rehearsal: Repeatedly accessed memories strengthened
        - Pruning: Unimportant memories fade
        - Integration: Related memories linked
        - Optimization: Embeddings indexed for fast retrieval
        
        Args:
            force: Force consolidation even if not enough time passed
        """
        logger.info("Starting memory consolidation...")
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        consolidated_count = 0
        
        for memory in self.short_term_buffer:
            # Check if already consolidated
            cursor.execute('''
                SELECT id FROM memories WHERE content = ? AND consolidated = TRUE
            ''', (memory.content,))
            
            if cursor.fetchone():
                continue
            
            # Store in long-term memory
            embedding_blob = json.dumps(memory.embedding).encode() if memory.embedding else None
            tags_json = json.dumps(memory.tags) if memory.tags else '[]'
            
            cursor.execute('''
                INSERT INTO memories (content, embedding, importance, consolidated, tags)
                VALUES (?, ?, ?, ?, ?)
            ''', (memory.content, embedding_blob, memory.importance, True, tags_json))
            
            consolidated_count += 1
        
        # Optimize: Remove very old, low-importance unconsolidated memories
        if force or self._should_cleanup():
            cursor.execute('''
                DELETE FROM memories 
                WHERE consolidated = FALSE 
                AND importance < 0.3
                AND created_at < datetime('now', '-7 days')
            ''')
            deleted = cursor.rowcount
            logger.info(f"Cleaned up {deleted} low-importance memories")
        
        # Update access counts based on similarity searches (rehearsal effect)
        self._rehearse_frequently_accessed(cursor)
        
        conn.commit()
        conn.close()
        
        # Clear short-term buffer
        self.short_term_buffer.clear()
        
        logger.info(f"Consolidation complete: {consolidated_count} memories stored")
    
    def _should_cleanup(self) -> bool:
        """Check if database needs cleanup"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('SELECT COUNT(*) FROM memories WHERE consolidated = FALSE')
        count = cursor.fetchone()[0]
        
        conn.close()
        return count > 1000  # Cleanup if more than 1000 unconsolidated
    
    def _rehearse_frequently_accessed(self, cursor):
        """Strengthen frequently accessed memories (rehearsal)"""
        # Increase importance for memories that match recent queries
        cursor.execute('''
            UPDATE memories 
            SET importance = MIN(importance * 1.1, 1.0),
                last_accessed = CURRENT_TIMESTAMP
            WHERE access_count > 5
        ''')
    
    def search_memories(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        Search for relevant memories using semantic similarity.
        
        Args:
            query: Search query
            top_k: Number of results to return
            
        Returns:
            List of relevant memories with similarity scores
        """
        # Generate query embedding
        query_embedding = self._generate_embedding(query)
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        # Retrieve all consolidated memories (optimize with vector DB in production)
        cursor.execute('''
            SELECT id, content, embedding, importance, access_count, tags
            FROM memories
            WHERE consolidated = TRUE
            ORDER BY importance DESC
            LIMIT 100
        ''')
        
        results = []
        for row in cursor.fetchall():
            mem_id, content, embedding_blob, importance, access_count, tags_json = row
            
            if embedding_blob:
                stored_embedding = json.loads(embedding_blob.decode())
                
                # Calculate cosine similarity
                similarity = self._cosine_similarity(query_embedding, stored_embedding)
                
                # Boost by importance and recency
                final_score = similarity * 0.7 + importance * 0.3
                
                results.append({
                    'id': mem_id,
                    'content': content,
                    'similarity': float(final_score),
                    'importance': importance,
                    'access_count': access_count,
                    'tags': json.loads(tags_json) if tags_json else []
                })
        
        conn.close()
        
        # Sort by final score and return top_k
        results.sort(key=lambda x: x['similarity'], reverse=True)
        
        # Update access counts
        self._update_access_counts([r['id'] for r in results[:top_k]])
        
        return results[:top_k]
    
    def _cosine_similarity(self, vec1: List[float], vec2: List[float]) -> float:
        """Calculate cosine similarity between two vectors"""
        vec1_np = np.array(vec1)
        vec2_np = np.array(vec2)
        
        dot_product = np.dot(vec1_np, vec2_np)
        norm1 = np.linalg.norm(vec1_np)
        norm2 = np.linalg.norm(vec2_np)
        
        if norm1 == 0 or norm2 == 0:
            return 0.0
        
        return float(dot_product / (norm1 * norm2))
    
    def _update_access_counts(self, memory_ids: List[int]):
        """Update access counts for retrieved memories"""
        if not memory_ids:
            return
        
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        placeholders = ','.join('?' * len(memory_ids))
        cursor.execute(f'''
            UPDATE memories 
            SET access_count = access_count + 1,
                last_accessed = CURRENT_TIMESTAMP
            WHERE id IN ({placeholders})
        ''', memory_ids)
        
        conn.commit()
        conn.close()
    
    def get_recent_conversations(self, hours: int = 24) -> List[Dict]:
        """Get conversations from the last N hours"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT id, role, content, timestamp, context_id
            FROM conversations
            WHERE timestamp >= datetime('now', ?)
            ORDER BY timestamp DESC
        ''', (f'-{hours} hours',))
        
        results = [
            {
                'id': row[0],
                'role': row[1],
                'content': row[2],
                'timestamp': row[3],
                'context_id': row[4]
            }
            for row in cursor.fetchall()
        ]
        
        conn.close()
        return results
    
    def get_statistics(self) -> Dict:
        """Get memory palace statistics"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        stats = {}
        
        # Total memories
        cursor.execute('SELECT COUNT(*) FROM memories')
        stats['total_memories'] = cursor.fetchone()[0]
        
        # Consolidated vs unconsolidated
        cursor.execute('SELECT COUNT(*) FROM memories WHERE consolidated = TRUE')
        stats['consolidated_memories'] = cursor.fetchone()[0]
        
        # Average importance
        cursor.execute('SELECT AVG(importance) FROM memories')
        stats['avg_importance'] = cursor.fetchone()[0] or 0
        
        # Total conversations
        cursor.execute('SELECT COUNT(*) FROM conversations')
        stats['total_conversations'] = cursor.fetchone()[0]
        
        # Recent activity (last 24h)
        cursor.execute('''
            SELECT COUNT(*) FROM conversations 
            WHERE timestamp >= datetime('now', '-24 hours')
        ''')
        stats['recent_conversations'] = cursor.fetchone()[0]
        
        conn.close()
        
        return stats
    
    def export_memories(self, filepath: str):
        """Export all memories to JSON file"""
        conn = sqlite3.connect(str(self.db_path))
        cursor = conn.cursor()
        
        cursor.execute('''
            SELECT content, embedding, importance, created_at, consolidated, 
                   access_count, last_accessed, tags
            FROM memories
            WHERE consolidated = TRUE
        ''')
        
        memories = []
        for row in cursor.fetchall():
            embedding = json.loads(row[1].decode()) if row[1] else None
            memories.append({
                'content': row[0],
                'embedding': embedding,
                'importance': row[2],
                'created_at': row[3],
                'consolidated': row[4],
                'access_count': row[5],
                'last_accessed': row[6],
                'tags': json.loads(row[7]) if row[7] else []
            })
        
        conn.close()
        
        with open(filepath, 'w') as f:
            json.dump(memories, f, indent=2)
        
        logger.info(f"Exported {len(memories)} memories to {filepath}")


# =============================================================================
# Main Demo/Test Function
# =============================================================================
def demo():
    """Demonstrate Memory Palace functionality"""
    print("=" * 70)
    print("🧠 Memory Palace Demo - Hippocampus-Inspired AI Memory")
    print("=" * 70)
    
    # Initialize
    palace = MemoryPalace("user_data/memory_palace/memories.db")
    
    # Add some conversations
    conversations = [
        ("user", "What is quantum computing?", "session_001"),
        ("assistant", "Quantum computing is a type of computation that harnesses quantum mechanical phenomena like superposition and entanglement. Unlike classical computers that use bits (0 or 1), quantum computers use quantum bits or qubits, which can exist in multiple states simultaneously. This allows them to solve certain problems exponentially faster than classical computers, particularly in cryptography, drug discovery, and optimization problems."),
        ("user", "Remember this: Python is my favorite programming language", "session_001"),
        ("assistant", "I've noted that Python is your favorite programming language! Python is indeed popular for its readability, extensive libraries, and versatility in web development, data science, AI/ML, and automation."),
        ("user", "Can you help me debug this code?", "session_002"),
        ("assistant", "Of course! Please share the code you're working on and describe the issue you're encountering. I'll help you identify bugs, suggest improvements, and explain what's going wrong."),
    ]
    
    print("\n📝 Adding conversations...")
    for role, content, ctx_id in conversations:
        palace.add_conversation(role, content, ctx_id)
        print(f"  ✓ Added {role}: {content[:50]}...")
    
    # Consolidate memories
    print("\n💤 Running sleep consolidation...")
    palace.consolidate_memories(force=True)
    
    # Search memories
    print("\n🔍 Searching for 'quantum'...")
    results = palace.search_memories("quantum computing", top_k=3)
    for i, result in enumerate(results, 1):
        print(f"\n  Result {i} (Score: {result['similarity']:.3f}):")
        print(f"    Content: {result['content'][:100]}...")
        print(f"    Importance: {result['importance']:.2f}")
        print(f"    Tags: {', '.join(result['tags']) if result['tags'] else 'None'}")
    
    # Statistics
    print("\n📊 Memory Palace Statistics:")
    stats = palace.get_statistics()
    for key, value in stats.items():
        print(f"  {key.replace('_', ' ').title()}: {value}")
    
    print("\n✅ Demo complete!")


if __name__ == "__main__":
    demo()
