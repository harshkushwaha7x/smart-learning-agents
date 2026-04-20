"""Script to run the FastAPI backend."""

import uvicorn

if __name__ == "__main__":
    print("Starting Governed AI Content Pipeline API...")
    print("API will be available at: http://localhost:8000")
    print("Interactive docs at: http://localhost:8000/docs")
    print("Press CTRL+C to stop")
    print()
    
    uvicorn.run(
        "api.backend:app",
        host="0.0.0.0",
        port=8000,
        reload=True,
        log_level="info"
    )
