#!/usr/bin/env python
"""
Quick Verification: Production Logging System

Run this to verify all logging components are working correctly.
"""

import sys
from pathlib import Path

# Add workspace to path
workspace = Path(__file__).parent
sys.path.insert(0, str(workspace))

def test_imports():
    """Test that all logging modules can be imported."""
    print("✓ Testing imports...")
    try:
        from src.logging import (
            configure_logging,
            get_logger,
            bind_run_context,
            ensure_run_context,
            record_database_query,
            record_embedding_call,
            record_llm_call,
            record_memory_event,
            record_retrieval_event,
            spawn_background_task,
            log_node,
            log_graph,
        )
        from src.logging.context import ExecutionSummary
        from src.logging.formatters import ContextAwareFormatter, StructuredJSONFormatter
        from src.logging.logger import ContextFilter
        from src.logging.db import ObservedCursor, ObservedConnection, instrument_connection
        print("  ✓ All logging modules imported successfully")
        return True
    except Exception as e:
        print(f"  ✗ Import failed: {e}")
        return False


def test_logger_configuration():
    """Test that logger can be configured."""
    print("✓ Testing logger configuration...")
    try:
        from src.logging import configure_logging, get_logger
        configure_logging()
        logger = get_logger("test")
        logger.info("Test log message", extra={"test": True})
        print("  ✓ Logger configured and working")
        return True
    except Exception as e:
        print(f"  ✗ Logger configuration failed: {e}")
        return False


def test_context_propagation():
    """Test that context variables work correctly."""
    print("✓ Testing context propagation...")
    try:
        from src.logging import ensure_run_context, get_run_context, bind_run_context
        
        run_id = ensure_run_context()
        context = get_run_context()
        assert context["run_id"] == run_id, "run_id not in context"
        
        with bind_run_context(graph_name="TestGraph", node_name="test_node"):
            context2 = get_run_context()
            assert context2["graph_name"] == "TestGraph", "graph_name not set"
            assert context2["node_name"] == "test_node", "node_name not set"
        
        print("  ✓ Context propagation working")
        return True
    except Exception as e:
        print(f"  ✗ Context propagation failed: {e}")
        return False


def test_summary_creation():
    """Test that ExecutionSummary can be created and used."""
    print("✓ Testing ExecutionSummary...")
    try:
        from src.logging.context import ExecutionSummary
        from time import perf_counter
        
        summary = ExecutionSummary(run_id="test-run", started_at=perf_counter())
        summary.graphs.add("TestGraph")
        summary.db_queries = 10
        summary.llm_calls = 1
        summary.prompt_tokens = 100
        
        data = summary.as_dict()
        assert data["run_id"] == "test-run", "run_id not in summary"
        assert "TestGraph" in data["graphs"], "graphs not in summary"
        assert data["db_queries"] == 10, "db_queries not in summary"
        
        formatted = summary.format_block()
        assert "EXECUTION SUMMARY" in formatted, "format_block failed"
        
        print("  ✓ ExecutionSummary working")
        return True
    except Exception as e:
        print(f"  ✗ ExecutionSummary failed: {e}")
        return False


def test_persistence_instrumentation():
    """Test that persistence layer is properly instrumented."""
    print("✓ Testing persistence instrumentation...")
    try:
        from src.persistence.semantic_store import conn
        from src.logging.db import ObservedConnection
        
        # Check that conn is instrumented
        assert isinstance(conn, ObservedConnection), "semantic_store.conn not instrumented"
        
        from src.persistence.episodic_store import conn as episodic_conn
        assert isinstance(episodic_conn, ObservedConnection), "episodic_store.conn not instrumented"
        
        print("  ✓ Persistence layer instrumented")
        return True
    except Exception as e:
        print(f"  ✗ Persistence instrumentation failed: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_decorators():
    """Test that decorators can be applied."""
    print("✓ Testing decorators...")
    try:
        from src.logging.decorators import log_node, log_graph, track_call
        
        @log_node(node_name="test_node")
        def test_func(state):
            return state
        
        # Test that decorator doesn't break function
        result = test_func({"test": "data"})
        assert result == {"test": "data"}, "log_node decorator broke function"
        
        print("  ✓ Decorators working")
        return True
    except Exception as e:
        print(f"  ✗ Decorators failed: {e}")
        return False


def main():
    """Run all verification tests."""
    print("\n" + "="*60)
    print("  PRODUCTION LOGGING SYSTEM VERIFICATION")
    print("="*60 + "\n")
    
    tests = [
        test_imports,
        test_logger_configuration,
        test_context_propagation,
        test_summary_creation,
        test_persistence_instrumentation,
        test_decorators,
    ]
    
    results = [test() for test in tests]
    
    print("\n" + "="*60)
    passed = sum(results)
    total = len(results)
    print(f"  RESULTS: {passed}/{total} tests passed")
    print("="*60 + "\n")
    
    if all(results):
        print("✓ All verification tests passed!")
        print("\nYour production logging system is ready to use:")
        print("  1. Call configure_logging() once at startup")
        print("  2. Use get_logger(__name__) in all modules")
        print("  3. Wrap graphs with @log_graph")
        print("  4. Wrap nodes with @log_node")
        print("  5. Database queries are auto-logged")
        print("  6. Execution summary auto-emitted at run end")
        print("\nSee LOGGING.md for complete documentation")
        return 0
    else:
        print("✗ Some tests failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())
