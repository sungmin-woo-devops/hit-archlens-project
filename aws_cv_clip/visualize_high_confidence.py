#!/usr/bin/env python3
"""
높은 Confidence Threshold 바운딩 박스 시각화 도구
다양한 confidence threshold를 적용하여 바운딩 박스 수를 비교합니다.
"""

import json
import os
import argparse
from pathlib import Path
from typing import List, Dict, Tuple, Optional
import matplotlib.pyplot as plt
import matplotlib.patches as patches
from matplotlib.patches import Rectangle
import numpy as np
from PIL import Image
import random


class HighConfidenceVisualizer:
    """높은 Confidence Threshold 시각화 클래스"""
    
    def __init__(self, results_path: str, images_dir: str):
        """
        Args:
            results_path: results.json 파일 경로
            images_dir: 이미지 파일들이 있는 디렉토리 경로
        """
        self.results_path = Path(results_path)
        self.images_dir = Path(images_dir)
        self.results = self._load_results()
        
        # 카테고리별 색상 매핑
        self.category_colors = self._generate_category_colors()
    
    def _load_results(self) -> List[Dict]:
        """결과 JSON 파일을 로드합니다."""
        with open(self.results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _generate_category_colors(self) -> Dict[str, Tuple[float, float, float]]:
        """카테고리별 고유 색상을 생성합니다."""
        categories = set()
        for result in self.results:
            for obj in result.get('objects', []):
                categories.add(obj.get('category', 'unknown'))
        
        # 고유한 색상 생성
        colors = plt.cm.Set3(np.linspace(0, 1, len(categories)))
        return {cat: tuple(colors[i]) for i, cat in enumerate(sorted(categories))}
    
    def filter_by_confidence(self, objects: List[Dict], threshold: float) -> List[Dict]:
        """Confidence threshold로 객체를 필터링합니다."""
        return [obj for obj in objects if obj.get('score', 0.0) >= threshold]
    
    def visualize_with_thresholds(self, image_path: str, thresholds: List[float] = [0.7, 0.8, 0.85, 0.9], 
                                 save_path: Optional[str] = None, figsize: Tuple[int, int] = (20, 15)) -> None:
        """
        다양한 threshold로 바운딩 박스를 시각화합니다.
        
        Args:
            image_path: 이미지 파일 경로
            thresholds: 적용할 confidence threshold 목록
            save_path: 저장할 파일 경로
            figsize: 그래프 크기
        """
        # 결과에서 해당 이미지 찾기
        result = None
        for r in self.results:
            if r['image_path'] == image_path:
                result = r
                break
        
        if not result:
            print(f"이미지를 찾을 수 없습니다: {image_path}")
            return
        
        # 이미지 로드
        if image_path.startswith('images/'):
            relative_path = image_path[7:]
            full_image_path = self.images_dir / relative_path
        else:
            full_image_path = self.images_dir / image_path
            
        if not full_image_path.exists():
            print(f"이미지 파일을 찾을 수 없습니다: {full_image_path}")
            return
        
        image = Image.open(full_image_path)
        
        # 한글 폰트 설정
        plt.rcParams['font.family'] = ['DejaVu Sans', 'NanumGothic', 'Malgun Gothic', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        # 서브플롯 생성
        n_thresholds = len(thresholds)
        fig, axes = plt.subplots(2, 2, figsize=figsize)
        axes = axes.flatten()
        
        # 각 threshold별로 시각화
        for i, threshold in enumerate(thresholds):
            if i >= len(axes):
                break
                
            ax = axes[i]
            ax.imshow(image)
            ax.axis('off')
            
            # 해당 threshold로 필터링
            filtered_objects = self.filter_by_confidence(result.get('objects', []), threshold)
            
            # 바운딩 박스 그리기
            for obj in filtered_objects:
                bbox = obj['bbox']
                label = obj['label']
                score = obj['score']
                category = obj.get('category', 'unknown')
                
                # 바운딩 박스 좌표
                x, y, w, h = bbox
                
                # 색상 선택
                color = self.category_colors.get(category, (1, 0, 0))
                
                # 바운딩 박스 그리기
                rect = Rectangle((x, y), w, h, linewidth=2, 
                               edgecolor=color, facecolor='none', alpha=0.8)
                ax.add_patch(rect)
                
                # 라벨 텍스트
                text = f"{label} | {score:.3f}"
                ax.text(x, y - 5, text, fontsize=8, color='white',
                       bbox=dict(boxstyle="round,pad=0.2", facecolor=color, alpha=0.8))
            
            # 제목 설정
            title = f"Threshold: {threshold} (감지: {len(filtered_objects)}개)"
            ax.set_title(title, fontsize=12, pad=10)
        
        # 전체 제목
        fig.suptitle(f'Confidence Threshold별 바운딩 박스 비교: {image_path}', 
                    fontsize=16, y=0.95)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"비교 이미지가 저장되었습니다: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def compare_all_images(self, thresholds: List[float] = [0.7, 0.8, 0.85, 0.9], 
                          output_dir: str = "out/high_confidence_comparison") -> None:
        """모든 이미지에 대해 threshold 비교를 수행합니다."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        images = [result['image_path'] for result in self.results]
        print(f"총 {len(images)}개 이미지를 처리합니다...")
        
        for i, image_path in enumerate(images, 1):
            print(f"처리 중: {i}/{len(images)} - {image_path}")
            
            # 파일명 생성
            filename = Path(image_path).stem
            save_path = output_path / f"{filename}_threshold_comparison.png"
            
            try:
                self.visualize_with_thresholds(image_path, thresholds, str(save_path))
            except Exception as e:
                print(f"오류 발생 ({image_path}): {e}")
        
        print(f"모든 비교 이미지가 저장되었습니다: {output_dir}")
    
    def analyze_threshold_impact(self) -> Dict:
        """Threshold별 영향 분석을 수행합니다."""
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]
        analysis = {}
        
        for threshold in thresholds:
            total_objects = 0
            filtered_objects = 0
            
            for result in self.results:
                objects = result.get('objects', [])
                total_objects += len(objects)
                filtered_objects += len(self.filter_by_confidence(objects, threshold))
            
            analysis[threshold] = {
                'total_objects': total_objects,
                'filtered_objects': filtered_objects,
                'filtered_percentage': (filtered_objects / total_objects * 100) if total_objects > 0 else 0
            }
        
        return analysis
    
    def print_threshold_analysis(self) -> None:
        """Threshold 분석 결과를 출력합니다."""
        print("=" * 60)
        print("CONFIDENCE THRESHOLD 영향 분석")
        print("=" * 60)
        
        analysis = self.analyze_threshold_impact()
        
        print(f"\n📊 Threshold별 필터링 결과:")
        for threshold, data in analysis.items():
            print(f"  Threshold {threshold}:")
            print(f"    - 전체 객체: {data['total_objects']:,}개")
            print(f"    - 필터링 후: {data['filtered_objects']:,}개")
            print(f"    - 필터링 비율: {data['filtered_percentage']:.1f}%")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        print(f"  - 0.8 threshold: {analysis[0.8]['filtered_percentage']:.1f}% 유지 (균형)")
        print(f"  - 0.85 threshold: {analysis[0.85]['filtered_percentage']:.1f}% 유지 (높은 정확도)")
        print(f"  - 0.9 threshold: {analysis[0.9]['filtered_percentage']:.1f}% 유지 (매우 높은 정확도)")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="높은 Confidence Threshold 시각화 도구")
    parser.add_argument("--results", default="out/results.json", 
                       help="results.json 파일 경로")
    parser.add_argument("--images-dir", default="images", 
                       help="이미지 디렉토리 경로")
    parser.add_argument("--image", help="특정 이미지 파일명")
    parser.add_argument("--all", action="store_true", 
                       help="모든 이미지 처리")
    parser.add_argument("--output-dir", default="out/high_confidence_comparison", 
                       help="출력 디렉토리")
    parser.add_argument("--save", help="저장할 파일 경로")
    parser.add_argument("--analyze", action="store_true", 
                       help="Threshold 영향 분석만 수행")
    parser.add_argument("--thresholds", nargs='+', type=float, 
                       default=[0.7, 0.8, 0.85, 0.9],
                       help="비교할 threshold 목록")
    
    args = parser.parse_args()
    
    # 시각화 도구 초기화
    visualizer = HighConfidenceVisualizer(args.results, args.images_dir)
    
    # Threshold 영향 분석
    if args.analyze:
        visualizer.print_threshold_analysis()
        return
    
    # 특정 이미지 처리
    if args.image:
        visualizer.visualize_with_thresholds(
            args.image, 
            args.thresholds,
            args.save
        )
    
    # 모든 이미지 처리
    elif args.all:
        visualizer.compare_all_images(
            args.thresholds,
            args.output_dir
        )
    
    # 기본값: 첫 번째 이미지 처리
    else:
        images = [result['image_path'] for result in visualizer.results]
        if images:
            print(f"기본 이미지 처리: {images[0]}")
            visualizer.visualize_with_thresholds(
                images[0],
                args.thresholds,
                args.save
            )
        else:
            print("처리할 이미지가 없습니다.")


if __name__ == "__main__":
    main()
