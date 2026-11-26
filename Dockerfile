FROM python:3.12-slim
WORKDIR /game
COPY games/whack-a-mole/ ./
USER nobody
CMD ["python", "-m", "http.server", "8000"]
