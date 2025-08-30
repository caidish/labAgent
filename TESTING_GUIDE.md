# ArXiv Daily Update System - Testing Guide

## Prerequisites

### 1. Environment Setup
```bash
# Navigate to project directory
cd /Users/caijiaqi/Documents/GitHub/labAgent

# Verify Python environment and dependencies
python --version  # Should be 3.8+
pip list | grep -E "(streamlit|openai|beautifulsoup4|requests)"
```

### 2. Required Configuration
Create/verify `.env` file in project root:
```bash
# Check if .env exists
ls -la .env

# If not, copy from example
cp .env.example .env
```

**CRITICAL**: Add your OpenAI API key to `.env`:
```
OPENAI_API_KEY=sk-your-openai-api-key-here
OPENAI_MODEL=gpt-4o
DEBUG=true
LOG_LEVEL=DEBUG
```

### 3. Verify File Structure
Ensure all components exist:
```bash
# Check core files
ls -la lab_agent/tools/arxiv_daily_scraper.py
ls -la lab_agent/tools/paper_scorer.py  
ls -la lab_agent/tools/daily_report_generator.py
ls -la lab_agent/agents/arxiv_daily_agent.py
ls -la lab_agent/config/interestKeywords.txt
ls -la lab_agent/config/promptArxivRecommender.txt
```

---

## Testing Protocol

### **Test 1: Basic System Startup**

**Objective**: Verify the system starts without errors

```bash
# Start the web application
streamlit run lab_agent/web/app.py
```

**Expected Results**:
- ✅ Browser opens to http://localhost:8501
- ✅ No error messages in terminal
- ✅ Web interface loads with tabs: "🏠 Overview", "📚 ArXiv Daily", "🔧 Tools", "📋 Logs"
- ✅ ArXiv agent initializes successfully (check terminal logs)

**Failure Signs**:
- ❌ ImportError or ModuleNotFoundError
- ❌ "ArXiv agent not available" error message
- ❌ OpenAI API key errors

---

### **Test 2: Manual Report Generation**

**Objective**: Generate your first daily report

**Steps**:
1. Navigate to **📚 ArXiv Daily** tab
2. Click **🔄 Generate Daily Report** button
3. Wait for processing (2-5 minutes expected)

**Expected Results**:
- ✅ Spinner shows "Generating daily report... This may take a few minutes."
- ✅ Success message: "✅ Generated daily report with X papers"
- ✅ Summary shows: "📊 Summary: X papers | Priority 3: Y | Priority 2: Z | Priority 1: W"
- ✅ Report appears in expandable section with today's date

**Expected Timing**:
- ArXiv scraping: 10-30 seconds
- GPT-4 scoring: 1-3 minutes (depends on number of papers)
- Report generation: < 5 seconds

**Failure Signs**:
- ❌ "No papers found or failed to fetch papers"
- ❌ OpenAI API errors (check API key and credits)
- ❌ Network timeout errors
- ❌ Permission errors creating reports directory

---

### **Test 3: Report Viewing and Navigation**

**Objective**: Verify report display functionality

**Steps**:
1. Expand the report section for today's date
2. Check summary metrics (Total Papers, Priority 3, 2, 1)
3. Click **📄 View HTML Report**
4. Click **📋 View JSON Data**
5. Review "🔴 Top Priority Papers" section

**Expected Results**:
- ✅ Metrics display correctly with numbers
- ✅ HTML report renders in embedded viewer with:
  - Professional styling and color coding
  - Priority sections (red=3, orange=2, gray=1)
  - Paper titles, authors, abstracts
  - AI assessment reasons
  - Working links to ArXiv abstracts and PDFs
- ✅ JSON data shows structured format
- ✅ Top priority papers show with AI reasoning

**Quality Checks**:
- Papers should be relevant to 2D materials/condensed matter
- Priority 3 papers should be most relevant (graphene, TMDs, etc.)
- AI reasons should make sense and be research-specific
- Links should work when clicked

---

### **Test 4: Duplicate Prevention**

**Objective**: Verify reports aren't regenerated if they exist

**Steps**:
1. Click **🔄 Generate Daily Report** again (same day)
2. Check response time and message

**Expected Results**:
- ✅ Much faster response (< 5 seconds)
- ✅ Message indicates existing report was loaded
- ✅ Same report content appears
- ✅ No duplicate processing

---

### **Test 5: Clear Reports Functionality**

**Objective**: Test report cleanup

**Steps**:
1. Click **🗑️ Clear All Reports**
2. Check that reports disappear
3. Verify file system cleanup

**Expected Results**:
- ✅ Success message: "✅ Cleared X report files"
- ✅ Report sections disappear from interface
- ✅ Files removed from `./reports/` directory

```bash
# Verify cleanup
ls -la ./reports/
# Should be empty or directory shouldn't exist
```

---

### **Test 6: Configuration Validation**

**Objective**: Verify keyword and prompt configuration

**Steps**:
1. Check keyword file content:
```bash
cat lab_agent/config/interestKeywords.txt
```

2. Check prompt template:
```bash
cat lab_agent/config/promptArxivRecommender.txt
```

3. Generate a report and verify scoring aligns with keywords

**Expected Results**:
- ✅ Keywords include 2D materials, graphene, TMDs, etc.
- ✅ Prompt mentions lab research focus
- ✅ High priority papers match keyword themes
- ✅ AI explanations reference relevant keywords

---

### **Test 7: Error Handling**

**Objective**: Test system resilience

**Test 7a: Network Issues**
```bash
# Temporarily disconnect internet, then try generating report
# Should show appropriate error messages
```

**Test 7b: Invalid API Key**
```bash
# Temporarily set wrong API key in .env
OPENAI_API_KEY=invalid-key
# Restart app, should show clear error message
```

**Test 7c: ArXiv Site Issues**
```bash
# Test with invalid ArXiv URL (modify agent code temporarily)
# Should handle gracefully with error message
```

---

## Performance Benchmarks

### **Expected Performance**:
- **Startup Time**: < 10 seconds
- **ArXiv Scraping**: 10-30 seconds (typically 20-50 papers)
- **GPT-4 Scoring**: 1-3 minutes (batch processing with rate limits)
- **Report Generation**: < 5 seconds
- **Total Time**: 2-4 minutes for complete report

### **Resource Usage**:
- **Memory**: ~200-500 MB (Streamlit + processing)
- **Network**: ~1-5 MB (ArXiv page + OpenAI API calls)
- **Storage**: ~500KB-2MB per report (HTML + JSON)

---

## Validation Checklist

Mark each item as you complete testing:

### **Basic Functionality**
- [ ] System starts without errors
- [ ] ArXiv agent initializes successfully
- [ ] Can generate daily report
- [ ] Reports display correctly in web UI
- [ ] HTML report renders properly
- [ ] JSON data is well-structured
- [ ] Clear reports functionality works

### **Content Quality**
- [ ] Papers are relevant to research interests
- [ ] Priority 3 papers are most relevant
- [ ] Priority 1 papers are least relevant
- [ ] AI reasoning is sensible and specific
- [ ] ArXiv links work correctly
- [ ] Report formatting is professional

### **Performance**
- [ ] Complete report generation under 5 minutes
- [ ] Duplicate prevention works
- [ ] System handles 20+ papers efficiently
- [ ] No memory leaks during extended use

### **Error Handling**
- [ ] Graceful handling of network issues
- [ ] Clear error messages for API problems
- [ ] System recovers from failures
- [ ] Logging provides useful debugging info

---

## Common Issues and Solutions

### **Issue**: "ArXiv agent not available"
**Solution**: Check OpenAI API key in `.env` file and verify it's valid

### **Issue**: "No papers found"
**Solution**: Check internet connection and verify ArXiv website is accessible

### **Issue**: GPT-4 scoring takes too long
**Solution**: Normal for 20+ papers. Batch processing includes rate limiting delays

### **Issue**: Reports directory permission errors
**Solution**: Ensure write permissions in project directory

### **Issue**: High Priority papers seem irrelevant
**Solution**: Review and update keywords in `lab_agent/config/interestKeywords.txt`

---

## Success Criteria

**✅ PASS**: System successfully generates, displays, and manages daily ArXiv reports with AI-powered relevance scoring

**❌ FAIL**: Critical errors prevent core functionality or reports are consistently low quality

---

**Next Steps After Testing**: 
1. Update `CLAUDE.md` with test results
2. Report any issues found during testing
3. Consider customizing keywords for better relevance
4. Plan integration with daily automation if desired