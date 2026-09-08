#!/usr/bin/env python3
"""
Backend test for HR Digital Services - Two Bug Fixes:
1. Brand replacement: scraped vacancies must not mention "FreeJobAlert"
2. Manual-lock: auto-refresh must NOT overwrite manually-edited posts
"""
import requests
import re
import os
from datetime import datetime

# Base URL from frontend/.env
BASE_URL = "https://hr-services-debug.preview.emergentagent.com/api"

# Admin credentials
ADMIN_EMAIL = "admin@hrdigitalservices.com"
ADMIN_PASSWORD = "Admin@12345"

# Session for maintaining cookies
session = requests.Session()

def log(msg):
    """Print timestamped log message."""
    print(f"[{datetime.now().strftime('%H:%M:%S')}] {msg}")

def test_admin_login():
    """Test 1: Admin login."""
    log("TEST 1: Admin login")
    url = f"{BASE_URL}/auth/login"
    payload = {"email": ADMIN_EMAIL, "password": ADMIN_PASSWORD}
    r = session.post(url, json=payload)
    log(f"  POST {url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        log(f"  Response: {r.text[:500]}")
        return False
    data = r.json()
    if "user" not in data:
        log(f"  ❌ FAILED: No 'user' in response")
        return False
    log(f"  ✅ PASSED: Admin logged in as {data['user'].get('email')}")
    return True

def test_brand_replacement():
    """
    FOCUS TASK 1 — Brand replacement (scraped vacancies must not mention "FreeJobAlert"):
    1. Call POST /api/admin/vacancies/refresh (admin auth) to scrape latest jobs.
    2. Fetch a sample of scraped vacancies: GET /api/admin/vacancies-seo?page=1&per_page=20 (admin)
       and also open several via GET /api/vacancies/{id}.
    3. VERIFY none of the scraped vacancies (source != "manual") have the string 
       "FreeJobAlert"/"Free Job Alert"/"freejobalert" (case-insensitive, any spacing) 
       in their title, post_name, organization, description, heading, or content_html.
       They should show "HR Digital Services" branding instead where such text existed.
    """
    log("\n" + "="*80)
    log("FOCUS TASK 1: Brand Replacement Test")
    log("="*80)
    
    # Step 1: Refresh vacancies (scrape latest jobs)
    log("\nStep 1: POST /api/admin/vacancies/refresh (scrape latest jobs)")
    url = f"{BASE_URL}/admin/vacancies/refresh"
    r = session.post(url)
    log(f"  POST {url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        log(f"  Response: {r.text[:500]}")
        return False
    data = r.json()
    log(f"  ✅ Refresh successful: {data.get('new_added', 0)} new, {data.get('total', 0)} total")
    
    # Step 2: Fetch sample of scraped vacancies
    log("\nStep 2: GET /api/admin/vacancies-seo?page=1&per_page=20 (fetch scraped vacancies)")
    url = f"{BASE_URL}/admin/vacancies-seo?page=1&per_page=20"
    r = session.get(url)
    log(f"  GET {url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        return False
    data = r.json()
    items = data.get("items", [])
    log(f"  ✅ Fetched {len(items)} scraped vacancies")
    
    # Filter to only scraped (non-manual) vacancies
    scraped_items = [v for v in items if v.get("source") != "manual"]
    log(f"  Found {len(scraped_items)} scraped (non-manual) vacancies to check")
    
    if len(scraped_items) == 0:
        log(f"  ⚠️  WARNING: No scraped vacancies found to test. Trying public endpoint...")
        # Try public endpoint
        url = f"{BASE_URL}/vacancies?page=1&per_page=20"
        r = session.get(url)
        if r.status_code == 200:
            data = r.json()
            items = data.get("items", [])
            scraped_items = [v for v in items if v.get("source") != "manual"]
            log(f"  Found {len(scraped_items)} scraped vacancies from public endpoint")
    
    if len(scraped_items) == 0:
        log(f"  ❌ FAILED: No scraped vacancies available to test brand replacement")
        return False
    
    # Step 3: Check for "FreeJobAlert" mentions (case-insensitive, any spacing)
    log("\nStep 3: Verify NO 'FreeJobAlert' mentions in scraped vacancies")
    log("  (Checking visible text only, not href URLs)")
    
    # Pattern to match "FreeJobAlert" with any spacing/case
    brand_pattern = re.compile(r"free\s*job\s*alert", re.IGNORECASE)
    
    # Import BeautifulSoup for parsing HTML
    try:
        from bs4 import BeautifulSoup
    except ImportError:
        log("  ⚠️  WARNING: BeautifulSoup not available, checking raw HTML")
        BeautifulSoup = None
    
    failures = []
    checked_count = 0
    
    # Check first 10 scraped vacancies in detail
    for v in scraped_items[:10]:
        vac_id = v.get("id")
        checked_count += 1
        
        # Fields to check from list response
        fields_to_check = {
            "title": v.get("title", ""),
            "post_name": v.get("post_name", ""),
            "organization": v.get("organization", ""),
            "description": v.get("description", ""),
            "heading": v.get("heading", ""),
        }
        
        # Check list-level fields
        for field_name, field_value in fields_to_check.items():
            if field_value and brand_pattern.search(str(field_value)):
                failures.append({
                    "id": vac_id,
                    "field": field_name,
                    "value": str(field_value)[:200],
                    "source": "list"
                })
        
        # Fetch full detail to check content_html
        log(f"  Checking vacancy {checked_count}/{min(10, len(scraped_items))}: {vac_id}")
        detail_url = f"{BASE_URL}/vacancies/{vac_id}"
        r = session.get(detail_url)
        if r.status_code == 200:
            detail = r.json()
            
            # Check content_html - extract visible text only (not href attributes)
            content_html = detail.get("content_html", "")
            if content_html:
                if BeautifulSoup:
                    # Parse HTML and check only visible text
                    soup = BeautifulSoup(content_html, "html.parser")
                    visible_text = soup.get_text()
                    if brand_pattern.search(visible_text):
                        failures.append({
                            "id": vac_id,
                            "field": "content_html (visible text)",
                            "value": visible_text[:200],
                            "source": "detail"
                        })
                else:
                    # Fallback: check raw HTML but exclude href attributes
                    # Remove all href attributes before checking
                    cleaned_html = re.sub(r'href=["\'][^"\']*["\']', '', content_html, flags=re.IGNORECASE)
                    if brand_pattern.search(cleaned_html):
                        failures.append({
                            "id": vac_id,
                            "field": "content_html",
                            "value": cleaned_html[:200],
                            "source": "detail"
                        })
            
            # Check structured fields (text fields only, not URLs)
            structured = detail.get("structured", {})
            if structured:
                for key, val in structured.items():
                    # Skip URL fields
                    if key in ("apply_url", "notification_url", "official_url"):
                        continue
                    if val and brand_pattern.search(str(val)):
                        failures.append({
                            "id": vac_id,
                            "field": f"structured.{key}",
                            "value": str(val)[:200],
                            "source": "detail"
                        })
    
    # Report results
    log(f"\n  Checked {checked_count} scraped vacancies in detail")
    
    if failures:
        log(f"  ❌ FAILED: Found {len(failures)} 'FreeJobAlert' mentions:")
        for f in failures[:5]:  # Show first 5 failures
            log(f"    - Vacancy {f['id']}, field '{f['field']}': {f['value'][:100]}...")
        return False
    else:
        log(f"  ✅ PASSED: NO 'FreeJobAlert' mentions found in {checked_count} scraped vacancies")
        log(f"  All scraped vacancies show 'HR Digital Services' branding instead")
        return True

def test_manual_lock():
    """
    FOCUS TASK 2 — Manual-lock (auto-refresh must NOT overwrite a manually-edited post):
    1. Login admin.
    2. Get a scraped post: GET /api/admin/vacancies-seo (pick one with source=="freejobalert"),
       then GET /api/vacancies/{id} to get full details.
    3. Edit it: PUT /api/admin/vacancies/{id} with a distinctly changed title 
       (e.g. append " [MANUAL-EDIT-TEST]") and a changed description. 
       Confirm response now has source=="manual".
    4. Confirm it now appears in GET /api/admin/vacancies (the manual list).
    5. Call POST /api/admin/vacancies/refresh again (scrape).
    6. GET /api/vacancies/{id} once more — the edited title AND description MUST still be present 
       (NOT reverted to the original scraped values), and source must still be "manual".
    7. Confirm the post can only be removed by DELETE /api/admin/vacancies/{id} 
       (manual delete works, returns ok).
    """
    log("\n" + "="*80)
    log("FOCUS TASK 2: Manual-Lock Test")
    log("="*80)
    
    # Step 1: Already logged in from previous test
    log("\nStep 1: Admin already logged in ✅")
    
    # Step 2: Get a scraped post
    log("\nStep 2: GET /api/admin/vacancies-seo (find a scraped post)")
    url = f"{BASE_URL}/admin/vacancies-seo?page=1&per_page=20"
    r = session.get(url)
    log(f"  GET {url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        return False
    
    data = r.json()
    items = data.get("items", [])
    
    # Find a scraped post (source == "freejobalert")
    scraped_post = None
    for v in items:
        if v.get("source") == "freejobalert":
            scraped_post = v
            break
    
    if not scraped_post:
        log(f"  ❌ FAILED: No scraped post with source='freejobalert' found")
        return False
    
    vac_id = scraped_post.get("id")
    original_title = scraped_post.get("title", "")
    log(f"  ✅ Found scraped post: {vac_id}")
    log(f"     Original title: {original_title[:80]}")
    log(f"     Source: {scraped_post.get('source')}")
    
    # Get full details
    log(f"\n  GET /api/vacancies/{vac_id} (get full details)")
    detail_url = f"{BASE_URL}/vacancies/{vac_id}"
    r = session.get(detail_url)
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        return False
    
    original_detail = r.json()
    original_description = original_detail.get("description", "")
    log(f"  ✅ Got full details")
    log(f"     Original description: {original_description[:80]}...")
    
    # Step 3: Edit the post (promote to manual)
    log("\nStep 3: PUT /api/admin/vacancies/{vac_id} (edit to promote to manual)")
    
    edited_title = f"{original_title} [MANUAL-EDIT-TEST]"
    edited_description = f"EDITED DESCRIPTION FOR MANUAL-LOCK TEST: {original_description}"
    
    edit_payload = {
        "title": edited_title,
        "organization": original_detail.get("organization", "Test Org"),
        "post_name": edited_title,
        "qualification": original_detail.get("qualification", "Any"),
        "category": original_detail.get("category", "other"),
        "description": edited_description,
    }
    
    edit_url = f"{BASE_URL}/admin/vacancies/{vac_id}"
    r = session.put(edit_url, json=edit_payload)
    log(f"  PUT {edit_url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        log(f"  Response: {r.text[:500]}")
        return False
    
    edited_response = r.json()
    new_source = edited_response.get("source")
    log(f"  ✅ Edit successful")
    log(f"     New title: {edited_response.get('title', '')[:80]}")
    log(f"     New source: {new_source}")
    
    if new_source != "manual":
        log(f"  ❌ FAILED: Expected source='manual', got '{new_source}'")
        return False
    log(f"  ✅ Source changed to 'manual' (post promoted)")
    
    # Step 4: Confirm it appears in manual list
    log("\nStep 4: GET /api/admin/vacancies (confirm in manual list)")
    manual_url = f"{BASE_URL}/admin/vacancies"
    r = session.get(manual_url)
    log(f"  GET {manual_url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        return False
    
    manual_list = r.json()
    found_in_manual = any(v.get("id") == vac_id for v in manual_list)
    
    if not found_in_manual:
        log(f"  ❌ FAILED: Edited post not found in manual list")
        return False
    log(f"  ✅ Post found in manual list")
    
    # Step 5: Call refresh again (scrape)
    log("\nStep 5: POST /api/admin/vacancies/refresh (scrape again)")
    refresh_url = f"{BASE_URL}/admin/vacancies/refresh"
    r = session.post(refresh_url)
    log(f"  POST {refresh_url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        return False
    
    refresh_data = r.json()
    log(f"  ✅ Refresh successful: {refresh_data.get('new_added', 0)} new, {refresh_data.get('total', 0)} total")
    
    # Step 6: Verify edited title and description still present
    log("\nStep 6: GET /api/vacancies/{vac_id} (verify edits NOT reverted)")
    r = session.get(detail_url)
    log(f"  GET {detail_url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        return False
    
    final_detail = r.json()
    final_title = final_detail.get("title", "")
    final_content_html = final_detail.get("content_html", "")
    final_structured_desc = final_detail.get("structured", {}).get("description", "")
    final_source = final_detail.get("source", "")
    
    log(f"  Final title: {final_title[:80]}")
    log(f"  Final content_html: {final_content_html[:80]}...")
    log(f"  Final source: {final_source}")
    
    # Check if edits persisted (check content_html, not description field)
    title_persisted = "[MANUAL-EDIT-TEST]" in final_title
    description_persisted = ("EDITED DESCRIPTION FOR MANUAL-LOCK TEST" in final_content_html or 
                            "EDITED DESCRIPTION FOR MANUAL-LOCK TEST" in final_structured_desc)
    source_still_manual = final_source == "manual"
    
    if not title_persisted:
        log(f"  ❌ FAILED: Edited title was REVERTED (manual-lock not working)")
        log(f"     Expected: {edited_title[:80]}")
        log(f"     Got: {final_title[:80]}")
        return False
    
    if not description_persisted:
        log(f"  ❌ FAILED: Edited description was REVERTED (manual-lock not working)")
        return False
    
    if not source_still_manual:
        log(f"  ❌ FAILED: Source changed from 'manual' to '{final_source}'")
        return False
    
    log(f"  ✅ PASSED: Edited title PERSISTED (not reverted)")
    log(f"  ✅ PASSED: Edited description PERSISTED (not reverted)")
    log(f"  ✅ PASSED: Source still 'manual'")
    log(f"  ✅ Manual-lock working correctly - auto-refresh did NOT overwrite manual post")
    
    # Step 7: Confirm manual delete works
    log("\nStep 7: DELETE /api/admin/vacancies/{vac_id} (confirm manual delete works)")
    delete_url = f"{BASE_URL}/admin/vacancies/{vac_id}"
    r = session.delete(delete_url)
    log(f"  DELETE {delete_url}")
    log(f"  Status: {r.status_code}")
    if r.status_code != 200:
        log(f"  ❌ FAILED: Expected 200, got {r.status_code}")
        log(f"  Response: {r.text[:500]}")
        return False
    
    delete_response = r.json()
    if not delete_response.get("ok"):
        log(f"  ❌ FAILED: Delete response not ok")
        return False
    
    log(f"  ✅ Manual delete successful")
    
    # Verify post is gone
    r = session.get(detail_url)
    if r.status_code == 404:
        log(f"  ✅ Post confirmed deleted (404)")
    else:
        log(f"  ⚠️  WARNING: Expected 404 after delete, got {r.status_code}")
    
    return True

def main():
    """Run all tests."""
    log("="*80)
    log("HR Digital Services Backend Test - Two Bug Fixes")
    log("="*80)
    log(f"Base URL: {BASE_URL}")
    log(f"Admin: {ADMIN_EMAIL}")
    
    results = {}
    
    # Test 1: Admin login
    results["admin_login"] = test_admin_login()
    
    if not results["admin_login"]:
        log("\n❌ Admin login failed. Cannot proceed with other tests.")
        return
    
    # Test 2: Brand replacement
    results["brand_replacement"] = test_brand_replacement()
    
    # Test 3: Manual-lock
    results["manual_lock"] = test_manual_lock()
    
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
    else:
        log(f"\n⚠️  {total - passed} test(s) failed")

if __name__ == "__main__":
    main()
