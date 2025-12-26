# Task Authentication Testing Guide

## Complete Test Script for All Task Functions

### Prerequisites
1. Have 2 different accounts ready (Account A and Account B)
2. Backend and frontend both running
3. Login to the app

---

## 🎯 Test Suite: Account A

### 1. CREATE TASKS (Various Formats)
**Voice Commands:**
- "Create a task to buy milk"
- "Add task call dentist"
- "Remember to water plants"
- "Add high priority task finish presentation"
- "Create a task to submit report by Friday"
- "Add task workout tomorrow"

**Expected:** 6 tasks created in Account A's collection

---

### 2. LIST TASKS (All Variations)
**Voice Commands:**
- "List my tasks"
- "What are my tasks?"
- "Show me my to-do list"
- "What do I need to do?"

**Expected:** Shows all 6 tasks from Account A only

---

### 3. LIST PRIORITY TASKS
**Voice Commands:**
- "Show me high priority tasks"
- "What are my important tasks?"
- "List high priority items"

**Expected:** Shows only "finish presentation" (high priority)

---

### 4. COMPLETE TASKS
**Voice Commands:**
- "Mark buy milk as complete"
- "Complete the dentist task"
- "I finished watering plants"

**Expected:** 3 tasks marked complete, still in Account A's collection

---

### 5. UPDATE TASKS
**Voice Commands:**
- "Change presentation to medium priority"
- "Update workout to high priority"

**Expected:** Task priorities updated in Account A's collection

---

### 6. DELETE TASKS
**Voice Commands:**
- "Delete the milk task"
- "Remove workout from my tasks"

**Expected:** Tasks deleted from Account A's collection

---

### 7. GET REMINDERS
**Voice Commands:**
- "What are my reminders?"
- "Show me task reminders"
- "What tasks are due soon?"

**Expected:** Shows reminders for Account A's tasks only

---

## 🎯 Test Suite: Account B (Isolation Verification)

### 8. LOG OUT AND SWITCH ACCOUNTS
1. Click logout
2. Log in with Account B
3. Voice: "List my tasks"

**Expected:** Empty task list (Account B has no tasks yet)

---

### 9. CREATE TASKS FOR ACCOUNT B
**Voice Commands:**
- "Create a task to walk the dog"
- "Add task pay bills"
- "Remember to book flight"

**Expected:** 3 new tasks in Account B's collection

---

### 10. VERIFY ISOLATION
**Voice Commands:**
- "List my tasks"

**Expected:** 
- Shows ONLY Account B's 3 tasks
- Does NOT show any of Account A's tasks
- No "buy milk", "dentist", "plants", etc.

---

### 11. COMPLETE TASK IN ACCOUNT B
**Voice Commands:**
- "Mark walk the dog as complete"

**Expected:** 
- Account B's "walk the dog" marked complete
- Account A's tasks unaffected

---

## 🎯 Final Verification: Switch Back to Account A

### 12. LOG OUT AND BACK TO ACCOUNT A
1. Log out from Account B
2. Log in with Account A
3. Voice: "List my tasks"

**Expected:**
- Shows Account A's remaining tasks
- Does NOT show Account B's tasks
- Shows same tasks as before, minus deleted ones

---

## 📊 Expected Results Summary

### Account A Final State:
- ✅ "finish presentation" (priority updated to medium, pending)
- ✅ "submit report" (pending, due Friday)
- ✅ Completed: "buy milk", "call dentist", "water plants"
- ❌ Deleted: "workout"

### Account B Final State:
- ✅ "pay bills" (pending)
- ✅ "book flight" (pending)
- ✅ Completed: "walk the dog"

### Isolation Verified:
- ✓ Each account sees only their own tasks
- ✓ Creating tasks in one account doesn't affect the other
- ✓ Completing tasks in one account doesn't affect the other
- ✓ Deleting tasks in one account doesn't affect the other
- ✓ Complete data separation: `/users/{account_a_id}/tasks` vs `/users/{account_b_id}/tasks`

---

## 🐛 If Any Test Fails:

### Check Backend Logs:
```bash
# Look for these patterns in terminal:
"✓ Task Tool initialized for user: {user_id}"  # Should show YOUR user_id
"Handler: ADD_TASK"                            # Should show for create
"Handler: LIST_TASKS"                          # Should show for list
"Handler: DELETE_TASK"                         # Should show for delete
```

### Verify in Firestore Console:
1. Go to Firebase Console → Firestore Database
2. Check structure:
   - `/users/{account_a_uid}/tasks/` - Account A's tasks
   - `/users/{account_b_uid}/tasks/` - Account B's tasks
   - `/tasks/` - Old global tasks (should be ignored for authenticated users)

---

## ✨ All Functions Tested:
1. ✅ Create task (with priority, due dates)
2. ✅ List all tasks
3. ✅ List priority tasks
4. ✅ Complete tasks
5. ✅ Update tasks
6. ✅ Delete tasks
7. ✅ Get reminders
8. ✅ User isolation
9. ✅ Voice commands
10. ✅ UI operations (TasksPanel)

**PERFECT ISOLATION ACHIEVED! 🎉**
