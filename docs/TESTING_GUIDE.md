# Week 3-4 Testing Guide - Step-by-Step Instructions

**Purpose:** Practical guide to test toast notifications and validation
**Duration:** ~2-3 hours for complete testing
**Prerequisites:** Application running locally on http://localhost:5000

---

## 🚀 Before You Start

### 1. Start the Application
```bash
# Make sure you're in the project directory
cd /home/jibran/work/rws/github/ccr

# Start with podman-compose
podman-compose up -d

# OR start manually
python run.py
```

### 2. Open Browser
- Open Chrome or Firefox
- Navigate to: http://localhost:5000
- Open Developer Tools (F12)
- Go to Console tab

### 3. Verify Libraries Loaded
You should see in console:
```
✅ Validation library loaded (SQL injection protection allows legitimate AND/OR operators)
Initializing Common Configuration Repository (CCR) with validation...
```

If you DON'T see these messages, STOP and check script loading (we'll fix in Option 2).

---

## 📋 PHASE 1: Quick Smoke Test (5 minutes)

**Goal:** Verify basic functionality before detailed testing

### Test 1.1: Toast System Works
1. Open browser console
2. Type: `showSuccess("Test message")`
3. Press Enter

**Expected Result:**
- ✅ Green toast appears in top-right corner
- ✅ Shows "Success" title
- ✅ Shows "Test message"
- ✅ Has checkmark icon (✓)
- ✅ Has progress bar animating
- ✅ Disappears after ~5 seconds

**If this doesn't work:** Script loading issue or CSS issue. Skip to Option 2/3.

---

### Test 1.2: Error Toast Works
1. In console: `showError("Test error")`

**Expected Result:**
- ✅ Red toast appears
- ✅ Shows "Error" title
- ✅ Has X icon (✕)
- ✅ Stays longer (~8 seconds)

---

### Test 1.3: Validation Library Works
1. In console: `ValidationLib.validateSearchQuery("test")`
2. Should return: `{valid: true, error: null, sanitized: "test"}`

3. In console: `ValidationLib.validateSearchQuery("'; DROP TABLE apis; --")`
4. Should return: `{valid: false, error: "...", sanitized: "..."}`

**If this doesn't work:** Validation library not loaded properly.

---

### Test 1.4: Basic Search Works
1. In the search box, type: `user`
2. Click "Search" button

**Expected Result:**
- ✅ Search executes (no errors in console)
- ✅ Results display (or "No results found")
- ✅ No toast appears (search is valid)

**If this works, continue to Phase 2. If not, check console for errors.**

---

## 📋 PHASE 2: Toast Notification Testing (30 minutes)

### Test 2.1: All Toast Types

**Success Toast:**
```javascript
// In console:
showSuccess("Operation completed successfully")
```
- ✅ Green background
- ✅ Checkmark icon
- ✅ Disappears in ~5 seconds

**Error Toast:**
```javascript
showError("Something went wrong")
```
- ✅ Red background
- ✅ X icon
- ✅ Disappears in ~8 seconds

**Warning Toast:**
```javascript
showWarning("Please review your input")
```
- ✅ Orange/yellow background
- ✅ Warning icon (⚠)
- ✅ Disappears in ~6 seconds

**Info Toast:**
```javascript
showInfo("Here is some information")
```
- ✅ Blue background
- ✅ Info icon (ℹ)
- ✅ Disappears in ~5 seconds

---

### Test 2.2: Toast Features

**Manual Dismiss:**
1. Run: `showSuccess("Click me to dismiss", {duration: 0})`
2. Click anywhere on the toast
3. ✅ Toast should fade out and disappear

**Progress Bar:**
1. Run: `showSuccess("Watch the progress bar")`
2. Watch the bottom of the toast
3. ✅ Progress bar should shrink from right to left over 5 seconds

**Custom Duration:**
1. Run: `showSuccess("Fast toast", {duration: 2000})`
2. ✅ Should disappear after 2 seconds (not 5)

**Custom Title:**
1. Run: `showSuccess("Custom message", {title: "My Title"})`
2. ✅ Should show "My Title" instead of "Success"

**No Auto-Dismiss:**
1. Run: `showError("Permanent error", {duration: 0})`
2. ✅ Toast should stay until clicked
3. Click to dismiss

---

### Test 2.3: Multiple Toasts (Toast Stacking)

**Test Stack Behavior:**
1. Quickly run these commands:
```javascript
showSuccess("Toast 1")
showInfo("Toast 2")
showWarning("Toast 3")
```

**Expected Result:**
- ✅ All 3 toasts appear
- ✅ Stacked vertically (top-right corner)
- ✅ Oldest at bottom, newest at top
- ✅ Each dismisses independently

**Test Max Toasts (5 limit):**
```javascript
for(let i = 1; i <= 7; i++) {
  showInfo(`Toast ${i}`)
}
```

**Expected Result:**
- ✅ Only 5 toasts visible at once
- ✅ Toast 1 and 2 should be automatically dismissed
- ✅ Toasts 3-7 should be visible

---

### Test 2.4: XSS Protection

**HTML in Message:**
```javascript
showError("<script>alert('XSS')</script>")
```
- ✅ Should show the text literally (not execute script)
- ✅ Should display: `<script>alert('XSS')</script>` as text

**HTML in Title:**
```javascript
showSuccess("Message", {title: "<b>Bold Title</b>"})
```
- ✅ Should show: `<b>Bold Title</b>` as text (not bold)
- ✅ Should NOT render HTML

**Special Characters:**
```javascript
showError("Error: <>&\"'")
```
- ✅ Should display all characters correctly
- ✅ No console errors

---

### Test 2.5: Toast Position & Responsiveness

**Desktop (Full Screen):**
1. Make browser window full screen
2. Show a toast: `showSuccess("Desktop test")`
3. ✅ Toast appears in top-right corner
4. ✅ Doesn't overlap with page content

**Narrow Window (Tablet Size):**
1. Resize browser to ~768px width
2. Show a toast
3. ✅ Toast remains visible
4. ✅ Adjusts width if needed

**Mobile Size:**
1. Open browser DevTools (F12)
2. Toggle device toolbar (Ctrl+Shift+M)
3. Select iPhone or Android device
4. Show a toast
5. ✅ Toast visible and readable
6. ✅ Doesn't break layout

**Scrolling:**
1. Show a toast
2. Scroll page up and down
3. ✅ Toast stays in fixed position (doesn't scroll with page)

---

## 📋 PHASE 3: Validation Testing (45 minutes)

### Test 3.1: Valid Search Queries (Should All Work)

**Test each of these queries in the search box:**

1. Empty search (just click Search with empty box)
   - ✅ Returns all results
   - ✅ No error toast

2. Simple text: `user`
   - ✅ Searches successfully
   - ✅ No error toast

3. Attribute search: `Platform = IP4`
   - ✅ Searches successfully
   - ✅ Filters to IP4 only

4. Logical AND: `Platform = IP4 AND Environment = prd`
   - ✅ Searches successfully
   - ✅ No error about "SQL injection"
   - ✅ This is CRITICAL - AND should be allowed

5. Logical OR: `Status = RUNNING OR Status = DEPLOYING`
   - ✅ Searches successfully
   - ✅ No error about "SQL injection"
   - ✅ This is CRITICAL - OR should be allowed

6. Comparison: `Version >= 2.0`
   - ✅ Searches successfully

7. Contains: `APIName contains user`
   - ✅ Searches successfully

8. Property search: `Properties : owner = team-alpha`
   - ✅ Searches successfully

**If ANY of these fail with "SQL injection" error, there's a bug in validation.js**

---

### Test 3.2: Invalid Queries (Should Show Error Toast)

**Test each of these - they should all be BLOCKED:**

1. SQL Comment: `test --comment`
   - ✅ Shows error toast
   - ✅ Search input border turns red
   - ✅ Search is blocked (doesn't execute)

2. Union injection: `' UNION SELECT * FROM users`
   - ✅ Blocked with error toast

3. Semicolon attack: `test; DROP TABLE apis`
   - ✅ Blocked with error toast

4. Tautology: `' OR '1'='1`
   - ✅ Blocked with error toast

5. Delete command: `test; DELETE FROM apis`
   - ✅ Blocked with error toast

6. HTML tags: `<script>alert('xss')</script>`
   - ✅ Sanitized (not necessarily blocked, but sanitized)
   - ✅ No script execution

7. Too long (501+ characters):
   - Type 501 characters in search box
   - ✅ Shows "Search query must not exceed 500 characters"
   - ✅ Blocked with error toast

---

### Test 3.3: Real-time Validation Feedback

**Test visual feedback:**

1. Start typing valid query: `Platform = IP4`
   - ✅ Input stays normal (white background, default border)

2. Continue typing to make invalid: `Platform = IP4; DROP TABLE`
   - ✅ After ~500ms, input border turns RED
   - ✅ Background changes to light red/pink
   - ✅ Console shows warning

3. Delete the invalid part: remove `; DROP TABLE`
   - ✅ After ~500ms, red border disappears
   - ✅ Background returns to white
   - ✅ Input looks normal again

4. Type very fast: type entire query in under 500ms
   - ✅ Validation should NOT trigger during typing
   - ✅ Should only validate 500ms after you STOP typing

**This debounce behavior is important for UX!**

---

### Test 3.4: Search Submission Validation

**Test submission blocking:**

1. Enter invalid query: `'; DROP TABLE apis; --`
2. Click "Search" button

**Expected Result:**
- ✅ Search is BLOCKED (doesn't execute)
- ✅ Error toast appears with message
- ✅ Focus returns to search input
- ✅ Input border is red
- ✅ No results displayed (search didn't happen)
- ✅ Console shows no API request

3. Now type valid query: `Platform = IP4`
4. Click "Search" button

**Expected Result:**
- ✅ Search executes normally
- ✅ No error toast
- ✅ Red border clears
- ✅ Results display
- ✅ Console shows API request

---

### Test 3.5: Sanitization

**Test input sanitization:**

1. Enter: `   user   api   ` (extra spaces)
   - ✅ Click search
   - ✅ Spaces should be trimmed/normalized

2. Enter: `<b>test</b>`
   - ✅ HTML tags should be stripped
   - ✅ Becomes: `test`

3. Copy/paste text with weird characters
   - ✅ Should be sanitized
   - ✅ No console errors

---

### Test 3.6: Filter Input Validation

**Test column filters:**

1. Click filter icon on "API Name" column
2. In the filter search box, type: `test`
   - ✅ Dropdown filters correctly
   - ✅ No errors

3. In filter search box, type: `<script>alert('xss')</script>`
   - ✅ Should be sanitized
   - ✅ No script execution
   - ✅ Dropdown still works

4. Type 101+ characters in filter search
   - ✅ Should show error (max 100 for filters)

5. Type SQL injection in filter: `' OR '1'='1`
   - ✅ Should be blocked with error

**Repeat for Platform and Environment filters**

---

## 📋 PHASE 4: Integration Testing (30 minutes)

### Test 4.1: Complete User Flows

**Flow 1: Successful Search**
1. Open application
2. Type valid query: `Platform = IP4 AND Environment = prd`
3. Click Search
4. ✅ Search executes
5. ✅ Results display
6. ✅ No error toasts
7. ✅ Stats show correct count

**Flow 2: Invalid Search → Fix → Successful Search**
1. Type invalid: `test; DROP TABLE apis`
2. Click Search
3. ✅ Error toast appears
4. ✅ Search blocked
5. Fix the query: `test`
6. Click Search
7. ✅ Red border clears
8. ✅ Search executes successfully
9. ✅ No error toast

**Flow 3: Apply Filters with Validation**
1. Perform a search: `user`
2. Apply API Name filter (select some values)
3. ✅ Results filter correctly
4. Apply Platform filter
5. ✅ Results update
6. Click "Clear ALL"
7. ✅ Filters clear
8. ✅ Search query clears
9. ✅ All results show

**Flow 4: Export with Toast Feedback**
1. Perform a search
2. Click "Export JSON"
3. ✅ Success toast appears
4. ✅ File downloads
5. Click "Export CSV"
6. ✅ Success toast appears
7. ✅ File downloads

---

### Test 4.2: Error Handling Integration

**Backend Error Simulation:**
1. Stop the backend: `podman-compose down`
2. Try to search
3. ✅ Error toast should appear
4. ✅ Message should indicate connection error
5. Restart backend: `podman-compose up -d`
6. Search again
7. ✅ Should work normally

**Network Error:**
1. Open DevTools → Network tab
2. Set throttling to "Offline"
3. Try to search
4. ✅ Error toast appears
5. Set back to "No throttling"

---

### Test 4.3: Backward Compatibility

**Legacy displayError function:**
```javascript
// In console:
displayError("Legacy error message")
```
- ✅ Should show error toast (red)
- ✅ Works like showError()

---

## 📋 PHASE 5: Edge Cases & Stress Testing (20 minutes)

### Test 5.1: Edge Cases

**Empty and Whitespace:**
1. Enter empty search, click Search
   - ✅ Returns all results

2. Enter only spaces: `     `, click Search
   - ✅ Treated as empty, returns all

**Exactly at Limits:**
1. Enter exactly 500 characters
   - ✅ Should work (at the limit)

2. Enter 501 characters
   - ✅ Error: "must not exceed 500 characters"

**Special Characters:**
1. Enter emoji: `🚀 rocket api`
   - ✅ Should work (or be sanitized)

2. Enter Chinese: `用户 API`
   - ✅ Should work

3. Enter all operators: `= != > < >= <= : AND OR`
   - ✅ Should work (these are valid)

---

### Test 5.2: Stress Testing

**Rapid Clicking:**
1. Type valid query
2. Click Search button 10 times rapidly

**Expected Result:**
- ✅ Should NOT freeze UI
- ✅ Should NOT show 10 toasts
- ✅ Should handle gracefully (queue or ignore duplicates)

**Toast Spam:**
```javascript
// In console:
for(let i = 0; i < 20; i++) {
  showError(`Error ${i}`)
}
```
- ✅ Should cap at 5 toasts
- ✅ Browser should NOT crash
- ✅ Older toasts dismissed automatically

**Long Session:**
1. Use app for 10 minutes
2. Perform 20+ searches
3. Apply/clear filters multiple times
4. Show various toasts

**Check:**
- ✅ App remains responsive
- ✅ No memory leaks (check DevTools → Memory)
- ✅ No console errors accumulating

---

### Test 5.3: Browser Testing

**Chrome/Edge (Chromium):**
- Test all above scenarios
- ✅ Note: Should work perfectly (primary development browser)

**Firefox:**
- Test key scenarios:
  - Toast display
  - Validation
  - Search with AND/OR
- ✅ Note any differences

**Safari (if available):**
- Test basic functionality
- ✅ Note any differences

---

## 📋 PHASE 6: Regression Testing (15 minutes)

**Verify existing features still work:**

### Test 6.1: Search Features
- [ ] Simple text search works
- [ ] Attribute search works
- [ ] AND/OR logic works
- [ ] Regex patterns work
- [ ] Pagination works
- [ ] Results per page works

### Test 6.2: UI Features
- [ ] Results table displays
- [ ] "View Details" opens JSON modal
- [ ] Properties modal works
- [ ] Stats counter accurate
- [ ] Help section toggles

### Test 6.3: Filters
- [ ] API Name filter works
- [ ] Platform filter works
- [ ] Environment filter works
- [ ] Multiple filters work together
- [ ] Clear filter works
- [ ] Clear ALL works

---

## 📝 RESULTS DOCUMENTATION

### Create Test Results File

**File:** `WEEK_3-4_TEST_RESULTS.md`

```markdown
# Week 3-4 Test Results

**Date:** [DATE]
**Tester:** Jibran
**Browser:** Chrome [VERSION]
**Environment:** Development (localhost:5000)

---

## Summary

- Total Tests: [NUMBER]
- Passed: [NUMBER]
- Failed: [NUMBER]
- Blocked: [NUMBER]

---

## Phase 1: Smoke Test
- ✅ Toast system works
- ✅ Error toast works
- ✅ Validation library works
- ✅ Basic search works

## Phase 2: Toast Notifications
- ✅ All toast types display correctly
- ✅ Toast features work (duration, dismiss, progress)
- ✅ Multiple toasts stack correctly
- ✅ XSS protection works
- ✅ Responsive on all screen sizes

## Phase 3: Validation
- ✅ Valid queries allowed (including AND/OR)
- ✅ Invalid queries blocked
- ✅ Real-time feedback works
- ✅ Sanitization works
- ✅ Filter validation works

## Phase 4: Integration
- ✅ Complete user flows work
- ✅ Error handling works
- ✅ Backward compatibility maintained

## Phase 5: Edge Cases
- ✅ Edge cases handled
- ✅ Stress testing passed
- ✅ Works in multiple browsers

## Phase 6: Regression
- ✅ All existing features still work
- ✅ No breaking changes

---

## Bugs Found

### Bug #1: [TITLE]
- **Severity:** [Critical/High/Medium/Low]
- **Description:** [Description]
- **Steps to Reproduce:** [Steps]
- **Expected:** [Expected behavior]
- **Actual:** [Actual behavior]
- **Status:** [Open/Fixed/Deferred]

(Add more as needed)

---

## Performance Notes

- Page load time: [TIME] ms
- Search response: [TIME] ms
- Toast animation: Smooth / Laggy
- Memory after 10 min: [SIZE] MB
- Any slowdowns: Yes / No

---

## Recommendations

1. [Recommendation 1]
2. [Recommendation 2]
3. [Recommendation 3]

---

## Conclusion

Week 3-4 milestone is: **COMPLETE** / **NEEDS FIXES**

Ready to commit: **YES** / **NO**

Next steps:
1. [Step 1]
2. [Step 2]
```

---

## ✅ Testing Complete!

**After finishing all tests:**

1. Document results in `WEEK_3-4_TEST_RESULTS.md`
2. Fix any critical/high bugs found
3. Re-test the fixes
4. Move to Option 2: Verify script load order
5. Move to Option 3: Review CSS completeness
6. Commit changes to Git

---

## 🆘 If You Encounter Issues

### Toast Doesn't Appear
- Check: Is toast.js loaded? (View page source)
- Check: Console errors?
- Check: CSS loaded?
- Solution: Check script order (Option 2) and CSS (Option 3)

### Validation Doesn't Work
- Check: Is validation.js loaded?
- Check: Console shows "Validation library loaded"?
- Solution: Check script order (Option 2)

### Red Border Doesn't Appear
- Check: CSS for input validation styles
- Solution: Review CSS (Option 3)

### Legitimate AND/OR Blocked
- Bug in validation.js containsSqlInjection()
- Check line 111-161 in validation.js
- May need to adjust patterns

---

**Good luck with testing! Take your time and be thorough. 🎉**
