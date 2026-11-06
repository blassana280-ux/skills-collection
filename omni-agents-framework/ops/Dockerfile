# Image locale OMNIBRAIN SUPREME — stdlib uniquement, non-root, aucune clé embarquée.
# Construction : docker build -f ops/Dockerfile -t omnibrain-supreme:1.4.0 .
# Exécution locale : docker run --rm -p 127.0.0.1:8765:8765 -v supreme-var:/data omnibrain-supreme:1.4.0
# Aucune image n'est publiée ; aucun registre distant n'est contacté par ce dépôt.
FROM python:3.12-slim

ENV PYTHONUNBUFFERED=1 \
    PYTHONDONTWRITEBYTECODE=1 \
    SUPREME_VAR_DIR=/data \
    SUPREME_ALLOW_ANON_READ=0

RUN groupadd --system --gid 10001 supreme \
 && useradd --system --uid 10001 --gid supreme --no-create-home --shell /usr/sbin/nologin supreme \
 && mkdir -p /app /data && chown -R supreme:supreme /app /data

WORKDIR /app
COPY --chown=supreme:supreme supreme/ /app/supreme/
COPY --chown=supreme:supreme omni/ /app/omni/
COPY --chown=supreme:supreme ops/healthcheck.py /app/ops/healthcheck.py

USER supreme
VOLUME ["/data"]
EXPOSE 8765

HEALTHCHECK --interval=30s --timeout=10s --start-period=20s --retries=3 \
  CMD python3 /app/ops/healthcheck.py --url http://127.0.0.1:8765 || exit 1

# Liaison container interne ; la publication du port reste une décision humaine
# (`-p 127.0.0.1:8765:8765` pour un accès strictement local).
CMD ["python3", "-m", "supreme", "serve", "--host", "0.0.0.0", "--port", "8765"]
