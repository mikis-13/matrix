FROM python:3.13-slim

RUN apt-get update \
    && apt-get install -y --no-install-recommends openssh-client \
    && rm -rf /var/lib/apt/lists/* \
    && useradd --create-home --shell /usr/sbin/nologin matrix \
    && install -d -m 0700 -o matrix -g matrix /home/matrix/.matrix-control /home/matrix/.ssh

WORKDIR /app
COPY --chown=matrix:matrix app.py index.html ./

USER matrix
ENV PYTHONDONTWRITEBYTECODE=1 PYTHONUNBUFFERED=1 MATRIX_HOST=0.0.0.0 MATRIX_PORT=8765
EXPOSE 8765

CMD ["python", "app.py"]
