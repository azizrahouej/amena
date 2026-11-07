# AMENA : image de production (FastAPI + interface web).
# Construction :  docker build -t amena .
# Lancement    :  docker run -p 8000:8000 --env-file .env -v amena-donnees:/app/donnees amena
FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    PORT=8000 \
    # Comptes, avis et statistiques anonymes : dans un volume, pour survivre aux redéploiements.
    AMENA_BASE=/app/donnees/amena.db \
    # En production, pas de modèle local : Claude si ANTHROPIC_API_KEY est fournie, sinon mode extractif.
    AMENA_LLM=claude \
    AMENA_EMBEDDINGS=0

WORKDIR /app

# Dépendances d'abord (couche mise en cache tant que requirements-prod.txt ne change pas).
COPY requirements-prod.txt .
RUN pip install -r requirements-prod.txt

COPY src ./src
COPY web ./web
COPY mobile ./mobile
COPY data ./data
COPY scripts ./scripts

# La base juridique, l'index de recherche et le modèle de triage sont construits pendant la
# construction de l'image : le premier visiteur n'attend pas.
RUN AMENA_VEILLE=0 python -c "import sys; sys.path.insert(0, 'src'); from amena.construction import tout_construire; tout_construire(verbeux=True)"

# Utilisateur sans privilèges ; seul le dossier des données est accessible en écriture.
RUN useradd --create-home --uid 1000 amena && mkdir -p /app/donnees /app/reports && chown -R amena /app/donnees /app/reports /app/models /app/data
USER amena

EXPOSE 8000
HEALTHCHECK --interval=30s --timeout=5s --start-period=40s \
  CMD python -c "import urllib.request,os; urllib.request.urlopen(f'http://127.0.0.1:{os.environ.get(\"PORT\",\"8000\")}/api/sante', timeout=4)"

# --proxy-headers : derrière l'hébergeur (HTTPS), le cookie de session est bien marqué « secure ».
CMD ["sh", "-c", "uvicorn amena.api:app --app-dir src --host 0.0.0.0 --port ${PORT} --proxy-headers --forwarded-allow-ips='*'"]
