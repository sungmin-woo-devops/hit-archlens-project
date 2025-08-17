#!/usr/bin/env python3
"""
바운딩 박스 시각화 도구
AWS 아키텍처 다이어그램에서 감지된 객체들의 바운딩 박스를 이미지와 겹쳐서 표시합니다.
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


class BoundingBoxVisualizer:
    """바운딩 박스 시각화 클래스"""
    
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
    
    def visualize_image(self, image_path: str, save_path: Optional[str] = None, 
                       show_labels: bool = True, show_scores: bool = True,
                       figsize: Tuple[int, int] = (15, 10)) -> None:
        """
        특정 이미지의 바운딩 박스를 시각화합니다.
        
        Args:
            image_path: 이미지 파일 경로 (results.json의 image_path 기준)
            save_path: 저장할 파일 경로 (None이면 화면에 표시)
            show_labels: 라벨 표시 여부
            show_scores: 점수 표시 여부
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
        # image_path가 이미 'images/'로 시작하는 경우 처리
        if image_path.startswith('images/'):
            # 상대 경로에서 images/ 부분 제거
            relative_path = image_path[7:]  # 'images/' 제거
            full_image_path = self.images_dir / relative_path
        else:
            full_image_path = self.images_dir / image_path
            
        if not full_image_path.exists():
            print(f"이미지 파일을 찾을 수 없습니다: {full_image_path}")
            return
        
        image = Image.open(full_image_path)
        
        # 그래프 설정
        fig, ax = plt.subplots(1, 1, figsize=figsize)
        ax.imshow(image)
        ax.axis('off')
        
        # 바운딩 박스 그리기
        for obj in result.get('objects', []):
            bbox = obj['bbox']
            label = obj['label']
            score = obj['score']
            category = obj.get('category', 'unknown')
            
            # 바운딩 박스 좌표 (x, y, width, height)
            x, y, w, h = bbox
            
            # 색상 선택
            color = self.category_colors.get(category, (1, 0, 0))
            
            # 바운딩 박스 그리기
            rect = Rectangle((x, y), w, h, linewidth=2, 
                           edgecolor=color, facecolor='none', alpha=0.8)
            ax.add_patch(rect)
            
            # 라벨 텍스트
            text_parts = []
            if show_labels:
                text_parts.append(label)
            if show_scores:
                text_parts.append(f"{score:.3f}")
            
            if text_parts:
                text = " | ".join(text_parts)
                ax.text(x, y - 5, text, fontsize=10, color='white',
                       bbox=dict(boxstyle="round,pad=0.3", facecolor=color, alpha=0.8))
        
        # 제목 설정
        title = f"바운딩 박스 시각화: {image_path}"
        if result.get('width') and result.get('height'):
            title += f" ({result['width']}x{result['height']})"
        ax.set_title(title, fontsize=14, pad=20)
        
        # 범례 추가
        self._add_legend(ax)
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"이미지가 저장되었습니다: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def _add_legend(self, ax):
        """범례를 추가합니다."""
        legend_elements = []
        for category, color in self.category_colors.items():
            legend_elements.append(patches.Patch(color=color, label=category))
        
        if legend_elements:
            ax.legend(handles=legend_elements, loc='upper right', 
                     bbox_to_anchor=(1.15, 1), fontsize=8)
    
    def list_images(self) -> List[str]:
        """처리 가능한 이미지 목록을 반환합니다."""
        return [result['image_path'] for result in self.results]
    
    def visualize_random_image(self, save_path: Optional[str] = None, **kwargs) -> str:
        """랜덤 이미지를 선택하여 시각화합니다."""
        images = self.list_images()
        if not images:
            print("처리할 이미지가 없습니다.")
            return ""
        
        selected_image = random.choice(images)
        print(f"선택된 이미지: {selected_image}")
        self.visualize_image(selected_image, save_path, **kwargs)
        return selected_image
    
    def visualize_all_images(self, output_dir: str, **kwargs) -> None:
        """모든 이미지를 시각화하여 저장합니다."""
        output_path = Path(output_dir)
        output_path.mkdir(exist_ok=True)
        
        images = self.list_images()
        print(f"총 {len(images)}개 이미지를 처리합니다...")
        
        for i, image_path in enumerate(images, 1):
            print(f"처리 중: {i}/{len(images)} - {image_path}")
            
            # 파일명 생성
            filename = Path(image_path).stem
            save_path = output_path / f"{filename}_bbox.png"
            
            try:
                self.visualize_image(image_path, str(save_path), **kwargs)
            except Exception as e:
                print(f"오류 발생 ({image_path}): {e}")
        
        print(f"모든 이미지가 저장되었습니다: {output_dir}")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="바운딩 박스 시각화 도구")
    parser.add_argument("--results", default="out/results.json", 
                       help="results.json 파일 경로")
    parser.add_argument("--images-dir", default="images", 
                       help="이미지 디렉토리 경로")
    parser.add_argument("--image", help="특정 이미지 파일명 (예: cf3ed5f25c.png)")
    parser.add_argument("--random", action="store_true", 
                       help="랜덤 이미지 선택")
    parser.add_argument("--all", action="store_true", 
                       help="모든 이미지 처리")
    parser.add_argument("--output-dir", default="out/visualizations", 
                       help="출력 디렉토리")
    parser.add_argument("--save", help="저장할 파일 경로")
    parser.add_argument("--no-labels", action="store_true", 
                       help="라벨 숨기기")
    parser.add_argument("--no-scores", action="store_true", 
                       help="점수 숨기기")
    parser.add_argument("--list", action="store_true", 
                       help="처리 가능한 이미지 목록 출력")
    
    args = parser.parse_args()
    
    # 시각화 도구 초기화
    visualizer = BoundingBoxVisualizer(args.results, args.images_dir)
    
    # 처리 가능한 이미지 목록 출력
    if args.list:
        images = visualizer.list_images()
        print(f"처리 가능한 이미지 ({len(images)}개):")
        for img in images:
            print(f"  - {img}")
        return
    
    # 특정 이미지 처리
    if args.image:
        visualizer.visualize_image(
            args.image, 
            args.save,
            show_labels=not args.no_labels,
            show_scores=not args.no_scores
        )
    
    # 랜덤 이미지 처리
    elif args.random:
        visualizer.visualize_random_image(
            args.save,
            show_labels=not args.no_labels,
            show_scores=not args.no_scores
        )
    
    # 모든 이미지 처리
    elif args.all:
        visualizer.visualize_all_images(
            args.output_dir,
            show_labels=not args.no_labels,
            show_scores=not args.no_scores
        )
    
    # 기본값: 첫 번째 이미지 처리
    else:
        images = visualizer.list_images()
        if images:
            print(f"기본 이미지 처리: {images[0]}")
            visualizer.visualize_image(
                images[0],
                args.save,
                show_labels=not args.no_labels,
                show_scores=not args.no_scores
            )
        else:
            print("처리할 이미지가 없습니다.")


if __name__ == "__main__":
    main()
