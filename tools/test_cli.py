"""
CLI 도구 테스트 스크립트
"""

import sys
from pathlib import Path

# 프로젝트 루트를 Python 경로에 추가
project_root = Path(__file__).parent.parent
sys.path.insert(0, str(project_root))

from tools.cli import cli
from tools.config_validator import ConfigValidator
import click
from click.testing import CliRunner # CliRunner 임포트
import os
import json
import shutil # shutil 임포트


def test_config_validator():
    """설정 검증기 테스트"""
    print("🧪 설정 검증기 테스트")
    
    validator = ConfigValidator()
    
    # 기본 설정 검증
    default_config = validator.get_default_config()
    is_valid, errors = validator.validate_config(default_config)
    
    if is_valid:
        print("✅ 기본 설정 검증 통과")
    else:
        print("❌ 기본 설정 검증 실패:")
        for error in errors:
            print(f"   - {error}")
    
    # 잘못된 설정 테스트
    invalid_config = {
        "llm": {
            "provider": "invalid_provider"
        }
    }
    
    is_valid, errors = validator.validate_config(invalid_config)
    
    if not is_valid:
        print("✅ 잘못된 설정 감지 성공")
        for error in errors:
            print(f"   - {error}")
    else:
        print("❌ 잘못된 설정 감지 실패")
    
    print()


def test_cli_commands():
    """CLI 명령어 테스트"""
    print("🧪 CLI 명령어 테스트")
    
    # CLI 객체 생성
    cli_obj = cli
    
    # 명령어 목록 확인
    commands = list(cli_obj.commands.keys())
    print(f"📋 사용 가능한 명령어: {commands}")
    
    # 각 명령어의 도움말 확인
    for command_name in commands:
        command = cli_obj.commands[command_name]
        if hasattr(command, 'help') and command.help:
            print(f"   {command_name}: {command.help.split('.')[0]}")
    
    print()


def test_config_file_creation():
    """설정 파일 생성 테스트"""
    print("🧪 설정 파일 생성 테스트")
    
    validator = ConfigValidator()
    
    # 테스트 설정 파일 생성
    test_config_path = "test_config.yaml"
    success = validator.create_config_file(test_config_path)
    
    if success:
        print(f"✅ 설정 파일 생성 성공: {test_config_path}")
        
        # 생성된 파일 검증
        try:
            import yaml
            with open(test_config_path, 'r', encoding='utf-8') as f:
                config = yaml.safe_load(f)
            
            is_valid, errors = validator.validate_config(config)
            if is_valid:
                print("✅ 생성된 설정 파일 검증 통과")
            else:
                print("❌ 생성된 설정 파일 검증 실패")
                for error in errors:
                    print(f"   - {error}")
                    
        except Exception as e:
            print(f"❌ 생성된 설정 파일 로드 실패: {e}")
        
        # 테스트 파일 삭제
        try:
            Path(test_config_path).unlink()
            print(f"🗑️ 테스트 파일 삭제: {test_config_path}")
        except:
            pass
    else:
        print("❌ 설정 파일 생성 실패")
    
    print()


def test_analyze_command_and_visualize():
    """
    `analyze` 명령어를 실행하고 생성된 결과로 `visualize` 명령어를 테스트합니다.
    (실제 분석 대신 더미 결과 생성)
    """
    print(" `analyze` 및 `visualize` 명령어 통합 테스트 시작")

    runner = CliRunner()
    
    # 1. 테스트 출력 디렉토리 생성
    test_output_dir = Path("test_output_for_visualize")
    if test_output_dir.exists():
        shutil.rmtree(test_output_dir)
    test_output_dir.mkdir()
    print(f"  📁 테스트 출력 디렉토리 생성: {test_output_dir}")

    # 2. 더미 분석 결과 파일 생성
    # 실제 분석은 시간이 오래 걸리므로, 테스트를 위해 더미 결과를 만듭니다.
    dummy_results = [
        AnalysisResult(
            image_path="dummy_image_1.png",
            width=1000, height=800,
            detections=[
                DetectionResult(bbox=BoundingBox(10,10,50,50), label="Amazon EC2", confidence=0.9, service_code="ec2", canonical_name="Amazon EC2", cloud_provider=CloudProvider.AWS),
                DetectionResult(bbox=BoundingBox(70,70,60,60), label="S3", confidence=0.85, service_code="s3", canonical_name="Amazon S3", cloud_provider=CloudProvider.AWS),
                DetectionResult(bbox=BoundingBox(150,150,40,40), label="Lambda", confidence=0.7, service_code="lambda", canonical_name="AWS Lambda", cloud_provider=CloudProvider.AWS),
            ],
            processing_time=1.5,
            cloud_provider=CloudProvider.AWS,
            analysis_method=AnalysisMethod.HYBRID,
            timestamp=datetime.now()
        ).to_dict(),
        AnalysisResult(
            image_path="dummy_image_2.png",
            width=1200, height=900,
            detections=[
                DetectionResult(bbox=BoundingBox(20,20,70,70), label="RDS", confidence=0.92, service_code="rds", canonical_name="Amazon RDS", cloud_provider=CloudProvider.AWS),
                DetectionResult(bbox=BoundingBox(90,90,55,55), label="DynamoDB", confidence=0.8, service_code="dynamodb", canonical_name="Amazon DynamoDB", cloud_provider=CloudProvider.AWS),
            ],
            processing_time=1.0,
            cloud_provider=CloudProvider.AWS,
            analysis_method=AnalysisMethod.CV,
            timestamp=datetime.now()
        ).to_dict()
    ]

    for i, res_dict in enumerate(dummy_results):
        json_path = test_output_dir / f"analysis_result_{i:03d}.json"
        with open(json_path, 'w', encoding='utf-8') as f:
            json.dump(res_dict, f, indent=2, ensure_ascii=False)
        print(f"  📄 더미 결과 파일 생성: {json_path}")

    # 3. `visualize` 명령어 실행
    print("\n  📊 `visualize` 명령어 실행 중...")
    result = runner.invoke(cli, ['visualize', str(test_output_dir), '--output', str(test_output_dir)])

    print(f"  CLI 출력:\n{result.output}")
    if result.exception:
        print(f"  ❌ 오류 발생: {result.exception}")
        import traceback
        traceback.print_exc()

    assert result.exit_code == 0
    assert "분석 결과 시각화 완료" in result.output

    # 4. 생성된 이미지 파일 확인
    expected_image_files = [
        test_output_dir / "confidence_distribution.png",
        test_output_dir / "processing_time.png",
        test_output_dir / "detection_counts.png",
        test_output_dir / "service_distribution.png",
        test_output_dir / "normalization_success_rate.png",
    ]
    for img_file in expected_image_files:
        assert img_file.exists(), f"❌ 이미지 파일이 생성되지 않았습니다: {img_file}"
        print(f"  ✅ 이미지 파일 생성 확인: {img_file}")

    # 5. 요약 보고서 파일 확인
    summary_report_path = test_output_dir / "summary_report.txt"
    assert summary_report_path.exists(), f"❌ 요약 보고서가 생성되지 않았습니다: {summary_report_path}"
    print(f"  ✅ 요약 보고서 생성 확인: {summary_report_path}")
    
    # 6. 테스트 디렉토리 정리
    shutil.rmtree(test_output_dir)
    print(f"  🗑️ 테스트 디렉토리 정리: {test_output_dir}")

    print("✅ `analyze` 및 `visualize` 명령어 통합 테스트 완료\n")


def main():
    """메인 테스트 함수"""
    print(" CLI 도구 테스트 시작\n")
    
    test_config_validator()
    test_cli_commands()
    test_config_file_creation()
    test_analyze_command_and_visualize() # 새로운 테스트 함수 호출
    
    print("✅ CLI 도구 테스트 완료!")


if __name__ == "__main__":
    main()
