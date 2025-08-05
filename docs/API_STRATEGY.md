You're absolutely right! I apologize for the confusing formatting. **EVERYTHING should be included in the markdown files**, including the Intelligent Sync Strategy section. Let me provide the complete, properly formatted API_STRATEGY.md file:

## API_STRATEGY.md (COMPLETE FILE)
```markdown
# CompaniesHouseAI API Architecture - Zero to 10K Users

## 🎯 Core Philosophy: Cache EVERYTHING, Query NOTHING

### The 30GB Advantage
With 5.6M UK companies averaging 5KB each, our ENTIRE dataset is ~30GB compressed.
On 256GB storage, we can cache EVERYTHING and deliver sub-10ms responses while competitors hit rate limits.

## 📊 Three-Layer Cache Architecture

### Layer 1: Hot Cache (Redis) - 1GB
- Last 10,000 searched companies
- All FTSE 350 companies
- Trending companies (high search velocity)
- User's recent searches
- TTL: 24 hours

### Layer 2: Warm Cache (SQLite) - 30GB
- ALL 5.6M companies with core data
- Full-text search index (FTS5)
- Relationship graphs (directors, PSCs)
- Historical snapshots (monthly)
- TTL: 7 days for active, 30 days for dissolved

### Layer 3: Cold Storage (API) - On-demand
- Document downloads
- Real-time verification
- Newly incorporated companies
- Rate limit: 2/second (120/minute)

## 🚀 API Wrapper Implementation

```python
class CompaniesHouseIntelligence:
    def __init__(self):
        self.hot_cache = Redis(maxmemory='1gb', eviction='lru')
        self.warm_cache = SQLiteCache('companies.db')
        self.api_queue = PriorityQueue()
        self.rate_limiter = TokenBucket(2, 1)  # 2 per second
        
    async def get_company(self, number: str, priority: int = 5):
        # Check caches in order
        if data := await self.hot_cache.get(number):
            return data
            
        if data := await self.warm_cache.get(number):
            await self.hot_cache.set(number, data, ttl=86400)
            return data
            
        # Queue for API fetch
        return await self.queue_api_fetch(number, priority)
```

## 🎯 Intelligent Sync Strategy

### Priority Tiers
1. **Real-time (Priority 10)**: User-requested, not in cache
2. **High (Priority 7)**: Popular companies, daily sync
3. **Medium (Priority 5)**: Active companies, weekly sync
4. **Low (Priority 3)**: Dissolved companies, monthly sync
5. **Bulk (Priority 1)**: Full refresh, off-peak only

### Sync Schedule
```python
# Runs via systemd timer
0 2 * * * - Sync FTSE 350 + trending
0 3 * * 0 - Sync high-traffic companies
0 4 1 * * - Full dataset verification
*/5 * * * * - Process priority queue
```

## 🔥 Performance Optimizations

### 1. Bloom Filters for Existence Checks
- 5.6M companies = ~8MB bloom filter
- Check if company exists before searching
- Prevents unnecessary cache misses

### 2. Incremental Change Detection
```sql
CREATE TABLE company_changes (
    company_number TEXT PRIMARY KEY,
    last_modified INTEGER,
    change_hash TEXT,
    priority INTEGER DEFAULT 5
);
```

### 3. Batch API Requests
- Group by endpoint type
- Maximum 100 items per batch
- Compress similar requests

## 📈 Scaling Strategy

### Phase 1: 0-1K Users
- Single Pi handles everything
- Focus on cache warming
- Monitor query patterns

### Phase 2: 1K-10K Users
- Add read replica Pi
- Implement query caching
- CDN for static assets

### Phase 3: 10K+ Users
- Distributed SQLite (LiteFS)
- Multiple API workers
- Cloudflare Workers for edge compute

## 🎯 Developer API Strategy

### Pricing Tiers
- **Free**: 1,000 requests/month, 1 req/second
- **Startup**: £29/month, 10K requests, 10 req/second
- **Growth**: £99/month, 100K requests, 50 req/second
- **Enterprise**: Custom pricing, dedicated infrastructure

### Better Than Official API
- GraphQL endpoint for flexible queries
- Webhook notifications for changes
- Batch operations support
- AI-enriched responses
- 99.9% uptime SLA

### Sample Developer Experience
```bash
# One line to get started
curl -H "X-API-Key: your-key" \
  https://api.companieshouses.com/graphql \
  -d '{"query": "{ company(number: \"12345678\") { name, riskScore, aiSummary } }"}'
```

## 🚀 Implementation Roadmap

### Week 1: Foundation
- Implement SQLite cache layer
- Set up Redis for hot cache
- Create basic API wrapper
- Test with 100 companies

### Week 2: Intelligence Layer
- Add priority queue system
- Implement bloom filters
- Create change detection
- Set up sync schedules

### Week 3: Developer API
- GraphQL endpoint
- API key management
- Rate limiting
- Documentation site

### Week 4: Optimization
- Performance profiling
- Query optimization
- Cache tuning
- Load testing

## 📊 Success Metrics

### Performance KPIs
- Cache hit rate: >95%
- Average response time: <50ms
- API calls saved: >90%
- Uptime: 99.9%

### Business KPIs
- Developer signups: 100/week
- API revenue: £5K/month by Month 6
- Support tickets: <5% of users
- Churn rate: <5%

## 🛡️ Security & Compliance

### Data Protection
- API keys hashed with bcrypt
- Rate limiting per IP and key
- Request logging for 30 days
- GDPR compliant data handling

### Infrastructure Security
- Cloudflare DDoS protection
- Fail2ban for SSH
- Automated security updates
- Daily encrypted backups

## 💡 Innovation Pipeline

### Q1 2025
- Real-time WebSocket feeds
- Bulk export API
- Company comparison endpoints
- Industry aggregation APIs

### Q2 2025
- International expansion (Ireland first)
- Machine learning recommendations
- Custom webhook events
- White-label API solution

### Q3 2025
- Blockchain verification
- IPFS document storage
- Decentralized cache network
- Community-driven data validation

Remember: Every API call saved is money earned. Cache aggressively, update intelligently, serve instantly.
```

---

**KEY POINT**: Everything you see above goes into the API_STRATEGY.md file as one complete markdown document. The same applies to all the other strategy files - they should each be complete, self-contained markdown files with ALL sections included.