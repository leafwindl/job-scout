"""生成一份虚构简历画像，用于 README 截图（不暴露真实个人信息）。"""

from __future__ import annotations

import json
from pathlib import Path

DEMO = {
    "name": "林小满",
    "target": "AI 应用开发实习生（广州｜每周 5 天）",
    "education": [
        {
            "school": "华南理工大学",
            "major": "计算机科学与技术",
            "degree": "本科",
            "time": "2023.09 - 2027.06",
        }
    ],
    "skills": [
        "Python",
        "FastAPI",
        "LangChain",
        "RAG",
        "BM25",
        "向量检索",
        "Prompt Engineering",
        "MySQL",
        "Redis",
        "Docker",
        "Git",
        "pytest",
    ],
    "projects": [
        {
            "name": "校园二手交易平台",
            "period": "2025.03 - 2025.06",
            "tech": ["FastAPI", "MySQL", "Redis", "Vue3"],
            "bullets": [
                "独立完成后端接口设计与实现，覆盖商品发布、搜索、订单、评价四个模块，共 32 个接口。",
                "用 Redis 缓存热门商品列表与搜索热词，热门页 P95 从 180ms 降到 45ms。",
                "为订单状态机补 68 个单元测试，覆盖超时未付、重复支付、并发下单三种异常路径。",
            ],
        },
        {
            "name": "文档知识库问答系统",
            "period": "2025.09 - 2025.11",
            "tech": ["FastAPI", "LangChain", "BM25", "bge", "PostgreSQL"],
            "bullets": [
                "实现「一段落一个 chunk」的切分策略，保留标题层级作为检索元数据。",
                "BM25 与向量双路召回，用 RRF 融合，自建 40 条评测集把 MRR 从 0.71 提升到 0.89。",
                "回答强制标注来源段落编号，检索为空时明确拒答，人工抽检 40 条忠实度 91%。",
            ],
        },
        {
            "name": "课程作业自动批改工具",
            "period": "2025.06",
            "tech": ["Python", "Docker"],
            "bullets": [
                "用 Docker 隔离学生代码执行环境，限制 CPU 与内存，防止死循环拖垮评测机。",
                "支持 3 门课的作业模板，批改结果输出 CSV 供助教复核。",
            ],
        },
    ],
    "experience": [
        {
            "company": "某创业公司",
            "role": "后端开发实习生",
            "period": "2025.07 - 2025.09",
            "bullets": [
                "维护内部管理后台，用 Python 写数据同步脚本，日均处理 3 万条记录。",
                "优化一条慢查询，把报表接口耗时从 3s 降到 800ms。",
            ],
        }
    ],
    "raw_text": "（演示用虚构简历）",
    "source_file": "resume_demo.pdf",
}

out = Path("data/profile.json")
out.write_text(json.dumps(DEMO, ensure_ascii=False, indent=2), encoding="utf-8")
print(f"已写入虚构画像: {out}")
print(f"  姓名: {DEMO['name']}")
print(f"  技能: {len(DEMO['skills'])} 项")
print(f"  项目: {len(DEMO['projects'])} 个")
