from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from app.routers import brands, profile, pitches, tracking, discovery, analytics, webhooks, autopilot
from app.services.scheduler import start_scheduler, stop_scheduler

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: Start the background autopilot scheduler
    start_scheduler()
    yield
    # Shutdown: Stop the scheduler safely
    stop_scheduler()

# create FastAPI app
app = FastAPI(
    title="Hermes API",
    description="AI-powered brand pitch automation",
    version="1.0.0",
    lifespan=lifespan
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
app.include_router(analytics.router, prefix="/analytics", tags=["analytics"])
app.include_router(webhooks.router, prefix="/webhooks", tags=["webhooks"])
app.include_router(autopilot.router, prefix="/autopilot", tags=["autopilot"])


@app.get("/")
def read_root():
    return {"Hello": "World!"}
