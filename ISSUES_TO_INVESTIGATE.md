# Issues to Investigate - Phase 3 Deployment

**Date:** January 8, 2026
**Status:** Post-deployment investigation needed

---

## 🔍 Issue #1: Arabic Language Detection (HIGH PRIORITY)

### Problem:
Arabic PDFs are being misdetected as French/English by FastText language detector.

### Symptoms:
- FastText detecting "fr" (French) with ~50% confidence
- Should detect "ar" (Arabic) for Arabic books
- Current detection results in English TOC extraction being used instead of Arabic extractor

### Current Behavior:
```
Expected: language = "ar" (Arabic)
Actual:   language = "fr" (French) or "en" (English)
```

### Impact:
- **Severity:** Medium (not critical)
- **Workflow:** Still works (uses English extractor as fallback)
- **Quality:** May affect TOC extraction quality for Arabic books
- **User Experience:** Books process correctly, but not with optimal Arabic extraction

### Files Involved:
- [app/services/language_detector.py](app/services/language_detector.py) - FastText model
- [app/services/toc_extractor.py:45](app/services/toc_extractor.py#L45) - Language detection call
- [lid.176.ftz](lid.176.ftz) - FastText language model file

### Investigation Steps:

1. **Check FastText Model:**
   ```bash
   # Check model file size and integrity
   ls -lh lid.176.ftz

   # Expected: ~1MB file
   ```

2. **Test with Sample Arabic Text:**
   ```python
   from app.services.language_detector import language_detector

   # Test with pure Arabic text
   arabic_text = "هذا كتاب باللغة العربية"
   language, text, _ = language_detector.detect(arabic_text.encode())
   print(f"Detected: {language}")  # Should be "ar"
   ```

3. **Check PDF Text Extraction:**
   - Problem might be in text extraction, not language detection
   - Check if extracted text actually contains Arabic characters
   - Might need OCR for scanned Arabic PDFs

4. **Review Language Detector Configuration:**
   - Check threshold settings
   - Review confidence scores
   - Verify model supports Arabic

### Possible Solutions:

**Option A: Fix FastText Model**
- Download correct Arabic language model
- Retrain model with Arabic corpus
- Adjust confidence thresholds

**Option B: Use Azure Document Intelligence**
- Azure Document Intelligence supports Arabic OCR
- Already configured in environment
- Better for scanned Arabic PDFs

**Option C: Add Manual Override**
- Allow users to specify language during upload
- Override automatic detection if needed
- Quick fix while investigating root cause

### Next Steps:

1. Upload Arabic PDF with known Arabic text
2. Check logs for language detection results
3. Extract text and verify it contains Arabic
4. Test FastText with extracted text directly
5. Compare with Azure Document Intelligence results

---

## 🔍 Issue #2: Generation/Preview Status Unclear (MEDIUM PRIORITY)

### Problem:
User reported that generation and preview might not be working after deployment.

### Symptoms:
- Upload works perfectly (verified)
- Generation endpoint status unknown
- Preview functionality status unknown
- Logs only show upload completion

### Current Status:
- ✅ Upload workflow verified working
- ❓ Generation endpoints not tested
- ❓ Preview functionality not tested
- ❓ No error logs available yet

### Files Involved:
- [app/routers/generation.py](app/routers/generation.py) - Generation endpoints
- [app/services/html_generator.py](app/services/html_generator.py) - HTML generation
- [app/services/markdown_generator.py](app/services/markdown_generator.py) - Markdown generation
- [app/services/azure_storage_service.py](app/services/azure_storage_service.py) - File uploads

### Investigation Steps:

1. **Test HTML Generation Endpoint:**
   ```bash
   # After uploading a PDF, call:
   POST /generate-html

   # Check response
   # Expected: {"status": "success", "url": "https://..."}
   ```

2. **Test Markdown Generation Endpoint:**
   ```bash
   POST /generate-markdown

   # Check response
   ```

3. **Test "Generate All Files" Endpoint:**
   ```bash
   POST /generate-and-save

   # Should generate: HTML, Markdown, JSONL (pages), JSONL (sections)
   # Should upload to Azure Blob Storage
   # Should save URLs to database
   ```

4. **Check Azure Blob Storage Containers:**
   - After generation, verify files appear in:
     - `books-html` container
     - `books-markdown` container
     - `books-json` container

5. **Check Database Records:**
   ```sql
   SELECT html_url, markdown_url, pages_jsonl_url, sections_jsonl_url
   FROM books
   WHERE id = <last_uploaded_book_id>;

   -- URLs should be https:// format
   -- URLs should point to Azure Blob Storage
   ```

6. **Review Azure App Service Logs:**
   ```bash
   # Check for errors during generation
   # Azure Portal → App Service → Log stream
   ```

### Possible Issues:

**Issue A: Azure Storage Upload Fails**
- Symptoms: Generation works but files not uploaded
- Check: Azure storage connection string
- Check: Container permissions

**Issue B: Generation Timeout**
- Symptoms: Request times out before completion
- Solution: Already increased timeout to 300s
- Check: If PDF is very large, might need more time

**Issue C: Memory Issues**
- Symptoms: Worker crashes during generation
- Solution: Already reduced to 2 workers
- Check: Monitor memory usage

**Issue D: State Management**
- Symptoms: Generation can't access upload state
- Check: `_last_report`, `_last_book_id` variables
- Issue: In-memory state lost if worker restarts

### Next Steps:

1. **Upload Test PDF:**
   - Use small test PDF (< 50 pages)
   - Verify upload succeeds

2. **Call Generate Endpoints:**
   - Try each generation endpoint individually
   - Check responses for errors

3. **Monitor Logs:**
   - Watch Azure App Service log stream
   - Look for Python errors or exceptions

4. **Verify Azure Storage:**
   - Check if files appear in containers
   - Download generated files to verify content

5. **Test Database:**
   - Query book record
   - Verify URLs are saved correctly

---

## 🔍 Issue #3: Worker Memory Usage (LOW PRIORITY)

### Problem:
Reduced workers from 4 to 2 to prevent 502 errors. Need to monitor if 2 workers are sufficient.

### Current Configuration:
```bash
gunicorn -w 2 -k uvicorn.workers.UvicornWorker app.main:app --bind 0.0.0.0:8000 --timeout 300 --graceful-timeout 300
```

### Monitoring Needed:

1. **Check Azure App Service Metrics:**
   - Azure Portal → App Service → Metrics
   - Monitor: CPU usage, Memory usage
   - Watch for: Memory exhaustion, CPU spikes

2. **Load Testing:**
   - Test with multiple concurrent uploads
   - Verify 2 workers can handle load
   - Check response times

3. **Consider Scaling:**
   - If 2 workers insufficient, options:
     - Scale up: Increase App Service tier (more memory per worker)
     - Scale out: Add more workers (if memory allows)
     - Optimize: Reduce memory usage in code

### Next Steps:

1. Monitor for 1 week
2. Check for any 502 errors
3. Review response times
4. Adjust worker count if needed

---

## 🔍 Issue #4: In-Memory State Management (LOW PRIORITY)

### Problem:
Application uses in-memory variables (`_last_report`, `_last_book_id`) to pass state between upload and generation endpoints.

### Risk:
- If worker restarts, state is lost
- If multiple workers, state might not be shared
- If user's request goes to different worker, state missing

### Files Involved:
- [app/routers/upload.py](app/routers/upload.py) - Sets `_last_report`, `_last_book_id`
- [app/routers/generation.py](app/routers/generation.py) - Reads `_last_report`, `_last_book_id`

### Current Behavior:
```python
# upload.py
_last_report = analysis_report
_last_book_id = book_id

# generation.py
from .upload import _last_report, _last_book_id  # Risky!
```

### Possible Solutions:

**Option A: Use Session/Cookies**
- Store state in user session
- Persists across requests
- Worker-independent

**Option B: Use Database**
- Store intermediate state in database
- Query by user ID or session ID
- Most reliable

**Option C: Use Redis Cache**
- Store in Redis with TTL
- Fast and worker-independent
- Requires Redis service

**Option D: Pass State in Request**
- Client stores state
- Passes book_id in generation requests
- Simple but requires UI changes

### Recommendation:
- **Short term:** Keep current approach (working for now)
- **Long term:** Implement Option B (database) or C (Redis)

### Next Steps:
1. Document current behavior
2. Test with multiple workers
3. Implement proper state management if issues occur

---

## 📊 Investigation Priority

### High Priority (Do First):
1. ✅ Test generation endpoints
2. ✅ Fix Arabic language detection

### Medium Priority (Do Next):
3. ⏳ Monitor worker performance
4. ⏳ End-to-end testing

### Low Priority (Future):
5. ⏳ Implement proper state management
6. ⏳ Code cleanup and optimization

---

## 🧪 Testing Checklist

Before marking Phase 3 as fully complete:

- [ ] Upload Arabic PDF → Verify language detected as "ar"
- [ ] Upload English PDF → Verify language detected as "en"
- [ ] Generate HTML → Verify file appears in `books-html` container
- [ ] Generate Markdown → Verify file appears in `books-markdown` container
- [ ] Generate JSONL → Verify files appear in `books-json` container
- [ ] Check database → Verify URLs are `https://` format
- [ ] Preview HTML → Verify content displays correctly
- [ ] Preview Markdown → Verify content displays correctly
- [ ] Test with large PDF (>200 pages) → Verify no timeout
- [ ] Test with multiple uploads → Verify no memory issues
- [ ] Check Azure costs → Verify within budget

---

## 📝 How to Report Issues

When testing reveals problems:

1. **Capture Error Details:**
   - Full error message
   - Stack trace
   - Request that caused error
   - Browser console logs (if UI issue)

2. **Check Logs:**
   - Azure Portal → App Service → Log stream
   - Copy relevant log entries

3. **Document Reproduction Steps:**
   - What did you do?
   - What did you expect?
   - What actually happened?

4. **Create Issue:**
   - Add to this document
   - Include all details above
   - Tag with priority (HIGH/MEDIUM/LOW)

---

**Next Action:** Test generation endpoints and verify complete workflow! 🧪
