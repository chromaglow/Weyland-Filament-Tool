# Advanced Web Scraping Guide

## Anti-Detection Techniques Implemented

### 1. User-Agent Rotation
**Purpose**: Appear as different browsers/devices

**Implementation**:
- Rotates between 8+ realistic user agents
- Includes Chrome, Firefox, Edge, Safari
- Covers Windows, Mac, Linux platforms

**Benefit**: Prevents detection based on user-agent fingerprinting

### 2. Smart HTTP Headers
**What's randomized**:
- `User-Agent`: Different browsers
- `Accept-Language`: en-US, en-GB variations
- `Accept-Encoding`: gzip, deflate, br
- `DNT`: Do Not Track headers
- `Sec-Fetch-*`: Security headers

**Benefit**: Makes requests look like legitimate browsers

### 3. Intelligent Rate Limiting
**Features**:
- Per-domain tracking
- Random delays between 2-5 seconds
- Jitter added to avoid patterns

**Code**:
```python
# Random delay to avoid detection
delay = random.uniform(2.0, 5.0)
```

**Benefit**: Respectful scraping, avoids triggering rate limits

### 4. Exponential Backoff
**When 429 (Rate Limited) occurs**:
- Wait: 2^retry + random(0, 1) seconds
- Retry 1: ~2 seconds
- Retry 2: ~4 seconds
- Retry 3: ~8 seconds
- Retry 4: ~16 seconds
- Retry 5: ~32 seconds

**Benefit**: Automatically recovers from rate limiting

### 5. Smart Caching System
**How it works**:
- Caches all responses for 24 hours
- MD5 hash of URL as cache key
- Automatic expiration
- Reduces load on target sites

**Benefits**:
- Faster repeated searches
- Fewer requests to target sites
- Offline capability

**Cache location**: `data/cache/*.json`

**Clear cache**:
```python
scraper.clear_cache(older_than_hours=24)  # Clear old cache
scraper.clear_cache()  # Clear all
```

### 6. Session Persistence
**Maintains**:
- Cookies across requests
- Connection pooling
- HTTP keep-alive

**Benefit**: Looks more like a real browser session

### 7. API Detection
**Tries to find APIs before scraping HTML**:
- `/api/search`
- `/api/filaments`
- `/api/profiles`

**Benefit**: APIs are faster and less likely to be blocked

## Advanced Techniques (Optional)

### Proxy Support (Add if needed)
```python
# In advanced_scraper.py
self.session.proxies = {
    'http': 'http://proxy.example.com:8080',
    'https': 'https://proxy.example.com:8080'
}

# Or use rotating proxies
from itertools import cycle
proxies = cycle([
    'http://proxy1.com:8080',
    'http://proxy2.com:8080',
])
self.session.proxies = {'http': next(proxies)}
```

### Headless Browser (For JavaScript sites)
```python
from selenium import webdriver
from selenium.webdriver.chrome.options import Options

options = Options()
options.add_argument('--headless')
options.add_argument('--disable-blink-features=AutomationControlled')
options.add_argument(f'user-agent={random_user_agent}')

driver = webdriver.Chrome(options=options)
driver.get(url)
html = driver.page_source
```

### CloudFlare Bypass
If site uses CloudFlare:
```python
import cloudscraper

scraper = cloudscraper.create_scraper()
response = scraper.get(url)
```

## Best Practices

### DO:
✅ Use caching aggressively
✅ Respect robots.txt
✅ Add random delays
✅ Rotate user agents
✅ Check for official APIs first
✅ Handle errors gracefully
✅ Log all activities
✅ Set reasonable timeouts

### DON'T:
❌ Scrape too fast (>1 req/sec)
❌ Use the same user agent
❌ Ignore rate limit responses
❌ Scrape during peak hours
❌ Request the same URL repeatedly
❌ Use automated tools headers
❌ Ignore robots.txt

## Ethical Scraping Checklist

- [ ] Check for official API
- [ ] Read and respect robots.txt
- [ ] Implement rate limiting (2-5 sec delays)
- [ ] Use caching to minimize requests
- [ ] Identify yourself in User-Agent
- [ ] Handle errors properly
- [ ] Don't scrape personal data
- [ ] Give back to the community

## Troubleshooting

### Getting 403 Forbidden
**Solutions**:
1. Check User-Agent (add more realistic ones)
2. Add Referer header
3. Enable cookies
4. Try headless browser

### Getting 429 Too Many Requests
**Solutions**:
1. Increase delays (5-10 seconds)
2. Enable exponential backoff
3. Use caching
4. Spread requests over time

### No Data Found
**Solutions**:
1. Check if site uses JavaScript (use Selenium)
2. Look for API endpoints
3. Inspect network tab in browser
4. Check site structure hasn't changed

### CloudFlare Challenge
**Solutions**:
1. Use `cloudscraper` library
2. Use Selenium with undetected-chromedriver
3. Use proxy services
4. Contact site for API access

## Configuration

### Adjust Rate Limits
```python
# In advanced_scraper.py __init__
self.min_delay = 5.0  # More conservative
self.max_delay = 10.0
```

### Adjust Cache TTL
```python
self.cache_ttl = 48 * 60 * 60  # 48 hours
```

### Increase Retries
```python
self.max_retries = 10  # More persistent
```

## Performance Tips

1. **Use caching**: 100x faster for repeated searches
2. **Parallel requests**: Use ThreadPoolExecutor for multiple URLs
3. **API over HTML**: 10x faster when available
4. **Local database**: Cache processed results in SQLite

## Legal & Ethical Notes

- Always respect website Terms of Service
- Check robots.txt before scraping
- Don't overload servers
- Use data responsibly
- Consider asking for API access
- Contribute back to community databases

## Monitoring

Check logs for:
```
INFO | Advanced scraper initialized
DEBUG | Cache hit for {url}
WARNING | Rate limited (429)
INFO | Cleared 15 cache files
```

---

**Weyland-Yutani Corporation - Advanced Materials Division**
*Ethical Data Collection Practices*
