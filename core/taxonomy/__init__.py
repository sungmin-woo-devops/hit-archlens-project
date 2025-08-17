"""
Taxonomy Package

클라우드 서비스 분류를 위한 택소노미 모듈
"""

from .base_taxonomy import BaseTaxonomy, TaxonomyResult
from .aws_taxonomy import AWSTaxonomy

__all__ = [
    "BaseTaxonomy",
    "TaxonomyResult", 
    "AWSTaxonomy"
]

__version__ = "1.0.0"
