import json, requests
BASE = "http://100.99.61.125:1234"
url = f"{BASE}/v1/embeddings"
payload = {
  "model": "text-embedding-nomic-embed-text-v1.5",
  "input": ["WSL2에서 LM Studio 연결 테스트 문장입니다."]
}
r = requests.post(url, headers={"Content-Type":"application/json"}, data=json.dumps(payload))
r.raise_for_status()
vec = r.json()["data"][0]["embedding"]
print(len(vec), "dims, first3:", vec[:3])
