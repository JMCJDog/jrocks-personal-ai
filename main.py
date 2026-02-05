from fastapi import FastAPI

app = FastAPI()


@app.get("/")
def root():
    return {"status": "ok", "message": "Welcome to Vibe Coding"}


@app.get("/health")
def health():
    return {"status": "healthy"}
