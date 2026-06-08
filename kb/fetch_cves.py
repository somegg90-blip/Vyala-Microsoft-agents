# kb/fetch_cves.py
import requests
import json
import os
import time

# Target directory for Source 2
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "data", "2_cves")
os.makedirs(OUTPUT_DIR, exist_ok=True)

# Keywords specifically targeting classical crypto that quantum breaks
KEYWORDS = ["RSA", "ECDSA", "ECDH", "AES-128", "SHA-1", "MD5"]
HEADERS = {"User-Agent": "Vyala-Archon-Hackathon/1.0"}

def fetch_nvd_cves():
    total_saved = 0
    
    for kw in KEYWORDS:
        print(f"🔍 Fetching CVEs for: {kw}")
        # NVD API v2.0: 20 results per page is a safe limit
        url = f"https://services.nvd.nist.gov/rest/json/cves/2.0?keywordSearch={kw}&resultsPerPage=20"
        
        try:
            resp = requests.get(url, headers=HEADERS, timeout=15)
            if resp.status_code != 200:
                print(f"  ❌ Error {resp.status_code} for {kw}. Skipping.")
                continue
                
            data = resp.json()
            vulnerabilities = data.get("vulnerabilities", [])
            
            for vuln in vulnerabilities:
                cve = vuln["cve"]
                cve_id = cve["id"]
                
                # Extract English description
                descriptions = [d["value"] for d in cve.get("descriptions", []) if d["lang"] == "en"]
                desc = descriptions[0] if descriptions else "No description available."
                
                # Save as individual JSON file for easy vector chunking
                file_path = os.path.join(OUTPUT_DIR, f"{cve_id}.json")
                with open(file_path, "w", encoding="utf-8") as f:
                    json.dump({
                        "id": cve_id,
                        "source": "NVD",
                        "algorithm_keyword": kw,
                        "description": desc
                    }, f, indent=2)
                
                total_saved += 1
            
            print(f"  ✅ Saved {len(vulnerabilities)} CVEs for {kw}")
            
        except Exception as e:
            print(f"  ⚠️ Exception fetching {kw}: {e}")
            
        # NVD API rate limit: 5 requests per 30 seconds without API key.
        # 6 seconds delay ensures we don't get blocked.
        print("  ⏳ Waiting 6s to respect NVD rate limits...")
        time.sleep(6)

    print(f"\n🎉 Done! Total CVEs saved to {OUTPUT_DIR}: {total_saved}")

if __name__ == "__main__":
    fetch_nvd_cves()