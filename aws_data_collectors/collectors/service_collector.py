"""
AWS 서비스 정보 수집기
boto3를 통해 AWS 서비스 메타데이터를 수집합니다.
"""

import csv
import json
import os
import re
import sys
from collections import deque
from typing import List, Dict, Optional, Tuple, Set
from dataclasses import dataclass
from pathlib import Path

import boto3
import botocore.session

@dataclass
class ServiceInfo:
    """서비스 정보 데이터 클래스"""
    service_code: str
    service_full_name: str
    endpoint_prefix: str
    api_version: Optional[str]
    protocols: Optional[str]
    uid: Optional[str]
    regions: str
    region_count: int
    is_global_like: bool
    has_resource_interface: bool

@dataclass
class ResourceInfo:
    """리소스 정보 데이터 클래스"""
    service_code: str
    service_full_name: str
    main_resource_example: str
    secondary_examples: str
    from_operation: str
    id_fields_seen: str

class AWSServiceCollector:
    """
    AWS 서비스 정보 수집기
    
    boto3를 통해 AWS 서비스 메타데이터를 수집하고 대표 리소스를 추론합니다.
    
    사용 예시:
    ```python
    collector = AWSServiceCollector()
    services = collector.collect_services()
    resources = collector.infer_resources()
    collector.save_data(services, resources, "output.csv", "output.json")
    ```
    """
    
    def __init__(self):
        """초기화"""
        self.session = boto3.session.Session()
        self.botocore_session = botocore.session.get_session()
        
        # 설정
        self.max_depth = 8
        self.id_keys_priority = ("Arn", "Id", "Name")
        self.negative_hints = {
            "Tag", "Policy", "Quota", "Permission", "Endpoint", 
            "Error", "Limit", "Metadata"
        }
    
    def collect_services(self) -> List[ServiceInfo]:
        """
        AWS 서비스 메타데이터 수집
        
        Returns:
            List[ServiceInfo]: 서비스 정보 리스트
        """
        print("🔍 AWS 서비스 메타데이터 수집 중...")
        
        service_codes = sorted(self.session.get_available_services())
        resource_codes = set(self.session.get_available_resources())
        
        services = []
        for code in service_codes:
            try:
                model = self.botocore_session.get_service_model(code)
                md = model.metadata or {}
                
                full_name = md.get("serviceFullName") or code
                endpoint_prefix = md.get("endpointPrefix") or code
                api_version = md.get("apiVersion")
                uid = md.get("uid")
                
                # 프로토콜 처리
                protos = md.get("protocols") or md.get("protocol")
                if isinstance(protos, list):
                    protos = ",".join(sorted(protos))
                
                # 리전 정보
                regions = sorted(self.session.get_available_regions(code))
                has_resources = code in resource_codes
                is_global = len(regions) == 0
                
                service_info = ServiceInfo(
                    service_code=code,
                    service_full_name=full_name,
                    endpoint_prefix=endpoint_prefix,
                    api_version=api_version,
                    protocols=protos,
                    uid=uid,
                    regions=";".join(regions),
                    region_count=len(regions),
                    is_global_like=is_global,
                    has_resource_interface=has_resources
                )
                services.append(service_info)
                
            except Exception as e:
                print(f"⚠️ 서비스 {code} 처리 실패: {e}")
                continue
        
        print(f"✅ 수집된 서비스: {len(services)}개")
        return services
    
    def infer_resources(self) -> List[ResourceInfo]:
        """
        서비스별 대표 리소스 추론
        
        Returns:
            List[ResourceInfo]: 리소스 정보 리스트
        """
        print("🔍 AWS 서비스 대표 리소스 추론 중...")
        
        service_codes = sorted(self.session.get_available_services())
        rows = []
        
        for code in service_codes:
            try:
                model = self.botocore_session.get_service_model(code)
                md = model.metadata or {}
                full_name = md.get("serviceFullName") or code
                ops = model.operation_names
                
                candidates = []
                for op_name in ops:
                    try:
                        op = model.operation_model(op_name)
                        output_shape = op.output_shape
                    except Exception:
                        continue
                    
                    if output_shape is None:
                        continue
                    
                    for path, list_name, elem_label, id_fields in self._walk_output_shape(output_shape):
                        # 후보 라벨 만들기
                        label = self._normalize_resource_label(elem_label or list_name)
                        score = self._score_candidate(op_name, list_name, label, id_fields)
                        
                        if score <= 0:
                            continue
                        
                        candidates.append({
                            "service_code": code,
                            "service_full_name": full_name,
                            "operation": op_name,
                            "list_name": list_name,
                            "element_label": elem_label,
                            "representative_resource_guess": label,
                            "id_fields": ";".join(sorted(id_fields)),
                            "score": score,
                        })
                
                # 상위 3개만 남김
                candidates.sort(key=lambda x: (-x["score"], x["representative_resource_guess"]))
                top = candidates[:3] if candidates else []
                rows.extend(top)
                
            except Exception as e:
                print(f"⚠️ 서비스 {code} 리소스 추론 실패: {e}")
                continue
        
        # 서비스당 1~3개 대표 리소스로 집계
        aggregated = self._aggregate_resources(rows)
        
        print(f"✅ 추론된 리소스: {len(aggregated)}개 서비스")
        return aggregated
    
    def _walk_output_shape(self, output_shape) -> List[Tuple]:
        """
        순환 안전한 BFS로 출력 형태 탐색
        
        Args:
            output_shape: botocore 형태 객체
            
        Yields:
            Tuple: (경로, 리스트명, 요소라벨, 식별자필드집합)
        """
        if output_shape is None:
            return
        
        seen = set()  # shape 객체 id 단위로 방문 제어
        queue = deque()
        queue.append(((), output_shape, 0))  # (경로, shape, depth)
        
        while queue:
            path, shape, depth = queue.popleft()
            if shape is None:
                continue
            
            sid = id(shape)
            if sid in seen:
                continue
            seen.add(sid)
            
            if depth > self.max_depth:
                continue
            
            t = shape.type_name
            if t == "structure":
                # ResponseMetadata/토큰류는 패스
                for name, member in (shape.members or {}).items():
                    if name in ("ResponseMetadata", "NextToken", "Marker", "NextMarker", "ContinuationToken"):
                        continue
                    queue.append((path + (name,), member, depth + 1))
            
            elif t == "list":
                elem = self._safe_get_member(shape)
                list_name = path[-1] if path else "Items"
                
                if elem is None:
                    continue
                
                if elem.type_name == "structure":
                    # 구조체 원소 → 식별자 필드 수집
                    id_fields = set(
                        fname for fname, fshape in (elem.members or {}).items()
                        if fname.endswith(self.id_keys_priority)
                    )
                    elem_label = elem.name or "Item"
                    yield (path, list_name, elem_label, id_fields)
                    # 중첩(예: Reservations -> Instances) 탐색
                    queue.append((path, elem, depth + 1))
                else:
                    # 스칼라 리스트(예: TableNames: [string])도 대표 리소스로 취급
                    rep = self._normalize_resource_label(list_name)
                    yield (path, list_name, rep, {rep + "Name"})
    
    def _safe_get_member(self, shape):
        """안전한 멤버 접근"""
        try:
            return shape.member
        except RecursionError:
            return None
        except Exception:
            return None
    
    def _normalize_resource_label(self, label: str) -> str:
        """리소스 라벨 정규화"""
        if not label:
            return "Item"
        
        # 단수화
        l = self._singularize(label)
        
        # TableNames -> Table, FunctionArns -> Function 등 휴리스틱
        for suffix in ("Names", "Name", "Arns", "Arn", "Ids", "Id"):
            if l.endswith(suffix):
                l = l[:-len(suffix)]
                break
        
        return l or "Item"
    
    def _singularize(self, name: str) -> str:
        """간단한 단수화 휴리스틱"""
        if not name:
            return name
        if name.endswith("ies"):
            return name[:-3] + "y"
        if name.endswith("ses"):
            return name[:-2]
        if name.endswith("s") and not name.endswith("ss"):
            return name[:-1]
        return name
    
    def _is_negative_label(self, label: str) -> bool:
        """부정적인 라벨인지 확인"""
        s = (label or "").lower()
        return any(k.lower() in s for k in self.negative_hints)
    
    def _score_candidate(self, op_name: str, list_name: str, 
                        elem_label: str, id_fields: Set[str]) -> int:
        """후보 점수 계산"""
        score = 0
        
        # 식별자 가중치
        keys = [k for k in self.id_keys_priority 
                if any(f.endswith(k) for f in id_fields)]
        score += 3 * len(keys)
        
        # 오퍼레이션 네이밍
        if (op_name or "").lower().startswith(("list", "describe")):
            score += 1
        
        # 라벨 클린
        if self._is_negative_label(elem_label) or self._is_negative_label(list_name):
            score -= 3
        
        # 직관 이름 보너스
        positive_hints = {
            "instance", "bucket", "table", "function", "cluster", "queue", "topic",
            "domain", "user", "role", "stream", "loadbalancer", "dbinstance"
        }
        if any(k in (elem_label or "").lower() for k in positive_hints):
            score += 1
        
        return score
    
    def _aggregate_resources(self, rows: List[Dict]) -> List[ResourceInfo]:
        """리소스 정보 집계"""
        # 서비스별로 그룹화
        aggregated = {}
        for row in rows:
            key = (row["service_code"], row["service_full_name"])
            if key not in aggregated:
                aggregated[key] = []
            aggregated[key].append(row)
        
        # 각 서비스별로 상위 리소스 선택
        final = []
        for (code, name), lst in aggregated.items():
            lst = sorted(lst, key=lambda x: -x["score"])
            main = lst[0]
            secondary = [x["representative_resource_guess"] for x in lst[1:]]
            
            resource_info = ResourceInfo(
                service_code=code,
                service_full_name=name,
                main_resource_example=main["representative_resource_guess"],
                secondary_examples=";".join(secondary),
                from_operation=main["operation"],
                id_fields_seen=main["id_fields"]
            )
            final.append(resource_info)
        
        # 서비스 코드로 정렬
        final.sort(key=lambda x: x.service_code)
        return final
    
    def save_services(self, services: List[ServiceInfo], 
                     csv_path: str, json_path: str) -> None:
        """서비스 정보 저장"""
        # 출력 디렉터리 생성
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        
        # JSON 저장
        json_data = []
        for service in services:
            json_data.append({
                "service_code": service.service_code,
                "service_full_name": service.service_full_name,
                "endpoint_prefix": service.endpoint_prefix,
                "api_version": service.api_version,
                "protocols": service.protocols,
                "uid": service.uid,
                "regions": service.regions,
                "region_count": service.region_count,
                "is_global_like": service.is_global_like,
                "has_resource_interface": service.has_resource_interface,
            })
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # CSV 저장
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=list(json_data[0].keys()))
            w.writeheader()
            w.writerows(json_data)
        
        print(f"✅ 서비스 정보 저장: {csv_path} / {json_path}")
    
    def save_resources(self, resources: List[ResourceInfo], 
                      csv_path: str, json_path: str) -> None:
        """리소스 정보 저장"""
        # 출력 디렉터리 생성
        Path(csv_path).parent.mkdir(parents=True, exist_ok=True)
        Path(json_path).parent.mkdir(parents=True, exist_ok=True)
        
        # JSON 저장
        json_data = []
        for resource in resources:
            json_data.append({
                "service_code": resource.service_code,
                "service_full_name": resource.service_full_name,
                "main_resource_example": resource.main_resource_example,
                "secondary_examples": resource.secondary_examples,
                "from_operation": resource.from_operation,
                "id_fields_seen": resource.id_fields_seen,
            })
        
        with open(json_path, "w", encoding="utf-8") as f:
            json.dump(json_data, f, ensure_ascii=False, indent=2)
        
        # CSV 저장
        fieldnames = [
            "service_code", "service_full_name", "main_resource_example",
            "secondary_examples", "from_operation", "id_fields_seen"
        ]
        with open(csv_path, "w", newline="", encoding="utf-8") as f:
            w = csv.DictWriter(f, fieldnames=fieldnames)
            w.writeheader()
            for resource in resources:
                w.writerow({
                    "service_code": resource.service_code,
                    "service_full_name": resource.service_full_name,
                    "main_resource_example": resource.main_resource_example,
                    "secondary_examples": resource.secondary_examples,
                    "from_operation": resource.from_operation,
                    "id_fields_seen": resource.id_fields_seen,
                })
        
        print(f"✅ 리소스 정보 저장: {csv_path} / {json_path}")
    
    def get_statistics(self, services: List[ServiceInfo], 
                      resources: List[ResourceInfo]) -> Dict:
        """통계 정보"""
        stats = {
            "total_services": len(services),
            "total_resources": len(resources),
            "global_services": len([s for s in services if s.is_global_like]),
            "resource_services": len([s for s in services if s.has_resource_interface]),
            "avg_regions": sum(s.region_count for s in services) / len(services) if services else 0
        }
        return stats
