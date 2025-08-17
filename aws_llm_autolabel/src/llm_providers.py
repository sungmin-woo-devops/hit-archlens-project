"""
LLM 제공자 모듈
OpenAI와 DeepSeek Vision API를 추상화하여 일관된 인터페이스를 제공합니다.
"""

import os
import base64
import io
import json
import time
from abc import ABC, abstractmethod
from typing import Dict, Any, Optional
from PIL import Image
import requests
import openai

class LLMProvider(ABC):
    """LLM 제공자 추상 클래스"""
    
    def __init__(self, base_url: str, api_key: str, vision_model: str):
        self.base_url = base_url
        self.api_key = api_key
        self.vision_model = vision_model
    
    @abstractmethod
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """이미지 분석"""
        pass
    
    def _pil_to_b64(self, image: Image.Image) -> str:
        """PIL 이미지를 base64로 인코딩"""
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")

class OpenAIProvider(LLMProvider):
    """OpenAI Vision API 제공자"""
    
    def __init__(self, base_url: str, api_key: str, vision_model: str):
        super().__init__(base_url, api_key, vision_model)
        self.client = openai.OpenAI(base_url=base_url, api_key=api_key)
    
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """OpenAI Vision API로 이미지 분석"""
        b64_image = self._pil_to_b64(image)
        
        try:
            response = self.client.chat.completions.create(
                model=self.vision_model,
                messages=[
                    {
                        "role": "system",
                        "content": "You are a precise vision annotator. Return strictly valid JSON."
                    },
                    {
                        "role": "user",
                        "content": [
                            {"type": "text", "text": prompt},
                            {
                                "type": "image_url",
                                "image_url": {"url": f"data:image/png;base64,{b64_image}"}
                            }
                        ]
                    }
                ],
                temperature=0,
                timeout=120
            )
            return response.choices[0].message.content
        except Exception as e:
            print(f"⚠️ OpenAI API 호출 실패: {e}")
            return '{"objects": []}'

class DeepSeekProvider(LLMProvider):
    """DeepSeek Vision API 제공자"""
    
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """DeepSeek Vision API로 이미지 분석"""
        b64_image = self._pil_to_b64(image)
        
        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json"
        }
        
        payload = {
            "model": self.vision_model,
            "messages": [
                {
                    "role": "system",
                    "content": "You are a precise vision annotator. Return strictly valid JSON."
                },
                {
                    "role": "user",
                    "content": [
                        {"type": "text", "text": prompt},
                        {
                            "type": "image_url",
                            "image_url": {"url": f"data:image/png;base64,{b64_image}"}
                        }
                    ]
                }
            ],
            "temperature": 0
        }
        
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                headers=headers,
                json=payload,
                timeout=120
            )
            response.raise_for_status()
            data = response.json()
            return data["choices"][0]["message"]["content"]
        except Exception as e:
            print(f"⚠️ DeepSeek API 호출 실패: {e}")
            return '{"objects": []}'

class MockProvider(LLMProvider):
    """테스트용 Mock 제공자"""
    
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Mock 응답 반환"""
        # 간단한 Mock 응답
        return json.dumps({
            "objects": [
                {
                    "name": "Amazon S3",
                    "bbox": [100, 100, 50, 50],
                    "confidence": 0.85
                },
                {
                    "name": "AWS Lambda",
                    "bbox": [200, 150, 60, 60],
                    "confidence": 0.78
                }
            ]
        })
