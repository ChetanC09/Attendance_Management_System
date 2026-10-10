"""Uvicorn configuration shared by local Compose and Render deployments."""

import os

import uvicorn

SERVER_KEEP_ALIVE_TIMEOUT_SECONDS = 30


def build_server_config() -> uvicorn.Config:
    return uvicorn.Config(
        "app.main:app",
        host="0.0.0.0",
        port=int(os.getenv("PORT", "8000")),
        timeout_keep_alive=SERVER_KEEP_ALIVE_TIMEOUT_SECONDS,
    )


def main() -> None:
    uvicorn.Server(build_server_config()).run()


if __name__ == "__main__":
    main()
