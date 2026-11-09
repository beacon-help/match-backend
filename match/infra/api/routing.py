import json
from http import HTTPStatus
from typing import Any, Callable, Coroutine

from fastapi import HTTPException, Request, Response
from fastapi.exceptions import RequestValidationError
from fastapi.routing import APIRoute


class _DeferredJSONRequest(Request):
    json_error: ValueError | None = None

    async def json(self) -> Any:
        try:
            return await super().json()
        except ValueError as e:
            self.json_error = e
            return None


class AuthBeforeBodyRoute(APIRoute):
    """FastAPI decodes the JSON body before solving dependencies, so a malformed body would
    answer 422 before authentication could answer 401. This route defers the decoding error
    until the dependencies have run, then reports it the way FastAPI does."""

    def get_route_handler(self) -> Callable[[Request], Coroutine[Any, Any, Response]]:
        handler = super().get_route_handler()

        async def route_handler(request: Request) -> Response:
            request = _DeferredJSONRequest(request.scope, request.receive)
            try:
                return await handler(request)
            except RequestValidationError:
                error = request.json_error
                if isinstance(error, json.JSONDecodeError):
                    raise RequestValidationError(
                        [
                            {
                                "type": "json_invalid",
                                "loc": ("body", error.pos),
                                "msg": "JSON decode error",
                                "input": {},
                                "ctx": {"error": error.msg},
                            }
                        ],
                        body=error.doc,
                    ) from error
                if error:
                    raise HTTPException(
                        status_code=HTTPStatus.BAD_REQUEST,
                        detail="There was an error parsing the body",
                    ) from error
                raise

        return route_handler
