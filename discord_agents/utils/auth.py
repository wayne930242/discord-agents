from flask import Response, request
from functools import wraps
from discord_agents.env import ADMIN_USERNAME, ADMIN_PASSWORD
from typing import Callable, Any


def check_auth(username: str, password: str) -> bool:
    return username == ADMIN_USERNAME and password == ADMIN_PASSWORD


def authenticate() -> Response:
    return Response(
        "Could not verify your access level for that URL.\n"
        "You have to login with proper credentials",
        401,
        {"WWW-Authenticate": 'Basic realm="Login Required"'},
    )


def requires_auth(f: Callable[..., Any]) -> Callable[..., Any]:
    @wraps(f)
    def decorated(*args: Any, **kwargs: Any) -> Any:
        auth = request.authorization
        if (
            not auth
            or not auth.username
            or not auth.password
            or not check_auth(auth.username, auth.password)
        ):
            return authenticate()
        return f(*args, **kwargs)

    return decorated
