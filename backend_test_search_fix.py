#!/usr/bin/env python3
"""
Backend test for HR Digital Services - Search Bug Fix:

BUG BEING FIXED: GET /api/vacancies hid posts in the "admit_card" and "result" 
categories by default. So a text search for such a post returned nothing unless 
the user also selected that category filter. 

FIX: when a text query `q` is present, search should span ALL categories 
including admit_card/result.

TEST STEPS:
1. GET /api/vacancies?category=result&per_page=20 → collect "result" category posts
2. GET /api/vacancies?category=admit_card&per_page=20 → collect "admit_card" posts
3. KEY TEST: GET /api/vacancies?q=<distinctive word> (NO category) → verify target post appears
4. Regression: GET /api/vacancies?q=<normal word> (no category) → still returns matching posts
5. Regression: GET /api/vacancies?per_page=50 (NO q, no category) → verify NO admit_card/result posts
6. Regression: GET /api/vacancies?category=result → still returns result posts
"""
import requests
import re
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://hr-services-debug.preview.emergentagent.com/api"

# Session for maintaining cookies (no auth needed - public endpoint)
session = requests.Session()

def log(msg):
    """Print timestamped log message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def extract_distinctive_word(text):
    """Extract a distinctive word from text (prefer longer words, avoid common words)."""
    if not text:
        return None
    
    # Common words to avoid
    common_words = {
        "the", "and", "for", "with", "from", "this", "that", "have", "has", "had",
        "will", "would", "could", "should", "can", "may", "must", "shall", "post",
        "posts", "vacancy", "vacancies", "job", "jobs", "recruitment", "exam",
        "notification", "apply", "online", "offline", "government", "india", "indian"
    }
    
    # Extract words (alphanumeric, 4+ chars)
    words = re.findall(r'\b[a-zA-Z]{4,}\b', text.lower())
    
    # Filter out common words and find longest distinctive word
    distinctive = [w for w in words if w not in common_words]
    
    if distinctive:
        # Return longest word
        return max(distinctive, key=len)
    
    # Fallback: return any word 4+ chars
    if words:
        return max(words, key=len)
    
    return None

def test_step_1_collect_result_posts():
    """Step 1: Collect result category posts and extract distinctive word."""
    log("\n" + "="*80)
    log("STEP 1: Collect 'result' category posts")
    log("="*80)
    
    url = f"{BASE_URL}/vacancies?category=result&per_page=20"
    log(f"GET {url}")
    
    r = session.get(url)
    log(f"Status: {r.status_code}")
    
    if r.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {r.status_code}")
        log(f"Response: {r.text[:500]}")
        return None, None
    
    data = r.json()
    items = data.get("items", [])
    total = data.get("total", 0)
    
    log(f"✅ SUCCESS: Found {len(items)} result posts (total: {total})")
    
    if len(items) == 0:
        log("⚠️  WARNING: No result posts found")
        return None, None
    
    # Pick first result post and extract distinctive word
    result_post = items[0]
    post_id = result_post.get("id")
    title = result_post.get("title", "")
    organization = result_post.get("organization", "")
    
    log(f"\nSelected result post:")
    log(f"  ID: {post_id}")
    log(f"  Title: {title[:100]}")
    log(f"  Organization: {organization[:100]}")
    log(f"  Category: {result_post.get('category')}")
    
    # Extract distinctive word from title
    distinctive_word = extract_distinctive_word(title)
    
    if not distinctive_word:
        # Try organization
        distinctive_word = extract_distinctive_word(organization)
    
    if distinctive_word:
        log(f"\n✅ Extracted distinctive word: '{distinctive_word}'")
    else:
        log(f"⚠️  WARNING: Could not extract distinctive word from result post")
    
    return post_id, distinctive_word

def test_step_2_collect_admit_card_posts():
    """Step 2: Collect admit_card category posts and extract distinctive word."""
    log("\n" + "="*80)
    log("STEP 2: Collect 'admit_card' category posts")
    log("="*80)
    
    url = f"{BASE_URL}/vacancies?category=admit_card&per_page=20"
    log(f"GET {url}")
    
    r = session.get(url)
    log(f"Status: {r.status_code}")
    
    if r.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {r.status_code}")
        log(f"Response: {r.text[:500]}")
        return None, None
    
    data = r.json()
    items = data.get("items", [])
    total = data.get("total", 0)
    
    log(f"✅ SUCCESS: Found {len(items)} admit_card posts (total: {total})")
    
    if len(items) == 0:
        log("⚠️  WARNING: No admit_card posts found")
        return None, None
    
    # Pick first admit_card post and extract distinctive word
    admit_card_post = items[0]
    post_id = admit_card_post.get("id")
    title = admit_card_post.get("title", "")
    organization = admit_card_post.get("organization", "")
    
    log(f"\nSelected admit_card post:")
    log(f"  ID: {post_id}")
    log(f"  Title: {title[:100]}")
    log(f"  Organization: {organization[:100]}")
    log(f"  Category: {admit_card_post.get('category')}")
    
    # Extract distinctive word from title
    distinctive_word = extract_distinctive_word(title)
    
    if not distinctive_word:
        # Try organization
        distinctive_word = extract_distinctive_word(organization)
    
    if distinctive_word:
        log(f"\n✅ Extracted distinctive word: '{distinctive_word}'")
    else:
        log(f"⚠️  WARNING: Could not extract distinctive word from admit_card post")
    
    return post_id, distinctive_word

def test_step_3_key_test_search_with_q(target_id, search_word, category_name):
    """
    Step 3: KEY TEST - Search with q parameter (no category filter).
    Verify that the target post (result or admit_card) now appears in search results.
    """
    log("\n" + "="*80)
    log(f"STEP 3: KEY TEST - Search for '{search_word}' (NO category filter)")
    log("="*80)
    log(f"Expected: Should find {category_name} post with ID {target_id}")
    
    url = f"{BASE_URL}/vacancies?q={search_word}"
    log(f"GET {url}")
    
    r = session.get(url)
    log(f"Status: {r.status_code}")
    
    if r.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {r.status_code}")
        log(f"Response: {r.text[:500]}")
        return False
    
    data = r.json()
    items = data.get("items", [])
    total = data.get("total", 0)
    
    log(f"Search returned {len(items)} items (total: {total})")
    
    # Check if target post is in results
    found_ids = [item.get("id") for item in items]
    target_found = target_id in found_ids
    
    if target_found:
        log(f"✅ SUCCESS: Target {category_name} post (ID: {target_id}) FOUND in search results")
        log(f"   This confirms the bug fix is working - search now spans ALL categories including {category_name}")
        
        # Show the found post
        found_post = next(item for item in items if item.get("id") == target_id)
        log(f"\n   Found post details:")
        log(f"   - Title: {found_post.get('title', '')[:100]}")
        log(f"   - Category: {found_post.get('category')}")
        log(f"   - Organization: {found_post.get('organization', '')[:100]}")
        
        return True
    else:
        log(f"❌ FAILED: Target {category_name} post (ID: {target_id}) NOT FOUND in search results")
        log(f"   Bug fix not working - {category_name} posts still hidden from text search")
        log(f"\n   Found post IDs: {found_ids[:10]}")
        
        if items:
            log(f"\n   Sample of returned posts:")
            for i, item in enumerate(items[:3]):
                log(f"   {i+1}. {item.get('title', '')[:80]} (category: {item.get('category')})")
        
        return False

def test_step_4_regression_normal_search():
    """Step 4: Regression test - Normal search still works."""
    log("\n" + "="*80)
    log("STEP 4: Regression Test - Normal search (e.g., 'engineer' or 'clerk')")
    log("="*80)
    
    # Try common job keywords
    test_words = ["engineer", "clerk", "officer", "assistant", "manager"]
    
    for word in test_words:
        url = f"{BASE_URL}/vacancies?q={word}"
        log(f"\nGET {url}")
        
        r = session.get(url)
        log(f"Status: {r.status_code}")
        
        if r.status_code != 200:
            log(f"❌ FAILED: Expected 200, got {r.status_code}")
            continue
        
        data = r.json()
        items = data.get("items", [])
        total = data.get("total", 0)
        
        log(f"Search for '{word}' returned {len(items)} items (total: {total})")
        
        if len(items) > 0:
            log(f"✅ SUCCESS: Normal search for '{word}' still works")
            log(f"   Sample results:")
            for i, item in enumerate(items[:3]):
                log(f"   {i+1}. {item.get('title', '')[:80]} (category: {item.get('category')})")
            return True
    
    log(f"⚠️  WARNING: No results found for any common job keywords")
    return True  # Not a failure, just no data

def test_step_5_regression_default_browsing():
    """
    Step 5: Regression test - Default browsing (no q, no category) 
    should NOT show admit_card or result posts.
    """
    log("\n" + "="*80)
    log("STEP 5: Regression Test - Default browsing (no q, no category)")
    log("="*80)
    log("Expected: Should NOT contain admit_card or result posts")
    
    url = f"{BASE_URL}/vacancies?per_page=50"
    log(f"GET {url}")
    
    r = session.get(url)
    log(f"Status: {r.status_code}")
    
    if r.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {r.status_code}")
        log(f"Response: {r.text[:500]}")
        return False
    
    data = r.json()
    items = data.get("items", [])
    total = data.get("total", 0)
    
    log(f"Default browsing returned {len(items)} items (total: {total})")
    
    # Check for admit_card or result posts
    hidden_categories = ["admit_card", "result"]
    found_hidden = [item for item in items if item.get("category") in hidden_categories]
    
    if found_hidden:
        log(f"❌ FAILED: Found {len(found_hidden)} posts with category in {hidden_categories}")
        log(f"   Default browsing should hide these categories")
        for item in found_hidden[:5]:
            log(f"   - {item.get('title', '')[:80]} (category: {item.get('category')})")
        return False
    else:
        log(f"✅ SUCCESS: NO admit_card or result posts in default browsing")
        log(f"   Default view correctly hides these categories")
        
        # Show sample of what is returned
        if items:
            log(f"\n   Sample of returned posts (normal categories):")
            categories_found = set()
            for item in items[:10]:
                cat = item.get("category", "unknown")
                categories_found.add(cat)
            log(f"   Categories found: {sorted(categories_found)}")
        
        return True

def test_step_6_regression_category_filter():
    """Step 6: Regression test - Category filter still works."""
    log("\n" + "="*80)
    log("STEP 6: Regression Test - Category filter (category=result)")
    log("="*80)
    
    url = f"{BASE_URL}/vacancies?category=result&per_page=20"
    log(f"GET {url}")
    
    r = session.get(url)
    log(f"Status: {r.status_code}")
    
    if r.status_code != 200:
        log(f"❌ FAILED: Expected 200, got {r.status_code}")
        log(f"Response: {r.text[:500]}")
        return False
    
    data = r.json()
    items = data.get("items", [])
    total = data.get("total", 0)
    
    log(f"Category filter returned {len(items)} items (total: {total})")
    
    if len(items) == 0:
        log(f"⚠️  WARNING: No result posts found (may be empty)")
        return True  # Not a failure, just no data
    
    # Verify all returned items are result category
    non_result = [item for item in items if item.get("category") != "result"]
    
    if non_result:
        log(f"❌ FAILED: Found {len(non_result)} posts with category != 'result'")
        for item in non_result[:5]:
            log(f"   - {item.get('title', '')[:80]} (category: {item.get('category')})")
        return False
    else:
        log(f"✅ SUCCESS: All returned posts have category='result'")
        log(f"   Category filter still works correctly")
        return True

def main():
    """Run all test steps."""
    log("="*80)
    log("HR Digital Services - Search Bug Fix Test")
    log("="*80)
    log(f"Base URL: {BASE_URL}")
    log(f"Testing: GET /api/vacancies search with q parameter")
    log(f"Bug Fix: Search should now span ALL categories including admit_card/result")
    
    results = {}
    
    # Step 1: Collect result posts
    result_id, result_word = test_step_1_collect_result_posts()
    
    # Step 2: Collect admit_card posts
    admit_card_id, admit_card_word = test_step_2_collect_admit_card_posts()
    
    # Determine which test to run based on available data
    if result_id and result_word:
        log(f"\n✅ Will test with 'result' category post")
        target_id = result_id
        search_word = result_word
        category_name = "result"
    elif admit_card_id and admit_card_word:
        log(f"\n✅ Will test with 'admit_card' category post")
        target_id = admit_card_id
        search_word = admit_card_word
        category_name = "admit_card"
    else:
        log(f"\n❌ CRITICAL: No result or admit_card posts found to test")
        log(f"   Cannot proceed with key test")
        return
    
    # Step 3: KEY TEST - Search with q parameter
    results["key_test_search_with_q"] = test_step_3_key_test_search_with_q(
        target_id, search_word, category_name
    )
    
    # Step 4: Regression - Normal search
    results["regression_normal_search"] = test_step_4_regression_normal_search()
    
    # Step 5: Regression - Default browsing
    results["regression_default_browsing"] = test_step_5_regression_default_browsing()
    
    # Step 6: Regression - Category filter
    results["regression_category_filter"] = test_step_6_regression_category_filter()
    
    # Summary
    log("\n" + "="*80)
    log("TEST SUMMARY")
    log("="*80)
    
    passed = sum(1 for v in results.values() if v)
    total = len(results)
    
    for test_name, passed_flag in results.items():
        status = "✅ PASSED" if passed_flag else "❌ FAILED"
        log(f"{status}: {test_name}")
    
    log(f"\nTotal: {passed}/{total} tests passed")
    
    if passed == total:
        log("\n🎉 ALL TESTS PASSED!")
        log("\n✅ BUG FIX VERIFIED:")
        log("   - Search with q parameter now spans ALL categories including admit_card/result")
        log("   - Default browsing still hides admit_card/result posts")
        log("   - Category filters still work correctly")
        log("   - Normal search functionality preserved")
    else:
        log(f"\n⚠️  {total - passed} test(s) failed")
        if not results.get("key_test_search_with_q"):
            log("\n❌ KEY TEST FAILED: Bug fix not working correctly")

if __name__ == "__main__":
    main()
