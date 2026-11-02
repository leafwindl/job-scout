# ---- Python API ----
#
# 只装运行时依赖：不装 playwright（采集在宿主机做）、不装 fastembed
# （向量模型 95MB，容器内降级为 BM25 检索）。
#
# 国内网络无法直连 registry-1.docker.io，用 daocloud 镜像源；
# 海外环境可改回 python:3.12-slim。

FROM docker.m.daocloud.io/library/python:3.12-slim

WORKDIR /app

ENV PYTHONUNBUFFERED=1 \
    PIP_INDEX_URL=https://pypi.tuna.tsinghua.edu.cn/simple \
    PIP_NO_CACHE_DIR=1 \
    PYTHONPATH=/app/src

COPY api/requirements-docker.txt ./
RUN pip install -r requirements-docker.txt

COPY src ./src
COPY api ./api
COPY configs ./configs

EXPOSE 8001

CMD ["uvicorn", "api.app.main:app", "--host", "0.0.0.0", "--port", "8001"]
