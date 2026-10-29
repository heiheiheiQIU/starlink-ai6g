"""Start locally: python -m uvicorn backend.api.main:app --host 127.0.0.1 --port 8000 --workers 1."""
from contextlib import asynccontextmanager
import json
from pathlib import Path

from fastapi import FastAPI, Query, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse, Response
from pydantic import ValidationError
from starlette.exceptions import HTTPException

from backend.contracts import RunRequest, RunResult
from .service import RunService, ServiceError, checked_file
from .worker import execute_run


def create_app(root=None,*,worker=execute_run,timeout_s=120.0):
    service=RunService(root or Path(__file__).resolve().parents[2]/'runs/api',worker=worker,timeout_s=timeout_s)
    @asynccontextmanager
    async def lifespan(app):
        service.start()
        try: yield
        finally: service.close()
    app=FastAPI(title='星地智调 deterministic rule API',lifespan=lifespan)
    app.state.service=service

    @app.exception_handler(ServiceError)
    async def service_error(request,error): return JSONResponse(status_code=error.status,content=error.body)

    @app.exception_handler(RequestValidationError)
    async def validation_error(request,error):
        return JSONResponse(status_code=422,content=dict(code='INVALID_CONFIG',message='Invalid request',details={}))

    @app.exception_handler(HTTPException)
    async def http_error(request,error):
        return JSONResponse(status_code=error.status_code,content=dict(code='RUN_NOT_FOUND',message='Route not found',details={}))

    @app.post('/runs',status_code=202)
    def submit(payload:RunRequest):
        try: return service.submit(payload)
        except (ValueError,ValidationError) as error:
            raise ServiceError(422,'INVALID_CONFIG','Unsupported or invalid run configuration') from error

    @app.get('/runs/{identity}')
    def status(identity:str): return service.status(identity)

    @app.get('/runs/{identity}/events')
    def events(identity:str,after:int=Query(0,ge=0),limit:int=Query(500,ge=1,le=2000)):
        return service.events(identity,after,limit)

    @app.get('/runs/{identity}/results')
    def results(identity:str):
        folder=service.completed(identity)
        return RunResult.model_validate_json(checked_file(folder,'results.json').read_text(encoding='utf-8')).model_dump()

    @app.get('/runs/{identity}/export')
    def export(identity:str):
        try: data=service.export(identity)
        except (OSError,ValueError) as error:
            raise ServiceError(500,'INTERNAL_RUN_ERROR','Export artifact is unavailable') from error
        return Response(data,media_type='application/zip',headers={'Content-Disposition':f'attachment; filename="{identity}.zip"'})
    return app


app=create_app()
