"""Usage: python scripts/evaluate_evidence.py comparison.json

Reports evidence-acceptance rate, NOT semantic accuracy or retrieval recall.
"""
from __future__ import annotations
import json
import sys
from pathlib import Path


def main(path: Path):
    result=json.loads(path.read_text(encoding='utf-8'))
    items=[item for paper in result['papers'] for field in ('method','datasets','metrics') for item in paper.get(field,[])]
    verified=sum(bool(item.get('verified')) for item in items)
    print(f'保留的有原文匹配证据字段: {verified}/{len(items)}')
    print('注意：这一指标不衡量模型拒绝前候选量、检索召回率、科学正确性或指标可比性。')

if __name__=='__main__':
    if len(sys.argv)!=2: raise SystemExit('传入一个 comparison.json 文件路径')
    main(Path(sys.argv[1]))
