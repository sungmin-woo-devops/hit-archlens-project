"""
프롬프트 관리 모듈
LLM 분석에 사용되는 프롬프트들을 체계적으로 관리합니다.
"""

class PromptManager:
    """프롬프트 관리자"""
    
    def __init__(self):
        self._full_image_prompt = self._get_full_image_prompt()
        self._patch_prompt = self._get_patch_prompt()
    
    def get_full_image_prompt(self) -> str:
        """전체 이미지 분석 프롬프트"""
        return self._full_image_prompt
    
    def get_patch_prompt(self) -> str:
        """패치 분석 프롬프트"""
        return self._patch_prompt
    
    def _get_full_image_prompt(self) -> str:
        """전체 이미지 분석 프롬프트 생성"""
        return """Detect AWS service icons on this architecture diagram.
Return STRICT JSON:
{
 "objects":[
   {"name":"<service-name>", "bbox":[x,y,w,h], "confidence":0.0}
 ]
}
Coordinates in pixels, integer. Only include real icons.
For service-name, use the product or service brand as seen or inferred (e.g., "Amazon S3", "AWS Lambda").
Focus on AWS service icons, not generic shapes or text."""
    
    def _get_patch_prompt(self) -> str:
        """패치 분석 프롬프트 생성"""
        return """Identify the SINGLE most likely AWS service or product for this small icon patch.
Return STRICT JSON: {"candidates": ["<name1>", "<name2>", "<name3>"]} (max 3).
Use official AWS service names (e.g., "Amazon S3", "AWS Lambda", "Amazon EC2").
If unclear, return empty candidates array."""
    
    def get_custom_prompt(self, prompt_type: str, **kwargs) -> str:
        """사용자 정의 프롬프트 생성"""
        if prompt_type == "detailed":
            return self._get_detailed_prompt(**kwargs)
        elif prompt_type == "simple":
            return self._get_simple_prompt(**kwargs)
        else:
            return self._get_full_image_prompt()
    
    def _get_detailed_prompt(self, **kwargs) -> str:
        """상세 분석 프롬프트"""
        confidence_threshold = kwargs.get("confidence_threshold", 0.5)
        
        return f"""Analyze this AWS architecture diagram in detail.
Detect all AWS service icons and return their precise locations.

Return STRICT JSON:
{{
 "objects":[
   {{
     "name":"<service-name>",
     "bbox":[x,y,w,h],
     "confidence":0.0,
     "category":"<service-category>"
   }}
 ]
}}

Requirements:
- Coordinates in pixels, integer values
- Only include AWS service icons with confidence >= {confidence_threshold}
- Use official AWS service names
- Include service category if identifiable
- Focus on actual service icons, not decorative elements"""
    
    def _get_simple_prompt(self, **kwargs) -> str:
        """간단 분석 프롬프트"""
        return """Find AWS service icons in this image.
Return JSON: {"objects":[{"name":"<service>", "bbox":[x,y,w,h], "confidence":0.0}]}
Only include clear AWS service icons."""
