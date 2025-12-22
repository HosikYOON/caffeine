import logging

def setup_logging():
    """
    애플리케이션 전역 로깅 설정 및 audit 로거 초기화
    """
    logging.basicConfig(
        level=logging.INFO,
        format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
        handlers=[
            logging.FileHandler('audit.log'),  # 파일 로깅
            logging.StreamHandler()             # 콘솔 로깅
        ]
    )
    # audit 전용 로거 설정 보장
    logging.getLogger('audit')
