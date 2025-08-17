"""
LLM Providers Module

다양한 LLM 제공자들을 추상화하여 일관된 인터페이스를 제공
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


class LLMProvider(ABC):
    """LLM 제공자 추상 클래스"""
    
    def __init__(self, base_url: str, api_key: str, vision_model: str):
        """
        초기화
        
        Args:
            base_url: API 기본 URL
            api_key: API 키
            vision_model: 비전 모델명
        """
        self.base_url = base_url
        self.api_key = api_key
        self.vision_model = vision_model
    
    @abstractmethod
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """
        이미지 분석
        
        Args:
            image: 분석할 이미지
            prompt: 분석 프롬프트
            
        Returns:
            str: JSON 형태의 분석 결과
        """
        pass
    
    def _pil_to_b64(self, image: Image.Image) -> str:
        """PIL 이미지를 base64로 인코딩"""
        buf = io.BytesIO()
        image.save(buf, format="PNG")
        return base64.b64encode(buf.getvalue()).decode("utf-8")
    
    def _make_request(self, payload: Dict[str, Any], headers: Dict[str, str]) -> str:
        """HTTP 요청 수행"""
        try:
            response = requests.post(
                f"{self.base_url}/chat/completions",
                json=payload,
                headers=headers,
                timeout=120
            )
            response.raise_for_status()
            
            data = response.json()
            return data["choices"][0]["message"]["content"]
            
        except Exception as e:
            print(f"⚠️ API 요청 실패: {e}")
            return '{"objects": []}'


class OpenAIProvider(LLMProvider):
    """OpenAI Vision API 제공자"""
    
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """OpenAI Vision API로 이미지 분석"""
        try:
            import openai
            
            b64_image = self._pil_to_b64(image)
            
            client = openai.OpenAI(base_url=self.base_url, api_key=self.api_key)
            
            response = client.chat.completions.create(
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
            "temperature": 0,
            "max_tokens": 2000
        }
        
        return self._make_request(payload, headers)


class AnthropicProvider(LLMProvider):
    """Anthropic Claude Vision API 제공자"""
    
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """Anthropic Claude Vision API로 이미지 분석"""
        try:
            import anthropic
            
            b64_image = self._pil_to_b64(image)
            
            client = anthropic.Anthropic(api_key=self.api_key)
            
            response = client.messages.create(
                model=self.vision_model,
                max_tokens=2000,
                messages=[
                    {
                        "role": "user",
                        "content": [
                            {
                                "type": "text",
                                "text": prompt
                            },
                            {
                                "type": "image",
                                "source": {
                                    "type": "base64",
                                    "media_type": "image/png",
                                    "data": b64_image
                                }
                            }
                        ]
                    }
                ]
            )
            
            return response.content[0].text
            
        except Exception as e:
            print(f"⚠️ Anthropic API 호출 실패: {e}")
            return '{"objects": []}'


class LocalLLMProvider(LLMProvider):
    """로컬 LLM 제공자 (LM Studio, Ollama 등)"""
    
    def analyze_image(self, image: Image.Image, prompt: str) -> str:
        """로컬 LLM으로 이미지 분석"""
        b64_image = self._pil_to_b64(image)
        
        headers = {
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
            "temperature": 0,
            "max_tokens": 2000
        }
        
        return self._make_request(payload, headers)
