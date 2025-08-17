#!/usr/bin/env python3
# connect_local_llm.py
import os, json, re, requests, sys
from typing import Optional

def detect_win_host_ip() -> Optional[str]:
    # /etc/resolv.conf의 nameserver를 윈도우 호스트 IP로 사용
    try:
        with open("/etc/resolv.conf") as f:
            for line in f:
                m = re.search(r"nameserver\s+([0-9.]+)", line)
                if m:
                    return m.group(1)
    except Exception:
        pass
    return None

def pick_base_url() -> str:
    # 환경변수 우선, 그 다음 사용자가 성공 확인한 IP, 마지막으로 nameserver
    env = os.getenv("LMSTUDIO_BASE")
    if env:
        return env.rstrip("/")
    # 사용자가 방금 성공한 예: http://100.99.61.125:1234
    known = os.getenv("LMSTUDIO_KNOWN_IP", "100.99.61.125")
    if known:
        return f"http://{known}:1234"
    host = detect_win_host_ip()
    if host:
        return f"http://{host}:1234"
    # 최후의 수단: 로컬(일부 환경에선 통함)
    return "http://127.0.0.1:1234"

BASE = pick_base_url()
TIMEOUT = float(os.getenv("LMSTUDIO_TIMEOUT", "10"))
API_KEY = os.getenv("LMSTUDIO_API_KEY")  # LM Studio는 보통 불필요

def headers():
    h = {"Content-Type": "application/json"}
    if API_KEY:
        h["Authorization"] = f"Bearer {API_KEY}"
    return h

def get_models():
    url = f"{BASE}/v1/models"
    r = requests.get(url, timeout=TIMEOUT)
    r.raise_for_status()
    return [m["id"] for m in r.json().get("data", [])]

def chat(model: str, system: str, user: str) -> str:
    url = f"{BASE}/v1/chat/completions"
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": system},
            {"role": "user", "content": user},
        ],
        "temperature": 0.2,
        "max_tokens": 256,
        "stream": False,
    }
    r = requests.post(url, headers=headers(), data=json.dumps(payload), timeout=TIMEOUT)
    r.raise_for_status()
    j = r.json()
    return j["choices"][0]["message"]["content"]

def main():
    print(f"[i] Base URL: {BASE}")
    try:
        models = get_models()
    except Exception as e:
        print(f"[x] /v1/models 실패: {e}")
        sys.exit(1)

    if not models:
        print("[x] 사용 가능한 모델이 없습니다. LM Studio에서 모델을 Load 하세요.")
        sys.exit(2)

    preferred = "openai/gpt-oss-20b"
    model = preferred if preferred in models else models[0]
    if model != preferred:
        print(f"[!] '{preferred}' 미탐지 → '{model}' 사용")

    try:
        out = chat(
            model,
            system="You are a concise assistant. Answer in Korean.",
            user="WSL2에서 연결 테스트 중입니다. 한 줄로 응답해주세요.",
        )
        print("\n=== Response ===")
        print(out.strip())
    except requests.HTTPError as e:
        print(f"[x] chat 실패(HTTP {e.response.status_code}): {e.response.text}")
        sys.exit(3)
    except Exception as e:
        print(f"[x] chat 실패: {e}")
        sys.exit(4)

if __name__ == "__main__":
    LMSTUDIO_BASE="http://100.99.61.125:1234"
    LMSTUDIO_API_KEY="lm-studio"
    main()
