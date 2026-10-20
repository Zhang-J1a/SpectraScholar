FROM python:3.12-slim
WORKDIR /code
COPY requirements.txt requirements-live.txt ./
ARG INSTALL_GPT_RESEARCHER=0
RUN pip install --no-cache-dir -r requirements.txt && \
    if [ "$INSTALL_GPT_RESEARCHER" = "1" ]; then pip install --no-cache-dir -r requirements-live.txt; fi
COPY spectrascholar ./spectrascholar
COPY web ./web
RUN mkdir -p workspace/papers workspace/reports
EXPOSE 8000
CMD ["uvicorn", "spectrascholar.main:app", "--host", "0.0.0.0", "--port", "8000"]
