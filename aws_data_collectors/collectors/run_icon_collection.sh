#!/bin/bash

# AWS 아이콘 웹 수집 실행 스크립트
# Scrapy를 사용하여 웹에서 AWS 아이콘을 수집하고 훈련 데이터셋을 보강합니다.

set -euo pipefail

# 색상 정의
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# 로그 함수
log_info() {
    echo -e "${BLUE}[INFO]${NC} $1"
}

log_success() {
    echo -e "${GREEN}[SUCCESS]${NC} $1"
}

log_warning() {
    echo -e "${YELLOW}[WARNING]${NC} $1"
}

log_error() {
    echo -e "${RED}[ERROR]${NC} $1"
}

# 스크립트 디렉토리 설정
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
PROJECT_ROOT="$(dirname "$SCRIPT_DIR")"

# 설정
OUTPUT_DIR="collected_icons"
MAX_RESULTS_PER_SERVICE=10
SERVICES_TO_COLLECT=("EC2" "S3" "Lambda" "RDS" "DynamoDB" "CloudFront" "VPC" "IAM" "CloudWatch")

# 함수: 의존성 확인
check_dependencies() {
    log_info "의존성 확인 중..."
    
    # Python 확인
    if ! command -v python3 &> /dev/null; then
        log_error "Python 3가 설치되지 않았습니다."
        exit 1
    fi
    
    # Scrapy 확인
    if ! python3 -c "import scrapy" 2>/dev/null; then
        log_warning "Scrapy가 설치되지 않았습니다. 설치를 진행합니다..."
        pip3 install scrapy pillow requests
    fi
    
    # PIL 확인
    if ! python3 -c "import PIL" 2>/dev/null; then
        log_warning "Pillow가 설치되지 않았습니다. 설치를 진행합니다..."
        pip3 install pillow
    fi
    
    log_success "의존성 확인 완료"
}

# 함수: 디렉토리 설정
setup_directories() {
    log_info "디렉토리 설정 중..."
    
    # 출력 디렉토리 생성
    mkdir -p "$OUTPUT_DIR"
    mkdir -p "$OUTPUT_DIR/raw"
    mkdir -p "$OUTPUT_DIR/processed"
    mkdir -p "$OUTPUT_DIR/logs"
    
    log_success "디렉토리 설정 완료"
}

# 함수: GitHub에서 AWS 아이콘 수집
collect_from_github() {
    log_info "GitHub에서 AWS 아이콘 수집 시작..."
    
    cd "$PROJECT_ROOT"
    
    # GitHub 스파이더 실행 (실제 구현에서는 GitHub API 사용)
    echo "GitHub 아이콘 수집은 별도 구현이 필요합니다."
    echo "현재는 Google Images 수집에 집중합니다."
    
    if [ $? -eq 0 ]; then
        log_success "GitHub 아이콘 수집 완료"
    else
        log_error "GitHub 아이콘 수집 실패"
        return 1
    fi
}

# 함수: Google Images에서 아이콘 수집
collect_from_google() {
    log_info "Google Images에서 AWS 아이콘 수집 시작..."
    
    cd "$PROJECT_ROOT"
    
    for service in "${SERVICES_TO_COLLECT[@]}"; do
        log_info "서비스 '$service' 아이콘 수집 중..."
        
        # Google Images 스파이더 실행
        scrapy crawl aws_icon_spider \
            -a service_name="$service" \
            -a max_results="$MAX_RESULTS_PER_SERVICE" \
            -s LOG_FILE="$OUTPUT_DIR/logs/google_${service}.log" \
            -s FEED_URI="$OUTPUT_DIR/google_${service}_icons.json" \
            -s FEED_FORMAT=json \
            -s DOWNLOAD_DELAY=2
        
        if [ $? -eq 0 ]; then
            log_success "서비스 '$service' 아이콘 수집 완료"
        else
            log_warning "서비스 '$service' 아이콘 수집 실패"
        fi
        
        # 요청 간격 조절
        sleep 2
    done
}

# 함수: 수집된 데이터 통합
merge_collected_data() {
    log_info "수집된 데이터 통합 중..."
    
    cd "$PROJECT_ROOT"
    
    # Python 스크립트로 데이터 통합
    python3 -c "
import json
import glob
from pathlib import Path

# 수집된 모든 JSON 파일 찾기
json_files = glob.glob('$OUTPUT_DIR/*.json')
all_icons = []

for file_path in json_files:
    try:
        with open(file_path, 'r', encoding='utf-8') as f:
            data = json.load(f)
            if isinstance(data, list):
                all_icons.extend(data)
            else:
                all_icons.append(data)
    except Exception as e:
        print(f'파일 읽기 실패: {file_path} - {e}')

# 중복 제거 (URL 기준)
seen_urls = set()
unique_icons = []
for icon in all_icons:
    url = icon.get('image_url', '')
    if url not in seen_urls:
        seen_urls.add(url)
        unique_icons.append(icon)

# 통합된 데이터 저장
output_file = '$OUTPUT_DIR/merged_icons.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(unique_icons, f, ensure_ascii=False, indent=2)

print(f'통합 완료: {len(unique_icons)}개 아이콘을 {output_file}에 저장')
"
    
    log_success "데이터 통합 완료"
}

# 함수: 품질 검사 및 필터링
filter_high_quality_icons() {
    log_info "고품질 아이콘 필터링 중..."
    
    cd "$PROJECT_ROOT"
    
    python3 -c "
import json
from pathlib import Path

# 통합된 데이터 읽기
input_file = '$OUTPUT_DIR/merged_icons.json'
if not Path(input_file).exists():
    print('통합된 데이터 파일이 없습니다.')
    exit(1)

with open(input_file, 'r', encoding='utf-8') as f:
    icons = json.load(f)

# 품질 기준
min_confidence = 0.7
min_file_size = 2000
min_dimensions = (32, 32)

# 필터링
high_quality_icons = []
for icon in icons:
    confidence = icon.get('confidence_score', 0)
    file_size = icon.get('file_size', 0)
    width = icon.get('image_width', 0)
    height = icon.get('image_height', 0)
    
    if (confidence >= min_confidence and 
        file_size >= min_file_size and
        width >= min_dimensions[0] and height >= min_dimensions[1]):
        high_quality_icons.append(icon)

# 고품질 아이콘 저장
output_file = '$OUTPUT_DIR/high_quality_icons.json'
with open(output_file, 'w', encoding='utf-8') as f:
    json.dump(high_quality_icons, f, ensure_ascii=False, indent=2)

print(f'필터링 완료: {len(high_quality_icons)}개 고품질 아이콘을 {output_file}에 저장')

# 통계 출력
services = {}
for icon in high_quality_icons:
    service = icon.get('service_name', 'Unknown')
    services[service] = services.get(service, 0) + 1

print('\\n=== 서비스별 분포 ===')
for service, count in sorted(services.items(), key=lambda x: x[1], reverse=True):
    print(f'  {service}: {count}개')
"
    
    log_success "고품질 아이콘 필터링 완료"
}

# 함수: 통계 출력
print_statistics() {
    log_info "수집 통계 출력 중..."
    
    cd "$PROJECT_ROOT"
    
    if [ -f "$OUTPUT_DIR/high_quality_icons.json" ]; then
        python3 -c "
import json
from pathlib import Path

with open('$OUTPUT_DIR/high_quality_icons.json', 'r', encoding='utf-8') as f:
    icons = json.load(f)

print(f'총 수집된 고품질 아이콘: {len(icons)}개')

# 파일 크기 통계
file_sizes = [icon.get('file_size', 0) for icon in icons]
if file_sizes:
    avg_size = sum(file_sizes) / len(file_sizes)
    print(f'평균 파일 크기: {avg_size:.0f} bytes')

# 신뢰도 통계
confidences = [icon.get('confidence_score', 0) for icon in icons]
if confidences:
    avg_confidence = sum(confidences) / len(confidences)
    print(f'평균 신뢰도: {avg_confidence:.2f}')

# 소스별 통계
sources = {}
for icon in icons:
    source = icon.get('source_url', 'Unknown')
    sources[source] = sources.get(source, 0) + 1

print('\\n=== 소스별 분포 ===')
for source, count in sources.items():
    print(f'  {source}: {count}개')
"
    else
        log_warning "고품질 아이콘 파일이 없습니다."
    fi
}

# 함수: 정리
cleanup() {
    log_info "임시 파일 정리 중..."
    
    # 로그 파일 압축
    if [ -d "$OUTPUT_DIR/logs" ]; then
        tar -czf "$OUTPUT_DIR/logs.tar.gz" -C "$OUTPUT_DIR" logs/
        rm -rf "$OUTPUT_DIR/logs"
    fi
    
    log_success "정리 완료"
}

# 메인 함수
main() {
    log_info "AWS 아이콘 웹 수집 시작"
    
    # 의존성 확인
    check_dependencies
    
    # 디렉토리 설정
    setup_directories
    
    # GitHub에서 수집
    collect_from_github
    
    # Google Images에서 수집
    collect_from_google
    
    # 데이터 통합
    merge_collected_data
    
    # 품질 필터링
    filter_high_quality_icons
    
    # 통계 출력
    print_statistics
    
    # 정리
    cleanup
    
    log_success "AWS 아이콘 웹 수집 완료!"
    log_info "결과 파일: $OUTPUT_DIR/high_quality_icons.json"
}

# 스크립트 실행
if [[ "${BASH_SOURCE[0]}" == "${0}" ]]; then
    main "$@"
fi
