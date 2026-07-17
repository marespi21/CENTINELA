from fastapi import FastAPI

app = FastAPI(
    title="Centinela API",
    version="1.0.0",
)


@app.get("/")
def root():
    return {
        "status": "running",
        "service": "Centinela",
    }
