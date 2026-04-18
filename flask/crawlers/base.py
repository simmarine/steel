"""
crawlers/base.py
- DB 엔진 생성 (node/.env 로드)
- crawl_logs 기록 헬퍼
- retry 데코레이터 (3회, Exponential Backoff)
"""
import os
import time
import functools
from pathlib import Path
from datetime import datetime
from urllib.parse import quote_plus

from dotenv import load_dotenv
from sqlalchemy import create_engine, text

# flask/.env 와 node/.env 양쪽 로드 (flask/.env 가 우선)
_BASE_DIR = Path(__file__).parent.parent.parent   # steel/
load_dotenv(_BASE_DIR / 'flask' / '.env')
load_dotenv(_BASE_DIR / 'node'  / '.env')

MYSQL_HOST = os.getenv('MYSQL_HOST', 'localhost')
MYSQL_USER = os.getenv('MYSQL_USER', 'root')
MYSQL_PASSWORD = os.getenv('MYSQL_PASSWORD', '')
MYSQL_DB   = 'steel_db'

# steelprice.co.kr 자격증명
STEEL_PRICE_ID = os.getenv('STEEL_PRICE_ID', '')
STEEL_PRICE_PW = os.getenv('STEEL_PRICE_PW', '')

# steeldaily.co.kr / steelin.co.kr 자격증명
STEELDAILY_ID = os.getenv('STEELDAILY_ID', '')
STEELDAILY_PW = os.getenv('STEELDAILY_PW', '')
STEELIN_ID = os.getenv('STEELIN_ID', '')
STEELIN_PW = os.getenv('STEELIN_PW', '')

# ECOS / KOSIS API 키
ECOS_API_KEY  = os.getenv('ECOS_API_KEY',  '')
KOSIS_API_KEY = os.getenv('KOSIS_API_KEY', '')


def get_engine():
    """SQLAlchemy 엔진 반환 (steel_db)"""
    pw = quote_plus(MYSQL_PASSWORD)
    return create_engine(
        f'mysql+mysqlconnector://{MYSQL_USER}:{pw}@{MYSQL_HOST}/{MYSQL_DB}?charset=utf8mb4',
        echo=False,
        pool_pre_ping=True,
    )


def log_crawl(engine, crawl_type: str, start_date, end_date,
              status: str, rows_fetched: int = 0,
              error_msg: str = None, duration_sec: float = None):
    """crawl_logs 테이블에 실행 이력을 기록한다."""
    try:
        with engine.connect() as conn:
            conn.execute(text("""
                INSERT INTO crawl_logs
                    (crawl_type, start_date, end_date, status,
                     rows_fetched, error_msg, duration_sec)
                VALUES
                    (:crawl_type, :start_date, :end_date, :status,
                     :rows_fetched, :error_msg, :duration_sec)
            """), {
                'crawl_type':   crawl_type,
                'start_date':   start_date,
                'end_date':     end_date,
                'status':       status,
                'rows_fetched': rows_fetched,
                'error_msg':    error_msg,
                'duration_sec': duration_sec,
            })
            conn.commit()
    except Exception as e:
        print(f'[crawl_log 기록 실패] {e}')


def retry(max_attempts: int = 3, base_delay: float = 2.0, exceptions=(Exception,)):
    """
    재시도 데코레이터.
    실패 시 base_delay * 2^(시도횟수-1) 초 대기 후 재시도.
    max_attempts 번 모두 실패하면 마지막 예외를 raise.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(*args, **kwargs):
            last_exc = None
            for attempt in range(1, max_attempts + 1):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    last_exc = e
                    if attempt < max_attempts:
                        delay = base_delay * (2 ** (attempt - 1))
                        print(f'[retry] {func.__name__} 실패({attempt}/{max_attempts}), '
                              f'{delay:.1f}초 후 재시도… 오류: {e}')
                        time.sleep(delay)
            raise last_exc
        return wrapper
    return decorator
