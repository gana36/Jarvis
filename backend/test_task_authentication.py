"""Test task authentication and user isolation"""
import sys
import os

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from app.services.task_tool import get_task_tool

def test_user_isolation():
    """Test that different users get different task collections"""
    
    print("\n" + "="*60)
    print("TESTING TASK AUTHENTICATION & USER ISOLATION")
    print("="*60)
    
    # Test 1: Default user uses global collection
    print("\n[TEST 1] Default user should use global /tasks collection")
    default_tool = get_task_tool()  # No user_id provided
    print(f"✓ Collection path: {default_tool.collection._path}")
    expected = ('tasks',)
    actual = default_tool.collection._path
    assert actual == expected, f"Expected {expected}, got {actual}"
    print(f"✓ PASS: Default user uses global collection")
    
    # Test 2: User A gets user-scoped collection
    print("\n[TEST 2] User A should use /users/userA/tasks collection")
    user_a_tool = get_task_tool("userA")
    print(f"✓ Collection path: {user_a_tool.collection._path}")
    # Path should be ('users', 'userA', 'tasks')
    assert 'users' in user_a_tool.collection._path, "Should contain 'users'"
    assert 'userA' in user_a_tool.collection._path, "Should contain 'userA'"
    assert 'tasks' in user_a_tool.collection._path, "Should contain 'tasks'"
    print(f"✓ PASS: User A gets scoped collection")
    
    # Test 3: User B gets different collection than User A
    print("\n[TEST 3] User B should use /users/userB/tasks collection")
    user_b_tool = get_task_tool("userB")
    print(f"✓ Collection path: {user_b_tool.collection._path}")
    assert 'userB' in user_b_tool.collection._path, "Should contain 'userB'"
    assert user_a_tool.collection._path != user_b_tool.collection._path, "Collections should differ"
    print(f"✓ PASS: User B gets different scoped collection")
    
    # Test 4: Create tasks for different users
    print("\n[TEST 4] Creating tasks for different users")
    
    # Create task for User A
    task_a = user_a_tool.add_task(
        title="User A's Task",
        status="pending",
        priority="high"
    )
    print(f"✓ Created task for User A: {task_a.get('id')}")
    
    # Create task for User B
    task_b = user_b_tool.add_task(
        title="User B's Task",
        status="pending",
        priority="low"
    )
    print(f"✓ Created task for User B: {task_b.get('id')}")
    
    # Test 5: Verify isolation - User A can't see User B's tasks
    print("\n[TEST 5] Verifying task isolation")
    
    user_a_tasks = user_a_tool.list_tasks()
    user_b_tasks = user_b_tool.list_tasks()
    
    print(f"✓ User A has {len(user_a_tasks)} task(s)")
    print(f"✓ User B has {len(user_b_tasks)} task(s)")
    
    # Check User A can see their task
    user_a_titles = [t['title'] for t in user_a_tasks]
    assert "User A's Task" in user_a_titles, "User A should see their own task"
    assert "User B's Task" not in user_a_titles, "User A should NOT see User B's task"
    print(f"✓ User A can only see their own tasks")
    
    # Check User B can see their task
    user_b_titles = [t['title'] for t in user_b_tasks]
    assert "User B's Task" in user_b_titles, "User B should see their own task"
    assert "User A's Task" not in user_b_titles, "User B should NOT see User A's task"
    print(f"✓ User B can only see their own tasks")
    
    # Cleanup
    print("\n[CLEANUP] Deleting test tasks")
    user_a_tool.delete_task(task_a['id'])
    user_b_tool.delete_task(task_b['id'])
    print(f"✓ Test tasks cleaned up")
    
    print("\n" + "="*60)
    print("✅ ALL TESTS PASSED - USER ISOLATION WORKING!")
    print("="*60)
    

if __name__ == "__main__":
    try:
        test_user_isolation()
    except Exception as e:
        print(f"\n❌ TEST FAILED: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
