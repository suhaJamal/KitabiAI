# Phase 5: AI Chatbot - SR&ED Experimentation Guide
## Quick Reference for Future SR&ED Work

**Status**: 🔜 PLANNED (Not yet implemented)
**Estimated SR&ED Time**: 80-120 hours
**Estimated Commercial Time**: 40-60 hours (UI, API, deployment)

---

## Purpose of This Document

This guide helps you maximize SR&ED eligibility when implementing the bilingual AI chatbot feature. Use this as a template for your experiments and documentation.

**Important**: When you start Phase 5, copy the experiment format from [02_EXPERIMENT_LOG.md](02_EXPERIMENT_LOG.md) and track ALL experiments here.

---

## SR&ED-Eligible Work (Track This!)

### Experiment Templates

#### EXP-010: Arabic Embedding Model Selection

**Hypothesis**: Multilingual-E5 will achieve >85% retrieval accuracy (MRR@10) for Arabic book content queries.

**Method**:
1. Create test corpus: 100 questions across 10 Arabic books
2. Generate ground-truth answers (manual human evaluation)
3. Test embedding models:
   - multilingual-e5-large
   - intfloat/multilingual-e5-base
   - sentence-transformers/LaBSE
   - sentence-transformers/paraphrase-multilingual-mpnet-base-v2
   - CAMeL-Lab/bert-base-arabic-camelbert-mix (Arabic-specific)
4. Chunk book content into: sentences, paragraphs, sections
5. Measure retrieval accuracy: MRR@10, Recall@5, Recall@10
6. Compare cost (embedding size, inference time)

**Success Criteria**: >85% MRR@10, <200ms embedding time per query

**Track Time**: Document hours spent on:
- ✅ Research embedding models (SR&ED eligible)
- ✅ Implementing test harness (SR&ED eligible)
- ✅ Running experiments (SR&ED eligible)
- ✅ Analyzing results (SR&ED eligible)
- ❌ Building API endpoint (routine)
- ❌ UI development (routine)

**Expected Result**: One model will win; document why others failed.

---

#### EXP-011: Cross-Lingual Query Translation Strategy

**Hypothesis**: Translating English queries to Arabic before search achieves >80% answer accuracy (vs. monolingual baseline).

**Method**:
1. Test corpus: 50 English questions about Arabic books
2. Test three approaches:
   - **Approach A**: Translate query → search Arabic embeddings → answer in English
   - **Approach B**: Multilingual embeddings (query English, content Arabic, no translation)
   - **Approach C**: Translate book content to English → monolingual search
3. Measure:
   - Answer accuracy (BLEU, ROUGE-L, human eval 1-5 scale)
   - Translation cost (Azure Translator API: $10/1M chars)
   - Latency (total query time)

**Success Criteria**: >80% answer accuracy, <2 seconds total latency

**Failure Modes to Document**:
- Translation loses nuance (literary Arabic → English)
- Multilingual embeddings have lower accuracy
- Cost-prohibitive for production

---

#### EXP-012: Context Window Optimization (Cost vs. Quality)

**Hypothesis**: 5 retrieved sections provide optimal cost-accuracy trade-off for GPT-4 question answering.

**Method**:
1. Test corpus: 100 questions (mix: simple, complex, multi-hop reasoning)
2. Test context sizes: 1, 3, 5, 10, 20 retrieved sections
3. For each size, measure:
   - Answer accuracy (human eval: correct, partial, incorrect)
   - Token cost (input tokens × $0.01/1K + output tokens × $0.03/1K)
   - Answer completeness (does it cite sources? cover all aspects?)
4. Calculate cost per correct answer
5. Find point of diminishing returns

**Success Criteria**: <$0.05/query, >85% accuracy

**Trade-off Analysis**:
```
Expected Results (hypothetical):
1 section: $0.02/query, 60% accuracy (too low)
3 sections: $0.04/query, 75% accuracy (better but below target)
5 sections: $0.06/query, 87% accuracy (optimal?) ✅
10 sections: $0.12/query, 89% accuracy (minimal gain, 2x cost)
20 sections: $0.25/query, 90% accuracy (not worth it)
```

**Document Finding**: Optimal is 5 sections (justifies production parameter).

---

#### EXP-013: Hallucination Detection & Citation Validation

**Hypothesis**: RAG with strict citation validation reduces hallucination rate to <5%.

**Method**:
1. Test corpus: 50 questions designed to trigger hallucinations (e.g., "What does the book say about X?" when X is not mentioned)
2. Test three RAG architectures:
   - **Architecture A**: Pure retrieval (no generation, just return top sections)
   - **Architecture B**: GPT-4 with instruction "Only use provided context, cite page numbers"
   - **Architecture C**: GPT-4 + citation validation (verify page numbers exist and contain quoted text)
3. Measure hallucination rate:
   - Fabricated facts (information not in book)
   - Incorrect citations (page number wrong)
   - Out-of-context answers (uses GPT-4 training data instead of book)
4. Test validation logic:
   ```python
   def validate_citation(answer, book_content):
       # Extract page numbers from answer
       cited_pages = extract_page_numbers(answer)

       # Extract quoted text from answer
       quotes = extract_quotes(answer)

       # Verify each quote exists in cited page
       for quote, page in zip(quotes, cited_pages):
           if quote not in book_content[page]:
               return False  # Hallucination detected
       return True
   ```

**Success Criteria**: <5% hallucination rate, >90% citation accuracy

**Expected Failures**:
- Pure retrieval: Too restrictive, low user satisfaction
- GPT-4 without validation: 20-30% hallucination rate
- GPT-4 with validation: <5% hallucination ✅

---

#### EXP-014: Chunk Size Optimization for Retrieval

**Hypothesis**: Section-level chunking (500-2000 words) achieves better retrieval than sentence or paragraph chunking.

**Method**:
1. Test chunking strategies:
   - Sentences (avg 20-50 words)
   - Paragraphs (avg 100-300 words)
   - Sections from TOC (avg 500-2000 words)
   - Fixed-size windows (512 tokens, 1024 tokens)
2. Generate 100 test questions
3. For each strategy, measure:
   - Retrieval accuracy (MRR@10)
   - Context relevance (does retrieved chunk contain answer?)
   - Answer quality (can LLM answer from this chunk?)
4. Consider trade-offs:
   - Small chunks: More precise retrieval but may miss context
   - Large chunks: More context but may dilute relevance score

**Success Criteria**: >85% retrieval accuracy, >80% answer quality

**Expected Result**: Sections provide best balance (book structure naturally separates topics).

---

## Non-Eligible Routine Work (Do NOT Track as SR&ED)

### Routine Development Activities

These are standard software engineering - do NOT claim as SR&ED:

❌ **API Development**:
- Creating `/api/chat` endpoint
- Request/response schemas
- Error handling
- Rate limiting

❌ **UI Development**:
- Chat interface design
- Message bubbles, typing indicators
- Dark mode, responsive layout
- Copy/share functionality

❌ **Database Schema**:
- `chat_sessions` table
- `chat_messages` table
- User history tracking

❌ **Deployment**:
- OpenAI API key configuration
- Vector database setup (Pinecone, Weaviate, etc.)
- Caching layer (Redis)
- Load balancing

❌ **Testing** (functional, not experimental):
- Unit tests for API
- Integration tests
- User acceptance testing

---

## Experimental Development Checklist

### Before Starting Any Experiment

1. ✅ **Formulate clear hypothesis**
   - What are you testing?
   - What outcome do you expect?
   - Why is it uncertain?

2. ✅ **Define success criteria**
   - Measurable metrics (accuracy %, cost $, latency ms)
   - Threshold values (>85% accuracy, <$0.05/query)

3. ✅ **Design test methodology**
   - Test corpus size and composition
   - Variables to control
   - Metrics to measure

4. ✅ **Start time tracking**
   - Record start time
   - Log activity as "SR&ED: EXP-0XX - [description]"

### During Experiment

1. ✅ **Document everything**
   - Code changes (git commits with experiment ID)
   - Results spreadsheet (quantitative data)
   - Observations (qualitative notes)

2. ✅ **Test systematically**
   - Control variables (change one thing at a time)
   - Measure before/after
   - Run multiple trials for statistical significance

3. ✅ **Track failures**
   - Failed approaches are VALUABLE for SR&ED
   - Document why something didn't work
   - Analyze root causes

### After Experiment

1. ✅ **Analyze results**
   - Compare to success criteria
   - Identify best approach
   - Calculate cost-benefit

2. ✅ **Document findings**
   - Update experiment log (use template from 02_EXPERIMENT_LOG.md)
   - Add to technical obstacles if new uncertainty discovered
   - Record time spent (end time - start time)

3. ✅ **Make decision**
   - Choose best approach with justification
   - If all approaches failed, document and plan next experiment

---

## Time Tracking Template

Copy this format to track Phase 5 time:

```markdown
### Week of [Date]

| Date | Duration | Activity | SR&ED | Ref | Notes |
|------|----------|----------|-------|-----|-------|
| [Date] | 3.0 hrs | Research Arabic embedding models | ✅ | EXP-010 | Compared 5 models, literature review |
| [Date] | 4.0 hrs | Implement embedding test harness | ✅ | EXP-010 | Code to measure MRR@10, Recall@5 |
| [Date] | 2.0 hrs | Run embedding experiments on 100 questions | ✅ | EXP-010 | Tested all 5 models |
| [Date] | 1.0 hr | Analyze experiment results | ✅ | EXP-010 | multilingual-e5 won with 87% MRR@10 |
| [Date] | 2.0 hrs | Build chat API endpoint | ❌ | N/A | Routine API development |
| [Date] | 3.0 hrs | Design chat UI interface | ❌ | N/A | Routine frontend work |

**Week Total**: 15.0 hours
**SR&ED Eligible**: 10.0 hours (67%)
**Non-Eligible**: 5.0 hours (33%)
```

---

## Expected SR&ED vs. Routine Split

**Estimated Time Breakdown** for Phase 5:

| Activity Category | SR&ED Time | Routine Time | Total |
|-------------------|------------|--------------|-------|
| Embedding model experiments | 20 hrs | - | 20 hrs |
| Cross-lingual QA experiments | 15 hrs | - | 15 hrs |
| Context optimization experiments | 12 hrs | - | 12 hrs |
| Hallucination prevention experiments | 15 hrs | - | 15 hrs |
| Chunk size optimization | 10 hrs | - | 10 hrs |
| Response generation experiments | 8 hrs | - | 8 hrs |
| Failed approaches & iteration | 10 hrs | - | 10 hrs |
| Analysis & documentation | 10 hrs | - | 10 hrs |
| **SR&ED Subtotal** | **100 hrs** | - | **100 hrs** |
| Chat API development | - | 15 hrs | 15 hrs |
| Chat UI development | - | 20 hrs | 20 hrs |
| Vector database setup | - | 8 hrs | 8 hrs |
| Caching & optimization (routine) | - | 7 hrs | 7 hrs |
| Testing & deployment | - | 10 hrs | 10 hrs |
| **Routine Subtotal** | - | **60 hrs** | **60 hrs** |
| **Total Phase 5** | **100 hrs** | **60 hrs** | **160 hrs** |

**SR&ED Proportion**: 63% (typical for R&D-heavy features)

---

## Cloud Costs (Eligible Materials)

**Track separately for SR&ED claim**:

### Eligible Experimental Costs

- ✅ OpenAI API (experimental trials): Estimate $50-100
  - Embedding API: $0.0001/1K tokens × test queries
  - GPT-4 API: $0.01-0.03/1K tokens × experiments
- ✅ Azure Translator (experiment trials): $10-20
  - $10/1M characters translated
- ✅ Vector database (test environment): $20/month during experiments
  - Pinecone free tier or paid tier for experiments

### Non-Eligible Production Costs

- ❌ OpenAI API (production queries after launch)
- ❌ Vector database (production hosting)
- ❌ Caching (Redis production)

**Example Cost Tracking**:
```
Experiment EXP-011 (Cross-lingual QA):
- OpenAI embeddings: 50K queries × $0.0001/1K = $5.00
- Azure Translator: 100K chars × $10/1M = $1.00
- GPT-4 API: 500 queries × 2K tokens × $0.01/1K = $10.00
Total eligible cost: $16.00
```

---

## Key Technological Uncertainties (Why This is SR&ED)

### 1. Arabic Embedding Model Performance on Literary Text

**Uncertainty**: Embedding models trained on web text (Wikipedia, news, social media) may not generalize to formal literary Arabic in books.

**Why Unknown**:
- No published benchmarks for Arabic book content retrieval
- Literary Arabic differs significantly from Modern Standard Arabic (MSA) in web training data
- Classical Arabic texts use archaic vocabulary not in modern embeddings

**Experimentation Required**: Test multiple models, measure accuracy, compare to baseline.

### 2. Cross-Lingual Semantic Matching Accuracy

**Uncertainty**: Can English queries retrieve relevant Arabic content with >80% accuracy?

**Why Unknown**:
- Multilingual embeddings have lower accuracy than monolingual (known trade-off)
- Translation quality varies (literary Arabic → English loses nuance)
- No published research on cross-lingual retrieval for Arabic books

**Experimentation Required**: Test translation vs. multilingual embeddings vs. dual-index approaches.

### 3. LLM Context Window Size for Book QA

**Uncertainty**: What is the optimal number of book sections to include in GPT-4 context?

**Why Unknown**:
- More context = better answers but higher cost (linear relationship?)
- Diminishing returns point unknown (5 sections? 10 sections? 20 sections?)
- Book content has unique structure (not web text or documentation)

**Experimentation Required**: Test 1, 3, 5, 10, 20 sections; measure cost-accuracy curve.

### 4. Hallucination Prevention in Book QA

**Uncertainty**: Can we reduce LLM hallucinations to <5% for book content?

**Why Unknown**:
- GPT-4 often fabricates plausible-sounding "facts" not in source material
- Citation validation methods not well-established (especially for Arabic)
- Unknown if strict RAG architecture degrades user experience (too restrictive?)

**Experimentation Required**: Test RAG architectures, measure hallucination rates, validate citations.

### 5. Optimal Chunking Strategy for Arabic Books

**Uncertainty**: Should we chunk by sentences, paragraphs, sections, or fixed-size windows?

**Why Unknown**:
- Small chunks: Precise but may miss context
- Large chunks: Contextual but may dilute relevance
- Arabic sentence boundaries harder to detect (different punctuation)
- Book structure (TOC sections) may or may not align with semantic topics

**Experimentation Required**: Test all strategies, measure retrieval + answer quality.

---

## SR&ED Documentation Checklist

When you complete Phase 5, ensure you have:

1. ✅ **Experiment Log** (like 02_EXPERIMENT_LOG.md)
   - All experiments documented with hypotheses, methods, results
   - Failed approaches included (critical!)
   - Quantitative data (accuracy %, cost $, latency ms)

2. ✅ **Time Tracking** (add to 06_TIME_TRACKING.md)
   - Week-by-week activity log
   - SR&ED vs. routine classification
   - Experiment references

3. ✅ **Code Evidence** (add to 05_CODE_EVIDENCE.md)
   - Source code for experimental test harnesses
   - Git commits showing iteration
   - Comments explaining SR&ED context

4. ✅ **Technical Obstacles** (add to 03_TECHNICAL_OBSTACLES.md)
   - New uncertainties discovered
   - Why standard approaches didn't work
   - Technological challenges overcome

5. ✅ **Failed Approaches** (add to 04_FAILED_APPROACHES.md)
   - Approaches that didn't meet success criteria
   - Root cause analysis
   - Lessons learned

6. ✅ **Financial Tracking**
   - Cloud API costs (experimental only)
   - Salary/time costs
   - Total SR&ED investment

---

## Quick Tips for Maximizing SR&ED Eligibility

### DO This ✅

1. **Formulate hypotheses BEFORE coding**
   - "I believe X will achieve Y because Z"
   - Document in experiment log

2. **Test multiple approaches**
   - Don't just pick one and go
   - Compare 3+ alternatives with data

3. **Measure everything**
   - Accuracy, cost, latency - all quantitative
   - Create spreadsheets with results

4. **Document failures**
   - Failed experiments are VALUABLE
   - Prove you faced genuine uncertainty

5. **Use git commits**
   - Reference experiment IDs in commits
   - Shows iteration over time

### DON'T Do This ❌

1. **Don't start coding without a hypothesis**
   - Random trial-and-error is not systematic investigation

2. **Don't claim routine work as SR&ED**
   - Building API endpoints = routine
   - Testing embedding models = SR&ED
   - Keep them separate!

3. **Don't skip documentation**
   - If you don't document it, you can't claim it
   - Real-time logging is easier than retroactive

4. **Don't mix SR&ED and production costs**
   - Track experimental API calls separately
   - Use separate OpenAI API keys if needed

5. **Don't ignore time tracking**
   - Log hours daily (accurate)
   - Weekly summaries lose detail

---

## Example: Good SR&ED Experiment

### EXP-010: Embedding Model Selection (Example)

**Hypothesis**: multilingual-e5-large will achieve >85% MRR@10 for Arabic book queries.

**Method**:
1. Test corpus: 100 questions across 10 Arabic books (manually created ground truth)
2. Embedding models tested:
   - multilingual-e5-large (1024 dims)
   - multilingual-e5-base (768 dims)
   - LaBSE (768 dims)
   - paraphrase-multilingual-mpnet (768 dims)
   - bert-base-arabic-camelbert (768 dims)
3. Chunk strategy: TOC sections (avg 500-2000 words)
4. Metrics: MRR@10, Recall@5, Recall@10, embedding time

**Results**:
| Model | MRR@10 | Recall@5 | Recall@10 | Embed Time (ms) |
|-------|--------|----------|-----------|-----------------|
| multilingual-e5-large | **87%** ✅ | 82% | 91% | 45ms |
| multilingual-e5-base | 81% | 76% | 88% | 28ms |
| LaBSE | 78% | 71% | 85% | 32ms |
| paraphrase-multilingual-mpnet | 74% | 68% | 82% | 30ms |
| bert-base-arabic-camelbert | 69% | 63% | 79% | 25ms |

**Analysis**:
- multilingual-e5-large achieved 87% MRR@10 (exceeds 85% target) ✅
- Arabic-specific BERT performed worst (69%) - surprising!
  - Root cause: Trained on MSA news text, not literary Arabic
- Trade-off: e5-large is 60% slower than e5-base but +6% accuracy
  - Worth it for quality-focused application

**Decision**: Use multilingual-e5-large for production.

**Time Spent**: 12 hours (all SR&ED eligible)
- 3 hrs: Research models, setup test harness
- 4 hrs: Run experiments
- 2 hrs: Analyze results
- 1 hr: Document findings
- 2 hrs: Investigate why Arabic-BERT failed

**Cost**: $8.50 (eligible SR&ED material)
- Embedding API calls: 100 queries × 5 models × 10 sections = 5000 embeddings
- Cost: 5000 × 1000 tokens × $0.0001/1K = $8.50

---

## Conclusion

Phase 5 chatbot implementation has strong SR&ED potential (estimated 100 hours eligible work). Use this guide to:

1. **Plan experiments systematically** (hypothesis → method → results)
2. **Track time accurately** (SR&ED vs. routine)
3. **Document everything** (experiments, failures, costs)
4. **Maximize claim value** (proper classification)

When you're ready to start Phase 5, refer back to this guide and the main SR&ED documents for templates and examples.

**Good luck with your SR&ED claim and Phase 5 development!** 🚀

---

**Last Updated**: January 12, 2026
**Status**: 📋 Ready for future use
**Next Action**: Implement Phase 5 and track all SR&ED work using this guide
