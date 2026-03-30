from fastapi import FastAPI

app = FastAPI(title="Library SaaS API")

@app.get("/")
def root():
    return {"status": "ok"}