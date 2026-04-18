"""
crawlers/__init__.py

기존 app_test.py 가 `from crawl import crawl_feature_*` 형태로 임포트하는
인터페이스를 그대로 재수출 (하위 호환).

신규 코드는 각 서브모듈을 직접 임포트할 것.
"""

from .steeldaily import (
    crawl_feature_2,
    crawl_feature_38,
)
from .steelprice import (
    crawl_feature_3,
    crawl_feature_4,
    crawl_feature_5,
    crawl_feature_6,
    crawl_feature_7,
    crawl_feature_10,
    crawl_feature_12,
)
from .misc import (
    crawl_feature_8,
    crawl_feature_23,
    crawl_feature_29,
    crawl_feature_30,
)
from .ecos import (
    crawl_feature_13,
    crawl_feature_22,
    crawl_feature_31,
    crawl_feature_32,
    crawl_feature_33,
    crawl_feature_34,
    crawl_feature_35,
    crawl_feature_36,
    crawl_feature_37,
)
from .kosis import (
    crawl_feature_15,
    crawl_feature_16,
    crawl_feature_17,
    crawl_feature_18,
    crawl_feature_19,
    crawl_feature_20,
    crawl_feature_21,
    crawl_feature_24,
    crawl_feature_25,
    crawl_feature_26,
)

__all__ = [
    'crawl_feature_2',
    'crawl_feature_3',
    'crawl_feature_4',
    'crawl_feature_5',
    'crawl_feature_6',
    'crawl_feature_7',
    'crawl_feature_8',
    'crawl_feature_10',
    'crawl_feature_12',
    'crawl_feature_13',
    'crawl_feature_15',
    'crawl_feature_16',
    'crawl_feature_17',
    'crawl_feature_18',
    'crawl_feature_19',
    'crawl_feature_20',
    'crawl_feature_21',
    'crawl_feature_22',
    'crawl_feature_23',
    'crawl_feature_24',
    'crawl_feature_25',
    'crawl_feature_26',
    'crawl_feature_29',
    'crawl_feature_30',
    'crawl_feature_31',
    'crawl_feature_32',
    'crawl_feature_33',
    'crawl_feature_34',
    'crawl_feature_35',
    'crawl_feature_36',
    'crawl_feature_37',
    'crawl_feature_38',
]
