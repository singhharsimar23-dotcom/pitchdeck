"""
sor_integrations.py — System-of-Record (Track C) integrations.
Real, official, free APIs: USPTO PatentsView, SEC EDGAR full-text search, GitHub public API,
plus Stripe Connect verified revenue aggregation.
"""
import logging
import json
from datetime import datetime, timedelta, timezone
from typing import Optional, List, Dict, Any
import httpx
import stripe_connect

logger = logging.getLogger("pitch-pipeline.sor")

USPTO_API = "https://search.patentsview.org/api/v1/patent/"
EDGAR_SEARCH = "https://efts.sec.gov/LATEST/search-index"
SEC_USER_AGENT = "PitchPressureTester research@pitchpressuretester.internal"

def _compute_direction(counts: List[int]) -> str:
    """
    Computes patent filing momentum across quarterly counts.
    Accelerating (>15% increase), decelerating (<-15% drop), or flat.
    """
    if len(counts) < 2:
        return "insufficient_data"
    first_half = sum(counts[:len(counts)//2])
    second_half = sum(counts[len(counts)//2:])
    if first_half == 0:
        return "accelerating" if second_half > 0 else "insufficient_data"
    change = (second_half - first_half) / float(first_half)
    if change > 0.15:
        return "accelerating"
    if change < -0.15:
        return "decelerating"
    return "flat"

async def query_patent_velocity(keyword: str, quarters_back: int = 4) -> Dict[str, Any]:
    """
    Free, official, unauthenticated USPTO PatentsView API.
    Returns quarterly filing counts so the caller receives DIRECTION
    (accelerating/flat/decelerating), not a single point-in-time number.
    
    Honest limit: only meaningful for deep-tech claims with a real technical category.
    Includes resilient fallback if the endpoint is undergoing migration or unreachable.
    """
    if not keyword or len(keyword.strip()) < 3:
        return {
            "source": "uspto_patentsview",
            "keyword": keyword,
            "quarters": [],
            "direction": "insufficient_data",
            "reason": "Keyword too short or empty for deep-tech patent lookup."
        }

    clean_kw = keyword.strip()
    end = datetime.now(timezone.utc)
    quarters = []

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            for i in range(quarters_back):
                q_end = end - timedelta(days=90 * i)
                q_start = q_end - timedelta(days=90)
                query = {
                    "_and": [
                        {"_text_any": {"patent_title": clean_kw}},
                        {"_gte": {"patent_date": q_start.strftime("%Y-%m-%d")}},
                        {"_lt": {"patent_date": q_end.strftime("%Y-%m-%d")}},
                    ]
                }
                params = {
                    "q": json.dumps(query),
                    "f": json.dumps(["patent_id"]),
                    "o": json.dumps({"size": 1}),
                }
                resp = await client.get(USPTO_API, params=params, timeout=10.0)
                if resp.status_code == 200 and "application/json" in resp.headers.get("content-type", ""):
                    data = resp.json()
                    count = data.get("total_hits", 0)
                else:
                    # Endpoint returned redirect/html (e.g. USPTO portal transition)
                    count = 0
                quarters.append({
                    "quarter_start": q_start.strftime("%Y-%m-%d"),
                    "quarter_end": q_end.strftime("%Y-%m-%d"),
                    "count": count,
                })
        quarters.reverse()
        counts = [q["count"] for q in quarters]
        # If all counts are 0 due to API migration or no records found:
        direction = _compute_direction(counts) if any(c > 0 for c in counts) else "insufficient_data"
        return {
            "source": "uspto_patentsview",
            "keyword": clean_kw,
            "quarters": quarters,
            "direction": direction,
        }
    except Exception as e:
        logger.warning(f"USPTO PatentsView query failed: {e}. Returning insufficient_data.")
        return {
            "source": "uspto_patentsview",
            "keyword": clean_kw,
            "quarters": [],
            "direction": "insufficient_data",
            "error": str(e)
        }

async def query_edgar_mentions(company_or_category: str) -> Dict[str, Any]:
    """
    Free, official, no auth SEC EDGAR full-text search.
    Checks whether a real public-company comparable exists and mentions the category.
    Requires compliant User-Agent per SEC developer rules.
    """
    if not company_or_category or len(company_or_category.strip()) < 2:
        return {
            "source": "sec_edgar_fulltext",
            "query": company_or_category,
            "total_matches": 0,
            "sample_filers": [],
        }

    clean_q = company_or_category.strip().strip('"')
    headers = {"User-Agent": SEC_USER_AGENT}
    params = {
        "q": f'"{clean_q}"',
        "forms": "10-K,10-Q,S-1",
        "dateRange": "custom"
    }

    try:
        async with httpx.AsyncClient(follow_redirects=True) as client:
            resp = await client.get(EDGAR_SEARCH, params=params, headers=headers, timeout=12.0)
            resp.raise_for_status()
            data = resp.json()

        hits = data.get("hits", {}).get("hits", [])
        total = data.get("hits", {}).get("total", {}).get("value", 0)
        sample_filers = []
        for h in hits[:5]:
            display = h.get("_source", {}).get("display_names", ["Unknown"])
            if display:
                sample_filers.append(display[0])

        return {
            "source": "sec_edgar_fulltext",
            "query": clean_q,
            "total_matches": total,
            "sample_filers": sample_filers,
        }
    except Exception as e:
        logger.warning(f"SEC EDGAR query failed: {e}")
        return {
            "source": "sec_edgar_fulltext",
            "query": clean_q,
            "total_matches": 0,
            "sample_filers": [],
            "error": str(e)
        }

async def query_github_velocity(org_or_repo: str) -> Dict[str, Any]:
    """
    Public GitHub API query (no auth required for basic rate tier).
    Provides factual commit cadence and release counts for the founder's repo or public competitor.
    """
    clean_repo = org_or_repo.strip().strip("/")
    if "/" not in clean_repo:
        return {"source": "github", "found": False, "reason": "Repo must be in owner/repo format"}

    headers = {
        "Accept": "application/vnd.github.v3+json",
        "User-Agent": "PitchPressureTester-SoR-Agent"
    }

    try:
        async with httpx.AsyncClient() as client:
            repo_res = await client.get(f"https://api.github.com/repos/{clean_repo}", headers=headers, timeout=10.0)
            if repo_res.status_code == 404:
                return {"source": "github", "found": False, "repo": clean_repo}
            repo_res.raise_for_status()
            repo_data = repo_res.json()

            commits_res = await client.get(
                f"https://api.github.com/repos/{clean_repo}/commits",
                params={"per_page": 30},
                headers=headers,
                timeout=10.0
            )
            commit_count = len(commits_res.json()) if commits_res.status_code == 200 and isinstance(commits_res.json(), list) else 0

            releases_res = await client.get(
                f"https://api.github.com/repos/{clean_repo}/releases",
                params={"per_page": 10},
                headers=headers,
                timeout=10.0
            )
            release_count = len(releases_res.json()) if releases_res.status_code == 200 and isinstance(releases_res.json(), list) else 0

        return {
            "source": "github",
            "found": True,
            "repo": clean_repo,
            "stars": repo_data.get("stargazers_count", 0),
            "recent_commit_count_30": commit_count,
            "release_count": release_count,
            "last_pushed": repo_data.get("pushed_at"),
            "html_url": repo_data.get("html_url", f"https://github.com/{clean_repo}")
        }
    except Exception as e:
        logger.warning(f"GitHub velocity check failed for {clean_repo}: {e}")
        return {"source": "github", "found": False, "error": str(e)}

async def gather_system_of_record_evidence(
    founder_opted_in: bool = False,
    repo: Optional[str] = None,
    stripe_creds: Optional[dict] = None,
    category_keyword: Optional[str] = None,
    competitor_name: Optional[str] = None
) -> List[Dict[str, Any]]:
    """
    STAGE 3c: Gather verified system-of-record evidence items.
    
    Weights:
    - GitHub product velocity: 1.0 (direct proof of code activity)
    - Stripe Connect revenue: 1.0 (direct proof of aggregate charge volume)
    - USPTO PatentsView: 0.6 (proxy for deep-tech market heat, not direct claim support)
    - SEC EDGAR filings: 0.5 (proxy for public category comps, not founder traction)
    """
    evidence = []

    # 1. GitHub Repo Velocity
    if repo:
        gh = await query_github_velocity(repo)
        if gh.get("found"):
            commits = gh.get("recent_commit_count_30", 0)
            releases = gh.get("release_count", 0)
            stars = gh.get("stars", 0)
            finding_text = f"GitHub repo '{gh.get('repo')}': {commits} commits in last 30 fetched, {releases} releases, {stars:,} stars"
            evidence.append({
                "tier": "system_of_record",
                "source": gh.get("html_url", "github"),
                "finding": finding_text,
                "independence": "sole_source",
                "weight": 1.0,  # verified, not inferred
                "as_of": "live",
                "target_slide": 9,  # Team / Execution / Product Velocity
                "metadata": gh
            })

    # 2. Stripe Connect Verified Revenue
    if founder_opted_in and stripe_creds:
        try:
            rev = await stripe_connect.fetch_verified_revenue_signal(**stripe_creds)
            volume = rev.get("recent_gross_volume_usd", 0.0)
            evidence.append({
                "tier": "system_of_record",
                "source": "stripe_connect",
                "finding": f"${volume:,.2f} verified recent gross volume from Stripe transactions",
                "independence": "sole_source",
                "weight": 1.0,
                "as_of": "live",
                "target_slide": 7,  # Traction / Unit Economics
                "metadata": rev
            })
        except Exception as e:
            logger.warning(f"Stripe signal retrieval failed: {e}")

    # 3. USPTO Patent Velocity (Deep-Tech only)
    if category_keyword and len(category_keyword.strip()) >= 3:
        patents = await query_patent_velocity(category_keyword)
        if patents.get("direction") != "insufficient_data":
            evidence.append({
                "tier": "system_of_record",
                "source": "uspto_patentsview",
                "finding": f"US patent filings for '{category_keyword}' are {patents['direction']} across past 4 quarters",
                "independence": "sole_source",
                "weight": 0.6,  # proxy for market heat, not direct claim support
                "as_of": "live",
                "target_slide": 4,  # Market Size / Category Timing
                "metadata": patents
            })

    # 4. SEC EDGAR Public Comps
    if competitor_name and competitor_name != "none_stated" and len(competitor_name.strip()) >= 2:
        comps = await query_edgar_mentions(competitor_name)
        if comps.get("total_matches", 0) > 0:
            sample_str = ", ".join(comps.get("sample_filers", [])[:2])
            finding_text = f"{comps['total_matches']:,} SEC filings mention '{competitor_name}' ({sample_str})" if sample_str else f"{comps['total_matches']:,} SEC filings mention '{competitor_name}'"
            evidence.append({
                "tier": "system_of_record",
                "source": "https://efts.sec.gov",
                "finding": finding_text,
                "independence": "sole_source",
                "weight": 0.5,  # proxy for public category comps
                "as_of": "live",
                "target_slide": 8,  # Competitors / Landscape
                "metadata": comps
            })

    return evidence
