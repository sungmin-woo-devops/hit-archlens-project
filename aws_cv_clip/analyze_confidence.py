#!/usr/bin/env python3
"""
Confidence 점수 분석 도구
results.json의 confidence 점수 분포를 분석하여 최적의 threshold를 제안합니다.
"""

import json
import argparse
from pathlib import Path
from typing import List, Dict, Tuple
import matplotlib.pyplot as plt
import numpy as np
from collections import defaultdict


class ConfidenceAnalyzer:
    """Confidence 점수 분석 클래스"""
    
    def __init__(self, results_path: str):
        self.results_path = Path(results_path)
        self.results = self._load_results()
        self.scores = self._extract_scores()
    
    def _load_results(self) -> List[Dict]:
        """결과 JSON 파일을 로드합니다."""
        with open(self.results_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    
    def _extract_scores(self) -> List[float]:
        """모든 confidence 점수를 추출합니다."""
        scores = []
        for result in self.results:
            for obj in result.get('objects', []):
                scores.append(obj.get('score', 0.0))
        return scores
    
    def analyze_distribution(self) -> Dict:
        """점수 분포를 분석합니다."""
        if not self.scores:
            return {}
        
        scores = np.array(self.scores)
        
        analysis = {
            'total_detections': len(scores),
            'mean': float(np.mean(scores)),
            'median': float(np.median(scores)),
            'std': float(np.std(scores)),
            'min': float(np.min(scores)),
            'max': float(np.max(scores)),
            'percentiles': {
                '10': float(np.percentile(scores, 10)),
                '25': float(np.percentile(scores, 25)),
                '50': float(np.percentile(scores, 50)),
                '75': float(np.percentile(scores, 75)),
                '90': float(np.percentile(scores, 90)),
                '95': float(np.percentile(scores, 95)),
                '99': float(np.percentile(scores, 99))
            },
            'threshold_analysis': self._analyze_thresholds(scores)
        }
        
        return analysis
    
    def _analyze_thresholds(self, scores: np.ndarray) -> Dict:
        """다양한 threshold에 대한 분석을 수행합니다."""
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]
        analysis = {}
        
        for threshold in thresholds:
            above_threshold = scores >= threshold
            count_above = np.sum(above_threshold)
            percentage_above = (count_above / len(scores)) * 100
            
            analysis[f'threshold_{threshold}'] = {
                'count_above': int(count_above),
                'percentage_above': float(percentage_above),
                'count_below': int(len(scores) - count_above),
                'percentage_below': float(100 - percentage_above)
            }
        
        return analysis
    
    def analyze_by_category(self) -> Dict:
        """카테고리별 점수 분석을 수행합니다."""
        category_scores = defaultdict(list)
        
        for result in self.results:
            for obj in result.get('objects', []):
                category = obj.get('category', 'unknown')
                score = obj.get('score', 0.0)
                category_scores[category].append(score)
        
        analysis = {}
        for category, scores in category_scores.items():
            scores_array = np.array(scores)
            analysis[category] = {
                'count': len(scores),
                'mean': float(np.mean(scores_array)),
                'median': float(np.median(scores_array)),
                'std': float(np.std(scores_array)),
                'min': float(np.min(scores_array)),
                'max': float(np.max(scores_array))
            }
        
        return analysis
    
    def analyze_by_label(self) -> Dict:
        """라벨별 점수 분석을 수행합니다."""
        label_scores = defaultdict(list)
        
        for result in self.results:
            for obj in result.get('objects', []):
                label = obj.get('label', 'unknown')
                score = obj.get('score', 0.0)
                label_scores[label].append(score)
        
        analysis = {}
        for label, scores in label_scores.items():
            scores_array = np.array(scores)
            analysis[label] = {
                'count': len(scores),
                'mean': float(np.mean(scores_array)),
                'median': float(np.median(scores_array)),
                'std': float(np.std(scores_array)),
                'min': float(np.min(scores_array)),
                'max': float(np.max(scores_array))
            }
        
        return analysis
    
    def plot_distribution(self, save_path: str = None) -> None:
        """점수 분포를 시각화합니다."""
        if not self.scores:
            print("분석할 점수가 없습니다.")
            return
        
        # 한글 폰트 설정
        plt.rcParams['font.family'] = ['DejaVu Sans', 'NanumGothic', 'Malgun Gothic', 'Arial Unicode MS']
        plt.rcParams['axes.unicode_minus'] = False
        
        fig, ((ax1, ax2), (ax3, ax4)) = plt.subplots(2, 2, figsize=(15, 12))
        
        scores = np.array(self.scores)
        
        # 히스토그램
        ax1.hist(scores, bins=50, alpha=0.7, color='skyblue', edgecolor='black')
        ax1.axvline(np.mean(scores), color='red', linestyle='--', label=f'평균: {np.mean(scores):.3f}')
        ax1.axvline(np.median(scores), color='green', linestyle='--', label=f'중앙값: {np.median(scores):.3f}')
        ax1.set_xlabel('Confidence Score')
        ax1.set_ylabel('빈도')
        ax1.set_title('Confidence 점수 분포')
        ax1.legend()
        ax1.grid(True, alpha=0.3)
        
        # 박스플롯
        ax2.boxplot(scores, vert=True)
        ax2.set_ylabel('Confidence Score')
        ax2.set_title('Confidence 점수 박스플롯')
        ax2.grid(True, alpha=0.3)
        
        # 누적 분포
        sorted_scores = np.sort(scores)
        cumulative = np.arange(1, len(sorted_scores) + 1) / len(sorted_scores)
        ax3.plot(sorted_scores, cumulative, linewidth=2)
        ax3.set_xlabel('Confidence Score')
        ax3.set_ylabel('누적 비율')
        ax3.set_title('누적 분포 함수')
        ax3.grid(True, alpha=0.3)
        
        # Threshold별 필터링 결과
        thresholds = [0.5, 0.6, 0.7, 0.8, 0.85, 0.9, 0.95]
        percentages = []
        for threshold in thresholds:
            percentage = (np.sum(scores >= threshold) / len(scores)) * 100
            percentages.append(percentage)
        
        ax4.bar(thresholds, percentages, alpha=0.7, color='orange')
        ax4.set_xlabel('Threshold')
        ax4.set_ylabel('Threshold 이상 비율 (%)')
        ax4.set_title('Threshold별 필터링 결과')
        ax4.grid(True, alpha=0.3)
        
        # 값 표시
        for i, (threshold, percentage) in enumerate(zip(thresholds, percentages)):
            ax4.text(threshold, percentage + 1, f'{percentage:.1f}%', 
                    ha='center', va='bottom')
        
        plt.tight_layout()
        
        if save_path:
            plt.savefig(save_path, dpi=300, bbox_inches='tight')
            print(f"분포 그래프가 저장되었습니다: {save_path}")
        else:
            plt.show()
        
        plt.close()
    
    def print_analysis(self) -> None:
        """분석 결과를 출력합니다."""
        print("=" * 60)
        print("CONFIDENCE 점수 분석 결과")
        print("=" * 60)
        
        if not self.scores:
            print("분석할 점수가 없습니다.")
            return
        
        # 기본 통계
        analysis = self.analyze_distribution()
        print(f"\n📊 기본 통계:")
        print(f"  총 감지 수: {analysis['total_detections']:,}개")
        print(f"  평균: {analysis['mean']:.4f}")
        print(f"  중앙값: {analysis['median']:.4f}")
        print(f"  표준편차: {analysis['std']:.4f}")
        print(f"  최소값: {analysis['min']:.4f}")
        print(f"  최대값: {analysis['max']:.4f}")
        
        # 백분위수
        print(f"\n📈 백분위수:")
        percentiles = analysis['percentiles']
        for p, value in percentiles.items():
            print(f"  {p}%: {value:.4f}")
        
        # Threshold 분석
        print(f"\n🎯 Threshold 분석:")
        threshold_analysis = analysis['threshold_analysis']
        for threshold_key, data in threshold_analysis.items():
            threshold = threshold_key.split('_')[1]
            print(f"  Threshold {threshold}:")
            print(f"    - {threshold} 이상: {data['count_above']:,}개 ({data['percentage_above']:.1f}%)")
            print(f"    - {threshold} 미만: {data['count_below']:,}개 ({data['percentage_below']:.1f}%)")
        
        # 카테고리별 분석
        print(f"\n🏷️ 카테고리별 분석:")
        category_analysis = self.analyze_by_category()
        for category, data in sorted(category_analysis.items(), key=lambda x: x[1]['count'], reverse=True):
            print(f"  {category}:")
            print(f"    - 개수: {data['count']}개")
            print(f"    - 평균: {data['mean']:.4f}")
            print(f"    - 중앙값: {data['median']:.4f}")
        
        # 라벨별 분석 (상위 10개)
        print(f"\n🏷️ 라벨별 분석 (상위 10개):")
        label_analysis = self.analyze_by_label()
        sorted_labels = sorted(label_analysis.items(), key=lambda x: x[1]['count'], reverse=True)
        for label, data in sorted_labels[:10]:
            print(f"  {label}:")
            print(f"    - 개수: {data['count']}개")
            print(f"    - 평균: {data['mean']:.4f}")
            print(f"    - 중앙값: {data['median']:.4f}")
        
        # 권장사항
        print(f"\n💡 권장사항:")
        mean_score = analysis['mean']
        median_score = analysis['median']
        
        if mean_score > 0.8:
            print(f"  - 평균 점수가 높음 ({mean_score:.3f}) → 높은 threshold 권장")
            if median_score > 0.85:
                recommended_threshold = 0.85
            else:
                recommended_threshold = 0.8
        elif mean_score > 0.6:
            print(f"  - 평균 점수가 보통 ({mean_score:.3f}) → 중간 threshold 권장")
            recommended_threshold = 0.7
        else:
            print(f"  - 평균 점수가 낮음 ({mean_score:.3f}) → 낮은 threshold 권장")
            recommended_threshold = 0.6
        
        print(f"  - 권장 threshold: {recommended_threshold}")
        
        # 현재 threshold에서의 결과
        current_threshold_data = threshold_analysis[f'threshold_{recommended_threshold}']
        print(f"  - 권장 threshold 적용 시: {current_threshold_data['count_above']:,}개 감지 ({current_threshold_data['percentage_above']:.1f}%)")


def main():
    """메인 함수"""
    parser = argparse.ArgumentParser(description="Confidence 점수 분석 도구")
    parser.add_argument("--results", default="out/results.json", 
                       help="results.json 파일 경로")
    parser.add_argument("--plot", help="분포 그래프 저장 경로")
    parser.add_argument("--output", help="분석 결과 JSON 저장 경로")
    
    args = parser.parse_args()
    
    # 분석기 초기화
    analyzer = ConfidenceAnalyzer(args.results)
    
    # 분석 실행
    analyzer.print_analysis()
    
    # 그래프 생성
    if args.plot:
        analyzer.plot_distribution(args.plot)
    
    # JSON 결과 저장
    if args.output:
        analysis_result = {
            'distribution': analyzer.analyze_distribution(),
            'by_category': analyzer.analyze_by_category(),
            'by_label': analyzer.analyze_by_label()
        }
        
        with open(args.output, 'w', encoding='utf-8') as f:
            json.dump(analysis_result, f, ensure_ascii=False, indent=2)
        
        print(f"\n분석 결과가 저장되었습니다: {args.output}")


if __name__ == "__main__":
    main()
