# Companies House API Integration Strategy

## Rate Limits
- 600 requests per 5 minutes (2/second)
- Strategy: Intelligent caching + request queuing

## Caching Tiers
### Tier 1: Core Data (Cache 24h)
- Company profiles (/company/{number})
- Officers lists
- PSC information

### Tier 2: Moderate Updates (Cache 6-12h)
- Filing history
- Charges
- Popular search results

### Tier 3: Dynamic Data (Cache 1-6h)
- Insolvency status
- Recent appointments

### Never Cache
- User-specific searches
- Live document downloads

## Priority Endpoints
1. /company/{number} - Essential profile data
2. /company/{number}/officers - High-value network data
3. /company/{number}/filing-history - Critical compliance info
4. /company/{number}/charges - Risk assessment data
5. /search/companies - User-facing functionality

## Data Freshness Strategy
- Background job updates popular companies hourly
- On-demand fetching for rare companies
- Full refresh monthly for data integrity
