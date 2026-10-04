import sys
import time
import urllib.request
import json

def check_health(base_url: str = "http://localhost:8000"):
    health_url = f"{base_url.rstrip('/')}/health"
    print(f"🔍 Checking health for REVA server at: {health_url}")

    start_time = time.time()
    try:
        req = urllib.request.Request(health_url, headers={"User-Agent": "REVA-HealthCheck/1.0"})
        with urllib.request.urlopen(req, timeout=5) as response:
            latency_ms = round((time.time() - start_time) * 1000, 2)
            status_code = response.getcode()
            body = response.read().decode("utf-8")
            data = json.loads(body)

            if status_code == 200 and data.get("status") == "ok":
                print(f"✅ SYSTEM HEALTHY | HTTP {status_code} | Latency: {latency_ms}ms")
                print(f"   Payload: {data}")
                return True
            else:
                print(f"⚠️ SYSTEM UNHEALTHY | HTTP {status_code} | Payload: {data}")
                return False

    except Exception as e:
        print(f"❌ HEALTH CHECK FAILED | Error: {e}")
        return False

if __name__ == "__main__":
    target_url = sys.argv[1] if len(sys.argv) > 1 else "http://localhost:8000"
    success = check_health(target_url)
    sys.exit(0 if success else 1)
