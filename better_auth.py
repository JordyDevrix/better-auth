import logging
import os
from dotenv import load_dotenv
load_dotenv()
from server import PromptServer
from aiohttp import web
from dataclasses import dataclass

try:
    secret_token = os.getenv("COMFY_AUTH_TOKEN")
except Exception as e:
    logging.error(f"Couldn't get token:\n{e}")

@dataclass
class Route:
    path: str
    method: str
    protected: bool=False

class AuthConfig:
    def __init__(self, require_auth_by_default=False):
        self.routes: list[Route] = []
        self.auth_by_default = require_auth_by_default

    def add_route(self, route: Route):
        self.routes.append(route)

    def configure_route(self, index: int, protected: bool):
        self.routes[index].protected = protected

    def is_protected(self, path: str, method: str) -> bool:
        for r in self.routes:
            if path.startswith(r.path) and method.upper() == r.method.upper():
                return r.protected
        return self.auth_by_default

    def configure_route_by_path_method(self, path: str, methods: str | list, protected: bool):
        for r in self.routes:
            # if path.startswith(r.path):
            if path == r.path:
                if type(methods) == list:
                    for method in methods:
                        if method.upper() == r.method.upper():
                            r.protected = protected
                else:
                    if methods.upper() == r.method.upper():
                        r.protected = protected

authconfig: AuthConfig = AuthConfig()

# Handle startup
async def add_default_routes(app):
    for route in app.router.routes():
        if route.method in ["GET", "POST", "DELETE", "PUT"]:
            path = getattr(getattr(route, "resource", None), "canonical", str(route.resource))

            route_config: Route = Route(
                path = path,
                method = route.method,
                protected = authconfig.auth_by_default,
            )
            authconfig.add_route(route_config)


logging.info(f"Using auth config: {authconfig.auth_by_default}")
PromptServer.instance.app.on_startup.append(add_default_routes)

# Middleware
async def auth_middleware(app, handler):
    async def middleware_handler(request):
        if authconfig.is_protected(request.path, request.method):
            token = request.headers.get("Authorization")
            if token != f"Bearer {secret_token}":
                return web.json_response(
                    {"error": "Unauthorized"},
                    status=401
                )
        return await handler(request)
    return middleware_handler

PromptServer.instance.app.middlewares.append(auth_middleware)

logging.info("[BetterAuth] Auth middleware loaded (aiohttp mode)")

# Routes configuration #
authconfig.configure_route_by_path_method(
    path = "/prompt",
    methods = ["GET", "POST"],
    protected = True,
)

class BetterAuth:
    def __init__(self):
        pass

    @classmethod
    def INPUT_TYPES(cls):
        return {"required": {}}

    RETURN_TYPES = ()
    OUTPUT_NODE = False
    FUNCTION = "run"
    CATEGORY = "Authentication"

    def run(self):
        return ()

NODE_CLASS_MAPPINGS = {
    "BetterAuth": BetterAuth
}

# A dictionary that contains the friendly/humanly readable titles for the nodes
NODE_DISPLAY_NAME_MAPPINGS = {
    "BetterAuth": "Better authentication"
}
