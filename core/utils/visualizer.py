"""
Analysis Result Visualizer Module

Hit ArchLens의 분석 결과를 시각화하는 함수들을 제공합니다.
"""

import matplotlib.pyplot as plt
import seaborn as sns
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional, Union, Tuple
import os
from PIL import Image, ImageDraw, ImageFont # PIL의 Image, ImageDraw, ImageFont 임포트
import numpy as np
from collections import defaultdict

from ..models import AnalysisResult, BatchAnalysisResult, DetectionResult


def setup_plot_style(figsize: Tuple[int, int] = (10, 6)) -> None:
    """Matplotlib 및 Seaborn 플롯 스타일 설정"""
    sns.set_theme(style="whitegrid", palette="viridis")
    plt.rcParams["figure.figsize"] = figsize
    plt.rcParams["font.family"] = "sans-serif"
    plt.rcParams["font.sans-serif"] = ["DejaVu Sans"] # 한글 폰트 설정 (필요시 나눔고딕 등으로 변경)
    plt.rcParams["axes.unicode_minus"] = False # 마이너스 폰트 깨짐 방지


def plot_detection_confidence(
    results: List[AnalysisResult], 
    output_path: Union[str, Path], 
    title: str = "Detection Confidence Distribution"
) -> None:
    """
    감지된 객체들의 신뢰도 분포를 히스토그램으로 시각화합니다.
    
    Args:
        results: AnalysisResult 객체 목록
        output_path: 그래프를 저장할 경로
        title: 그래프 제목
    """
    setup_plot_style()
    
    confidences = [d.confidence for res in results for d in res.detections]
    
    if not confidences:
        print("⚠️ 시각화할 데이터가 없습니다 (신뢰도 분포)")
        return
        
    plt.figure()
    sns.histplot(confidences, bins=20, kde=True)
    plt.title(title)
    plt.xlabel("Confidence")
    plt.ylabel("Frequency")
    plt.xlim(0, 1)
    plt.savefig(output_path)
    plt.close()
    print(f"✅ 신뢰도 분포 그래프 저장: {output_path}")


def plot_processing_time(
    batch_result: BatchAnalysisResult, 
    output_path: Union[str, Path], 
    title: str = "Total and Average Processing Time"
) -> None:
    """
    총 처리 시간과 평균 처리 시간을 시각화합니다.
    
    Args:
        batch_result: BatchAnalysisResult 객체
        output_path: 그래프를 저장할 경로
        title: 그래프 제목
    """
    setup_plot_style()
    
    data = {
        "Metric": ["Total Processing Time", "Average Processing Time"],
        "Value": [batch_result.total_processing_time, batch_result.average_processing_time]
    }
    df = pd.DataFrame(data)
    
    plt.figure()
    sns.barplot(data=df, x="Metric", y="Value", palette="pastel")
    plt.title(title)
    plt.xlabel("Metric")
    plt.ylabel("Processing Time (seconds)")
    plt.savefig(output_path)
    plt.close()
    print(f"✅ 처리 시간 그래프 저장: {output_path}")


def plot_detection_counts(
    results: List[AnalysisResult], 
    output_path: Union[str, Path], 
    title: str = "Detection Counts by Analysis Method"
) -> None:
    """
    분석 방법별 감지된 객체 수를 시각화합니다.
    
    Args:
        results: AnalysisResult 객체 목록
        output_path: 그래프를 저장할 경로
        title: 그래프 제목
    """
    setup_plot_style()
    
    data = []
    for res in results:
        data.append({
            "image_path": res.image_path.name,
            "detection_count": res.detection_count,
            "method": res.analysis_method.value,
            "cloud_provider": res.cloud_provider.value
        })

    if not data:
        print("⚠️ 시각화할 데이터가 없습니다 (감지 수)")
        return
        
    df = pd.DataFrame(data)
    
    plt.figure()
    sns.barplot(data=df, x="method", y="detection_count", hue="cloud_provider", errorbar='sd')
    plt.title(title)
    plt.xlabel("Analysis Method")
    plt.ylabel("Number of Detections")
    plt.savefig(output_path)
    plt.close()
    print(f"✅ 감지 수 그래프 저장: {output_path}")


def plot_service_distribution(
    results: List[AnalysisResult], 
    output_path: Union[str, Path], 
    top_n: int = 10, 
    title: str = "Top Detected Services Distribution"
) -> None:
    """
    가장 많이 감지된 서비스들의 분포를 시각화합니다.
    
    Args:
        results: AnalysisResult 객체 목록
        output_path: 그래프를 저장할 경로
        top_n: 상위 N개 서비스 표시
        title: 그래프 제목
    """
    setup_plot_style(figsize=(14, 10))
    
    service_counts = defaultdict(int)
    for res in results:
        for det in res.detections:
            if det.canonical_name:
                service_counts[det.canonical_name] += 1
            else:
                service_counts[det.label] += 1
    
    if not service_counts:
        print("⚠️ 시각화할 데이터가 없습니다 (서비스 분포)")
        return
        
    df_services = pd.DataFrame(service_counts.items(), columns=['service', 'count'])
    df_services = df_services.sort_values(by='count', ascending=False).head(top_n)
    
    plt.figure()
    sns.barplot(data=df_services, x='count', y='service', palette='viridis')
    plt.title(title)
    plt.xlabel("Count")
    plt.ylabel("Service Name")
    plt.savefig(output_path)
    plt.close()
    print(f"✅ 서비스 분포 그래프 저장: {output_path}")


def plot_normalization_success_rate(
    results: List[AnalysisResult],
    output_path: Union[str, Path],
    title: str = "Normalization Success Rate by Method"
) -> None:
    """
    분석 방법별 정규화 성공률을 시각화합니다.
    
    Args:
        results: AnalysisResult 객체 목록
        output_path: 그래프를 저장할 경로
        title: 그래프 제목
    """
    setup_plot_style()
    
    data = []
    for res in results:
        data.append({
            "method": res.analysis_method.value,
            "normalization_rate": res.normalization_success_rate,
            "cloud_provider": res.cloud_provider.value
        })

    if not data:
        print("⚠️ 시각화할 데이터가 없습니다 (정규화 성공률)")
        return
        
    df = pd.DataFrame(data)
    
    plt.figure()
    sns.barplot(data=df, x="method", y="normalization_rate", hue="cloud_provider", errorbar='sd')
    plt.title(title)
    plt.xlabel("Analysis Method")
    plt.ylabel("Normalization Success Rate")
    plt.ylim(0, 1)
    plt.savefig(output_path)
    plt.close()
    print(f"✅ 정규화 성공률 그래프 저장: {output_path}")


def create_summary_report(batch_result: BatchAnalysisResult, output_dir: Union[str, Path]) -> None:
    """
    배치 분석 결과에 대한 요약 보고서를 생성합니다.
    
    Args:
        batch_result: BatchAnalysisResult 객체
        output_dir: 보고서를 저장할 디렉토리
    """
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    
    report_path = output_dir / "summary_report.txt"
    
    with open(report_path, 'w', encoding='utf-8') as f:
        f.write(f"--- Analysis Summary Report ---\n")
        f.write(f"Timestamp: {batch_result.results[0].timestamp.isoformat() if batch_result.results else 'N/A'}\n")
        f.write(f"Cloud Provider: {batch_result.results[0].cloud_provider.value if batch_result.results else 'N/A'}\n")
        f.write(f"Analysis Method: {batch_result.results[0].analysis_method.value if batch_result.results else 'N/A'}\n\n")
        
        f.write(f"Total Images Analyzed: {batch_result.total_images}\n")
        f.write(f"Successful Analyses: {batch_result.success_count}\n")
        f.write(f"Failed Analyses: {batch_result.error_count}\n")
        f.write(f"Success Rate: {batch_result.success_rate:.2%}\n")
        f.write(f"Total Detections: {batch_result.total_detections}\n")
        f.write(f"Average Detections per Image: {batch_result.average_detections_per_image:.2f}\n")
        f.write(f"Average Processing Time: {batch_result.average_processing_time:.2f} seconds\n")
        f.write(f"Average Confidence: {batch_result.average_confidence:.3f}\n")
        f.write(f"Average Normalization Success Rate: {batch_result.average_normalization_success_rate:.2%}\n")
        f.write(f"\nDetailed Errors:\n")
        if batch_result.errors:
            for error in batch_result.errors:
                f.write(f"- {error.get('image_path', 'N/A')}: {error.get('message', 'N/A')}\n")
        else:
            f.write("- No errors reported.\n")
    
    print(f"✅ 요약 보고서 저장: {report_path}")


def draw_detections_on_image(
    image_path: Union[str, Path], 
    detections: List[DetectionResult], 
    output_path: Union[str, Path],
    font_path: Optional[str] = None
) -> None:
    """
    이미지에 감지된 바운딩 박스와 라벨을 그립니다.
    
    Args:
        image_path: 원본 이미지 경로
        detections: 감지 결과 (DetectionResult 목록)
        output_path: 결과 이미지를 저장할 경로
        font_path: 사용할 폰트 파일 경로 (기본값: PIL 기본 폰트)
    """
    try:
        image = Image.open(image_path).convert("RGB")
        draw = ImageDraw.Draw(image)
        
        try:
            # 폰트 로드 (Windows, Linux 경로 고려)
            if font_path and Path(font_path).exists():
                font_size = 20
                font = ImageFont.truetype(str(font_path), font_size)
            else:
                font_size = 20
                font = ImageFont.load_default()
        except Exception:
            # 폰트 로드 실패 시 기본 폰트 사용
            font_size = 20
            font = ImageFont.load_default()


        # 각 감지 결과에 대해 바운딩 박스와 라벨 그리기
        for detection in detections:
            bbox = detection.bbox
            label = detection.canonical_name if detection.canonical_name else detection.label
            confidence = detection.confidence
            
            # 바운딩 박스 그리기
            draw.rectangle(
                [(bbox.x, bbox.y), (bbox.x + bbox.width, bbox.y + bbox.height)], 
                outline="red", 
                width=3
            )
            
            # 라벨 텍스트
            text = f"{label} ({confidence:.2f})"
            
            # 텍스트 배경 그리기
            text_bbox = draw.textbbox((bbox.x, bbox.y - font_size - 5), text, font=font)
            draw.rectangle(text_bbox, fill="red")
            
            # 텍스트 그리기
            draw.text(
                (bbox.x + 5, bbox.y - font_size - 5), 
                text, 
                fill="white", 
                font=font
            )
        
        # 이미지 저장
        output_path.parent.mkdir(parents=True, exist_ok=True)
        image.save(output_path)
        print(f"✅ 바운딩 박스 이미지 저장: {output_path}")
        
    except Exception as e:
        print(f"❌ 이미지에 바운딩 박스 그리기 실패: {e}")


def plot_detection_status_distribution(
    results: List[AnalysisResult],
    output_path: Union[str, Path],
    title: str = "Detection Status Distribution"
) -> None:
    """
    감지 상태 (Detected, Not Detected, Uncertain 등)의 분포를 시각화합니다.
    """
    setup_plot_style()
    
    status_counts = defaultdict(int)
    for res in results:
        for det in res.detections:
            status_counts[det.status.value] += 1
            
    if not status_counts:
        print("⚠️ 시각화할 데이터가 없습니다 (감지 상태 분포)")
        return
    
    df_status = pd.DataFrame(status_counts.items(), columns=['status', 'count'])
    
    plt.figure()
    sns.barplot(data=df_status, x='status', y='count', palette='pastel')
    plt.title(title)
    plt.xlabel("Detection Status")
    plt.ylabel("Count")
    plt.savefig(output_path)
    plt.close()
    print(f"✅ 감지 상태 분포 그래프 저장: {output_path}")

