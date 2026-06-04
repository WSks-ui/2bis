from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.database import init_db
from app.routers import auth, points, membership, generate, payment, history

app = FastAPI(title="AI Image Generator")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
async def startup_event():
    await init_db()


app.include_router(auth.router, prefix="/api")
app.include_router(points.router, prefix="/api")
app.include_router(membership.router, prefix="/api")
app.include_router(generate.router, prefix="/api")
app.include_router(payment.router, prefix="/api")
app.include_router(history.router, prefix="/api")
