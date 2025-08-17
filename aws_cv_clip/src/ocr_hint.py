def ocr_text(pil, lang=("en",)):
    """
    주어진 PIL 이미지를 OCR(Optical Character Recognition)하여 텍스트를 추출합니다.
    
    :param pil: 텍스트를 추출할 PIL 이미지 객체
    :param lang: OCR에 사용할 언어의 튜플, 기본값은 영어 ("en",)
    :return: 이미지에서 추출된 텍스트 문자열
    """
    try:
        import easyocr
        import numpy as np
        
        # 지정된 언어로 EasyOCR Reader 객체 생성, GPU 사용 안 함
        r = easyocr.Reader(list(lang), gpu=False)
        
        # PIL 이미지를 numpy 배열로 변환하여 OCR 수행
        res = r.readtext(np.array(pil))
        
        # OCR 결과에서 텍스트 부분만 추출하여 공백으로 연결
        txt = " ".join([t[1] for t in res]) if res else ""
        
        return txt
    except Exception:
        # 예외 발생 시 빈 문자열 반환
        return ""
