"""
Test Cases for Task CRUD Operations
Run this to test all task management features
"""
import asyncio
from app.services.orchestrator import get_orchestrator


async def run_all_tests():
    orchestrator = get_orchestrator()
    
    print("=" * 80)
    print("TASK CRUD TEST SUITE")
    print("=" * 80)
    
    # ========== TEST 1: Create Tasks with Priority ==========
    print("\n📝 TEST 1: Create Tasks (with and without priority)")
    print("-" * 80)
    
    test_cases_create = [
        "Add buy groceries to my tasks",
        "Add high priority task finish presentation",
        "Create medium priority task call dentist",
        "Add task water plants",
    ]
    
    for test in test_cases_create:
        print(f"\nInput: '{test}'")
        result = await orchestrator.process_transcript(test)
        print(f"Intent: {result['intent']}")
        print(f"Message: {result['handler_response']['message']}")
        if 'data' in result['handler_response']:
            task_data = result['handler_response']['data']
            if 'id' in task_data:
                print(f"✓ Created: {task_data.get('title')} (Priority: {task_data.get('priority') or 'none'})")
    
    print("\n⏸️  Pause to verify tasks in Firestore...")
    await asyncio.sleep(2)
    
    # ========== TEST 2: Complete Tasks ==========
    print("\n\n✅ TEST 2: Complete Tasks (fuzzy matching)")
    print("-" * 80)
    
    test_cases_complete = [
        "Mark buy groceries as done",
        "Complete the presentation task",
        "I finished water plants",
        "Mark groceries complete",  # Should match "buy groceries"
        "Complete shopping",  # Should NOT match (doesn't exist)
    ]
    
    for test in test_cases_complete:
        print(f"\nInput: '{test}'")
        result = await orchestrator.process_transcript(test)
        print(f"Intent: {result['intent']}")
        print(f"Message: {result['handler_response']['message']}")
        if result.get('handler_response', {}).get('data', {}).get('status') == 'completed':
            print(f"✓ Marked complete")
    
    await asyncio.sleep(1)
    
    # ========== TEST 3: Update Tasks ==========
    print("\n\n🔄 TEST 3: Update Tasks (priority & title)")
    print("-" * 80)
    
    test_cases_update = [
        "Change call dentist to high priority",
        "Make water plants low priority",
        "Rename call dentist to schedule dentist appointment",
        "Set presentation to medium priority",  # Already completed, should still work
    ]
    
    for test in test_cases_update:
        print(f"\nInput: '{test}'")
        result = await orchestrator.process_transcript(test)
        print(f"Intent: {result['intent']}")
        print(f"Message: {result['handler_response']['message']}")
        if 'data' in result['handler_response'] and result['handler_response']['data']:
            data = result['handler_response']['data']
            if not data.get('error'):
                print(f"✓ Updated successfully")
    
    await asyncio.sleep(1)
    
    # ========== TEST 4: Delete Tasks ==========
    print("\n\n🗑️  TEST 4: Delete Tasks")
    print("-" * 80)
    
    test_cases_delete = [
        "Delete the old presentation task",
        "Remove water plants",
        "Get rid of dentist",  # Should match "schedule dentist appointment"
        "Delete shopping task",  # Should NOT find anything
    ]
    
    for test in test_cases_delete:
        print(f"\nInput: '{test}'")
        result = await orchestrator.process_transcript(test)
        print(f"Intent: {result['intent']}")
        print(f"Message: {result['handler_response']['message']}")
        if 'deleted_task' in result.get('handler_response', {}).get('data', {}):
            print(f"✓ Deleted successfully")
    
    # ========== TEST 5: Edge Cases ==========
    print("\n\n⚠️  TEST 5: Edge Cases")
    print("-" * 80)
    
    edge_cases = [
        ("Complete nonexistent task", "Mark fake task as done"),
        ("Update nonexistent task", "Change fake task to high priority"),
        ("Delete when empty", "Delete buy groceries"),
        ("Complete with no pending", "Mark anything done"),
    ]
    
    for test_name, test_input in edge_cases:
        print(f"\n{test_name}: '{test_input}'")
        result = await orchestrator.process_transcript(test_input)
        print(f"Message: {result['handler_response']['message']}")
    
    # ========== TEST 6: Priority Filtering via API ==========
    print("\n\n🔍 TEST 6: API Endpoint Tests")
    print("-" * 80)
    print("Test these manually via curl or Postman:")
    print("")
    print("# List all tasks:")
    print("  curl http://localhost:8000/api/tasks")
    print("")
    print("# List high priority tasks:")
    print("  curl 'http://localhost:8000/api/tasks?status=pending'")
    print("")
    print("# Update task (replace {id} with actual task ID):")
    print("  curl -X PATCH http://localhost:8000/api/tasks/{id} \\")
    print("    -H 'Content-Type: application/json' \\")
    print("    -d '{\"priority\": \"high\", \"status\": \"completed\"}'")
    print("")
    print("# Delete task:")
    print("  curl -X DELETE http://localhost:8000/api/tasks/{id}")
    
    print("\n" + "=" * 80)
    print("✅ TEST SUITE COMPLETE")
    print("=" * 80)
    print("\nCheck Firestore console to verify:")
    print("  - Tasks have correct priority values")
    print("  - Completed tasks show status='completed'")
    print("  - Deleted tasks are removed")
    print("  - Updated tasks have new titles/priorities")


if __name__ == "__main__":
    print("\n🚀 Starting Task CRUD Test Suite...\n")
    asyncio.run(run_all_tests())
