import json, requests

BASE = "http://100.99.61.125:1234"
url = f"{BASE}/v1/chat/completions"
payload = {
    "model": "openai/gpt-oss-20b",
    "messages": [
        {"role":"system","content":"Answer in Korean, concise."},
        {"role":"user","content":"WSL2 스트리밍 테스트 해줘."}
    ],
    "stream": True,
    "temperature": 0.2,
    "max_tokens": 256
}
with requests.post(url, data=json.dumps(payload),
                   headers={"Content-Type":"application/json"},
                   stream=True, timeout=0) as r:
    r.raise_for_status()
    for line in r.iter_lines(decode_unicode=True):
        if not line or not line.startswith("data: "): 
            continue
        if line.strip() == "data: [DONE]":
            break
        chunk = json.loads(line[len("data: "):])
        delta = chunk["choices"][0]["delta"].get("content", "")
        if delta:
            print(delta, end="", flush=True)
