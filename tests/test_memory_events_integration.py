"""
Integration test to verify independent consumer groups on document_ingest_stream.

This test proves that two consumer groups (hcl_crossref_workers and smds_matrix_workers)
can read the same events independently without interfering with each other's acknowledgment state.
"""
import os
import time
from uuid import uuid4, UUID
from datetime import datetime

import redis
from src.retrieval.memory_events import (
    MemoryEvent,
    emit_memory_event,
    read_memory_event_batch,
    ensure_consumer_group,
)


def test_independent_consumer_groups():
    """Test that two consumer groups can read the same event independently."""
    
    # Setup Redis connection
    r = redis.Redis(decode_responses=False)
    stream_name = "document_ingest_stream_test"
    group1 = "hcl_crossref_workers_test"
    group2 = "smds_matrix_workers_test"
    
    # Clean up any existing test stream
    try:
        r.delete(stream_name)
    except:
        pass
    
    try:
        # Step 1: Ensure both consumer groups exist
        ensure_consumer_group(stream_name, group1)
        ensure_consumer_group(stream_name, group2)
        print("✓ Consumer groups created")
        
        # Step 2: Emit one MemoryEvent
        test_event = MemoryEvent(
            event_id=uuid4(),
            event_type="document_ingest",
            user_id=uuid4(),
            workspace_id=uuid4(),
            source_id="test-paper-123",
            timestamp=datetime.utcnow(),
            payload={"title": "Test Paper", "content": "Test content"},
            provenance_uri="test://paper/123"
        )
        emit_memory_event(stream_name, test_event)
        print("✓ Test event emitted")
        
        # Step 3: Read via group1 (hcl_crossref_workers)
        batch1 = read_memory_event_batch(stream_name, group1, count=1, block_ms=1000)
        assert len(batch1) == 1, f"Group1 should read 1 event, got {len(batch1)}"
        entry_id_1, event_1 = batch1[0]
        assert event_1.event_id == test_event.event_id, "Group1 should read the test event"
        print(f"✓ Group1 read event via entry_id: {entry_id_1}")
        
        # Step 4: Read via group2 (smds_matrix_workers) - should also see it
        batch2 = read_memory_event_batch(stream_name, group2, count=1, block_ms=1000)
        assert len(batch2) == 1, f"Group2 should read 1 event, got {len(batch2)}"
        entry_id_2, event_2 = batch2[0]
        assert event_2.event_id == test_event.event_id, "Group2 should read the test event"
        print(f"✓ Group2 read event via entry_id: {entry_id_2}")
        
        # Step 5: Ack in group1 only
        r.xack(stream_name, group1, entry_id_1)
        print("✓ Event acknowledged in group1")
        
        # Step 6: Verify group2 can still read the same event (proves independent read position)
        # First, try to read again - group2 should still see it since we didn't ack in group2
        batch2_again = read_memory_event_batch(stream_name, group2, count=1, block_ms=1000)
        # Note: Since we already read it in group2, it won't be returned again unless we reset the consumer
        # Instead, we'll verify the group's pending entries still contain it
        pending = r.xpending(stream_name, group2)
        print(f"✓ Group2 pending entries: {pending}")
        
        # The key test: group1's pending should be 0 (we acked), group2's should be > 0 (we didn't ack)
        pending1 = r.xpending(stream_name, group1)
        pending2 = r.xpending(stream_name, group2)
        
        # After acking in group1, pending should be 0
        assert pending1['pending'] == 0, f"Group1 should have 0 pending after ack, got {pending1['pending']}"
        print(f"✓ Group1 pending count: {pending1['pending']} (correctly 0 after ack)")
        
        # Group2 should still have the event pending
        assert pending2['pending'] > 0, f"Group2 should have >0 pending, got {pending2['pending']}"
        print(f"✓ Group2 pending count: {pending2['pending']} (correctly >0, independent read position)")
        
        # Step 7: Ack in group2 to clean up
        r.xack(stream_name, group2, entry_id_2)
        print("✓ Event acknowledged in group2")
        
        print("\n" + "="*60)
        print("TEST PASSED: Consumer groups are independent!")
        print("Group1 acking did not affect Group2's read position.")
        print("="*60)
        
    finally:
        # Cleanup
        try:
            r.delete(stream_name)
        except:
            pass


if __name__ == "__main__":
    test_independent_consumer_groups()
