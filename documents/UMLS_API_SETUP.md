# UMLS API Setup Guide

## Overview

The Unified Medical Language System (UMLS) provides a comprehensive metathesaurus of biomedical vocabularies. Our RWE platform uses the UMLS REST API for medical concept standardization in Stage 2 of the Trialist parser.

## Prerequisites

- Internet connection
- Email address
- UMLS Terminology Services (UTS) account

## Step 1: Create UMLS Account

1. **Navigate to the UMLS Sign-Up Page**
   - Go to: https://uts.nlm.nih.gov/uts/signup-login
   - Click on "Sign Up" if you don't have an account

2. **Complete Registration Form**
   - Fill in your personal information
   - Provide institutional affiliation (if applicable)
   - Accept the UMLS Metathesaurus License Agreement
   - Click "Submit"

3. **Email Verification**
   - Check your email for verification link
   - Click the link to activate your account
   - Log in with your credentials

## Step 2: Generate API Key

1. **Access Your Profile**
   - Log in to https://uts.nlm.nih.gov/uts/profile
   - Navigate to "My Profile" section

2. **Generate New API Key**
   - Click on "API Key" tab or section
   - Click "Generate New API Key" or "Edit API Keys"
   - Copy the generated API key (it looks like: `12345678-abcd-1234-abcd-123456789abc`)
   - ⚠️ **Important**: Save this key securely - you won't be able to see it again

## Step 3: Configure Environment Variables

1. **Locate `.env` File**
   ```bash
   cd /path/to/datathon
   ```

2. **Add UMLS Configuration**
   Open `.env` file and add:
   ```bash
   # UMLS API Configuration
   UMLS_API_KEY=your_api_key_here
   UMLS_ENDPOINT=https://uts-ws.nlm.nih.gov/rest

   # Standardization Mode
   STANDARDIZATION_MODE=api
   ```

3. **Verify `.env` is in `.gitignore`**
   ```bash
   # Ensure .env is listed in .gitignore to prevent committing secrets
   grep ".env" .gitignore
   ```

## Step 4: Test API Connection

1. **Run Validation Script**
   ```bash
   python -c "
   from src.pipeline.clients.umls_client import UMLSClient
   import os
   from dotenv import load_dotenv

   load_dotenv()
   api_key = os.getenv('UMLS_API_KEY')

   client = UMLSClient(api_key=api_key)
   is_valid = client.validate_api_key()

   if is_valid:
       print('✅ UMLS API key is valid!')

       # Test a simple search
       concepts = client.search_concept('diabetes')
       print(f'✅ Found {len(concepts)} concepts for \"diabetes\"')
       if concepts:
           print(f'   - CUI: {concepts[0].cui}')
           print(f'   - Name: {concepts[0].preferred_name}')
   else:
       print('❌ UMLS API key validation failed')
   "
   ```

2. **Expected Output**
   ```
   ✅ UMLS API key is valid!
   ✅ Found 5 concepts for "diabetes"
      - CUI: C0011849
      - Name: Diabetes Mellitus
   ```

## API Usage and Rate Limits

### Rate Limits
- **Free Tier**: 20 requests per second per API key
- **Recommended**: Configure rate limiting in code (already implemented in `UMLSClient`)

### Best Practices
1. **Use Caching**: The system caches UMLS responses for 7 days
2. **Batch Operations**: Process multiple entities together when possible
3. **Monitor Usage**: Check API logs for rate limit warnings

### API Endpoints Used

Our implementation uses these UMLS REST API endpoints:

| Endpoint | Purpose | Example |
|----------|---------|---------|
| `/search/{version}` | Search for concepts | Search for "heart attack" |
| `/content/{version}/CUI/{cui}` | Get concept details | Get details for C0027051 |
| `/content/{version}/CUI/{cui}/atoms` | Get synonyms | Get all names for a CUI |
| `/content/{version}/CUI/{cui}/definitions` | Get definitions | Get medical definitions |

## Troubleshooting

### Error: "Invalid UMLS API key"
**Cause**: API key is incorrect or expired

**Solution**:
1. Verify the API key in your `.env` file has no extra spaces
2. Generate a new API key from your UTS profile
3. Update `.env` with the new key

### Error: "UMLS API rate limit exceeded"
**Cause**: Too many requests in short time

**Solution**:
1. Wait 60 seconds before retrying
2. Enable caching (should be enabled by default)
3. Reduce batch size or add delays between requests

### Error: "UMLS API timeout"
**Cause**: Network issues or slow API response

**Solution**:
1. Check internet connection
2. Increase timeout in configuration:
   ```python
   client = UMLSClient(api_key=api_key, timeout=15)  # 15 seconds
   ```

### Error: "No module named 'requests'"
**Cause**: Missing dependencies

**Solution**:
```bash
pip install -r requirements-api.txt
```

### Connection Test Fails
**Symptoms**: Cannot connect to UMLS API

**Checklist**:
- [ ] Verify internet connection
- [ ] Check firewall/proxy settings
- [ ] Confirm API key is active (log in to UTS website)
- [ ] Try accessing https://uts-ws.nlm.nih.gov/rest in browser

## Advanced Configuration

### Custom Timeout and Retries
```python
from src.pipeline.clients.umls_client import UMLSClient

client = UMLSClient(
    api_key=api_key,
    timeout=10,          # 10 seconds timeout
    max_retries=5,       # Retry up to 5 times
    retry_backoff=2.0    # Exponential backoff factor
)
```

### Filtering by Source Vocabularies
```python
concepts = client.search_concept(
    "hypertension",
    source_vocabularies=["SNOMEDCT_US", "ICD10CM"]
)
```

### Search Types
- `words`: Match all query words (default)
- `exact`: Exact synonym match
- `normalizedString`: Remove lexical variations
- `rightTruncation`: Prefix matching

## Resources

- **UMLS Home**: https://www.nlm.nih.gov/research/umls
- **API Documentation**: https://documentation.uts.nlm.nih.gov/rest/home.html
- **UTS Profile**: https://uts.nlm.nih.gov/uts/profile
- **UMLS Metathesaurus Browser**: https://uts.nlm.nih.gov/uts/umls/home

## Support

For UMLS-specific issues:
- **Email**: uts-support@nlm.nih.gov
- **FAQ**: https://www.nlm.nih.gov/research/umls/knowledge_sources/metathesaurus/faq.html

For RWE platform issues:
- Check platform documentation in `TRIALIST_README.md`
- Review logs in `workspace/*/logs/`
- Open GitHub issue with error details

---

**Last Updated**: 2025-10-14
**Version**: 1.0
