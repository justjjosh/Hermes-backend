from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from app.routers import brands, profile, pitches, tracking, discovery

# create FastAPI app
app = FastAPI(
    title="Hermes API",
    description="AI-powered brand pitch automation",
    version="1.0.0"
)

# Add cors middleware that allows requests from any origin
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

app.include_router(brands.router)
app.include_router(profile.router)
app.include_router(pitches.router)
app.include_router(tracking.router, prefix="/track", tags=["tracking"])
app.include_router(discovery.router, prefix="/discover", tags=["discovery"])


@app.get("/")
def read_root():
    return {"Hello": "World!"}
