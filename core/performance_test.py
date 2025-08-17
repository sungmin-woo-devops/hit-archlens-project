#!/usr/bin/env python3
"""
Performance Test Script

극적인 성능 개선 효과를 테스트하는 스크립트
"""

import time
import json
import yaml
from pathlib import Path
from typing import Dict, Any, List
import torch
import numpy as np
from PIL import Image

from core.auto_labeler.ultra_fast_cv_labeler import UltraFastCVAutoLabeler
from core.utils.performance_optimizer import PerformanceOptimizer, profile_performance
from core.models import CloudProvider


class PerformanceTester:
    """
    성능 테스트 도구
    
    주요 테스트:
    1. 처리 속도 비교
    2. 메모리 사용량 비교
    3. 정확도 비교
    4. 스케일링 테스트
    """
    
    def __init__(self, config_path: str = "core/configs/ultra_performance_config.yaml"):
        """
        성능 테스터 초기화
        
        Args:
            config_path: 설정 파일 경로
        """
        self.config = self._load_config(config_path)
        self.performance_optimizer = PerformanceOptimizer(self.config)
        
        # 테스트 이미지 준비
        self.test_images = self._load_test_images()
        
        print("🧪 Performance Tester 초기화 완료")
    
    def _load_config(self, config_path: str) -> Dict[str, Any]:
        """설정 파일 로드"""
        with open(config_path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    
    def _load_test_images(self) -> List[Image.Image]:
        """테스트 이미지 로드"""
        images = []
        
        # 실제 AWS 아이콘 이미지 사용
        icon_dir = Path("aws_data_collectors/collectors/collected_icons/raw")
        if icon_dir.exists():
            icon_files = list(icon_dir.glob("*.png")) + list(icon_dir.glob("*.jpg"))
            for icon_file in icon_files[:10]:  # 상위 10개만 사용
                try:
                    image = Image.open(icon_file)
                    images.append(image)
                    print(f"📁 로드된 이미지: {icon_file.name}")
                except Exception as e:
                    print(f"⚠️ 이미지 로드 실패: {icon_file.name} - {e}")
        
        # 실제 이미지가 없으면 더미 이미지 생성
        if not images:
            print("📝 더미 이미지 생성 중...")
            for i in range(10):
                # AWS 서비스 색상을 반영한 더미 이미지
                img = Image.new('RGB', (256, 256), color=(255, 153, 0))  # AWS 오렌지
                images.append(img)
        
        return images
    
    @profile_performance
    def test_processing_speed(self) -> Dict[str, Any]:
        """처리 속도 테스트"""
        print("🏃‍♂️ 처리 속도 테스트 시작...")
        
        results = {
            "total_images": len(self.test_images),
            "processing_times": [],
            "avg_processing_time": 0.0,
            "throughput": 0.0
        }
        
        # Ultra Fast CV Labeler 초기화
        labeler = UltraFastCVAutoLabeler(CloudProvider.AWS, self.config)
        
        # 각 이미지 처리 시간 측정
        for i, image in enumerate(self.test_images):
            with self.performance_optimizer.performance_monitoring(f"Image_{i}"):
                start_time = time.time()
                
                detections = labeler._analyze_single_image(image)
                
                processing_time = time.time() - start_time
                results["processing_times"].append(processing_time)
                
                print(f"  이미지 {i+1}: {processing_time:.3f}초, {len(detections)}개 감지")
        
        # 통계 계산
        results["avg_processing_time"] = np.mean(results["processing_times"])
        results["throughput"] = len(self.test_images) / sum(results["processing_times"])
        
        print(f"📊 처리 속도 테스트 결과:")
        print(f"  평균 처리 시간: {results['avg_processing_time']:.3f}초")
        print(f"  처리량: {results['throughput']:.2f} 이미지/초")
        
        return results
    
    @profile_performance
    def test_memory_usage(self) -> Dict[str, Any]:
        """메모리 사용량 테스트"""
        print("💾 메모리 사용량 테스트 시작...")
        
        results = {
            "memory_usage": [],
            "peak_memory": 0.0,
            "avg_memory": 0.0
        }
        
        # Ultra Fast CV Labeler 초기화
        labeler = UltraFastCVAutoLabeler(CloudProvider.AWS, self.config)
        
        # 메모리 사용량 모니터링
        for i, image in enumerate(self.test_images):
            # 메모리 사용량 측정
            memory_before = self.performance_optimizer.memory_tracker.get_memory_usage()
            
            detections = labeler._analyze_single_image(image)
            
            memory_after = self.performance_optimizer.memory_tracker.get_memory_usage()
            memory_used = memory_after - memory_before
            
            results["memory_usage"].append(memory_used)
            
            print(f"  이미지 {i+1}: 메모리 사용량 {memory_used:.1%}")
        
        # 통계 계산
        results["peak_memory"] = max(results["memory_usage"])
        results["avg_memory"] = np.mean(results["memory_usage"])
        
        print(f"📊 메모리 사용량 테스트 결과:")
        print(f"  평균 메모리 사용량: {results['avg_memory']:.1%}")
        print(f"  최대 메모리 사용량: {results['peak_memory']:.1%}")
        
        return results
    
    @profile_performance
    def test_scaling_performance(self) -> Dict[str, Any]:
        """스케일링 성능 테스트"""
        print("📈 스케일링 성능 테스트 시작...")
        
        results = {
            "batch_sizes": [1, 2, 4, 8, 16],
            "processing_times": [],
            "throughput": [],
            "memory_usage": []
        }
        
        # Ultra Fast CV Labeler 초기화
        labeler = UltraFastCVAutoLabeler(CloudProvider.AWS, self.config)
        
        # 다양한 배치 크기로 테스트
        for batch_size in results["batch_sizes"]:
            print(f"  배치 크기 {batch_size} 테스트 중...")
            
            # 배치 크기 설정
            labeler.batch_size = batch_size
            
            # 배치 처리 시간 측정
            start_time = time.time()
            memory_before = self.performance_optimizer.memory_tracker.get_memory_usage()
            
            # 배치로 이미지 처리
            for i in range(0, len(self.test_images), batch_size):
                batch_images = self.test_images[i:i+batch_size]
                for image in batch_images:
                    detections = labeler._analyze_single_image(image)
            
            processing_time = time.time() - start_time
            memory_after = self.performance_optimizer.memory_tracker.get_memory_usage()
            
            results["processing_times"].append(processing_time)
            results["throughput"].append(len(self.test_images) / processing_time)
            results["memory_usage"].append(memory_after - memory_before)
            
            print(f"    처리 시간: {processing_time:.3f}초")
            print(f"    처리량: {results['throughput'][-1]:.2f} 이미지/초")
            print(f"    메모리 사용량: {results['memory_usage'][-1]:.1%}")
        
        print(f"📊 스케일링 성능 테스트 결과:")
        for i, batch_size in enumerate(results["batch_sizes"]):
            print(f"  배치 크기 {batch_size}: {results['throughput'][i]:.2f} 이미지/초")
        
        return results
    
    @profile_performance
    def test_accuracy_comparison(self) -> Dict[str, Any]:
        """정확도 비교 테스트"""
        print("🎯 정확도 비교 테스트 시작...")
        
        results = {
            "detection_counts": [],
            "confidence_scores": [],
            "avg_confidence": 0.0
        }
        
        # Ultra Fast CV Labeler 초기화
        labeler = UltraFastCVAutoLabeler(CloudProvider.AWS, self.config)
        
        # 각 이미지의 감지 결과 분석
        for i, image in enumerate(self.test_images):
            detections = labeler._analyze_single_image(image)
            
            results["detection_counts"].append(len(detections))
            
            if detections:
                confidences = [d.confidence for d in detections]
                results["confidence_scores"].extend(confidences)
                
                avg_conf = np.mean(confidences)
                print(f"  이미지 {i+1}: {len(detections)}개 감지, 평균 신뢰도 {avg_conf:.3f}")
            else:
                print(f"  이미지 {i+1}: 감지 없음")
        
        # 통계 계산
        results["avg_confidence"] = np.mean(results["confidence_scores"]) if results["confidence_scores"] else 0.0
        
        print(f"📊 정확도 비교 테스트 결과:")
        print(f"  평균 감지 수: {np.mean(results['detection_counts']):.1f}")
        print(f"  평균 신뢰도: {results['avg_confidence']:.3f}")
        
        return results
    
    def run_comprehensive_test(self) -> Dict[str, Any]:
        """종합 성능 테스트 실행"""
        print("🚀 종합 성능 테스트 시작")
        print("=" * 50)
        
        comprehensive_results = {
            "test_timestamp": time.strftime("%Y-%m-%d %H:%M:%S"),
            "system_info": self._get_system_info(),
            "config": self.config
        }
        
        # 1. 처리 속도 테스트
        comprehensive_results["speed_test"] = self.test_processing_speed()
        
        # 2. 메모리 사용량 테스트
        comprehensive_results["memory_test"] = self.test_memory_usage()
        
        # 3. 스케일링 성능 테스트
        comprehensive_results["scaling_test"] = self.test_scaling_performance()
        
        # 4. 정확도 비교 테스트
        comprehensive_results["accuracy_test"] = self.test_accuracy_comparison()
        
        # 5. 성능 리포트 생성
        comprehensive_results["performance_report"] = self.performance_optimizer.get_performance_report()
        
        # 결과 저장
        self._save_results(comprehensive_results)
        
        # 결과 요약 출력
        self._print_summary(comprehensive_results)
        
        return comprehensive_results
    
    def _get_system_info(self) -> Dict[str, Any]:
        """시스템 정보 수집"""
        import sys
        return {
            "python_version": f"{sys.version_info.major}.{sys.version_info.minor}.{sys.version_info.micro}",
            "pytorch_version": torch.__version__,
            "cuda_available": torch.cuda.is_available(),
            "cuda_version": torch.version.cuda if torch.cuda.is_available() else "N/A",
            "gpu_count": torch.cuda.device_count() if torch.cuda.is_available() else 0,
            "gpu_name": torch.cuda.get_device_name(0) if torch.cuda.is_available() else "N/A"
        }
    
    def _save_results(self, results: Dict[str, Any]):
        """테스트 결과 저장"""
        output_dir = Path("performance_test_results")
        output_dir.mkdir(exist_ok=True)
        
        timestamp = time.strftime("%Y%m%d_%H%M%S")
        output_file = output_dir / f"performance_test_{timestamp}.json"
        
        with open(output_file, 'w', encoding='utf-8') as f:
            json.dump(results, f, ensure_ascii=False, indent=2)
        
        print(f"💾 테스트 결과 저장: {output_file}")
    
    def _print_summary(self, results: Dict[str, Any]):
        """결과 요약 출력"""
        print("\n" + "=" * 50)
        print("📊 종합 성능 테스트 결과 요약")
        print("=" * 50)
        
        # 처리 속도
        speed_test = results["speed_test"]
        print(f"🏃‍♂️ 처리 속도:")
        print(f"  평균 처리 시간: {speed_test['avg_processing_time']:.3f}초")
        print(f"  처리량: {speed_test['throughput']:.2f} 이미지/초")
        
        # 메모리 사용량
        memory_test = results["memory_test"]
        print(f"💾 메모리 사용량:")
        print(f"  평균 메모리 사용량: {memory_test['avg_memory']:.1%}")
        print(f"  최대 메모리 사용량: {memory_test['peak_memory']:.1%}")
        
        # 정확도
        accuracy_test = results["accuracy_test"]
        print(f"🎯 정확도:")
        print(f"  평균 감지 수: {np.mean(accuracy_test['detection_counts']):.1f}")
        print(f"  평균 신뢰도: {accuracy_test['avg_confidence']:.3f}")
        
        # 성능 개선 권장사항
        performance_report = results["performance_report"]
        if "recommendations" in performance_report:
            print(f"💡 성능 개선 권장사항:")
            for rec in performance_report["recommendations"]:
                print(f"  - {rec}")
        
        print("=" * 50)


def main():
    """메인 실행 함수"""
    print("🧪 Ultra Performance Test 시작")
    
    # 성능 테스터 초기화
    tester = PerformanceTester()
    
    # 종합 테스트 실행
    results = tester.run_comprehensive_test()
    
    print("✅ 성능 테스트 완료!")


if __name__ == "__main__":
    main()
