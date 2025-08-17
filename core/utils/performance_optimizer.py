"""
Performance Optimizer

극적인 성능 개선을 위한 최적화 도구들
"""

import time
import psutil
import torch
import numpy as np
from typing import Dict, Any, List, Optional, Tuple
from pathlib import Path
import json
import threading
from dataclasses import dataclass
from contextlib import contextmanager
import gc
import tracemalloc


@dataclass
class PerformanceMetrics:
    """성능 메트릭 데이터 클래스"""
    processing_time: float
    memory_usage: float
    cpu_usage: float
    gpu_usage: Optional[float] = None
    throughput: float = 0.0
    latency: float = 0.0
    cache_hit_rate: float = 0.0
    batch_efficiency: float = 0.0


class PerformanceOptimizer:
    """
    성능 최적화 도구
    
    주요 기능:
    1. 실시간 성능 모니터링
    2. 메모리 최적화
    3. GPU 최적화
    4. 캐시 최적화
    5. 배치 처리 최적화
    """
    
    def __init__(self, config: Dict[str, Any]):
        """
        성능 최적화 도구 초기화
        
        Args:
            config: 성능 설정
        """
        self.config = config
        self.metrics_history: List[PerformanceMetrics] = []
        self.optimization_enabled = config.get("performance", {}).get("enable_optimization", True)
        
        # 메모리 모니터링
        self.memory_tracker = MemoryTracker()
        
        # GPU 모니터링
        self.gpu_tracker = GPUTracker() if torch.cuda.is_available() else None
        
        # 캐시 최적화
        self.cache_optimizer = CacheOptimizer(config)
        
        # 배치 처리 최적화
        self.batch_optimizer = BatchOptimizer(config)
        
        print("🚀 Performance Optimizer 초기화 완료")
    
    @contextmanager
    def performance_monitoring(self, operation_name: str):
        """성능 모니터링 컨텍스트 매니저"""
        if not self.optimization_enabled:
            yield
            return
        
        start_time = time.time()
        start_memory = self.memory_tracker.get_memory_usage()
        start_cpu = psutil.cpu_percent()
        start_gpu = self.gpu_tracker.get_gpu_usage() if self.gpu_tracker else None
        
        try:
            yield
        finally:
            end_time = time.time()
            end_memory = self.memory_tracker.get_memory_usage()
            end_cpu = psutil.cpu_percent()
            end_gpu = self.gpu_tracker.get_gpu_usage() if self.gpu_tracker else None
            
            metrics = PerformanceMetrics(
                processing_time=end_time - start_time,
                memory_usage=end_memory - start_memory,
                cpu_usage=(start_cpu + end_cpu) / 2,
                gpu_usage=(start_gpu + end_gpu) / 2 if start_gpu and end_gpu else None
            )
            
            self.metrics_history.append(metrics)
            self._log_performance(operation_name, metrics)
    
    def optimize_memory(self):
        """메모리 최적화"""
        if not self.optimization_enabled:
            return
        
        # 가비지 컬렉션
        gc.collect()
        
        # PyTorch 캐시 정리
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
        
        # 메모리 사용량 확인
        memory_usage = self.memory_tracker.get_memory_usage()
        if memory_usage > 0.8:  # 80% 이상 사용 시
            print(f"⚠️ 높은 메모리 사용량 감지: {memory_usage:.1%}")
            self._emergency_memory_cleanup()
    
    def optimize_gpu(self):
        """GPU 최적화"""
        if not self.gpu_tracker or not self.optimization_enabled:
            return
        
        gpu_usage = self.gpu_tracker.get_gpu_usage()
        if gpu_usage and gpu_usage > 0.9:  # 90% 이상 사용 시
            print(f"⚠️ 높은 GPU 사용량 감지: {gpu_usage:.1%}")
            torch.cuda.empty_cache()
    
    def get_performance_report(self) -> Dict[str, Any]:
        """성능 리포트 생성"""
        if not self.metrics_history:
            return {"error": "No metrics available"}
        
        recent_metrics = self.metrics_history[-100:]  # 최근 100개
        
        avg_processing_time = np.mean([m.processing_time for m in recent_metrics])
        avg_memory_usage = np.mean([m.memory_usage for m in recent_metrics])
        avg_cpu_usage = np.mean([m.cpu_usage for m in recent_metrics])
        
        report = {
            "summary": {
                "total_operations": len(self.metrics_history),
                "avg_processing_time": avg_processing_time,
                "avg_memory_usage": avg_memory_usage,
                "avg_cpu_usage": avg_cpu_usage,
                "optimization_enabled": self.optimization_enabled
            },
            "recent_performance": {
                "last_10_operations": [
                    {
                        "processing_time": m.processing_time,
                        "memory_usage": m.memory_usage,
                        "cpu_usage": m.cpu_usage
                    }
                    for m in recent_metrics[-10:]
                ]
            },
            "recommendations": self._generate_recommendations()
        }
        
        return report
    
    def _log_performance(self, operation_name: str, metrics: PerformanceMetrics):
        """성능 로깅"""
        print(f"📊 {operation_name}: {metrics.processing_time:.3f}s, "
              f"Memory: {metrics.memory_usage:.1%}, CPU: {metrics.cpu_usage:.1%}")
    
    def _emergency_memory_cleanup(self):
        """긴급 메모리 정리"""
        print("🚨 긴급 메모리 정리 실행")
        
        # 강제 가비지 컬렉션
        gc.collect()
        
        # PyTorch 캐시 완전 정리
        if torch.cuda.is_available():
            torch.cuda.empty_cache()
            torch.cuda.synchronize()
        
        # 메모리 사용량 재확인
        memory_usage = self.memory_tracker.get_memory_usage()
        print(f"✅ 메모리 정리 완료: {memory_usage:.1%}")
    
    def _generate_recommendations(self) -> List[str]:
        """성능 개선 권장사항 생성"""
        recommendations = []
        
        if not self.metrics_history:
            return recommendations
        
        recent_metrics = self.metrics_history[-50:]
        avg_processing_time = np.mean([m.processing_time for m in recent_metrics])
        avg_memory_usage = np.mean([m.memory_usage for m in recent_metrics])
        
        if avg_processing_time > 1.0:
            recommendations.append("배치 크기를 늘려 처리 시간을 단축하세요")
        
        if avg_memory_usage > 0.7:
            recommendations.append("메모리 사용량이 높습니다. 모델 양자화를 고려하세요")
        
        if len(recommendations) == 0:
            recommendations.append("현재 성능이 양호합니다")
        
        return recommendations


class MemoryTracker:
    """메모리 사용량 추적기"""
    
    def __init__(self):
        self.process = psutil.Process()
    
    def get_memory_usage(self) -> float:
        """현재 메모리 사용량 반환 (0.0 ~ 1.0)"""
        memory_info = self.process.memory_info()
        return memory_info.rss / psutil.virtual_memory().total
    
    def get_memory_info(self) -> Dict[str, Any]:
        """상세 메모리 정보 반환"""
        memory_info = self.process.memory_info()
        virtual_memory = psutil.virtual_memory()
        
        return {
            "rss": memory_info.rss,
            "vms": memory_info.vms,
            "percent": memory_info.rss / virtual_memory.total,
            "available": virtual_memory.available,
            "total": virtual_memory.total
        }


class GPUTracker:
    """GPU 사용량 추적기"""
    
    def __init__(self):
        self.device = torch.cuda.current_device() if torch.cuda.is_available() else None
    
    def get_gpu_usage(self) -> Optional[float]:
        """GPU 사용량 반환 (0.0 ~ 1.0)"""
        if not torch.cuda.is_available():
            return None
        
        try:
            # GPU 메모리 사용량
            allocated = torch.cuda.memory_allocated(self.device)
            reserved = torch.cuda.memory_reserved(self.device)
            total = torch.cuda.get_device_properties(self.device).total_memory
            
            return allocated / total
        except:
            return None
    
    def get_gpu_info(self) -> Dict[str, Any]:
        """GPU 상세 정보 반환"""
        if not torch.cuda.is_available():
            return {"error": "GPU not available"}
        
        try:
            props = torch.cuda.get_device_properties(self.device)
            allocated = torch.cuda.memory_allocated(self.device)
            reserved = torch.cuda.memory_reserved(self.device)
            
            return {
                "name": props.name,
                "total_memory": props.total_memory,
                "allocated_memory": allocated,
                "reserved_memory": reserved,
                "memory_usage": allocated / props.total_memory
            }
        except:
            return {"error": "Failed to get GPU info"}


class CacheOptimizer:
    """캐시 최적화 도구"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.cache_config = config.get("caching", {})
        self.cache_stats = {
            "hits": 0,
            "misses": 0,
            "size": 0
        }
    
    def get_cache_hit_rate(self) -> float:
        """캐시 히트율 반환"""
        total = self.cache_stats["hits"] + self.cache_stats["misses"]
        return self.cache_stats["hits"] / total if total > 0 else 0.0
    
    def optimize_cache_size(self, target_hit_rate: float = 0.8):
        """캐시 크기 최적화"""
        current_hit_rate = self.get_cache_hit_rate()
        
        if current_hit_rate < target_hit_rate:
            # 캐시 크기 증가
            new_size = int(self.cache_stats["size"] * 1.5)
            print(f"📈 캐시 크기 증가: {self.cache_stats['size']} -> {new_size}")
            self.cache_stats["size"] = new_size
        elif current_hit_rate > 0.95:
            # 캐시 크기 감소
            new_size = int(self.cache_stats["size"] * 0.8)
            print(f"📉 캐시 크기 감소: {self.cache_stats['size']} -> {new_size}")
            self.cache_stats["size"] = new_size


class BatchOptimizer:
    """배치 처리 최적화 도구"""
    
    def __init__(self, config: Dict[str, Any]):
        self.config = config
        self.performance_config = config.get("performance", {})
        self.current_batch_size = self.performance_config.get("batch_size", 16)
        self.batch_history = []
    
    def optimize_batch_size(self, processing_times: List[float]) -> int:
        """최적 배치 크기 계산"""
        if len(processing_times) < 5:
            return self.current_batch_size
        
        # 처리 시간과 배치 크기의 관계 분석
        avg_time = np.mean(processing_times)
        
        if avg_time < 0.1:  # 매우 빠름
            new_batch_size = int(self.current_batch_size * 1.5)
        elif avg_time > 1.0:  # 매우 느림
            new_batch_size = int(self.current_batch_size * 0.7)
        else:
            new_batch_size = self.current_batch_size
        
        # 범위 제한
        new_batch_size = max(1, min(new_batch_size, 128))
        
        if new_batch_size != self.current_batch_size:
            print(f"🔄 배치 크기 최적화: {self.current_batch_size} -> {new_batch_size}")
            self.current_batch_size = new_batch_size
        
        return self.current_batch_size
    
    def get_optimal_batch_size(self) -> int:
        """현재 최적 배치 크기 반환"""
        return self.current_batch_size


# 성능 프로파일링 데코레이터
def profile_performance(func):
    """함수 성능 프로파일링 데코레이터"""
    def wrapper(*args, **kwargs):
        start_time = time.time()
        start_memory = psutil.Process().memory_info().rss
        
        result = func(*args, **kwargs)
        
        end_time = time.time()
        end_memory = psutil.Process().memory_info().rss
        
        processing_time = end_time - start_time
        memory_usage = (end_memory - start_memory) / 1024 / 1024  # MB
        
        print(f"📊 {func.__name__}: {processing_time:.3f}s, Memory: {memory_usage:.1f}MB")
        
        return result
    
    return wrapper


# 메모리 프로파일링 컨텍스트 매니저
@contextmanager
def memory_profiling():
    """메모리 프로파일링 컨텍스트 매니저"""
    tracemalloc.start()
    start_snapshot = tracemalloc.take_snapshot()
    
    try:
        yield
    finally:
        end_snapshot = tracemalloc.take_snapshot()
        tracemalloc.stop()
        
        # 메모리 사용량 비교
        top_stats = end_snapshot.compare_to(start_snapshot, 'lineno')
        
        print("📊 메모리 프로파일링 결과:")
        for stat in top_stats[:5]:
            print(f"  {stat.count_diff:+d} blocks: {stat.size_diff/1024:.1f}KB")
            print(f"    {stat.traceback.format()}")
