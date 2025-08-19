
# === NexusCore/openenv\Lib\site-packages\litellm\proxy\proxy_cli.py ===
# ruff: noqa: T201
import importlib
import json
import os
import random
import subprocess
import sys
import urllib.parse
import urllib.parse as urlparse
from typing import TYPE_CHECKING, Any, Optional, Union

import click
import httpx
from dotenv import load_dotenv

if TYPE_CHECKING:
    from fastapi import FastAPI
else:
    FastAPI = Any

sys.path.append(os.getcwd())

config_filename = "litellm.secrets"

litellm_mode = os.getenv("LITELLM_MODE", "DEV")  # "PRODUCTION", "DEV"
if litellm_mode == "DEV":
    load_dotenv()
from enum import Enum

telemetry = None


class LiteLLMDatabaseConnectionPool(Enum):
    database_connection_pool_limit = 10
    database_connection_pool_timeout = 60


def append_query_params(url, params) -> str:
    from litellm._logging import verbose_proxy_logger

    verbose_proxy_logger.debug(f"url: {url}")
    verbose_proxy_logger.debug(f"params: {params}")
    parsed_url = urlparse.urlparse(url)
    parsed_query = urlparse.parse_qs(parsed_url.query)
    parsed_query.update(params)
    encoded_query = urlparse.urlencode(parsed_query, doseq=True)
    modified_url = urlparse.urlunparse(parsed_url._replace(query=encoded_query))
    return modified_url  # type: ignore


class ProxyInitializationHelpers:
    @staticmethod
    def _echo_litellm_version():
        pkg_version = importlib.metadata.version("litellm")  # type: ignore
        click.echo(f"\nLiteLLM: Current Version = {pkg_version}\n")

    @staticmethod
    def _run_health_check(host, port):
        print("\nLiteLLM: Health Testing models in config")  # noqa
        response = httpx.get(url=f"http://{host}:{port}/health")
        print(json.dumps(response.json(), indent=4))  # noqa

    @staticmethod
    def _run_test_chat_completion(
        host: str,
        port: int,
        model: str,
        test: Union[bool, str],
    ):
        request_model = model or "gpt-3.5-turbo"
        click.echo(
            f"\nLiteLLM: Making a test ChatCompletions request to your proxy. Model={request_model}"
        )
        import openai

        api_base = f"http://{host}:{port}"
        if isinstance(test, str):
            api_base = test
        else:
            raise ValueError("Invalid test value")
        client = openai.OpenAI(api_key="My API Key", base_url=api_base)

        response = client.chat.completions.create(
            model=request_model,
            messages=[
                {
                    "role": "user",
                    "content": "this is a test request, write a short poem",
                }
            ],
            max_tokens=256,
        )
        click.echo(f"\nLiteLLM: response from proxy {response}")

        print(  # noqa
            f"\n LiteLLM: Making a test ChatCompletions + streaming r equest to proxy. Model={request_model}"
        )

        stream_response = client.chat.completions.create(
            model=request_model,
            messages=[
                {
                    "role": "user",
                    "content": "this is a test request, write a short poem",
                }
            ],
            stream=True,
        )
        for chunk in stream_response:
            click.echo(f"LiteLLM: streaming response from proxy {chunk}")
        print("\n making completion request to proxy")  # noqa
        completion_response = client.completions.create(
            model=request_model, prompt="this is a test request, write a short poem"
        )
        print(completion_response)  # noqa

    @staticmethod
    def _get_default_unvicorn_init_args(
        host: str,
        port: int,
        log_config: Optional[str] = None,
        keepalive_timeout: Optional[int] = None,
    ) -> dict:
        """
        Get the arguments for `uvicorn` worker
        """
        import litellm

        uvicorn_args = {
            "app": "litellm.proxy.proxy_server:app",
            "host": host,
            "port": port,
        }
        if log_config is not None:
            print(f"Using log_config: {log_config}")  # noqa
            uvicorn_args["log_config"] = log_config
        elif litellm.json_logs:
            print("Using json logs. Setting log_config to None.")  # noqa
            uvicorn_args["log_config"] = None
        if keepalive_timeout is not None:
            uvicorn_args["timeout_keep_alive"] = keepalive_timeout
        return uvicorn_args

    @staticmethod
    def _init_hypercorn_server(
        app: FastAPI,
        host: str,
        port: int,
        ssl_certfile_path: str,
        ssl_keyfile_path: str,
        ciphers: Optional[str] = None,
    ):
        """
        Initialize litellm with `hypercorn`
        """
        import asyncio

        from hypercorn.asyncio import serve
        from hypercorn.config import Config

        print(  # noqa
            f"\033[1;32mLiteLLM Proxy: Starting server on {host}:{port} using Hypercorn\033[0m\n"  # noqa
        )  # noqa
        config = Config()
        config.bind = [f"{host}:{port}"]

        if ssl_certfile_path is not None and ssl_keyfile_path is not None:
            print(  # noqa
                f"\033[1;32mLiteLLM Proxy: Using SSL with certfile: {ssl_certfile_path} and keyfile: {ssl_keyfile_path}\033[0m\n"  # noqa
            )
            config.certfile = ssl_certfile_path
            config.keyfile = ssl_keyfile_path
            if ciphers is not None:
                config.ciphers = ciphers

        # hypercorn serve raises a type warning when passing a fast api app - even though fast API is a valid type
        asyncio.run(serve(app, config))  # type: ignore

    @staticmethod
    def _run_gunicorn_server(
        host: str,
        port: int,
        app: FastAPI,
        num_workers: int,
        ssl_certfile_path: str,
        ssl_keyfile_path: str,
    ):
        """
        Run litellm with `gunicorn`
        """
        if os.name == "nt":
            pass
        else:
            import gunicorn.app.base

        # Gunicorn Application Class
        class StandaloneApplication(gunicorn.app.base.BaseApplication):
            def __init__(self, app, options=None):
                self.options = options or {}  # gunicorn options
                self.application = app  # FastAPI app
                super().__init__()

                _endpoint_str = (
                    f"curl --location 'http://0.0.0.0:{port}/chat/completions' \\"
                )
                curl_command = (
                    _endpoint_str
                    + """
                --header 'Content-Type: application/json' \\
                --data ' {
                "model": "gpt-3.5-turbo",
                "messages": [
                    {
                    "role": "user",
                    "content": "what llm are you"
                    }
                ]
                }'
                \n
                """
                )
                print()  # noqa
                print(  # noqa
                    '\033[1;34mLiteLLM: Test your local proxy with: "litellm --test" This runs an openai.ChatCompletion request to your proxy [In a new terminal tab]\033[0m\n'
                )
                print(  # noqa
                    f"\033[1;34mLiteLLM: Curl Command Test for your local proxy\n {curl_command} \033[0m\n"
                )
                print(  # noqa
                    "\033[1;34mDocs: https://docs.litellm.ai/docs/simple_proxy\033[0m\n"
                )  # noqa
                print(  # noqa
                    f"\033[1;34mSee all Router/Swagger docs on http://0.0.0.0:{port} \033[0m\n"
                )  # noqa

            def load_config(self):
                # note: This Loads the gunicorn config - has nothing to do with LiteLLM Proxy config
                if self.cfg is not None:
                    config = {
                        key: value
                        for key, value in self.options.items()
                        if key in self.cfg.settings and value is not None
                    }
                else:
                    config = {}
                for key, value in config.items():
                    if self.cfg is not None:
                        self.cfg.set(key.lower(), value)

            def load(self):
                # gunicorn app function
                return self.application

        print(  # noqa
            f"\033[1;32mLiteLLM Proxy: Starting server on {host}:{port} with {num_workers} workers\033[0m\n"  # noqa
        )
        gunicorn_options = {
            "bind": f"{host}:{port}",
            "workers": num_workers,  # default is 1
            "worker_class": "uvicorn.workers.UvicornWorker",
            "preload": True,  # Add the preload flag,
            "accesslog": "-",  # Log to stdout
            "timeout": 600,  # default to very high number, bedrock/anthropic.claude-v2:1 can take 30+ seconds for the 1st chunk to come in
            "access_log_format": '%(h)s %(l)s %(u)s %(t)s "%(r)s" %(s)s %(b)s',
        }

        if ssl_certfile_path is not None and ssl_keyfile_path is not None:
            print(  # noqa
                f"\033[1;32mLiteLLM Proxy: Using SSL with certfile: {ssl_certfile_path} and keyfile: {ssl_keyfile_path}\033[0m\n"  # noqa
            )
            gunicorn_options["certfile"] = ssl_certfile_path
            gunicorn_options["keyfile"] = ssl_keyfile_path

        StandaloneApplication(app=app, options=gunicorn_options).run()  # Run gunicorn

    @staticmethod
    def _run_ollama_serve():
        try:
            command = ["ollama", "serve"]

            with open(os.devnull, "w") as devnull:
                subprocess.Popen(command, stdout=devnull, stderr=devnull)
        except Exception as e:
            print(  # noqa
                f"""
                LiteLLM Warning: proxy started with `ollama` model\n`ollama serve` failed with Exception{e}. \nEnsure you run `ollama serve`
            """
            )  # noqa

    @staticmethod
    def _is_port_in_use(port):
        import socket

        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
            return s.connect_ex(("localhost", port)) == 0

    @staticmethod
    def _get_loop_type():
        """Helper function to determine the event loop type based on platform"""
        if sys.platform in ("win32", "cygwin", "cli"):
            return None  # Let uvicorn choose the default loop on Windows
        return "uvloop"


@click.command()
@click.option(
    "--host", default="0.0.0.0", help="Host for the server to listen on.", envvar="HOST"
)
@click.option("--port", default=4000, help="Port to bind the server to.", envvar="PORT")
@click.option(
    "--num_workers",
    default=1,
    help="Number of uvicorn / gunicorn workers to spin up. By default, 1 uvicorn is used.",
    envvar="NUM_WORKERS",
)
@click.option("--api_base", default=None, help="API base URL.")
@click.option(
    "--api_version",
    default="2024-07-01-preview",
    help="For azure - pass in the api version.",
)
@click.option(
    "--model", "-m", default=None, help="The model name to pass to litellm expects"
)
@click.option(
    "--alias",
    default=None,
    help='The alias for the model - use this to give a litellm model name (e.g. "huggingface/codellama/CodeLlama-7b-Instruct-hf") a more user-friendly name ("codellama")',
)
@click.option(
    "--add_key", default=None, help="The model name to pass to litellm expects"
)
@click.option("--headers", default=None, help="headers for the API call")
@click.option("--save", is_flag=True, type=bool, help="Save the model-specific config")
@click.option(
    "--debug",
    default=False,
    is_flag=True,
    type=bool,
    help="To debug the input",
    envvar="DEBUG",
)
@click.option(
    "--detailed_debug",
    default=False,
    is_flag=True,
    type=bool,
    help="To view detailed debug logs",
    envvar="DETAILED_DEBUG",
)
@click.option(
    "--use_queue",
    default=False,
    is_flag=True,
    type=bool,
    help="To use celery workers for async endpoints",
)
@click.option(
    "--temperature", default=None, type=float, help="Set temperature for the model"
)
@click.option(
    "--max_tokens", default=None, type=int, help="Set max tokens for the model"
)
@click.option(
    "--request_timeout",
    default=None,
    type=int,
    help="Set timeout in seconds for completion calls",
)
@click.option("--drop_params", is_flag=True, help="Drop any unmapped params")
@click.option(
    "--add_function_to_prompt",
    is_flag=True,
    help="If function passed but unsupported, pass it as prompt",
)
@click.option(
    "--config",
    "-c",
    default=None,
    help="Path to the proxy configuration file (e.g. config.yaml). Usage `litellm --config config.yaml`",
)
@click.option(
    "--max_budget",
    default=None,
    type=float,
    help="Set max budget for API calls - works for hosted models like OpenAI, TogetherAI, Anthropic, etc.`",
)
@click.option(
    "--telemetry",
    default=True,
    type=bool,
    help="Helps us know if people are using this feature. Turn this off by doing `--telemetry False`",
)
@click.option(
    "--log_config",
    default=None,
    type=str,
    help="Path to the logging configuration file",
)
@click.option(
    "--version",
    "-v",
    default=False,
    is_flag=True,
    type=bool,
    help="Print LiteLLM version",
)
@click.option(
    "--health",
    flag_value=True,
    help="Make a chat/completions request to all llms in config.yaml",
)
@click.option(
    "--test",
    flag_value=True,
    help="proxy chat completions url to make a test request to",
)
@click.option(
    "--test_async",
    default=False,
    is_flag=True,
    help="Calls async endpoints /queue/requests and /queue/response",
)
@click.option(
    "--iam_token_db_auth",
    default=False,
    is_flag=True,
    help="Connects to RDS DB with IAM token",
)
@click.option(
    "--num_requests",
    default=10,
    type=int,
    help="Number of requests to hit async endpoint with",
)
@click.option(
    "--run_gunicorn",
    default=False,
    is_flag=True,
    help="Starts proxy via gunicorn, instead of uvicorn (better for managing multiple workers)",
)
@click.option(
    "--run_hypercorn",
    default=False,
    is_flag=True,
    help="Starts proxy via hypercorn, instead of uvicorn (supports HTTP/2)",
)
@click.option(
    "--ssl_keyfile_path",
    default=None,
    type=str,
    help="Path to the SSL keyfile. Use this when you want to provide SSL certificate when starting proxy",
    envvar="SSL_KEYFILE_PATH",
)
@click.option(
    "--ssl_certfile_path",
    default=None,
    type=str,
    help="Path to the SSL certfile. Use this when you want to provide SSL certificate when starting proxy",
    envvar="SSL_CERTFILE_PATH",
)
@click.option(
    "--ciphers",
    default=None,
    type=str,
    help="Ciphers to use for the SSL setup.",
)
@click.option(
    "--use_prisma_migrate",
    is_flag=True,
    default=False,
    help="Use prisma migrate instead of prisma db push for database schema updates",
)
@click.option("--local", is_flag=True, default=False, help="for local debugging")
@click.option(
    "--skip_server_startup",
    is_flag=True,
    default=False,
    help="Skip starting the server after setup (useful for migrations only)",
)
@click.option(
    "--keepalive_timeout",
    default=None,
    type=int,
    help="Set the uvicorn keepalive timeout in seconds (uvicorn timeout_keep_alive parameter)",
    envvar="KEEPALIVE_TIMEOUT",
)
def run_server(  # noqa: PLR0915
    host,
    port,
    api_base,
    api_version,
    model,
    alias,
    add_key,
    headers,
    save,
    debug,
    detailed_debug,
    temperature,
    max_tokens,
    request_timeout,
    drop_params,
    add_function_to_prompt,
    config,
    max_budget,
    telemetry,
    test,
    local,
    num_workers,
    test_async,
    iam_token_db_auth,
    num_requests,
    use_queue,
    health,
    version,
    run_gunicorn,
    run_hypercorn,
    ssl_keyfile_path,
    ssl_certfile_path,
    ciphers,
    log_config,
    use_prisma_migrate,
    skip_server_startup,
    keepalive_timeout,
):
    args = locals()
    if local:
        from proxy_server import (
            KeyManagementSettings,
            ProxyConfig,
            app,
            save_worker_config,
        )
    else:
        try:
            from .proxy_server import (
                KeyManagementSettings,
                ProxyConfig,
                app,
                save_worker_config,
            )
        except ModuleNotFoundError as e:
            raise ModuleNotFoundError(
                f"Missing dependency {e}. Run `pip install 'litellm[proxy]'`"
            )
        except ImportError as e:
            if "litellm[proxy]" in str(e):
                # user is missing a proxy dependency, ask them to pip install litellm[proxy]
                raise e
            else:
                # this is just a local/relative import error, user git cloned litellm
                from proxy_server import (
                    KeyManagementSettings,
                    ProxyConfig,
                    app,
                    save_worker_config,
                )
    if version is True:
        ProxyInitializationHelpers._echo_litellm_version()
        return
    if model and "ollama" in model and api_base is None:
        ProxyInitializationHelpers._run_ollama_serve()
    if health is True:
        ProxyInitializationHelpers._run_health_check(host, port)
        return
    if test is True:
        ProxyInitializationHelpers._run_test_chat_completion(host, port, model, test)
        return
    else:
        if headers:
            headers = json.loads(headers)
        save_worker_config(
            model=model,
            alias=alias,
            api_base=api_base,
            api_version=api_version,
            debug=debug,
            detailed_debug=detailed_debug,
            temperature=temperature,
            max_tokens=max_tokens,
            request_timeout=request_timeout,
            max_budget=max_budget,
            telemetry=telemetry,
            drop_params=drop_params,
            add_function_to_prompt=add_function_to_prompt,
            headers=headers,
            save=save,
            config=config,
            use_queue=use_queue,
        )
        try:
            import uvicorn
        except Exception:
            raise ImportError(
                "uvicorn, gunicorn needs to be imported. Run - `pip install 'litellm[proxy]'`"
            )

        db_connection_pool_limit = 100
        db_connection_timeout = 60
        general_settings = {}
        ### GET DB TOKEN FOR IAM AUTH ###

        if iam_token_db_auth:
            from litellm.proxy.auth.rds_iam_token import generate_iam_auth_token

            db_host = os.getenv("DATABASE_HOST")
            db_port = os.getenv("DATABASE_PORT")
            db_user = os.getenv("DATABASE_USER")
            db_name = os.getenv("DATABASE_NAME")
            db_schema = os.getenv("DATABASE_SCHEMA")

            token = generate_iam_auth_token(
                db_host=db_host, db_port=db_port, db_user=db_user
            )

            # print(f"token: {token}")
            _db_url = f"postgresql://{db_user}:{token}@{db_host}:{db_port}/{db_name}"
            if db_schema:
                _db_url += f"?schema={db_schema}"

            os.environ["DATABASE_URL"] = _db_url
            os.environ["IAM_TOKEN_DB_AUTH"] = "True"

        ### DECRYPT ENV VAR ###

        from litellm.secret_managers.aws_secret_manager import decrypt_env_var

        if (
            os.getenv("USE_AWS_KMS", None) is not None
            and os.getenv("USE_AWS_KMS") == "True"
        ):
            ## V2 IMPLEMENTATION OF AWS KMS - USER WANTS TO DECRYPT MULTIPLE KEYS IN THEIR ENV
            new_env_var = decrypt_env_var()

            for k, v in new_env_var.items():
                os.environ[k] = v

        if config is not None:
            """
            Allow user to pass in db url via config

            read from there and save it to os.env['DATABASE_URL']
            """
            try:
                import asyncio

            except Exception:
                raise ImportError(
                    "yaml needs to be imported. Run - `pip install 'litellm[proxy]'`"
                )

            proxy_config = ProxyConfig()
            _config = asyncio.run(proxy_config.get_config(config_file_path=config))

            ### LITELLM SETTINGS ###
            litellm_settings = _config.get("litellm_settings", None)
            if (
                litellm_settings is not None
                and "json_logs" in litellm_settings
                and litellm_settings["json_logs"] is True
            ):
                import litellm

                litellm.json_logs = True

                litellm._turn_on_json()
            ### GENERAL SETTINGS ###
            general_settings = _config.get("general_settings", {})
            if general_settings is None:
                general_settings = {}
            if general_settings:
                ### LOAD SECRET MANAGER ###
                key_management_system = general_settings.get(
                    "key_management_system", None
                )
                proxy_config.initialize_secret_manager(key_management_system)
            key_management_settings = general_settings.get(
                "key_management_settings", None
            )
            if key_management_settings is not None:
                import litellm

                litellm._key_management_settings = KeyManagementSettings(
                    **key_management_settings
                )
            database_url = general_settings.get("database_url", None)
            if database_url is None and os.getenv("DATABASE_URL") is None:
                # Check if all required variables are provided
                database_host = os.getenv("DATABASE_HOST")
                database_username = os.getenv("DATABASE_USERNAME")
                database_password = os.getenv("DATABASE_PASSWORD")
                database_name = os.getenv("DATABASE_NAME")

                if (
                    database_host
                    and database_username
                    and database_password
                    and database_name
                ):
                    # Handle the problem of special character escaping in the database URL
                    database_username_enc = urllib.parse.quote_plus(database_username)
                    database_password_enc = urllib.parse.quote_plus(database_password)
                    database_name_enc = urllib.parse.quote_plus(database_name)

                    # Construct DATABASE_URL from the provided variables
                    database_url = f"postgresql://{database_username_enc}:{database_password_enc}@{database_host}/{database_name_enc}"

                    os.environ["DATABASE_URL"] = database_url
            db_connection_pool_limit = general_settings.get(
                "database_connection_pool_limit",
                LiteLLMDatabaseConnectionPool.database_connection_pool_limit.value,
            )
            db_connection_timeout = general_settings.get(
                "database_connection_pool_timeout",
                LiteLLMDatabaseConnectionPool.database_connection_pool_timeout.value,
            )
            if database_url and database_url.startswith("os.environ/"):
                original_dir = os.getcwd()
                # set the working directory to where this script is
                sys.path.insert(
                    0, os.path.abspath("../..")
                )  # Adds the parent directory to the system path - for litellm local dev
                import litellm
                from litellm import get_secret_str

                database_url = get_secret_str(database_url, default_value=None)
                os.chdir(original_dir)
            if database_url is not None and isinstance(database_url, str):
                os.environ["DATABASE_URL"] = database_url

        if (
            os.getenv("DATABASE_URL", None) is not None
            or os.getenv("DIRECT_URL", None) is not None
        ):
            try:
                from litellm.secret_managers.main import get_secret

                if os.getenv("DATABASE_URL", None) is not None:
                    ### add connection pool + pool timeout args
                    params = {
                        "connection_limit": db_connection_pool_limit,
                        "pool_timeout": db_connection_timeout,
                    }
                    database_url = get_secret("DATABASE_URL", default_value=None)
                    modified_url = append_query_params(database_url, params)
                    os.environ["DATABASE_URL"] = modified_url
                if os.getenv("DIRECT_URL", None) is not None:
                    ### add connection pool + pool timeout args
                    params = {
                        "connection_limit": db_connection_pool_limit,
                        "pool_timeout": db_connection_timeout,
                    }
                    database_url = os.getenv("DIRECT_URL")
                    modified_url = append_query_params(database_url, params)
                    os.environ["DIRECT_URL"] = modified_url
                    ###
                subprocess.run(["prisma"], capture_output=True)
                is_prisma_runnable = True
            except FileNotFoundError:
                is_prisma_runnable = False

            if is_prisma_runnable:
                from litellm.proxy.db.check_migration import check_prisma_schema_diff
                from litellm.proxy.db.prisma_client import (
                    PrismaManager,
                    should_update_prisma_schema,
                )

                if (
                    should_update_prisma_schema(
                        general_settings.get("disable_prisma_schema_update")
                    )
                    is False
                ):
                    check_prisma_schema_diff(db_url=None)
                else:
                    PrismaManager.setup_database(use_migrate=use_prisma_migrate)
            else:
                print(  # noqa
                    f"Unable to connect to DB. DATABASE_URL found in environment, but prisma package not found."  # noqa
                )
        if port == 4000 and ProxyInitializationHelpers._is_port_in_use(port):
            port = random.randint(1024, 49152)

        import litellm

        if detailed_debug is True:
            litellm._turn_on_debug()

        # DO NOT DELETE - enables global variables to work across files
        from litellm.proxy.proxy_server import app  # noqa

        # Skip server startup if requested (after all setup is done)
        if skip_server_startup:
            print(  # noqa
                "LiteLLM: Setup complete. Skipping server startup as requested."
            )
            return

        uvicorn_args = ProxyInitializationHelpers._get_default_unvicorn_init_args(
            host=host,
            port=port,
            log_config=log_config,
            keepalive_timeout=keepalive_timeout,
        )
        if run_gunicorn is False and run_hypercorn is False:
            if ssl_certfile_path is not None and ssl_keyfile_path is not None:
                print(  # noqa
                    f"\033[1;32mLiteLLM Proxy: Using SSL with certfile: {ssl_certfile_path} and keyfile: {ssl_keyfile_path}\033[0m\n"  # noqa
                )
                uvicorn_args["ssl_keyfile"] = ssl_keyfile_path
                uvicorn_args["ssl_certfile"] = ssl_certfile_path

            loop_type = ProxyInitializationHelpers._get_loop_type()
            if loop_type:
                uvicorn_args["loop"] = loop_type

            uvicorn.run(
                **uvicorn_args,
                workers=num_workers,
            )
        elif run_gunicorn is True:
            ProxyInitializationHelpers._run_gunicorn_server(
                host=host,
                port=port,
                app=app,
                num_workers=num_workers,
                ssl_certfile_path=ssl_certfile_path,
                ssl_keyfile_path=ssl_keyfile_path,
            )
        elif run_hypercorn is True:
            ProxyInitializationHelpers._init_hypercorn_server(
                app=app,
                host=host,
                port=port,
                ssl_certfile_path=ssl_certfile_path,
                ssl_keyfile_path=ssl_keyfile_path,
                ciphers=ciphers,
            )


if __name__ == "__main__":
    run_server()

# === NexusCore/openenv\Lib\site-packages\pythonwin\pywin\scintilla\view.py ===
# A general purpose MFC CCtrlView view that uses Scintilla.

import os
import re
import string
import struct
import sys

import __main__  # for attribute lookup
import win32con
import win32ui
from pywin.mfc import afxres, docview

from . import (
    IDLEenvironment,  # nopycln: import # Injects fast_readline into the IDLE auto-indent extension
    bindings,
    control,
    scintillacon,
)

PRINTDLGORD = 1538
IDC_PRINT_MAG_EDIT = 1010
EM_FORMATRANGE = win32con.WM_USER + 57

wordbreaks = "._" + string.ascii_uppercase + string.ascii_lowercase + string.digits

patImport = re.compile(r"import (?P<name>.*)")

_event_commands = [
    # File menu
    "win32ui.ID_FILE_LOCATE",
    "win32ui.ID_FILE_CHECK",
    "afxres.ID_FILE_CLOSE",
    "afxres.ID_FILE_NEW",
    "afxres.ID_FILE_OPEN",
    "afxres.ID_FILE_SAVE",
    "afxres.ID_FILE_SAVE_AS",
    "win32ui.ID_FILE_SAVE_ALL",
    # Edit menu
    "afxres.ID_EDIT_UNDO",
    "afxres.ID_EDIT_REDO",
    "afxres.ID_EDIT_CUT",
    "afxres.ID_EDIT_COPY",
    "afxres.ID_EDIT_PASTE",
    "afxres.ID_EDIT_SELECT_ALL",
    "afxres.ID_EDIT_FIND",
    "afxres.ID_EDIT_REPEAT",
    "afxres.ID_EDIT_REPLACE",
    # View menu
    "win32ui.ID_VIEW_WHITESPACE",
    "win32ui.ID_VIEW_FIXED_FONT",
    "win32ui.ID_VIEW_BROWSE",
    "win32ui.ID_VIEW_INTERACTIVE",
    # Window menu
    "afxres.ID_WINDOW_ARRANGE",
    "afxres.ID_WINDOW_CASCADE",
    "afxres.ID_WINDOW_NEW",
    "afxres.ID_WINDOW_SPLIT",
    "afxres.ID_WINDOW_TILE_HORZ",
    "afxres.ID_WINDOW_TILE_VERT",
    # Others
    "afxres.ID_APP_EXIT",
    "afxres.ID_APP_ABOUT",
]

_extra_event_commands = [
    ("EditDelete", afxres.ID_EDIT_CLEAR),
    ("LocateModule", win32ui.ID_FILE_LOCATE),
    ("GotoLine", win32ui.ID_EDIT_GOTO_LINE),
    ("DbgBreakpointToggle", win32ui.IDC_DBG_ADD),
    ("DbgGo", win32ui.IDC_DBG_GO),
    ("DbgStepOver", win32ui.IDC_DBG_STEPOVER),
    ("DbgStep", win32ui.IDC_DBG_STEP),
    ("DbgStepOut", win32ui.IDC_DBG_STEPOUT),
    ("DbgBreakpointClearAll", win32ui.IDC_DBG_CLEAR),
    ("DbgClose", win32ui.IDC_DBG_CLOSE),
]

event_commands = []


def _CreateEvents():
    for name in _event_commands:
        val = eval(name)
        name_parts = name.split("_")[1:]
        name_parts = [p.capitalize() for p in name_parts]
        event = "".join(name_parts)
        event_commands.append((event, val))
    for name, id in _extra_event_commands:
        event_commands.append((name, id))


_CreateEvents()
del _event_commands
del _extra_event_commands

command_reflectors = [
    (win32ui.ID_EDIT_UNDO, win32con.WM_UNDO),
    (win32ui.ID_EDIT_REDO, scintillacon.SCI_REDO),
    (win32ui.ID_EDIT_CUT, win32con.WM_CUT),
    (win32ui.ID_EDIT_COPY, win32con.WM_COPY),
    (win32ui.ID_EDIT_PASTE, win32con.WM_PASTE),
    (win32ui.ID_EDIT_CLEAR, win32con.WM_CLEAR),
    (win32ui.ID_EDIT_SELECT_ALL, scintillacon.SCI_SELECTALL),
]


def DoBraceMatch(control):
    curPos = control.SCIGetCurrentPos()
    charBefore = " "
    if curPos:
        charBefore = control.SCIGetCharAt(curPos - 1)
    charAt = control.SCIGetCharAt(curPos)
    braceAtPos = braceOpposite = -1
    if charBefore in "[](){}":
        braceAtPos = curPos - 1
    if braceAtPos == -1:
        if charAt in "[](){}":
            braceAtPos = curPos
    if braceAtPos != -1:
        braceOpposite = control.SCIBraceMatch(braceAtPos, 0)
    if braceAtPos != -1 and braceOpposite == -1:
        control.SCIBraceBadHighlight(braceAtPos)
    else:
        # either clear them both or set them both.
        control.SCIBraceHighlight(braceAtPos, braceOpposite)


def _get_class_attributes(ob):
    # Recurse into base classes looking for attributes
    items = []
    try:
        items.extend(dir(ob))
        for i in ob.__bases__:
            for item in _get_class_attributes(i):
                if item not in items:
                    items.append(item)
    except AttributeError:
        pass
    return items


# Supposed to look like an MFC CEditView, but
# also supports IDLE extensions and other source code generic features.
class CScintillaView(docview.CtrlView, control.CScintillaColorEditInterface):
    def __init__(self, doc):
        docview.CtrlView.__init__(
            self,
            doc,
            "Scintilla",
            win32con.WS_CHILD
            | win32con.WS_VSCROLL
            | win32con.WS_HSCROLL
            | win32con.WS_CLIPCHILDREN
            | win32con.WS_VISIBLE,
        )
        self._tabWidth = (
            8  # Mirror of what we send to Scintilla - never change this directly
        )
        self.bAutoCompleteAttributes = 1
        self.bShowCallTips = 1
        self.bMatchBraces = 0  # Editor option will default this to true later!
        self.bindings = bindings.BindingsManager(self)

        self.idle = IDLEenvironment.IDLEEditorWindow(self)
        self.idle.IDLEExtension("AutoExpand")
        # SendScintilla is called so frequently it is worth optimizing.
        self.SendScintilla = self._obj_.SendMessage

    def _MakeColorizer(self):
        ext = os.path.splitext(self.GetDocument().GetPathName())[1]
        from . import formatter

        return formatter.BuiltinPythonSourceFormatter(self, ext)

    # 	def SendScintilla(self, msg, w=0, l=0):
    # 		return self._obj_.SendMessage(msg, w, l)

    def SCISetTabWidth(self, width):
        # I need to remember the tab-width for the AutoIndent extension.  This may go.
        self._tabWidth = width
        control.CScintillaEditInterface.SCISetTabWidth(self, width)

    def GetTabWidth(self):
        return self._tabWidth

    def HookHandlers(self):
        # Create events for all the menu names.
        for name, val in event_commands:
            # 			handler = lambda id, code, tosend=val, parent=parent: parent.OnCommand(tosend, 0) and 0
            self.bindings.bind(name, None, cid=val)

        # Hook commands that do nothing other than send Scintilla messages.
        for command, reflection in command_reflectors:
            handler = (
                lambda id, code, ss=self.SendScintilla, tosend=reflection: ss(tosend)
                and 0
            )
            self.HookCommand(handler, command)

        self.HookCommand(self.OnCmdViewWS, win32ui.ID_VIEW_WHITESPACE)
        self.HookCommandUpdate(self.OnUpdateViewWS, win32ui.ID_VIEW_WHITESPACE)
        self.HookCommand(
            self.OnCmdViewIndentationGuides, win32ui.ID_VIEW_INDENTATIONGUIDES
        )
        self.HookCommandUpdate(
            self.OnUpdateViewIndentationGuides, win32ui.ID_VIEW_INDENTATIONGUIDES
        )
        self.HookCommand(self.OnCmdViewRightEdge, win32ui.ID_VIEW_RIGHT_EDGE)
        self.HookCommandUpdate(self.OnUpdateViewRightEdge, win32ui.ID_VIEW_RIGHT_EDGE)
        self.HookCommand(self.OnCmdViewEOL, win32ui.ID_VIEW_EOL)
        self.HookCommandUpdate(self.OnUpdateViewEOL, win32ui.ID_VIEW_EOL)
        self.HookCommand(self.OnCmdViewFixedFont, win32ui.ID_VIEW_FIXED_FONT)
        self.HookCommandUpdate(self.OnUpdateViewFixedFont, win32ui.ID_VIEW_FIXED_FONT)
        self.HookCommand(self.OnCmdFileLocate, win32ui.ID_FILE_LOCATE)
        self.HookCommand(self.OnCmdEditFind, win32ui.ID_EDIT_FIND)
        self.HookCommand(self.OnCmdEditRepeat, win32ui.ID_EDIT_REPEAT)
        self.HookCommand(self.OnCmdEditReplace, win32ui.ID_EDIT_REPLACE)
        self.HookCommand(self.OnCmdGotoLine, win32ui.ID_EDIT_GOTO_LINE)
        self.HookCommand(self.OnFilePrint, afxres.ID_FILE_PRINT)
        self.HookCommand(self.OnFilePrint, afxres.ID_FILE_PRINT_DIRECT)
        self.HookCommand(self.OnFilePrintPreview, win32ui.ID_FILE_PRINT_PREVIEW)
        # Key bindings.
        self.HookMessage(self.OnKeyDown, win32con.WM_KEYDOWN)
        self.HookMessage(self.OnKeyDown, win32con.WM_SYSKEYDOWN)
        # Hook wheeley mouse events
        # 		self.HookMessage(self.OnMouseWheel, win32con.WM_MOUSEWHEEL)
        self.HookFormatter()

    def OnInitialUpdate(self):
        doc = self.GetDocument()

        # Enable Unicode
        self.SendScintilla(scintillacon.SCI_SETCODEPAGE, scintillacon.SC_CP_UTF8, 0)
        self.SendScintilla(scintillacon.SCI_SETKEYSUNICODE, 1, 0)

        # Create margins
        self.SendScintilla(
            scintillacon.SCI_SETMARGINTYPEN, 1, scintillacon.SC_MARGIN_SYMBOL
        )
        self.SendScintilla(scintillacon.SCI_SETMARGINMASKN, 1, 0xF)
        self.SendScintilla(
            scintillacon.SCI_SETMARGINTYPEN, 2, scintillacon.SC_MARGIN_SYMBOL
        )
        self.SendScintilla(
            scintillacon.SCI_SETMARGINMASKN, 2, scintillacon.SC_MASK_FOLDERS
        )
        self.SendScintilla(scintillacon.SCI_SETMARGINSENSITIVEN, 2, 1)

        self.GetDocument().HookViewNotifications(
            self
        )  # is there an MFC way to grab this?
        self.HookHandlers()

        # Load the configuration information.
        self.OnWinIniChange(None)

        self.SetSel()

        self.GetDocument().FinalizeViewCreation(
            self
        )  # is there an MFC way to grab this?

    def _GetSubConfigNames(self):
        return None  # By default we use only sections without sub-sections.

    def OnWinIniChange(self, section=None):
        self.bindings.prepare_configure()
        try:
            self.DoConfigChange()
        finally:
            self.bindings.complete_configure()

    def DoConfigChange(self):
        # Bit of a hack I don't kow what to do about - these should be "editor options"
        from pywin.framework.editor import GetEditorOption

        self.bAutoCompleteAttributes = GetEditorOption("Autocomplete Attributes", 1)
        self.bShowCallTips = GetEditorOption("Show Call Tips", 1)
        # Update the key map and extension data.
        configManager.configure(self, self._GetSubConfigNames())
        if configManager.last_error:
            win32ui.MessageBox(configManager.last_error, "Configuration Error")
        self.bMatchBraces = GetEditorOption("Match Braces", 1)
        self.ApplyFormattingStyles(1)

    def OnDestroy(self, msg):
        self.bindings.close()
        self.bindings = None
        self.idle.close()
        self.idle = None
        control.CScintillaColorEditInterface.close(self)
        return docview.CtrlView.OnDestroy(self, msg)

    def OnMouseWheel(self, msg):
        zDelta = msg[2] >> 16
        vpos = self.GetScrollPos(win32con.SB_VERT)
        vpos -= zDelta / 40  # 3 lines per notch
        self.SetScrollPos(win32con.SB_VERT, vpos)
        self.SendScintilla(
            win32con.WM_VSCROLL, (vpos << 16) | win32con.SB_THUMBPOSITION, 0
        )

    def OnBraceMatch(self, std, extra):
        if not self.bMatchBraces:
            return
        DoBraceMatch(self)

    def OnNeedShown(self, std, extra):
        notify = self.SCIUnpackNotifyMessage(extra)
        # OnNeedShown is called before an edit operation when
        # text is folded (as it is possible the text insertion will happen
        # in a folded region.)  As this happens _before_ the insert,
        # we ignore the length (if we are at EOF, pos + length may
        # actually be beyond the end of buffer)
        self.EnsureCharsVisible(notify.position)

    def EnsureCharsVisible(self, start, end=None):
        if end is None:
            end = start
        lineStart = self.LineFromChar(min(start, end))
        lineEnd = self.LineFromChar(max(start, end))
        while lineStart <= lineEnd:
            self.SCIEnsureVisible(lineStart)
            lineStart += 1

    # Helper to add an event to a menu.
    def AppendMenu(self, menu, text="", event=None, flags=None, checked=0):
        if event is None:
            assert flags is not None, "No event or custom flags!"
            cmdid = 0
        else:
            cmdid = self.bindings.get_command_id(event)
            if cmdid is None:
                # No event of that name - no point displaying it.
                print(
                    'View.AppendMenu(): Unknown event "{}" specified for menu text "{}" - ignored'.format(
                        event, text
                    )
                )
                return
            keyname = configManager.get_key_binding(event, self._GetSubConfigNames())
            if keyname is not None:
                text += "\t" + keyname
        if flags is None:
            flags = win32con.MF_STRING | win32con.MF_ENABLED
        if checked:
            flags |= win32con.MF_CHECKED
        menu.AppendMenu(flags, cmdid, text)

    def OnKeyDown(self, msg):
        return self.bindings.fire_key_event(msg)

    def GotoEndOfFileEvent(self, event):
        self.SetSel(-1)

    def KeyDotEvent(self, event):
        ## Don't trigger autocomplete if any text is selected
        s, e = self.GetSel()
        if s != e:
            return 1
        self.SCIAddText(".")
        if self.bAutoCompleteAttributes:
            self._AutoComplete()

    # View Whitespace/EOL/Indentation UI.

    def OnCmdViewWS(self, cmd, code):  # Handle the menu command
        viewWS = self.SCIGetViewWS()
        self.SCISetViewWS(not viewWS)

    def OnUpdateViewWS(self, cmdui):  # Update the tick on the UI.
        cmdui.SetCheck(self.SCIGetViewWS())
        cmdui.Enable()

    def OnCmdViewIndentationGuides(self, cmd, code):  # Handle the menu command
        viewIG = self.SCIGetIndentationGuides()
        self.SCISetIndentationGuides(not viewIG)

    def OnUpdateViewIndentationGuides(self, cmdui):  # Update the tick on the UI.
        cmdui.SetCheck(self.SCIGetIndentationGuides())
        cmdui.Enable()

    def OnCmdViewRightEdge(self, cmd, code):  # Handle the menu command
        if self.SCIGetEdgeMode() == scintillacon.EDGE_NONE:
            mode = scintillacon.EDGE_BACKGROUND
        else:
            mode = scintillacon.EDGE_NONE
        self.SCISetEdgeMode(mode)

    def OnUpdateViewRightEdge(self, cmdui):  # Update the tick on the UI.
        cmdui.SetCheck(self.SCIGetEdgeMode() != scintillacon.EDGE_NONE)
        cmdui.Enable()

    def OnCmdViewEOL(self, cmd, code):  # Handle the menu command
        viewEOL = self.SCIGetViewEOL()
        self.SCISetViewEOL(not viewEOL)

    def OnUpdateViewEOL(self, cmdui):  # Update the tick on the UI.
        cmdui.SetCheck(self.SCIGetViewEOL())
        cmdui.Enable()

    def OnCmdViewFixedFont(self, cmd, code):  # Handle the menu command
        self._GetColorizer().bUseFixed = not self._GetColorizer().bUseFixed
        self.ApplyFormattingStyles(0)
        # Ensure the selection is visible!
        self.ScrollCaret()

    def OnUpdateViewFixedFont(self, cmdui):  # Update the tick on the UI.
        c = self._GetColorizer()
        if c is not None:
            cmdui.SetCheck(c.bUseFixed)
        cmdui.Enable(c is not None)

    def OnCmdEditFind(self, cmd, code):
        from . import find

        find.ShowFindDialog()

    def OnCmdEditRepeat(self, cmd, code):
        from . import find

        find.FindNext()

    def OnCmdEditReplace(self, cmd, code):
        from . import find

        find.ShowReplaceDialog()

    def OnCmdFileLocate(self, cmd, id):
        line = self.GetLine().strip()
        import pywin.framework.scriptutils

        m = patImport.match(line)
        if m:
            # Module name on this line - locate that!
            modName = m.group("name")
            fileName = pywin.framework.scriptutils.LocatePythonFile(modName)
            if fileName is None:
                win32ui.SetStatusText("Can't locate module %s" % modName)
                return 1  # Let the default get it.
            else:
                win32ui.GetApp().OpenDocumentFile(fileName)
        else:
            # Just to a "normal" locate - let the default handler get it.
            return 1
        return 0

    def OnCmdGotoLine(self, cmd, id):
        try:
            lineNo = int(input("Enter Line Number")) - 1
        except (ValueError, KeyboardInterrupt):
            return 0
        self.SCIEnsureVisible(lineNo)
        self.SCIGotoLine(lineNo)
        return 0

    def SaveTextFile(self, filename, encoding=None):
        doc = self.GetDocument()
        doc._SaveTextToFile(self, filename, encoding=encoding)
        doc.SetModifiedFlag(0)
        return 1

    def _AutoComplete(self):
        self.SCIAutoCCancel()  # Cancel old auto-complete lists.
        # First try and get an object without evaluating calls
        ob = self._GetObjectAtPos(bAllowCalls=0)
        # If that failed, try and process call or indexing to get the object.
        if ob is None:
            ob = self._GetObjectAtPos(bAllowCalls=1)
        items_dict = {}
        if ob is not None:
            try:  # Catch unexpected errors when fetching attribute names from the object
                # extra attributes of win32ui objects
                if hasattr(ob, "_obj_"):
                    try:
                        items_dict.update(dict.fromkeys(dir(ob._obj_)))
                    except AttributeError:
                        pass  # object has no __dict__

                # normal attributes
                try:
                    items_dict.update(dict.fromkeys(dir(ob)))
                except AttributeError:
                    pass  # object has no __dict__
                if hasattr(ob, "__class__"):
                    items_dict.update(
                        dict.fromkeys(_get_class_attributes(ob.__class__))
                    )
                # The object may be a COM object with typelib support - let's see if we can get its props.
                # (contributed by Stefan Migowsky)
                try:
                    # Get the automation attributes
                    items_dict.update(ob.__class__._prop_map_get_)
                    # See if there is an write only property
                    # could be optimized
                    items_dict.update(ob.__class__._prop_map_put_)
                    # append to the already evaluated list
                except AttributeError:
                    pass
                # The object might be a pure COM dynamic dispatch with typelib support - let's see if we can get its props.
                if hasattr(ob, "_oleobj_"):
                    try:
                        for iTI in range(0, ob._oleobj_.GetTypeInfoCount()):
                            typeInfo = ob._oleobj_.GetTypeInfo(iTI)
                            self._UpdateWithITypeInfo(items_dict, typeInfo)
                    except:
                        pass
            except:
                win32ui.SetStatusText(
                    f"Error attempting to get object attributes - {sys.exc_info()[0]!r}"
                )

        items = [
            k
            for k in
            # ensure all keys are strings.
            map(str, items_dict)
            # All names that start with "_" go!
            if not k.startswith("_")
        ]

        if not items:
            # Heuristics a-la AutoExpand
            # The idea is to find other usages of the current binding
            # and assume, that it refers to the same object (or at least,
            # to an object of the same type)
            # Contributed by Vadim Chugunov [vadimch@yahoo.com]
            left, right = self._GetWordSplit()
            if left == "":  # Ignore standalone dots
                return None
            # We limit our search to the current class, if that
            # information is available
            minline, maxline, curclass = self._GetClassInfoFromBrowser()
            endpos = self.LineIndex(maxline)
            text = self.GetTextRange(self.LineIndex(minline), endpos)
            try:
                l = re.findall(r"\b" + left + r"\.\w+", text)
            except re.error:
                # parens etc may make an invalid RE, but this code wouldnt
                # benefit even if the RE did work :-)
                l = []
            prefix = len(left) + 1
            unique = {}
            for li in l:
                unique[li[prefix:]] = 1
            # Assuming traditional usage of self...
            if curclass and left == "self":
                self._UpdateWithClassMethods(unique, curclass)

            items = [word for word in unique if word[:2] != "__" or word[-2:] != "__"]
            # Ignore the word currently to the right of the dot - probably a red-herring.
            try:
                items.remove(right[1:])
            except ValueError:
                pass
        if items:
            items.sort()
            self.SCIAutoCSetAutoHide(0)
            self.SCIAutoCShow(items)

    def _UpdateWithITypeInfo(self, items_dict, typeInfo):
        import pythoncom

        typeInfos = [typeInfo]
        # suppress IDispatch and IUnknown methods
        inspectedIIDs = {pythoncom.IID_IDispatch: None}

        while len(typeInfos) > 0:
            typeInfo = typeInfos.pop()
            typeAttr = typeInfo.GetTypeAttr()

            if typeAttr.iid not in inspectedIIDs:
                inspectedIIDs[typeAttr.iid] = None
                for iFun in range(0, typeAttr.cFuncs):
                    funDesc = typeInfo.GetFuncDesc(iFun)
                    funName = typeInfo.GetNames(funDesc.memid)[0]
                    if funName not in items_dict:
                        items_dict[funName] = None

                # Inspect the type info of all implemented types
                # E.g. IShellDispatch5 implements IShellDispatch4 which implements IShellDispatch3 ...
                for iImplType in range(0, typeAttr.cImplTypes):
                    iRefType = typeInfo.GetRefTypeOfImplType(iImplType)
                    refTypeInfo = typeInfo.GetRefTypeInfo(iRefType)
                    typeInfos.append(refTypeInfo)

    # TODO: This is kinda slow. Probably need some kind of cache
    # here that is flushed upon file save
    # Or maybe we don't need the superclass methods at all ?
    def _UpdateWithClassMethods(self, dict, classinfo):
        if not hasattr(classinfo, "methods"):
            # No 'methods' - probably not what we think it is.
            return
        dict.update(classinfo.methods)
        for super in classinfo.super:
            if hasattr(super, "methods"):
                self._UpdateWithClassMethods(dict, super)

    # Find which class definition caret is currently in and return
    # indexes of the the first and the last lines of that class definition
    # Data is obtained from module browser (if enabled)
    def _GetClassInfoFromBrowser(self, pos=-1):
        minline = 0
        maxline = self.GetLineCount() - 1
        doc = self.GetParentFrame().GetActiveDocument()
        browser = None
        try:
            if doc is not None:
                browser = doc.GetAllViews()[1]
        except IndexError:
            pass
        if browser is None:
            return (minline, maxline, None)  # Current window has no browser
        if not browser.list:
            return (minline, maxline, None)  # Not initialized
        path = self.GetDocument().GetPathName()
        if not path:
            return (minline, maxline, None)  # No current path

        import pywin.framework.scriptutils

        curmodule, path = pywin.framework.scriptutils.GetPackageModuleName(path)
        try:
            clbrdata = browser.list.root.clbrdata
        except AttributeError:
            return (minline, maxline, None)  # No class data for this module.
        curline = self.LineFromChar(pos)
        curclass = None
        # Find out which class we are in
        for item in clbrdata.values():
            if item.module == curmodule:
                item_lineno = (
                    item.lineno - 1
                )  # Scintilla counts lines from 0, whereas pyclbr - from 1
                if minline < item_lineno <= curline:
                    minline = item_lineno
                    curclass = item
                if curline < item_lineno < maxline:
                    maxline = item_lineno
        return (minline, maxline, curclass)

    def _GetObjectAtPos(self, pos=-1, bAllowCalls=0):
        left, right = self._GetWordSplit(pos, bAllowCalls)
        if left:  # It is an attribute lookup
            # How is this for a hack!
            namespace = sys.modules.copy()
            namespace.update(__main__.__dict__)
            # Get the debugger's context.
            try:
                from pywin.framework import interact

                if interact.edit is not None and interact.edit.currentView is not None:
                    globs, locs = interact.edit.currentView.GetContext()[:2]
                    if globs:
                        namespace.update(globs)
                    if locs:
                        namespace.update(locs)
            except ImportError:
                pass
            try:
                return eval(left, namespace)
            except:
                pass
        return None

    def _GetWordSplit(self, pos=-1, bAllowCalls=0):
        if pos == -1:
            pos = self.GetSel()[0] - 1  # Character before current one
        limit = self.GetTextLength()
        before = []
        after = []
        index = pos - 1
        wordbreaks_use = wordbreaks
        if bAllowCalls:
            wordbreaks_use += "()[]"
        while index >= 0:
            char = self.SCIGetCharAt(index)
            if char not in wordbreaks_use:
                break
            before.insert(0, char)
            index -= 1
        index = pos
        while index <= limit:
            char = self.SCIGetCharAt(index)
            if char not in wordbreaks_use:
                break
            after.append(char)
            index += 1
        return "".join(before), "".join(after)

    def OnPrepareDC(self, dc, pInfo):
        # print(
        #     "OnPrepareDC for page",
        #     pInfo.GetCurPage(),
        #     "of",
        #     pInfo.GetFromPage(),
        #     "to",
        #     pInfo.GetToPage(),
        #     ", starts=",
        #     self.starts,
        # )
        if dc.IsPrinting():
            # Check if we are beyond the end.
            # (only do this when actually printing, else messes up print preview!)
            if not pInfo.GetPreview() and self.starts is not None:
                prevPage = pInfo.GetCurPage() - 1
                if prevPage > 0 and self.starts[prevPage] >= self.GetTextLength():
                    # All finished.
                    pInfo.SetContinuePrinting(0)
                    return
            dc.SetMapMode(win32con.MM_TEXT)

    def OnPreparePrinting(self, pInfo):
        flags = (
            win32ui.PD_USEDEVMODECOPIES | win32ui.PD_ALLPAGES | win32ui.PD_NOSELECTION
        )  # Don't support printing just a selection.
        # NOTE: Custom print dialogs are stopping the user's values from coming back :-(
        # 		self.prtDlg = PrintDialog(pInfo, PRINTDLGORD, flags)
        # 		pInfo.SetPrintDialog(self.prtDlg)
        pInfo.SetMinPage(1)
        # max page remains undefined for now.
        pInfo.SetFromPage(1)
        pInfo.SetToPage(1)
        ret = self.DoPreparePrinting(pInfo)
        return ret

    def OnBeginPrinting(self, dc, pInfo):
        self.starts = None
        return self._obj_.OnBeginPrinting(dc, pInfo)

    def CalculatePageRanges(self, dc, pInfo):
        # Calculate page ranges and max page
        self.starts = {0: 0}
        metrics = dc.GetTextMetrics()
        left, top, right, bottom = pInfo.GetDraw()
        # Leave space at the top for the header.
        rc = (left, top + int((9 * metrics["tmHeight"]) / 2), right, bottom)
        pageStart = 0
        maxPage = 0
        textLen = self.GetTextLength()
        while pageStart < textLen:
            pageStart = self.FormatRange(dc, pageStart, textLen, rc, 0)
            maxPage += 1
            self.starts[maxPage] = pageStart
        # And a sentinel for one page past the end
        self.starts[maxPage + 1] = textLen
        # When actually printing, maxPage doesn't have any effect at this late state.
        # but is needed to make the Print Preview work correctly.
        pInfo.SetMaxPage(maxPage)

    def OnFilePrintPreview(self, *arg):
        self._obj_.OnFilePrintPreview()

    def OnFilePrint(self, *arg):
        self._obj_.OnFilePrint()

    def FormatRange(self, dc, pageStart, lengthDoc, rc, draw):
        """
        typedef struct _formatrange {
                HDC hdc;
                HDC hdcTarget;
                RECT rc;
                RECT rcPage;
                CHARRANGE chrg;} FORMATRANGE;
        """
        fmt = "PPIIIIIIIIll"
        hdcRender = dc.GetHandleOutput()
        hdcFormat = dc.GetHandleAttrib()
        fr = struct.pack(
            fmt,
            hdcRender,
            hdcFormat,
            rc[0],
            rc[1],
            rc[2],
            rc[3],
            rc[0],
            rc[1],
            rc[2],
            rc[3],
            pageStart,
            lengthDoc,
        )
        nextPageStart = self.SendScintilla(EM_FORMATRANGE, draw, fr)
        return nextPageStart

    def OnPrint(self, dc, pInfo):
        metrics = dc.GetTextMetrics()
        # print("dev", w, h, l, metrics["tmAscent"], metrics["tmDescent"])
        if self.starts is None:
            self.CalculatePageRanges(dc, pInfo)
        pageNum = pInfo.GetCurPage() - 1
        # Setup the header of the page - docname on left, pagenum on right.
        doc = self.GetDocument()
        cxChar = metrics["tmAveCharWidth"]
        cyChar = metrics["tmHeight"]
        left, top, right, bottom = pInfo.GetDraw()
        dc.TextOut(0, 2 * cyChar, doc.GetTitle())
        pagenum_str = win32ui.LoadString(afxres.AFX_IDS_PRINTPAGENUM) % (pageNum + 1,)
        dc.SetTextAlign(win32con.TA_RIGHT)
        dc.TextOut(right, 2 * cyChar, pagenum_str)
        dc.SetTextAlign(win32con.TA_LEFT)
        top += int(7 * cyChar / 2)
        dc.MoveTo(left, top)
        dc.LineTo(right, top)
        top += cyChar
        rc = (left, top, right, bottom)
        nextPageStart = self.FormatRange(
            dc, self.starts[pageNum], self.starts[pageNum + 1], rc, 1
        )


def LoadConfiguration():
    global configManager
    # Bit of a hack I don't kow what to do about?
    from .config import ConfigManager

    configName = rc = win32ui.GetProfileVal("Editor", "Keyboard Config", "default")
    configManager = ConfigManager(configName)
    if configManager.last_error:
        bTryDefault = 0
        msg = "Error loading configuration '{}'\n\n{}".format(
            configName,
            configManager.last_error,
        )
        if configName != "default":
            msg += "\n\nThe default configuration will be loaded."
            bTryDefault = 1
        win32ui.MessageBox(msg)
        if bTryDefault:
            configManager = ConfigManager("default")
            if configManager.last_error:
                win32ui.MessageBox(
                    "Error loading configuration 'default'\n\n%s"
                    % (configManager.last_error)
                )


configManager = None
LoadConfiguration()

# === NexusCore/openenv\Lib\site-packages\click\_termui_impl.py ===
"""
This module contains implementations for the termui module. To keep the
import time of Click down, some infrequently used functionality is
placed in this module and only imported as needed.
"""

from __future__ import annotations

import collections.abc as cabc
import contextlib
import math
import os
import shlex
import sys
import time
import typing as t
from gettext import gettext as _
from io import StringIO
from pathlib import Path
from shutil import which
from types import TracebackType

from ._compat import _default_text_stdout
from ._compat import CYGWIN
from ._compat import get_best_encoding
from ._compat import isatty
from ._compat import open_stream
from ._compat import strip_ansi
from ._compat import term_len
from ._compat import WIN
from .exceptions import ClickException
from .utils import echo

V = t.TypeVar("V")

if os.name == "nt":
    BEFORE_BAR = "\r"
    AFTER_BAR = "\n"
else:
    BEFORE_BAR = "\r\033[?25l"
    AFTER_BAR = "\033[?25h\n"


class ProgressBar(t.Generic[V]):
    def __init__(
        self,
        iterable: cabc.Iterable[V] | None,
        length: int | None = None,
        fill_char: str = "#",
        empty_char: str = " ",
        bar_template: str = "%(bar)s",
        info_sep: str = "  ",
        hidden: bool = False,
        show_eta: bool = True,
        show_percent: bool | None = None,
        show_pos: bool = False,
        item_show_func: t.Callable[[V | None], str | None] | None = None,
        label: str | None = None,
        file: t.TextIO | None = None,
        color: bool | None = None,
        update_min_steps: int = 1,
        width: int = 30,
    ) -> None:
        self.fill_char = fill_char
        self.empty_char = empty_char
        self.bar_template = bar_template
        self.info_sep = info_sep
        self.hidden = hidden
        self.show_eta = show_eta
        self.show_percent = show_percent
        self.show_pos = show_pos
        self.item_show_func = item_show_func
        self.label: str = label or ""

        if file is None:
            file = _default_text_stdout()

            # There are no standard streams attached to write to. For example,
            # pythonw on Windows.
            if file is None:
                file = StringIO()

        self.file = file
        self.color = color
        self.update_min_steps = update_min_steps
        self._completed_intervals = 0
        self.width: int = width
        self.autowidth: bool = width == 0

        if length is None:
            from operator import length_hint

            length = length_hint(iterable, -1)

            if length == -1:
                length = None
        if iterable is None:
            if length is None:
                raise TypeError("iterable or length is required")
            iterable = t.cast("cabc.Iterable[V]", range(length))
        self.iter: cabc.Iterable[V] = iter(iterable)
        self.length = length
        self.pos: int = 0
        self.avg: list[float] = []
        self.last_eta: float
        self.start: float
        self.start = self.last_eta = time.time()
        self.eta_known: bool = False
        self.finished: bool = False
        self.max_width: int | None = None
        self.entered: bool = False
        self.current_item: V | None = None
        self._is_atty = isatty(self.file)
        self._last_line: str | None = None

    def __enter__(self) -> ProgressBar[V]:
        self.entered = True
        self.render_progress()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc_value: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.render_finish()

    def __iter__(self) -> cabc.Iterator[V]:
        if not self.entered:
            raise RuntimeError("You need to use progress bars in a with block.")
        self.render_progress()
        return self.generator()

    def __next__(self) -> V:
        # Iteration is defined in terms of a generator function,
        # returned by iter(self); use that to define next(). This works
        # because `self.iter` is an iterable consumed by that generator,
        # so it is re-entry safe. Calling `next(self.generator())`
        # twice works and does "what you want".
        return next(iter(self))

    def render_finish(self) -> None:
        if self.hidden or not self._is_atty:
            return
        self.file.write(AFTER_BAR)
        self.file.flush()

    @property
    def pct(self) -> float:
        if self.finished:
            return 1.0
        return min(self.pos / (float(self.length or 1) or 1), 1.0)

    @property
    def time_per_iteration(self) -> float:
        if not self.avg:
            return 0.0
        return sum(self.avg) / float(len(self.avg))

    @property
    def eta(self) -> float:
        if self.length is not None and not self.finished:
            return self.time_per_iteration * (self.length - self.pos)
        return 0.0

    def format_eta(self) -> str:
        if self.eta_known:
            t = int(self.eta)
            seconds = t % 60
            t //= 60
            minutes = t % 60
            t //= 60
            hours = t % 24
            t //= 24
            if t > 0:
                return f"{t}d {hours:02}:{minutes:02}:{seconds:02}"
            else:
                return f"{hours:02}:{minutes:02}:{seconds:02}"
        return ""

    def format_pos(self) -> str:
        pos = str(self.pos)
        if self.length is not None:
            pos += f"/{self.length}"
        return pos

    def format_pct(self) -> str:
        return f"{int(self.pct * 100): 4}%"[1:]

    def format_bar(self) -> str:
        if self.length is not None:
            bar_length = int(self.pct * self.width)
            bar = self.fill_char * bar_length
            bar += self.empty_char * (self.width - bar_length)
        elif self.finished:
            bar = self.fill_char * self.width
        else:
            chars = list(self.empty_char * (self.width or 1))
            if self.time_per_iteration != 0:
                chars[
                    int(
                        (math.cos(self.pos * self.time_per_iteration) / 2.0 + 0.5)
                        * self.width
                    )
                ] = self.fill_char
            bar = "".join(chars)
        return bar

    def format_progress_line(self) -> str:
        show_percent = self.show_percent

        info_bits = []
        if self.length is not None and show_percent is None:
            show_percent = not self.show_pos

        if self.show_pos:
            info_bits.append(self.format_pos())
        if show_percent:
            info_bits.append(self.format_pct())
        if self.show_eta and self.eta_known and not self.finished:
            info_bits.append(self.format_eta())
        if self.item_show_func is not None:
            item_info = self.item_show_func(self.current_item)
            if item_info is not None:
                info_bits.append(item_info)

        return (
            self.bar_template
            % {
                "label": self.label,
                "bar": self.format_bar(),
                "info": self.info_sep.join(info_bits),
            }
        ).rstrip()

    def render_progress(self) -> None:
        import shutil

        if self.hidden:
            return

        if not self._is_atty:
            # Only output the label once if the output is not a TTY.
            if self._last_line != self.label:
                self._last_line = self.label
                echo(self.label, file=self.file, color=self.color)
            return

        buf = []
        # Update width in case the terminal has been resized
        if self.autowidth:
            old_width = self.width
            self.width = 0
            clutter_length = term_len(self.format_progress_line())
            new_width = max(0, shutil.get_terminal_size().columns - clutter_length)
            if new_width < old_width and self.max_width is not None:
                buf.append(BEFORE_BAR)
                buf.append(" " * self.max_width)
                self.max_width = new_width
            self.width = new_width

        clear_width = self.width
        if self.max_width is not None:
            clear_width = self.max_width

        buf.append(BEFORE_BAR)
        line = self.format_progress_line()
        line_len = term_len(line)
        if self.max_width is None or self.max_width < line_len:
            self.max_width = line_len

        buf.append(line)
        buf.append(" " * (clear_width - line_len))
        line = "".join(buf)
        # Render the line only if it changed.

        if line != self._last_line:
            self._last_line = line
            echo(line, file=self.file, color=self.color, nl=False)
            self.file.flush()

    def make_step(self, n_steps: int) -> None:
        self.pos += n_steps
        if self.length is not None and self.pos >= self.length:
            self.finished = True

        if (time.time() - self.last_eta) < 1.0:
            return

        self.last_eta = time.time()

        # self.avg is a rolling list of length <= 7 of steps where steps are
        # defined as time elapsed divided by the total progress through
        # self.length.
        if self.pos:
            step = (time.time() - self.start) / self.pos
        else:
            step = time.time() - self.start

        self.avg = self.avg[-6:] + [step]

        self.eta_known = self.length is not None

    def update(self, n_steps: int, current_item: V | None = None) -> None:
        """Update the progress bar by advancing a specified number of
        steps, and optionally set the ``current_item`` for this new
        position.

        :param n_steps: Number of steps to advance.
        :param current_item: Optional item to set as ``current_item``
            for the updated position.

        .. versionchanged:: 8.0
            Added the ``current_item`` optional parameter.

        .. versionchanged:: 8.0
            Only render when the number of steps meets the
            ``update_min_steps`` threshold.
        """
        if current_item is not None:
            self.current_item = current_item

        self._completed_intervals += n_steps

        if self._completed_intervals >= self.update_min_steps:
            self.make_step(self._completed_intervals)
            self.render_progress()
            self._completed_intervals = 0

    def finish(self) -> None:
        self.eta_known = False
        self.current_item = None
        self.finished = True

    def generator(self) -> cabc.Iterator[V]:
        """Return a generator which yields the items added to the bar
        during construction, and updates the progress bar *after* the
        yielded block returns.
        """
        # WARNING: the iterator interface for `ProgressBar` relies on
        # this and only works because this is a simple generator which
        # doesn't create or manage additional state. If this function
        # changes, the impact should be evaluated both against
        # `iter(bar)` and `next(bar)`. `next()` in particular may call
        # `self.generator()` repeatedly, and this must remain safe in
        # order for that interface to work.
        if not self.entered:
            raise RuntimeError("You need to use progress bars in a with block.")

        if not self._is_atty:
            yield from self.iter
        else:
            for rv in self.iter:
                self.current_item = rv

                # This allows show_item_func to be updated before the
                # item is processed. Only trigger at the beginning of
                # the update interval.
                if self._completed_intervals == 0:
                    self.render_progress()

                yield rv
                self.update(1)

            self.finish()
            self.render_progress()


def pager(generator: cabc.Iterable[str], color: bool | None = None) -> None:
    """Decide what method to use for paging through text."""
    stdout = _default_text_stdout()

    # There are no standard streams attached to write to. For example,
    # pythonw on Windows.
    if stdout is None:
        stdout = StringIO()

    if not isatty(sys.stdin) or not isatty(stdout):
        return _nullpager(stdout, generator, color)

    # Split and normalize the pager command into parts.
    pager_cmd_parts = shlex.split(os.environ.get("PAGER", ""), posix=False)
    if pager_cmd_parts:
        if WIN:
            if _tempfilepager(generator, pager_cmd_parts, color):
                return
        elif _pipepager(generator, pager_cmd_parts, color):
            return

    if os.environ.get("TERM") in ("dumb", "emacs"):
        return _nullpager(stdout, generator, color)
    if (WIN or sys.platform.startswith("os2")) and _tempfilepager(
        generator, ["more"], color
    ):
        return
    if _pipepager(generator, ["less"], color):
        return

    import tempfile

    fd, filename = tempfile.mkstemp()
    os.close(fd)
    try:
        if _pipepager(generator, ["more"], color):
            return
        return _nullpager(stdout, generator, color)
    finally:
        os.unlink(filename)


def _pipepager(
    generator: cabc.Iterable[str], cmd_parts: list[str], color: bool | None
) -> bool:
    """Page through text by feeding it to another program. Invoking a
    pager through this might support colors.

    Returns `True` if the command was found, `False` otherwise and thus another
    pager should be attempted.
    """
    # Split the command into the invoked CLI and its parameters.
    if not cmd_parts:
        return False
    cmd = cmd_parts[0]
    cmd_params = cmd_parts[1:]

    cmd_filepath = which(cmd)
    if not cmd_filepath:
        return False
    # Resolves symlinks and produces a normalized absolute path string.
    cmd_path = Path(cmd_filepath).resolve()
    cmd_name = cmd_path.name

    import subprocess

    # Make a local copy of the environment to not affect the global one.
    env = dict(os.environ)

    # If we're piping to less and the user hasn't decided on colors, we enable
    # them by default we find the -R flag in the command line arguments.
    if color is None and cmd_name == "less":
        less_flags = f"{os.environ.get('LESS', '')}{' '.join(cmd_params)}"
        if not less_flags:
            env["LESS"] = "-R"
            color = True
        elif "r" in less_flags or "R" in less_flags:
            color = True

    c = subprocess.Popen(
        [str(cmd_path)] + cmd_params,
        shell=True,
        stdin=subprocess.PIPE,
        env=env,
        errors="replace",
        text=True,
    )
    assert c.stdin is not None
    try:
        for text in generator:
            if not color:
                text = strip_ansi(text)

            c.stdin.write(text)
    except BrokenPipeError:
        # In case the pager exited unexpectedly, ignore the broken pipe error.
        pass
    except Exception as e:
        # In case there is an exception we want to close the pager immediately
        # and let the caller handle it.
        # Otherwise the pager will keep running, and the user may not notice
        # the error message, or worse yet it may leave the terminal in a broken state.
        c.terminate()
        raise e
    finally:
        # We must close stdin and wait for the pager to exit before we continue
        try:
            c.stdin.close()
        # Close implies flush, so it might throw a BrokenPipeError if the pager
        # process exited already.
        except BrokenPipeError:
            pass

        # Less doesn't respect ^C, but catches it for its own UI purposes (aborting
        # search or other commands inside less).
        #
        # That means when the user hits ^C, the parent process (click) terminates,
        # but less is still alive, paging the output and messing up the terminal.
        #
        # If the user wants to make the pager exit on ^C, they should set
        # `LESS='-K'`. It's not our decision to make.
        while True:
            try:
                c.wait()
            except KeyboardInterrupt:
                pass
            else:
                break

    return True


def _tempfilepager(
    generator: cabc.Iterable[str], cmd_parts: list[str], color: bool | None
) -> bool:
    """Page through text by invoking a program on a temporary file.

    Returns `True` if the command was found, `False` otherwise and thus another
    pager should be attempted.
    """
    # Split the command into the invoked CLI and its parameters.
    if not cmd_parts:
        return False
    cmd = cmd_parts[0]

    cmd_filepath = which(cmd)
    if not cmd_filepath:
        return False
    # Resolves symlinks and produces a normalized absolute path string.
    cmd_path = Path(cmd_filepath).resolve()

    import subprocess
    import tempfile

    fd, filename = tempfile.mkstemp()
    # TODO: This never terminates if the passed generator never terminates.
    text = "".join(generator)
    if not color:
        text = strip_ansi(text)
    encoding = get_best_encoding(sys.stdout)
    with open_stream(filename, "wb")[0] as f:
        f.write(text.encode(encoding))
    try:
        subprocess.call([str(cmd_path), filename])
    except OSError:
        # Command not found
        pass
    finally:
        os.close(fd)
        os.unlink(filename)

    return True


def _nullpager(
    stream: t.TextIO, generator: cabc.Iterable[str], color: bool | None
) -> None:
    """Simply print unformatted text.  This is the ultimate fallback."""
    for text in generator:
        if not color:
            text = strip_ansi(text)
        stream.write(text)


class Editor:
    def __init__(
        self,
        editor: str | None = None,
        env: cabc.Mapping[str, str] | None = None,
        require_save: bool = True,
        extension: str = ".txt",
    ) -> None:
        self.editor = editor
        self.env = env
        self.require_save = require_save
        self.extension = extension

    def get_editor(self) -> str:
        if self.editor is not None:
            return self.editor
        for key in "VISUAL", "EDITOR":
            rv = os.environ.get(key)
            if rv:
                return rv
        if WIN:
            return "notepad"
        for editor in "sensible-editor", "vim", "nano":
            if which(editor) is not None:
                return editor
        return "vi"

    def edit_files(self, filenames: cabc.Iterable[str]) -> None:
        import subprocess

        editor = self.get_editor()
        environ: dict[str, str] | None = None

        if self.env:
            environ = os.environ.copy()
            environ.update(self.env)

        exc_filename = " ".join(f'"{filename}"' for filename in filenames)

        try:
            c = subprocess.Popen(
                args=f"{editor} {exc_filename}", env=environ, shell=True
            )
            exit_code = c.wait()
            if exit_code != 0:
                raise ClickException(
                    _("{editor}: Editing failed").format(editor=editor)
                )
        except OSError as e:
            raise ClickException(
                _("{editor}: Editing failed: {e}").format(editor=editor, e=e)
            ) from e

    @t.overload
    def edit(self, text: bytes | bytearray) -> bytes | None: ...

    # We cannot know whether or not the type expected is str or bytes when None
    # is passed, so str is returned as that was what was done before.
    @t.overload
    def edit(self, text: str | None) -> str | None: ...

    def edit(self, text: str | bytes | bytearray | None) -> str | bytes | None:
        import tempfile

        if text is None:
            data = b""
        elif isinstance(text, (bytes, bytearray)):
            data = text
        else:
            if text and not text.endswith("\n"):
                text += "\n"

            if WIN:
                data = text.replace("\n", "\r\n").encode("utf-8-sig")
            else:
                data = text.encode("utf-8")

        fd, name = tempfile.mkstemp(prefix="editor-", suffix=self.extension)
        f: t.BinaryIO

        try:
            with os.fdopen(fd, "wb") as f:
                f.write(data)

            # If the filesystem resolution is 1 second, like Mac OS
            # 10.12 Extended, or 2 seconds, like FAT32, and the editor
            # closes very fast, require_save can fail. Set the modified
            # time to be 2 seconds in the past to work around this.
            os.utime(name, (os.path.getatime(name), os.path.getmtime(name) - 2))
            # Depending on the resolution, the exact value might not be
            # recorded, so get the new recorded value.
            timestamp = os.path.getmtime(name)

            self.edit_files((name,))

            if self.require_save and os.path.getmtime(name) == timestamp:
                return None

            with open(name, "rb") as f:
                rv = f.read()

            if isinstance(text, (bytes, bytearray)):
                return rv

            return rv.decode("utf-8-sig").replace("\r\n", "\n")
        finally:
            os.unlink(name)


def open_url(url: str, wait: bool = False, locate: bool = False) -> int:
    import subprocess

    def _unquote_file(url: str) -> str:
        from urllib.parse import unquote

        if url.startswith("file://"):
            url = unquote(url[7:])

        return url

    if sys.platform == "darwin":
        args = ["open"]
        if wait:
            args.append("-W")
        if locate:
            args.append("-R")
        args.append(_unquote_file(url))
        null = open("/dev/null", "w")
        try:
            return subprocess.Popen(args, stderr=null).wait()
        finally:
            null.close()
    elif WIN:
        if locate:
            url = _unquote_file(url)
            args = ["explorer", f"/select,{url}"]
        else:
            args = ["start"]
            if wait:
                args.append("/WAIT")
            args.append("")
            args.append(url)
        try:
            return subprocess.call(args)
        except OSError:
            # Command not found
            return 127
    elif CYGWIN:
        if locate:
            url = _unquote_file(url)
            args = ["cygstart", os.path.dirname(url)]
        else:
            args = ["cygstart"]
            if wait:
                args.append("-w")
            args.append(url)
        try:
            return subprocess.call(args)
        except OSError:
            # Command not found
            return 127

    try:
        if locate:
            url = os.path.dirname(_unquote_file(url)) or "."
        else:
            url = _unquote_file(url)
        c = subprocess.Popen(["xdg-open", url])
        if wait:
            return c.wait()
        return 0
    except OSError:
        if url.startswith(("http://", "https://")) and not locate and not wait:
            import webbrowser

            webbrowser.open(url)
            return 0
        return 1


def _translate_ch_to_exc(ch: str) -> None:
    if ch == "\x03":
        raise KeyboardInterrupt()

    if ch == "\x04" and not WIN:  # Unix-like, Ctrl+D
        raise EOFError()

    if ch == "\x1a" and WIN:  # Windows, Ctrl+Z
        raise EOFError()

    return None


if sys.platform == "win32":
    import msvcrt

    @contextlib.contextmanager
    def raw_terminal() -> cabc.Iterator[int]:
        yield -1

    def getchar(echo: bool) -> str:
        # The function `getch` will return a bytes object corresponding to
        # the pressed character. Since Windows 10 build 1803, it will also
        # return \x00 when called a second time after pressing a regular key.
        #
        # `getwch` does not share this probably-bugged behavior. Moreover, it
        # returns a Unicode object by default, which is what we want.
        #
        # Either of these functions will return \x00 or \xe0 to indicate
        # a special key, and you need to call the same function again to get
        # the "rest" of the code. The fun part is that \u00e0 is
        # "latin small letter a with grave", so if you type that on a French
        # keyboard, you _also_ get a \xe0.
        # E.g., consider the Up arrow. This returns \xe0 and then \x48. The
        # resulting Unicode string reads as "a with grave" + "capital H".
        # This is indistinguishable from when the user actually types
        # "a with grave" and then "capital H".
        #
        # When \xe0 is returned, we assume it's part of a special-key sequence
        # and call `getwch` again, but that means that when the user types
        # the \u00e0 character, `getchar` doesn't return until a second
        # character is typed.
        # The alternative is returning immediately, but that would mess up
        # cross-platform handling of arrow keys and others that start with
        # \xe0. Another option is using `getch`, but then we can't reliably
        # read non-ASCII characters, because return values of `getch` are
        # limited to the current 8-bit codepage.
        #
        # Anyway, Click doesn't claim to do this Right(tm), and using `getwch`
        # is doing the right thing in more situations than with `getch`.

        if echo:
            func = t.cast(t.Callable[[], str], msvcrt.getwche)
        else:
            func = t.cast(t.Callable[[], str], msvcrt.getwch)

        rv = func()

        if rv in ("\x00", "\xe0"):
            # \x00 and \xe0 are control characters that indicate special key,
            # see above.
            rv += func()

        _translate_ch_to_exc(rv)
        return rv

else:
    import termios
    import tty

    @contextlib.contextmanager
    def raw_terminal() -> cabc.Iterator[int]:
        f: t.TextIO | None
        fd: int

        if not isatty(sys.stdin):
            f = open("/dev/tty")
            fd = f.fileno()
        else:
            fd = sys.stdin.fileno()
            f = None

        try:
            old_settings = termios.tcgetattr(fd)

            try:
                tty.setraw(fd)
                yield fd
            finally:
                termios.tcsetattr(fd, termios.TCSADRAIN, old_settings)
                sys.stdout.flush()

                if f is not None:
                    f.close()
        except termios.error:
            pass

    def getchar(echo: bool) -> str:
        with raw_terminal() as fd:
            ch = os.read(fd, 32).decode(get_best_encoding(sys.stdin), "replace")

            if echo and isatty(sys.stdout):
                sys.stdout.write(ch)

            _translate_ch_to_exc(ch)
            return ch

# === NexusCore/openenv\Lib\site-packages\starlette\testclient.py ===
from __future__ import annotations

import contextlib
import inspect
import io
import json
import math
import queue
import sys
import typing
import warnings
from concurrent.futures import Future
from functools import cached_property
from types import GeneratorType
from urllib.parse import unquote, urljoin

import anyio
import anyio.abc
import anyio.from_thread
from anyio.abc import ObjectReceiveStream, ObjectSendStream
from anyio.streams.stapled import StapledObjectStream

from starlette._utils import is_async_callable
from starlette.types import ASGIApp, Message, Receive, Scope, Send
from starlette.websockets import WebSocketDisconnect

if sys.version_info >= (3, 10):  # pragma: no cover
    from typing import TypeGuard
else:  # pragma: no cover
    from typing_extensions import TypeGuard

try:
    import httpx
except ModuleNotFoundError:  # pragma: no cover
    raise RuntimeError(
        "The starlette.testclient module requires the httpx package to be installed.\n"
        "You can install this with:\n"
        "    $ pip install httpx\n"
    )
_PortalFactoryType = typing.Callable[
    [], typing.ContextManager[anyio.abc.BlockingPortal]
]

ASGIInstance = typing.Callable[[Receive, Send], typing.Awaitable[None]]
ASGI2App = typing.Callable[[Scope], ASGIInstance]
ASGI3App = typing.Callable[[Scope, Receive, Send], typing.Awaitable[None]]


_RequestData = typing.Mapping[str, typing.Union[str, typing.Iterable[str], bytes]]


def _is_asgi3(app: ASGI2App | ASGI3App) -> TypeGuard[ASGI3App]:
    if inspect.isclass(app):
        return hasattr(app, "__await__")
    return is_async_callable(app)


class _WrapASGI2:
    """
    Provide an ASGI3 interface onto an ASGI2 app.
    """

    def __init__(self, app: ASGI2App) -> None:
        self.app = app

    async def __call__(self, scope: Scope, receive: Receive, send: Send) -> None:
        instance = self.app(scope)
        await instance(receive, send)


class _AsyncBackend(typing.TypedDict):
    backend: str
    backend_options: dict[str, typing.Any]


class _Upgrade(Exception):
    def __init__(self, session: WebSocketTestSession) -> None:
        self.session = session


class WebSocketDenialResponse(  # type: ignore[misc]
    httpx.Response,
    WebSocketDisconnect,
):
    """
    A special case of `WebSocketDisconnect`, raised in the `TestClient` if the
    `WebSocket` is closed before being accepted with a `send_denial_response()`.
    """


class WebSocketTestSession:
    def __init__(
        self,
        app: ASGI3App,
        scope: Scope,
        portal_factory: _PortalFactoryType,
    ) -> None:
        self.app = app
        self.scope = scope
        self.accepted_subprotocol = None
        self.portal_factory = portal_factory
        self._receive_queue: queue.Queue[Message] = queue.Queue()
        self._send_queue: queue.Queue[Message | BaseException] = queue.Queue()
        self.extra_headers = None

    def __enter__(self) -> WebSocketTestSession:
        self.exit_stack = contextlib.ExitStack()
        self.portal = self.exit_stack.enter_context(self.portal_factory())

        try:
            _: Future[None] = self.portal.start_task_soon(self._run)
            self.send({"type": "websocket.connect"})
            message = self.receive()
            self._raise_on_close(message)
        except Exception:
            self.exit_stack.close()
            raise
        self.accepted_subprotocol = message.get("subprotocol", None)
        self.extra_headers = message.get("headers", None)
        return self

    @cached_property
    def should_close(self) -> anyio.Event:
        return anyio.Event()

    async def _notify_close(self) -> None:
        self.should_close.set()

    def __exit__(self, *args: typing.Any) -> None:
        try:
            self.close(1000)
        finally:
            self.portal.start_task_soon(self._notify_close)
            self.exit_stack.close()
        while not self._send_queue.empty():
            message = self._send_queue.get()
            if isinstance(message, BaseException):
                raise message

    async def _run(self) -> None:
        """
        The sub-thread in which the websocket session runs.
        """

        async def run_app(tg: anyio.abc.TaskGroup) -> None:
            try:
                await self.app(self.scope, self._asgi_receive, self._asgi_send)
            except anyio.get_cancelled_exc_class():
                ...
            except BaseException as exc:
                self._send_queue.put(exc)
                raise
            finally:
                tg.cancel_scope.cancel()

        async with anyio.create_task_group() as tg:
            tg.start_soon(run_app, tg)
            await self.should_close.wait()
            tg.cancel_scope.cancel()

    async def _asgi_receive(self) -> Message:
        while self._receive_queue.empty():
            await anyio.sleep(0)
        return self._receive_queue.get()

    async def _asgi_send(self, message: Message) -> None:
        self._send_queue.put(message)

    def _raise_on_close(self, message: Message) -> None:
        if message["type"] == "websocket.close":
            raise WebSocketDisconnect(
                code=message.get("code", 1000), reason=message.get("reason", "")
            )
        elif message["type"] == "websocket.http.response.start":
            status_code: int = message["status"]
            headers: list[tuple[bytes, bytes]] = message["headers"]
            body: list[bytes] = []
            while True:
                message = self.receive()
                assert message["type"] == "websocket.http.response.body"
                body.append(message["body"])
                if not message.get("more_body", False):
                    break
            raise WebSocketDenialResponse(
                status_code=status_code,
                headers=headers,
                content=b"".join(body),
            )

    def send(self, message: Message) -> None:
        self._receive_queue.put(message)

    def send_text(self, data: str) -> None:
        self.send({"type": "websocket.receive", "text": data})

    def send_bytes(self, data: bytes) -> None:
        self.send({"type": "websocket.receive", "bytes": data})

    def send_json(
        self, data: typing.Any, mode: typing.Literal["text", "binary"] = "text"
    ) -> None:
        text = json.dumps(data, separators=(",", ":"), ensure_ascii=False)
        if mode == "text":
            self.send({"type": "websocket.receive", "text": text})
        else:
            self.send({"type": "websocket.receive", "bytes": text.encode("utf-8")})

    def close(self, code: int = 1000, reason: str | None = None) -> None:
        self.send({"type": "websocket.disconnect", "code": code, "reason": reason})

    def receive(self) -> Message:
        message = self._send_queue.get()
        if isinstance(message, BaseException):
            raise message
        return message

    def receive_text(self) -> str:
        message = self.receive()
        self._raise_on_close(message)
        return typing.cast(str, message["text"])

    def receive_bytes(self) -> bytes:
        message = self.receive()
        self._raise_on_close(message)
        return typing.cast(bytes, message["bytes"])

    def receive_json(
        self, mode: typing.Literal["text", "binary"] = "text"
    ) -> typing.Any:
        message = self.receive()
        self._raise_on_close(message)
        if mode == "text":
            text = message["text"]
        else:
            text = message["bytes"].decode("utf-8")
        return json.loads(text)


class _TestClientTransport(httpx.BaseTransport):
    def __init__(
        self,
        app: ASGI3App,
        portal_factory: _PortalFactoryType,
        raise_server_exceptions: bool = True,
        root_path: str = "",
        *,
        app_state: dict[str, typing.Any],
    ) -> None:
        self.app = app
        self.raise_server_exceptions = raise_server_exceptions
        self.root_path = root_path
        self.portal_factory = portal_factory
        self.app_state = app_state

    def handle_request(self, request: httpx.Request) -> httpx.Response:
        scheme = request.url.scheme
        netloc = request.url.netloc.decode(encoding="ascii")
        path = request.url.path
        raw_path = request.url.raw_path
        query = request.url.query.decode(encoding="ascii")

        default_port = {"http": 80, "ws": 80, "https": 443, "wss": 443}[scheme]

        if ":" in netloc:
            host, port_string = netloc.split(":", 1)
            port = int(port_string)
        else:
            host = netloc
            port = default_port

        # Include the 'host' header.
        if "host" in request.headers:
            headers: list[tuple[bytes, bytes]] = []
        elif port == default_port:  # pragma: no cover
            headers = [(b"host", host.encode())]
        else:  # pragma: no cover
            headers = [(b"host", (f"{host}:{port}").encode())]

        # Include other request headers.
        headers += [
            (key.lower().encode(), value.encode())
            for key, value in request.headers.multi_items()
        ]

        scope: dict[str, typing.Any]

        if scheme in {"ws", "wss"}:
            subprotocol = request.headers.get("sec-websocket-protocol", None)
            if subprotocol is None:
                subprotocols: typing.Sequence[str] = []
            else:
                subprotocols = [value.strip() for value in subprotocol.split(",")]
            scope = {
                "type": "websocket",
                "path": unquote(path),
                "raw_path": raw_path,
                "root_path": self.root_path,
                "scheme": scheme,
                "query_string": query.encode(),
                "headers": headers,
                "client": ["testclient", 50000],
                "server": [host, port],
                "subprotocols": subprotocols,
                "state": self.app_state.copy(),
                "extensions": {"websocket.http.response": {}},
            }
            session = WebSocketTestSession(self.app, scope, self.portal_factory)
            raise _Upgrade(session)

        scope = {
            "type": "http",
            "http_version": "1.1",
            "method": request.method,
            "path": unquote(path),
            "raw_path": raw_path,
            "root_path": self.root_path,
            "scheme": scheme,
            "query_string": query.encode(),
            "headers": headers,
            "client": ["testclient", 50000],
            "server": [host, port],
            "extensions": {"http.response.debug": {}},
            "state": self.app_state.copy(),
        }

        request_complete = False
        response_started = False
        response_complete: anyio.Event
        raw_kwargs: dict[str, typing.Any] = {"stream": io.BytesIO()}
        template = None
        context = None

        async def receive() -> Message:
            nonlocal request_complete

            if request_complete:
                if not response_complete.is_set():
                    await response_complete.wait()
                return {"type": "http.disconnect"}

            body = request.read()
            if isinstance(body, str):
                body_bytes: bytes = body.encode("utf-8")  # pragma: no cover
            elif body is None:
                body_bytes = b""  # pragma: no cover
            elif isinstance(body, GeneratorType):
                try:  # pragma: no cover
                    chunk = body.send(None)
                    if isinstance(chunk, str):
                        chunk = chunk.encode("utf-8")
                    return {"type": "http.request", "body": chunk, "more_body": True}
                except StopIteration:  # pragma: no cover
                    request_complete = True
                    return {"type": "http.request", "body": b""}
            else:
                body_bytes = body

            request_complete = True
            return {"type": "http.request", "body": body_bytes}

        async def send(message: Message) -> None:
            nonlocal raw_kwargs, response_started, template, context

            if message["type"] == "http.response.start":
                assert (
                    not response_started
                ), 'Received multiple "http.response.start" messages.'
                raw_kwargs["status_code"] = message["status"]
                raw_kwargs["headers"] = [
                    (key.decode(), value.decode())
                    for key, value in message.get("headers", [])
                ]
                response_started = True
            elif message["type"] == "http.response.body":
                assert (
                    response_started
                ), 'Received "http.response.body" without "http.response.start".'
                assert (
                    not response_complete.is_set()
                ), 'Received "http.response.body" after response completed.'
                body = message.get("body", b"")
                more_body = message.get("more_body", False)
                if request.method != "HEAD":
                    raw_kwargs["stream"].write(body)
                if not more_body:
                    raw_kwargs["stream"].seek(0)
                    response_complete.set()
            elif message["type"] == "http.response.debug":
                template = message["info"]["template"]
                context = message["info"]["context"]

        try:
            with self.portal_factory() as portal:
                response_complete = portal.call(anyio.Event)
                portal.call(self.app, scope, receive, send)
        except BaseException as exc:
            if self.raise_server_exceptions:
                raise exc

        if self.raise_server_exceptions:
            assert response_started, "TestClient did not receive any response."
        elif not response_started:
            raw_kwargs = {
                "status_code": 500,
                "headers": [],
                "stream": io.BytesIO(),
            }

        raw_kwargs["stream"] = httpx.ByteStream(raw_kwargs["stream"].read())

        response = httpx.Response(**raw_kwargs, request=request)
        if template is not None:
            response.template = template  # type: ignore[attr-defined]
            response.context = context  # type: ignore[attr-defined]
        return response


class TestClient(httpx.Client):
    __test__ = False
    task: Future[None]
    portal: anyio.abc.BlockingPortal | None = None

    def __init__(
        self,
        app: ASGIApp,
        base_url: str = "http://testserver",
        raise_server_exceptions: bool = True,
        root_path: str = "",
        backend: typing.Literal["asyncio", "trio"] = "asyncio",
        backend_options: dict[str, typing.Any] | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        headers: dict[str, str] | None = None,
        follow_redirects: bool = True,
    ) -> None:
        self.async_backend = _AsyncBackend(
            backend=backend, backend_options=backend_options or {}
        )
        if _is_asgi3(app):
            asgi_app = app
        else:
            app = typing.cast(ASGI2App, app)  # type: ignore[assignment]
            asgi_app = _WrapASGI2(app)  # type: ignore[arg-type]
        self.app = asgi_app
        self.app_state: dict[str, typing.Any] = {}
        transport = _TestClientTransport(
            self.app,
            portal_factory=self._portal_factory,
            raise_server_exceptions=raise_server_exceptions,
            root_path=root_path,
            app_state=self.app_state,
        )
        if headers is None:
            headers = {}
        headers.setdefault("user-agent", "testclient")
        super().__init__(
            base_url=base_url,
            headers=headers,
            transport=transport,
            follow_redirects=follow_redirects,
            cookies=cookies,
        )

    @contextlib.contextmanager
    def _portal_factory(self) -> typing.Generator[anyio.abc.BlockingPortal, None, None]:
        if self.portal is not None:
            yield self.portal
        else:
            with anyio.from_thread.start_blocking_portal(
                **self.async_backend
            ) as portal:
                yield portal

    def _choose_redirect_arg(
        self, follow_redirects: bool | None, allow_redirects: bool | None
    ) -> bool | httpx._client.UseClientDefault:
        redirect: bool | httpx._client.UseClientDefault = (
            httpx._client.USE_CLIENT_DEFAULT
        )
        if allow_redirects is not None:
            message = (
                "The `allow_redirects` argument is deprecated. "
                "Use `follow_redirects` instead."
            )
            warnings.warn(message, DeprecationWarning)
            redirect = allow_redirects
        if follow_redirects is not None:
            redirect = follow_redirects
        elif allow_redirects is not None and follow_redirects is not None:
            raise RuntimeError(  # pragma: no cover
                "Cannot use both `allow_redirects` and `follow_redirects`."
            )
        return redirect

    def request(  # type: ignore[override]
        self,
        method: str,
        url: httpx._types.URLTypes,
        *,
        content: httpx._types.RequestContent | None = None,
        data: _RequestData | None = None,
        files: httpx._types.RequestFiles | None = None,
        json: typing.Any = None,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        url = self._merge_url(url)
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().request(
            method,
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def get(  # type: ignore[override]
        self,
        url: httpx._types.URLTypes,
        *,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().get(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def options(  # type: ignore[override]
        self,
        url: httpx._types.URLTypes,
        *,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().options(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def head(  # type: ignore[override]
        self,
        url: httpx._types.URLTypes,
        *,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().head(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def post(  # type: ignore[override]
        self,
        url: httpx._types.URLTypes,
        *,
        content: httpx._types.RequestContent | None = None,
        data: _RequestData | None = None,
        files: httpx._types.RequestFiles | None = None,
        json: typing.Any = None,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().post(
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def put(  # type: ignore[override]
        self,
        url: httpx._types.URLTypes,
        *,
        content: httpx._types.RequestContent | None = None,
        data: _RequestData | None = None,
        files: httpx._types.RequestFiles | None = None,
        json: typing.Any = None,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().put(
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def patch(  # type: ignore[override]
        self,
        url: httpx._types.URLTypes,
        *,
        content: httpx._types.RequestContent | None = None,
        data: _RequestData | None = None,
        files: httpx._types.RequestFiles | None = None,
        json: typing.Any = None,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().patch(
            url,
            content=content,
            data=data,
            files=files,
            json=json,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def delete(  # type: ignore[override]
        self,
        url: httpx._types.URLTypes,
        *,
        params: httpx._types.QueryParamTypes | None = None,
        headers: httpx._types.HeaderTypes | None = None,
        cookies: httpx._types.CookieTypes | None = None,
        auth: httpx._types.AuthTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        follow_redirects: bool | None = None,
        allow_redirects: bool | None = None,
        timeout: httpx._types.TimeoutTypes
        | httpx._client.UseClientDefault = httpx._client.USE_CLIENT_DEFAULT,
        extensions: dict[str, typing.Any] | None = None,
    ) -> httpx.Response:
        redirect = self._choose_redirect_arg(follow_redirects, allow_redirects)
        return super().delete(
            url,
            params=params,
            headers=headers,
            cookies=cookies,
            auth=auth,
            follow_redirects=redirect,
            timeout=timeout,
            extensions=extensions,
        )

    def websocket_connect(
        self,
        url: str,
        subprotocols: typing.Sequence[str] | None = None,
        **kwargs: typing.Any,
    ) -> WebSocketTestSession:
        url = urljoin("ws://testserver", url)
        headers = kwargs.get("headers", {})
        headers.setdefault("connection", "upgrade")
        headers.setdefault("sec-websocket-key", "testserver==")
        headers.setdefault("sec-websocket-version", "13")
        if subprotocols is not None:
            headers.setdefault("sec-websocket-protocol", ", ".join(subprotocols))
        kwargs["headers"] = headers
        try:
            super().request("GET", url, **kwargs)
        except _Upgrade as exc:
            session = exc.session
        else:
            raise RuntimeError("Expected WebSocket upgrade")  # pragma: no cover

        return session

    def __enter__(self) -> TestClient:
        with contextlib.ExitStack() as stack:
            self.portal = portal = stack.enter_context(
                anyio.from_thread.start_blocking_portal(**self.async_backend)
            )

            @stack.callback
            def reset_portal() -> None:
                self.portal = None

            send1: ObjectSendStream[typing.MutableMapping[str, typing.Any] | None]
            receive1: ObjectReceiveStream[typing.MutableMapping[str, typing.Any] | None]
            send2: ObjectSendStream[typing.MutableMapping[str, typing.Any]]
            receive2: ObjectReceiveStream[typing.MutableMapping[str, typing.Any]]
            send1, receive1 = anyio.create_memory_object_stream(math.inf)
            send2, receive2 = anyio.create_memory_object_stream(math.inf)
            self.stream_send = StapledObjectStream(send1, receive1)
            self.stream_receive = StapledObjectStream(send2, receive2)
            self.task = portal.start_task_soon(self.lifespan)
            portal.call(self.wait_startup)

            @stack.callback
            def wait_shutdown() -> None:
                portal.call(self.wait_shutdown)

            self.exit_stack = stack.pop_all()

        return self

    def __exit__(self, *args: typing.Any) -> None:
        self.exit_stack.close()

    async def lifespan(self) -> None:
        scope = {"type": "lifespan", "state": self.app_state}
        try:
            await self.app(scope, self.stream_receive.receive, self.stream_send.send)
        finally:
            await self.stream_send.send(None)

    async def wait_startup(self) -> None:
        await self.stream_receive.send({"type": "lifespan.startup"})

        async def receive() -> typing.Any:
            message = await self.stream_send.receive()
            if message is None:
                self.task.result()
            return message

        message = await receive()
        assert message["type"] in (
            "lifespan.startup.complete",
            "lifespan.startup.failed",
        )
        if message["type"] == "lifespan.startup.failed":
            await receive()

    async def wait_shutdown(self) -> None:
        async def receive() -> typing.Any:
            message = await self.stream_send.receive()
            if message is None:
                self.task.result()
            return message

        async with self.stream_send:
            await self.stream_receive.send({"type": "lifespan.shutdown"})
            message = await receive()
            assert message["type"] in (
                "lifespan.shutdown.complete",
                "lifespan.shutdown.failed",
            )
            if message["type"] == "lifespan.shutdown.failed":
                await receive()

# === NexusCore/openenv\Lib\site-packages\debugpy\_vendored\pydevd\pydevd_attach_to_process\winappdbg\win32\shlwapi.py ===
#!/usr/bin/env python
# -*- coding: utf-8 -*-

# Copyright (c) 2009-2014, Mario Vilas
# All rights reserved.
#
# Redistribution and use in source and binary forms, with or without
# modification, are permitted provided that the following conditions are met:
#
#     * Redistributions of source code must retain the above copyright notice,
#       this list of conditions and the following disclaimer.
#     * Redistributions in binary form must reproduce the above copyright
#       notice,this list of conditions and the following disclaimer in the
#       documentation and/or other materials provided with the distribution.
#     * Neither the name of the copyright holder nor the names of its
#       contributors may be used to endorse or promote products derived from
#       this software without specific prior written permission.
#
# THIS SOFTWARE IS PROVIDED BY THE COPYRIGHT HOLDERS AND CONTRIBUTORS "AS IS"
# AND ANY EXPRESS OR IMPLIED WARRANTIES, INCLUDING, BUT NOT LIMITED TO, THE
# IMPLIED WARRANTIES OF MERCHANTABILITY AND FITNESS FOR A PARTICULAR PURPOSE
# ARE DISCLAIMED. IN NO EVENT SHALL THE COPYRIGHT OWNER OR CONTRIBUTORS BE
# LIABLE FOR ANY DIRECT, INDIRECT, INCIDENTAL, SPECIAL, EXEMPLARY, OR
# CONSEQUENTIAL DAMAGES (INCLUDING, BUT NOT LIMITED TO, PROCUREMENT OF
# SUBSTITUTE GOODS OR SERVICES; LOSS OF USE, DATA, OR PROFITS; OR BUSINESS
# INTERRUPTION) HOWEVER CAUSED AND ON ANY THEORY OF LIABILITY, WHETHER IN
# CONTRACT, STRICT LIABILITY, OR TORT (INCLUDING NEGLIGENCE OR OTHERWISE)
# ARISING IN ANY WAY OUT OF THE USE OF THIS SOFTWARE, EVEN IF ADVISED OF THE
# POSSIBILITY OF SUCH DAMAGE.

"""
Wrapper for shlwapi.dll in ctypes.
"""

__revision__ = "$Id$"

from winappdbg.win32.defines import *
from winappdbg.win32.kernel32 import *

# ==============================================================================
# This is used later on to calculate the list of exported symbols.
_all = None
_all = set(vars().keys())
# ==============================================================================

OS_WINDOWS = 0
OS_NT = 1
OS_WIN95ORGREATER = 2
OS_NT4ORGREATER = 3
OS_WIN98ORGREATER = 5
OS_WIN98_GOLD = 6
OS_WIN2000ORGREATER = 7
OS_WIN2000PRO = 8
OS_WIN2000SERVER = 9
OS_WIN2000ADVSERVER = 10
OS_WIN2000DATACENTER = 11
OS_WIN2000TERMINAL = 12
OS_EMBEDDED = 13
OS_TERMINALCLIENT = 14
OS_TERMINALREMOTEADMIN = 15
OS_WIN95_GOLD = 16
OS_MEORGREATER = 17
OS_XPORGREATER = 18
OS_HOME = 19
OS_PROFESSIONAL = 20
OS_DATACENTER = 21
OS_ADVSERVER = 22
OS_SERVER = 23
OS_TERMINALSERVER = 24
OS_PERSONALTERMINALSERVER = 25
OS_FASTUSERSWITCHING = 26
OS_WELCOMELOGONUI = 27
OS_DOMAINMEMBER = 28
OS_ANYSERVER = 29
OS_WOW6432 = 30
OS_WEBSERVER = 31
OS_SMALLBUSINESSSERVER = 32
OS_TABLETPC = 33
OS_SERVERADMINUI = 34
OS_MEDIACENTER = 35
OS_APPLIANCE = 36

# --- shlwapi.dll --------------------------------------------------------------


# BOOL IsOS(
#     DWORD dwOS
# );
def IsOS(dwOS):
    try:
        _IsOS = windll.shlwapi.IsOS
        _IsOS.argtypes = [DWORD]
        _IsOS.restype = bool
    except AttributeError:
        # According to MSDN, on Windows versions prior to Vista
        # this function is exported only by ordinal number 437.
        # http://msdn.microsoft.com/en-us/library/bb773795%28VS.85%29.aspx
        _GetProcAddress = windll.kernel32.GetProcAddress
        _GetProcAddress.argtypes = [HINSTANCE, DWORD]
        _GetProcAddress.restype = LPVOID
        _IsOS = windll.kernel32.GetProcAddress(windll.shlwapi._handle, 437)
        _IsOS = WINFUNCTYPE(bool, DWORD)(_IsOS)
    return _IsOS(dwOS)


# LPTSTR PathAddBackslash(
#     LPTSTR lpszPath
# );
def PathAddBackslashA(lpszPath):
    _PathAddBackslashA = windll.shlwapi.PathAddBackslashA
    _PathAddBackslashA.argtypes = [LPSTR]
    _PathAddBackslashA.restype = LPSTR

    lpszPath = ctypes.create_string_buffer(lpszPath, MAX_PATH)
    retval = _PathAddBackslashA(lpszPath)
    if retval == NULL:
        raise ctypes.WinError()
    return lpszPath.value


def PathAddBackslashW(lpszPath):
    _PathAddBackslashW = windll.shlwapi.PathAddBackslashW
    _PathAddBackslashW.argtypes = [LPWSTR]
    _PathAddBackslashW.restype = LPWSTR

    lpszPath = ctypes.create_unicode_buffer(lpszPath, MAX_PATH)
    retval = _PathAddBackslashW(lpszPath)
    if retval == NULL:
        raise ctypes.WinError()
    return lpszPath.value


PathAddBackslash = GuessStringType(PathAddBackslashA, PathAddBackslashW)


# BOOL PathAddExtension(
#     LPTSTR pszPath,
#     LPCTSTR pszExtension
# );
def PathAddExtensionA(lpszPath, pszExtension=None):
    _PathAddExtensionA = windll.shlwapi.PathAddExtensionA
    _PathAddExtensionA.argtypes = [LPSTR, LPSTR]
    _PathAddExtensionA.restype = bool
    _PathAddExtensionA.errcheck = RaiseIfZero

    if not pszExtension:
        pszExtension = None
    lpszPath = ctypes.create_string_buffer(lpszPath, MAX_PATH)
    _PathAddExtensionA(lpszPath, pszExtension)
    return lpszPath.value


def PathAddExtensionW(lpszPath, pszExtension=None):
    _PathAddExtensionW = windll.shlwapi.PathAddExtensionW
    _PathAddExtensionW.argtypes = [LPWSTR, LPWSTR]
    _PathAddExtensionW.restype = bool
    _PathAddExtensionW.errcheck = RaiseIfZero

    if not pszExtension:
        pszExtension = None
    lpszPath = ctypes.create_unicode_buffer(lpszPath, MAX_PATH)
    _PathAddExtensionW(lpszPath, pszExtension)
    return lpszPath.value


PathAddExtension = GuessStringType(PathAddExtensionA, PathAddExtensionW)


# BOOL PathAppend(
#     LPTSTR pszPath,
#     LPCTSTR pszMore
# );
def PathAppendA(lpszPath, pszMore=None):
    _PathAppendA = windll.shlwapi.PathAppendA
    _PathAppendA.argtypes = [LPSTR, LPSTR]
    _PathAppendA.restype = bool
    _PathAppendA.errcheck = RaiseIfZero

    if not pszMore:
        pszMore = None
    lpszPath = ctypes.create_string_buffer(lpszPath, MAX_PATH)
    _PathAppendA(lpszPath, pszMore)
    return lpszPath.value


def PathAppendW(lpszPath, pszMore=None):
    _PathAppendW = windll.shlwapi.PathAppendW
    _PathAppendW.argtypes = [LPWSTR, LPWSTR]
    _PathAppendW.restype = bool
    _PathAppendW.errcheck = RaiseIfZero

    if not pszMore:
        pszMore = None
    lpszPath = ctypes.create_unicode_buffer(lpszPath, MAX_PATH)
    _PathAppendW(lpszPath, pszMore)
    return lpszPath.value


PathAppend = GuessStringType(PathAppendA, PathAppendW)


# LPTSTR PathCombine(
#     LPTSTR lpszDest,
#     LPCTSTR lpszDir,
#     LPCTSTR lpszFile
# );
def PathCombineA(lpszDir, lpszFile):
    _PathCombineA = windll.shlwapi.PathCombineA
    _PathCombineA.argtypes = [LPSTR, LPSTR, LPSTR]
    _PathCombineA.restype = LPSTR

    lpszDest = ctypes.create_string_buffer("", max(MAX_PATH, len(lpszDir) + len(lpszFile) + 1))
    retval = _PathCombineA(lpszDest, lpszDir, lpszFile)
    if retval == NULL:
        return None
    return lpszDest.value


def PathCombineW(lpszDir, lpszFile):
    _PathCombineW = windll.shlwapi.PathCombineW
    _PathCombineW.argtypes = [LPWSTR, LPWSTR, LPWSTR]
    _PathCombineW.restype = LPWSTR

    lpszDest = ctypes.create_unicode_buffer("", max(MAX_PATH, len(lpszDir) + len(lpszFile) + 1))
    retval = _PathCombineW(lpszDest, lpszDir, lpszFile)
    if retval == NULL:
        return None
    return lpszDest.value


PathCombine = GuessStringType(PathCombineA, PathCombineW)


# BOOL PathCanonicalize(
#     LPTSTR lpszDst,
#     LPCTSTR lpszSrc
# );
def PathCanonicalizeA(lpszSrc):
    _PathCanonicalizeA = windll.shlwapi.PathCanonicalizeA
    _PathCanonicalizeA.argtypes = [LPSTR, LPSTR]
    _PathCanonicalizeA.restype = bool
    _PathCanonicalizeA.errcheck = RaiseIfZero

    lpszDst = ctypes.create_string_buffer("", MAX_PATH)
    _PathCanonicalizeA(lpszDst, lpszSrc)
    return lpszDst.value


def PathCanonicalizeW(lpszSrc):
    _PathCanonicalizeW = windll.shlwapi.PathCanonicalizeW
    _PathCanonicalizeW.argtypes = [LPWSTR, LPWSTR]
    _PathCanonicalizeW.restype = bool
    _PathCanonicalizeW.errcheck = RaiseIfZero

    lpszDst = ctypes.create_unicode_buffer("", MAX_PATH)
    _PathCanonicalizeW(lpszDst, lpszSrc)
    return lpszDst.value


PathCanonicalize = GuessStringType(PathCanonicalizeA, PathCanonicalizeW)


# BOOL PathRelativePathTo(
#   _Out_  LPTSTR pszPath,
#   _In_   LPCTSTR pszFrom,
#   _In_   DWORD dwAttrFrom,
#   _In_   LPCTSTR pszTo,
#   _In_   DWORD dwAttrTo
# );
def PathRelativePathToA(pszFrom=None, dwAttrFrom=FILE_ATTRIBUTE_DIRECTORY, pszTo=None, dwAttrTo=FILE_ATTRIBUTE_DIRECTORY):
    _PathRelativePathToA = windll.shlwapi.PathRelativePathToA
    _PathRelativePathToA.argtypes = [LPSTR, LPSTR, DWORD, LPSTR, DWORD]
    _PathRelativePathToA.restype = bool
    _PathRelativePathToA.errcheck = RaiseIfZero

    # Make the paths absolute or the function fails.
    if pszFrom:
        pszFrom = GetFullPathNameA(pszFrom)[0]
    else:
        pszFrom = GetCurrentDirectoryA()
    if pszTo:
        pszTo = GetFullPathNameA(pszTo)[0]
    else:
        pszTo = GetCurrentDirectoryA()

    # Argh, this function doesn't receive an output buffer size!
    # We'll try to guess the maximum possible buffer size.
    dwPath = max((len(pszFrom) + len(pszTo)) * 2 + 1, MAX_PATH + 1)
    pszPath = ctypes.create_string_buffer("", dwPath)

    # Also, it doesn't set the last error value.
    # Whoever coded it must have been drunk or tripping on acid. Or both.
    # The only failure conditions I've seen were invalid paths, paths not
    # on the same drive, or the path is not absolute.
    SetLastError(ERROR_INVALID_PARAMETER)

    _PathRelativePathToA(pszPath, pszFrom, dwAttrFrom, pszTo, dwAttrTo)
    return pszPath.value


def PathRelativePathToW(pszFrom=None, dwAttrFrom=FILE_ATTRIBUTE_DIRECTORY, pszTo=None, dwAttrTo=FILE_ATTRIBUTE_DIRECTORY):
    _PathRelativePathToW = windll.shlwapi.PathRelativePathToW
    _PathRelativePathToW.argtypes = [LPWSTR, LPWSTR, DWORD, LPWSTR, DWORD]
    _PathRelativePathToW.restype = bool
    _PathRelativePathToW.errcheck = RaiseIfZero

    # Refer to PathRelativePathToA to know why this code is so ugly.
    if pszFrom:
        pszFrom = GetFullPathNameW(pszFrom)[0]
    else:
        pszFrom = GetCurrentDirectoryW()
    if pszTo:
        pszTo = GetFullPathNameW(pszTo)[0]
    else:
        pszTo = GetCurrentDirectoryW()
    dwPath = max((len(pszFrom) + len(pszTo)) * 2 + 1, MAX_PATH + 1)
    pszPath = ctypes.create_unicode_buffer("", dwPath)
    SetLastError(ERROR_INVALID_PARAMETER)
    _PathRelativePathToW(pszPath, pszFrom, dwAttrFrom, pszTo, dwAttrTo)
    return pszPath.value


PathRelativePathTo = GuessStringType(PathRelativePathToA, PathRelativePathToW)


# BOOL PathFileExists(
#     LPCTSTR pszPath
# );
def PathFileExistsA(pszPath):
    _PathFileExistsA = windll.shlwapi.PathFileExistsA
    _PathFileExistsA.argtypes = [LPSTR]
    _PathFileExistsA.restype = bool
    return _PathFileExistsA(pszPath)


def PathFileExistsW(pszPath):
    _PathFileExistsW = windll.shlwapi.PathFileExistsW
    _PathFileExistsW.argtypes = [LPWSTR]
    _PathFileExistsW.restype = bool
    return _PathFileExistsW(pszPath)


PathFileExists = GuessStringType(PathFileExistsA, PathFileExistsW)


# LPTSTR PathFindExtension(
#     LPCTSTR pszPath
# );
def PathFindExtensionA(pszPath):
    _PathFindExtensionA = windll.shlwapi.PathFindExtensionA
    _PathFindExtensionA.argtypes = [LPSTR]
    _PathFindExtensionA.restype = LPSTR
    pszPath = ctypes.create_string_buffer(pszPath)
    return _PathFindExtensionA(pszPath)


def PathFindExtensionW(pszPath):
    _PathFindExtensionW = windll.shlwapi.PathFindExtensionW
    _PathFindExtensionW.argtypes = [LPWSTR]
    _PathFindExtensionW.restype = LPWSTR
    pszPath = ctypes.create_unicode_buffer(pszPath)
    return _PathFindExtensionW(pszPath)


PathFindExtension = GuessStringType(PathFindExtensionA, PathFindExtensionW)


# LPTSTR PathFindFileName(
#     LPCTSTR pszPath
# );
def PathFindFileNameA(pszPath):
    _PathFindFileNameA = windll.shlwapi.PathFindFileNameA
    _PathFindFileNameA.argtypes = [LPSTR]
    _PathFindFileNameA.restype = LPSTR
    pszPath = ctypes.create_string_buffer(pszPath)
    return _PathFindFileNameA(pszPath)


def PathFindFileNameW(pszPath):
    _PathFindFileNameW = windll.shlwapi.PathFindFileNameW
    _PathFindFileNameW.argtypes = [LPWSTR]
    _PathFindFileNameW.restype = LPWSTR
    pszPath = ctypes.create_unicode_buffer(pszPath)
    return _PathFindFileNameW(pszPath)


PathFindFileName = GuessStringType(PathFindFileNameA, PathFindFileNameW)


# LPTSTR PathFindNextComponent(
#     LPCTSTR pszPath
# );
def PathFindNextComponentA(pszPath):
    _PathFindNextComponentA = windll.shlwapi.PathFindNextComponentA
    _PathFindNextComponentA.argtypes = [LPSTR]
    _PathFindNextComponentA.restype = LPSTR
    pszPath = ctypes.create_string_buffer(pszPath)
    return _PathFindNextComponentA(pszPath)


def PathFindNextComponentW(pszPath):
    _PathFindNextComponentW = windll.shlwapi.PathFindNextComponentW
    _PathFindNextComponentW.argtypes = [LPWSTR]
    _PathFindNextComponentW.restype = LPWSTR
    pszPath = ctypes.create_unicode_buffer(pszPath)
    return _PathFindNextComponentW(pszPath)


PathFindNextComponent = GuessStringType(PathFindNextComponentA, PathFindNextComponentW)


# BOOL PathFindOnPath(
#     LPTSTR pszFile,
#     LPCTSTR *ppszOtherDirs
# );
def PathFindOnPathA(pszFile, ppszOtherDirs=None):
    _PathFindOnPathA = windll.shlwapi.PathFindOnPathA
    _PathFindOnPathA.argtypes = [LPSTR, LPSTR]
    _PathFindOnPathA.restype = bool

    pszFile = ctypes.create_string_buffer(pszFile, MAX_PATH)
    if not ppszOtherDirs:
        ppszOtherDirs = None
    else:
        szArray = ""
        for pszOtherDirs in ppszOtherDirs:
            if pszOtherDirs:
                szArray = "%s%s\0" % (szArray, pszOtherDirs)
        szArray = szArray + "\0"
        pszOtherDirs = ctypes.create_string_buffer(szArray)
        ppszOtherDirs = ctypes.pointer(pszOtherDirs)
    if _PathFindOnPathA(pszFile, ppszOtherDirs):
        return pszFile.value
    return None


def PathFindOnPathW(pszFile, ppszOtherDirs=None):
    _PathFindOnPathW = windll.shlwapi.PathFindOnPathA
    _PathFindOnPathW.argtypes = [LPWSTR, LPWSTR]
    _PathFindOnPathW.restype = bool

    pszFile = ctypes.create_unicode_buffer(pszFile, MAX_PATH)
    if not ppszOtherDirs:
        ppszOtherDirs = None
    else:
        szArray = ""
        for pszOtherDirs in ppszOtherDirs:
            if pszOtherDirs:
                szArray = "%s%s\0" % (szArray, pszOtherDirs)
        szArray = szArray + "\0"
        pszOtherDirs = ctypes.create_unicode_buffer(szArray)
        ppszOtherDirs = ctypes.pointer(pszOtherDirs)
    if _PathFindOnPathW(pszFile, ppszOtherDirs):
        return pszFile.value
    return None


PathFindOnPath = GuessStringType(PathFindOnPathA, PathFindOnPathW)


# LPTSTR PathGetArgs(
#     LPCTSTR pszPath
# );
def PathGetArgsA(pszPath):
    _PathGetArgsA = windll.shlwapi.PathGetArgsA
    _PathGetArgsA.argtypes = [LPSTR]
    _PathGetArgsA.restype = LPSTR
    pszPath = ctypes.create_string_buffer(pszPath)
    return _PathGetArgsA(pszPath)


def PathGetArgsW(pszPath):
    _PathGetArgsW = windll.shlwapi.PathGetArgsW
    _PathGetArgsW.argtypes = [LPWSTR]
    _PathGetArgsW.restype = LPWSTR
    pszPath = ctypes.create_unicode_buffer(pszPath)
    return _PathGetArgsW(pszPath)


PathGetArgs = GuessStringType(PathGetArgsA, PathGetArgsW)


# BOOL PathIsContentType(
#     LPCTSTR pszPath,
#     LPCTSTR pszContentType
# );
def PathIsContentTypeA(pszPath, pszContentType):
    _PathIsContentTypeA = windll.shlwapi.PathIsContentTypeA
    _PathIsContentTypeA.argtypes = [LPSTR, LPSTR]
    _PathIsContentTypeA.restype = bool
    return _PathIsContentTypeA(pszPath, pszContentType)


def PathIsContentTypeW(pszPath, pszContentType):
    _PathIsContentTypeW = windll.shlwapi.PathIsContentTypeW
    _PathIsContentTypeW.argtypes = [LPWSTR, LPWSTR]
    _PathIsContentTypeW.restype = bool
    return _PathIsContentTypeW(pszPath, pszContentType)


PathIsContentType = GuessStringType(PathIsContentTypeA, PathIsContentTypeW)


# BOOL PathIsDirectory(
#     LPCTSTR pszPath
# );
def PathIsDirectoryA(pszPath):
    _PathIsDirectoryA = windll.shlwapi.PathIsDirectoryA
    _PathIsDirectoryA.argtypes = [LPSTR]
    _PathIsDirectoryA.restype = bool
    return _PathIsDirectoryA(pszPath)


def PathIsDirectoryW(pszPath):
    _PathIsDirectoryW = windll.shlwapi.PathIsDirectoryW
    _PathIsDirectoryW.argtypes = [LPWSTR]
    _PathIsDirectoryW.restype = bool
    return _PathIsDirectoryW(pszPath)


PathIsDirectory = GuessStringType(PathIsDirectoryA, PathIsDirectoryW)


# BOOL PathIsDirectoryEmpty(
#     LPCTSTR pszPath
# );
def PathIsDirectoryEmptyA(pszPath):
    _PathIsDirectoryEmptyA = windll.shlwapi.PathIsDirectoryEmptyA
    _PathIsDirectoryEmptyA.argtypes = [LPSTR]
    _PathIsDirectoryEmptyA.restype = bool
    return _PathIsDirectoryEmptyA(pszPath)


def PathIsDirectoryEmptyW(pszPath):
    _PathIsDirectoryEmptyW = windll.shlwapi.PathIsDirectoryEmptyW
    _PathIsDirectoryEmptyW.argtypes = [LPWSTR]
    _PathIsDirectoryEmptyW.restype = bool
    return _PathIsDirectoryEmptyW(pszPath)


PathIsDirectoryEmpty = GuessStringType(PathIsDirectoryEmptyA, PathIsDirectoryEmptyW)


# BOOL PathIsNetworkPath(
#     LPCTSTR pszPath
# );
def PathIsNetworkPathA(pszPath):
    _PathIsNetworkPathA = windll.shlwapi.PathIsNetworkPathA
    _PathIsNetworkPathA.argtypes = [LPSTR]
    _PathIsNetworkPathA.restype = bool
    return _PathIsNetworkPathA(pszPath)


def PathIsNetworkPathW(pszPath):
    _PathIsNetworkPathW = windll.shlwapi.PathIsNetworkPathW
    _PathIsNetworkPathW.argtypes = [LPWSTR]
    _PathIsNetworkPathW.restype = bool
    return _PathIsNetworkPathW(pszPath)


PathIsNetworkPath = GuessStringType(PathIsNetworkPathA, PathIsNetworkPathW)


# BOOL PathIsRelative(
#     LPCTSTR lpszPath
# );
def PathIsRelativeA(pszPath):
    _PathIsRelativeA = windll.shlwapi.PathIsRelativeA
    _PathIsRelativeA.argtypes = [LPSTR]
    _PathIsRelativeA.restype = bool
    return _PathIsRelativeA(pszPath)


def PathIsRelativeW(pszPath):
    _PathIsRelativeW = windll.shlwapi.PathIsRelativeW
    _PathIsRelativeW.argtypes = [LPWSTR]
    _PathIsRelativeW.restype = bool
    return _PathIsRelativeW(pszPath)


PathIsRelative = GuessStringType(PathIsRelativeA, PathIsRelativeW)


# BOOL PathIsRoot(
#     LPCTSTR pPath
# );
def PathIsRootA(pszPath):
    _PathIsRootA = windll.shlwapi.PathIsRootA
    _PathIsRootA.argtypes = [LPSTR]
    _PathIsRootA.restype = bool
    return _PathIsRootA(pszPath)


def PathIsRootW(pszPath):
    _PathIsRootW = windll.shlwapi.PathIsRootW
    _PathIsRootW.argtypes = [LPWSTR]
    _PathIsRootW.restype = bool
    return _PathIsRootW(pszPath)


PathIsRoot = GuessStringType(PathIsRootA, PathIsRootW)


# BOOL PathIsSameRoot(
#     LPCTSTR pszPath1,
#     LPCTSTR pszPath2
# );
def PathIsSameRootA(pszPath1, pszPath2):
    _PathIsSameRootA = windll.shlwapi.PathIsSameRootA
    _PathIsSameRootA.argtypes = [LPSTR, LPSTR]
    _PathIsSameRootA.restype = bool
    return _PathIsSameRootA(pszPath1, pszPath2)


def PathIsSameRootW(pszPath1, pszPath2):
    _PathIsSameRootW = windll.shlwapi.PathIsSameRootW
    _PathIsSameRootW.argtypes = [LPWSTR, LPWSTR]
    _PathIsSameRootW.restype = bool
    return _PathIsSameRootW(pszPath1, pszPath2)


PathIsSameRoot = GuessStringType(PathIsSameRootA, PathIsSameRootW)


# BOOL PathIsUNC(
#     LPCTSTR pszPath
# );
def PathIsUNCA(pszPath):
    _PathIsUNCA = windll.shlwapi.PathIsUNCA
    _PathIsUNCA.argtypes = [LPSTR]
    _PathIsUNCA.restype = bool
    return _PathIsUNCA(pszPath)


def PathIsUNCW(pszPath):
    _PathIsUNCW = windll.shlwapi.PathIsUNCW
    _PathIsUNCW.argtypes = [LPWSTR]
    _PathIsUNCW.restype = bool
    return _PathIsUNCW(pszPath)


PathIsUNC = GuessStringType(PathIsUNCA, PathIsUNCW)

# XXX WARNING
# PathMakePretty turns filenames into all lowercase.
# I'm not sure how well that might work on Wine.


# BOOL PathMakePretty(
#     LPCTSTR pszPath
# );
def PathMakePrettyA(pszPath):
    _PathMakePrettyA = windll.shlwapi.PathMakePrettyA
    _PathMakePrettyA.argtypes = [LPSTR]
    _PathMakePrettyA.restype = bool
    _PathMakePrettyA.errcheck = RaiseIfZero

    pszPath = ctypes.create_string_buffer(pszPath, MAX_PATH)
    _PathMakePrettyA(pszPath)
    return pszPath.value


def PathMakePrettyW(pszPath):
    _PathMakePrettyW = windll.shlwapi.PathMakePrettyW
    _PathMakePrettyW.argtypes = [LPWSTR]
    _PathMakePrettyW.restype = bool
    _PathMakePrettyW.errcheck = RaiseIfZero

    pszPath = ctypes.create_unicode_buffer(pszPath, MAX_PATH)
    _PathMakePrettyW(pszPath)
    return pszPath.value


PathMakePretty = GuessStringType(PathMakePrettyA, PathMakePrettyW)


# void PathRemoveArgs(
#     LPTSTR pszPath
# );
def PathRemoveArgsA(pszPath):
    _PathRemoveArgsA = windll.shlwapi.PathRemoveArgsA
    _PathRemoveArgsA.argtypes = [LPSTR]

    pszPath = ctypes.create_string_buffer(pszPath, MAX_PATH)
    _PathRemoveArgsA(pszPath)
    return pszPath.value


def PathRemoveArgsW(pszPath):
    _PathRemoveArgsW = windll.shlwapi.PathRemoveArgsW
    _PathRemoveArgsW.argtypes = [LPWSTR]

    pszPath = ctypes.create_unicode_buffer(pszPath, MAX_PATH)
    _PathRemoveArgsW(pszPath)
    return pszPath.value


PathRemoveArgs = GuessStringType(PathRemoveArgsA, PathRemoveArgsW)


# void PathRemoveBackslash(
#     LPTSTR pszPath
# );
def PathRemoveBackslashA(pszPath):
    _PathRemoveBackslashA = windll.shlwapi.PathRemoveBackslashA
    _PathRemoveBackslashA.argtypes = [LPSTR]

    pszPath = ctypes.create_string_buffer(pszPath, MAX_PATH)
    _PathRemoveBackslashA(pszPath)
    return pszPath.value


def PathRemoveBackslashW(pszPath):
    _PathRemoveBackslashW = windll.shlwapi.PathRemoveBackslashW
    _PathRemoveBackslashW.argtypes = [LPWSTR]

    pszPath = ctypes.create_unicode_buffer(pszPath, MAX_PATH)
    _PathRemoveBackslashW(pszPath)
    return pszPath.value


PathRemoveBackslash = GuessStringType(PathRemoveBackslashA, PathRemoveBackslashW)


# void PathRemoveExtension(
#     LPTSTR pszPath
# );
def PathRemoveExtensionA(pszPath):
    _PathRemoveExtensionA = windll.shlwapi.PathRemoveExtensionA
    _PathRemoveExtensionA.argtypes = [LPSTR]

    pszPath = ctypes.create_string_buffer(pszPath, MAX_PATH)
    _PathRemoveExtensionA(pszPath)
    return pszPath.value


def PathRemoveExtensionW(pszPath):
    _PathRemoveExtensionW = windll.shlwapi.PathRemoveExtensionW
    _PathRemoveExtensionW.argtypes = [LPWSTR]

    pszPath = ctypes.create_unicode_buffer(pszPath, MAX_PATH)
    _PathRemoveExtensionW(pszPath)
    return pszPath.value


PathRemoveExtension = GuessStringType(PathRemoveExtensionA, PathRemoveExtensionW)


# void PathRemoveFileSpec(
#     LPTSTR pszPath
# );
def PathRemoveFileSpecA(pszPath):
    _PathRemoveFileSpecA = windll.shlwapi.PathRemoveFileSpecA
    _PathRemoveFileSpecA.argtypes = [LPSTR]

    pszPath = ctypes.create_string_buffer(pszPath, MAX_PATH)
    _PathRemoveFileSpecA(pszPath)
    return pszPath.value


def PathRemoveFileSpecW(pszPath):
    _PathRemoveFileSpecW = windll.shlwapi.PathRemoveFileSpecW
    _PathRemoveFileSpecW.argtypes = [LPWSTR]

    pszPath = ctypes.create_unicode_buffer(pszPath, MAX_PATH)
    _PathRemoveFileSpecW(pszPath)
    return pszPath.value


PathRemoveFileSpec = GuessStringType(PathRemoveFileSpecA, PathRemoveFileSpecW)


# BOOL PathRenameExtension(
#     LPTSTR pszPath,
#     LPCTSTR pszExt
# );
def PathRenameExtensionA(pszPath, pszExt):
    _PathRenameExtensionA = windll.shlwapi.PathRenameExtensionA
    _PathRenameExtensionA.argtypes = [LPSTR, LPSTR]
    _PathRenameExtensionA.restype = bool

    pszPath = ctypes.create_string_buffer(pszPath, MAX_PATH)
    if _PathRenameExtensionA(pszPath, pszExt):
        return pszPath.value
    return None


def PathRenameExtensionW(pszPath, pszExt):
    _PathRenameExtensionW = windll.shlwapi.PathRenameExtensionW
    _PathRenameExtensionW.argtypes = [LPWSTR, LPWSTR]
    _PathRenameExtensionW.restype = bool

    pszPath = ctypes.create_unicode_buffer(pszPath, MAX_PATH)
    if _PathRenameExtensionW(pszPath, pszExt):
        return pszPath.value
    return None


PathRenameExtension = GuessStringType(PathRenameExtensionA, PathRenameExtensionW)


# BOOL PathUnExpandEnvStrings(
#     LPCTSTR pszPath,
#     LPTSTR pszBuf,
#     UINT cchBuf
# );
def PathUnExpandEnvStringsA(pszPath):
    _PathUnExpandEnvStringsA = windll.shlwapi.PathUnExpandEnvStringsA
    _PathUnExpandEnvStringsA.argtypes = [LPSTR, LPSTR]
    _PathUnExpandEnvStringsA.restype = bool
    _PathUnExpandEnvStringsA.errcheck = RaiseIfZero

    cchBuf = MAX_PATH
    pszBuf = ctypes.create_string_buffer("", cchBuf)
    _PathUnExpandEnvStringsA(pszPath, pszBuf, cchBuf)
    return pszBuf.value


def PathUnExpandEnvStringsW(pszPath):
    _PathUnExpandEnvStringsW = windll.shlwapi.PathUnExpandEnvStringsW
    _PathUnExpandEnvStringsW.argtypes = [LPWSTR, LPWSTR]
    _PathUnExpandEnvStringsW.restype = bool
    _PathUnExpandEnvStringsW.errcheck = RaiseIfZero

    cchBuf = MAX_PATH
    pszBuf = ctypes.create_unicode_buffer("", cchBuf)
    _PathUnExpandEnvStringsW(pszPath, pszBuf, cchBuf)
    return pszBuf.value


PathUnExpandEnvStrings = GuessStringType(PathUnExpandEnvStringsA, PathUnExpandEnvStringsW)

# ==============================================================================
# This calculates the list of exported symbols.
_all = set(vars().keys()).difference(_all)
__all__ = [_x for _x in _all if not _x.startswith("_")]
__all__.sort()
# ==============================================================================

# === NexusCore/openenv\Lib\site-packages\pydantic\_internal\_decorators.py ===
"""Logic related to validators applied to models etc. via the `@field_validator` and `@model_validator` decorators."""

from __future__ import annotations as _annotations

import types
from collections import deque
from collections.abc import Iterable
from dataclasses import dataclass, field
from functools import cached_property, partial, partialmethod
from inspect import Parameter, Signature, isdatadescriptor, ismethoddescriptor, signature
from itertools import islice
from typing import TYPE_CHECKING, Any, Callable, ClassVar, Generic, Literal, TypeVar, Union

from pydantic_core import PydanticUndefined, PydanticUndefinedType, core_schema
from typing_extensions import TypeAlias, is_typeddict

from ..errors import PydanticUserError
from ._core_utils import get_type_ref
from ._internal_dataclass import slots_true
from ._namespace_utils import GlobalsNamespace, MappingNamespace
from ._typing_extra import get_function_type_hints
from ._utils import can_be_positional

if TYPE_CHECKING:
    from ..fields import ComputedFieldInfo
    from ..functional_validators import FieldValidatorModes


@dataclass(**slots_true)
class ValidatorDecoratorInfo:
    """A container for data from `@validator` so that we can access it
    while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@validator'.
        fields: A tuple of field names the validator should be called on.
        mode: The proposed validator mode.
        each_item: For complex objects (sets, lists etc.) whether to validate individual
            elements rather than the whole object.
        always: Whether this method and other validators should be called even if the value is missing.
        check_fields: Whether to check that the fields actually exist on the model.
    """

    decorator_repr: ClassVar[str] = '@validator'

    fields: tuple[str, ...]
    mode: Literal['before', 'after']
    each_item: bool
    always: bool
    check_fields: bool | None


@dataclass(**slots_true)
class FieldValidatorDecoratorInfo:
    """A container for data from `@field_validator` so that we can access it
    while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@field_validator'.
        fields: A tuple of field names the validator should be called on.
        mode: The proposed validator mode.
        check_fields: Whether to check that the fields actually exist on the model.
        json_schema_input_type: The input type of the function. This is only used to generate
            the appropriate JSON Schema (in validation mode) and can only specified
            when `mode` is either `'before'`, `'plain'` or `'wrap'`.
    """

    decorator_repr: ClassVar[str] = '@field_validator'

    fields: tuple[str, ...]
    mode: FieldValidatorModes
    check_fields: bool | None
    json_schema_input_type: Any


@dataclass(**slots_true)
class RootValidatorDecoratorInfo:
    """A container for data from `@root_validator` so that we can access it
    while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@root_validator'.
        mode: The proposed validator mode.
    """

    decorator_repr: ClassVar[str] = '@root_validator'
    mode: Literal['before', 'after']


@dataclass(**slots_true)
class FieldSerializerDecoratorInfo:
    """A container for data from `@field_serializer` so that we can access it
    while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@field_serializer'.
        fields: A tuple of field names the serializer should be called on.
        mode: The proposed serializer mode.
        return_type: The type of the serializer's return value.
        when_used: The serialization condition. Accepts a string with values `'always'`, `'unless-none'`, `'json'`,
            and `'json-unless-none'`.
        check_fields: Whether to check that the fields actually exist on the model.
    """

    decorator_repr: ClassVar[str] = '@field_serializer'
    fields: tuple[str, ...]
    mode: Literal['plain', 'wrap']
    return_type: Any
    when_used: core_schema.WhenUsed
    check_fields: bool | None


@dataclass(**slots_true)
class ModelSerializerDecoratorInfo:
    """A container for data from `@model_serializer` so that we can access it
    while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@model_serializer'.
        mode: The proposed serializer mode.
        return_type: The type of the serializer's return value.
        when_used: The serialization condition. Accepts a string with values `'always'`, `'unless-none'`, `'json'`,
            and `'json-unless-none'`.
    """

    decorator_repr: ClassVar[str] = '@model_serializer'
    mode: Literal['plain', 'wrap']
    return_type: Any
    when_used: core_schema.WhenUsed


@dataclass(**slots_true)
class ModelValidatorDecoratorInfo:
    """A container for data from `@model_validator` so that we can access it
    while building the pydantic-core schema.

    Attributes:
        decorator_repr: A class variable representing the decorator string, '@model_validator'.
        mode: The proposed serializer mode.
    """

    decorator_repr: ClassVar[str] = '@model_validator'
    mode: Literal['wrap', 'before', 'after']


DecoratorInfo: TypeAlias = """Union[
    ValidatorDecoratorInfo,
    FieldValidatorDecoratorInfo,
    RootValidatorDecoratorInfo,
    FieldSerializerDecoratorInfo,
    ModelSerializerDecoratorInfo,
    ModelValidatorDecoratorInfo,
    ComputedFieldInfo,
]"""

ReturnType = TypeVar('ReturnType')
DecoratedType: TypeAlias = (
    'Union[classmethod[Any, Any, ReturnType], staticmethod[Any, ReturnType], Callable[..., ReturnType], property]'
)


@dataclass  # can't use slots here since we set attributes on `__post_init__`
class PydanticDescriptorProxy(Generic[ReturnType]):
    """Wrap a classmethod, staticmethod, property or unbound function
    and act as a descriptor that allows us to detect decorated items
    from the class' attributes.

    This class' __get__ returns the wrapped item's __get__ result,
    which makes it transparent for classmethods and staticmethods.

    Attributes:
        wrapped: The decorator that has to be wrapped.
        decorator_info: The decorator info.
        shim: A wrapper function to wrap V1 style function.
    """

    wrapped: DecoratedType[ReturnType]
    decorator_info: DecoratorInfo
    shim: Callable[[Callable[..., Any]], Callable[..., Any]] | None = None

    def __post_init__(self):
        for attr in 'setter', 'deleter':
            if hasattr(self.wrapped, attr):
                f = partial(self._call_wrapped_attr, name=attr)
                setattr(self, attr, f)

    def _call_wrapped_attr(self, func: Callable[[Any], None], *, name: str) -> PydanticDescriptorProxy[ReturnType]:
        self.wrapped = getattr(self.wrapped, name)(func)
        if isinstance(self.wrapped, property):
            # update ComputedFieldInfo.wrapped_property
            from ..fields import ComputedFieldInfo

            if isinstance(self.decorator_info, ComputedFieldInfo):
                self.decorator_info.wrapped_property = self.wrapped
        return self

    def __get__(self, obj: object | None, obj_type: type[object] | None = None) -> PydanticDescriptorProxy[ReturnType]:
        try:
            return self.wrapped.__get__(obj, obj_type)
        except AttributeError:
            # not a descriptor, e.g. a partial object
            return self.wrapped  # type: ignore[return-value]

    def __set_name__(self, instance: Any, name: str) -> None:
        if hasattr(self.wrapped, '__set_name__'):
            self.wrapped.__set_name__(instance, name)  # pyright: ignore[reportFunctionMemberAccess]

    def __getattr__(self, name: str, /) -> Any:
        """Forward checks for __isabstractmethod__ and such."""
        return getattr(self.wrapped, name)


DecoratorInfoType = TypeVar('DecoratorInfoType', bound=DecoratorInfo)


@dataclass(**slots_true)
class Decorator(Generic[DecoratorInfoType]):
    """A generic container class to join together the decorator metadata
    (metadata from decorator itself, which we have when the
    decorator is called but not when we are building the core-schema)
    and the bound function (which we have after the class itself is created).

    Attributes:
        cls_ref: The class ref.
        cls_var_name: The decorated function name.
        func: The decorated function.
        shim: A wrapper function to wrap V1 style function.
        info: The decorator info.
    """

    cls_ref: str
    cls_var_name: str
    func: Callable[..., Any]
    shim: Callable[[Any], Any] | None
    info: DecoratorInfoType

    @staticmethod
    def build(
        cls_: Any,
        *,
        cls_var_name: str,
        shim: Callable[[Any], Any] | None,
        info: DecoratorInfoType,
    ) -> Decorator[DecoratorInfoType]:
        """Build a new decorator.

        Args:
            cls_: The class.
            cls_var_name: The decorated function name.
            shim: A wrapper function to wrap V1 style function.
            info: The decorator info.

        Returns:
            The new decorator instance.
        """
        func = get_attribute_from_bases(cls_, cls_var_name)
        if shim is not None:
            func = shim(func)
        func = unwrap_wrapped_function(func, unwrap_partial=False)
        if not callable(func):
            # This branch will get hit for classmethod properties
            attribute = get_attribute_from_base_dicts(cls_, cls_var_name)  # prevents the binding call to `__get__`
            if isinstance(attribute, PydanticDescriptorProxy):
                func = unwrap_wrapped_function(attribute.wrapped)
        return Decorator(
            cls_ref=get_type_ref(cls_),
            cls_var_name=cls_var_name,
            func=func,
            shim=shim,
            info=info,
        )

    def bind_to_cls(self, cls: Any) -> Decorator[DecoratorInfoType]:
        """Bind the decorator to a class.

        Args:
            cls: the class.

        Returns:
            The new decorator instance.
        """
        return self.build(
            cls,
            cls_var_name=self.cls_var_name,
            shim=self.shim,
            info=self.info,
        )


def get_bases(tp: type[Any]) -> tuple[type[Any], ...]:
    """Get the base classes of a class or typeddict.

    Args:
        tp: The type or class to get the bases.

    Returns:
        The base classes.
    """
    if is_typeddict(tp):
        return tp.__orig_bases__  # type: ignore
    try:
        return tp.__bases__
    except AttributeError:
        return ()


def mro(tp: type[Any]) -> tuple[type[Any], ...]:
    """Calculate the Method Resolution Order of bases using the C3 algorithm.

    See https://www.python.org/download/releases/2.3/mro/
    """
    # try to use the existing mro, for performance mainly
    # but also because it helps verify the implementation below
    if not is_typeddict(tp):
        try:
            return tp.__mro__
        except AttributeError:
            # GenericAlias and some other cases
            pass

    bases = get_bases(tp)
    return (tp,) + mro_for_bases(bases)


def mro_for_bases(bases: tuple[type[Any], ...]) -> tuple[type[Any], ...]:
    def merge_seqs(seqs: list[deque[type[Any]]]) -> Iterable[type[Any]]:
        while True:
            non_empty = [seq for seq in seqs if seq]
            if not non_empty:
                # Nothing left to process, we're done.
                return
            candidate: type[Any] | None = None
            for seq in non_empty:  # Find merge candidates among seq heads.
                candidate = seq[0]
                not_head = [s for s in non_empty if candidate in islice(s, 1, None)]
                if not_head:
                    # Reject the candidate.
                    candidate = None
                else:
                    break
            if not candidate:
                raise TypeError('Inconsistent hierarchy, no C3 MRO is possible')
            yield candidate
            for seq in non_empty:
                # Remove candidate.
                if seq[0] == candidate:
                    seq.popleft()

    seqs = [deque(mro(base)) for base in bases] + [deque(bases)]
    return tuple(merge_seqs(seqs))


_sentinel = object()


def get_attribute_from_bases(tp: type[Any] | tuple[type[Any], ...], name: str) -> Any:
    """Get the attribute from the next class in the MRO that has it,
    aiming to simulate calling the method on the actual class.

    The reason for iterating over the mro instead of just getting
    the attribute (which would do that for us) is to support TypedDict,
    which lacks a real __mro__, but can have a virtual one constructed
    from its bases (as done here).

    Args:
        tp: The type or class to search for the attribute. If a tuple, this is treated as a set of base classes.
        name: The name of the attribute to retrieve.

    Returns:
        Any: The attribute value, if found.

    Raises:
        AttributeError: If the attribute is not found in any class in the MRO.
    """
    if isinstance(tp, tuple):
        for base in mro_for_bases(tp):
            attribute = base.__dict__.get(name, _sentinel)
            if attribute is not _sentinel:
                attribute_get = getattr(attribute, '__get__', None)
                if attribute_get is not None:
                    return attribute_get(None, tp)
                return attribute
        raise AttributeError(f'{name} not found in {tp}')
    else:
        try:
            return getattr(tp, name)
        except AttributeError:
            return get_attribute_from_bases(mro(tp), name)


def get_attribute_from_base_dicts(tp: type[Any], name: str) -> Any:
    """Get an attribute out of the `__dict__` following the MRO.
    This prevents the call to `__get__` on the descriptor, and allows
    us to get the original function for classmethod properties.

    Args:
        tp: The type or class to search for the attribute.
        name: The name of the attribute to retrieve.

    Returns:
        Any: The attribute value, if found.

    Raises:
        KeyError: If the attribute is not found in any class's `__dict__` in the MRO.
    """
    for base in reversed(mro(tp)):
        if name in base.__dict__:
            return base.__dict__[name]
    return tp.__dict__[name]  # raise the error


@dataclass(**slots_true)
class DecoratorInfos:
    """Mapping of name in the class namespace to decorator info.

    note that the name in the class namespace is the function or attribute name
    not the field name!
    """

    validators: dict[str, Decorator[ValidatorDecoratorInfo]] = field(default_factory=dict)
    field_validators: dict[str, Decorator[FieldValidatorDecoratorInfo]] = field(default_factory=dict)
    root_validators: dict[str, Decorator[RootValidatorDecoratorInfo]] = field(default_factory=dict)
    field_serializers: dict[str, Decorator[FieldSerializerDecoratorInfo]] = field(default_factory=dict)
    model_serializers: dict[str, Decorator[ModelSerializerDecoratorInfo]] = field(default_factory=dict)
    model_validators: dict[str, Decorator[ModelValidatorDecoratorInfo]] = field(default_factory=dict)
    computed_fields: dict[str, Decorator[ComputedFieldInfo]] = field(default_factory=dict)

    @staticmethod
    def build(model_dc: type[Any]) -> DecoratorInfos:  # noqa: C901 (ignore complexity)
        """We want to collect all DecFunc instances that exist as
        attributes in the namespace of the class (a BaseModel or dataclass)
        that called us
        But we want to collect these in the order of the bases
        So instead of getting them all from the leaf class (the class that called us),
        we traverse the bases from root (the oldest ancestor class) to leaf
        and collect all of the instances as we go, taking care to replace
        any duplicate ones with the last one we see to mimic how function overriding
        works with inheritance.
        If we do replace any functions we put the replacement into the position
        the replaced function was in; that is, we maintain the order.
        """
        # reminder: dicts are ordered and replacement does not alter the order
        res = DecoratorInfos()
        for base in reversed(mro(model_dc)[1:]):
            existing: DecoratorInfos | None = base.__dict__.get('__pydantic_decorators__')
            if existing is None:
                existing = DecoratorInfos.build(base)
            res.validators.update({k: v.bind_to_cls(model_dc) for k, v in existing.validators.items()})
            res.field_validators.update({k: v.bind_to_cls(model_dc) for k, v in existing.field_validators.items()})
            res.root_validators.update({k: v.bind_to_cls(model_dc) for k, v in existing.root_validators.items()})
            res.field_serializers.update({k: v.bind_to_cls(model_dc) for k, v in existing.field_serializers.items()})
            res.model_serializers.update({k: v.bind_to_cls(model_dc) for k, v in existing.model_serializers.items()})
            res.model_validators.update({k: v.bind_to_cls(model_dc) for k, v in existing.model_validators.items()})
            res.computed_fields.update({k: v.bind_to_cls(model_dc) for k, v in existing.computed_fields.items()})

        to_replace: list[tuple[str, Any]] = []

        for var_name, var_value in vars(model_dc).items():
            if isinstance(var_value, PydanticDescriptorProxy):
                info = var_value.decorator_info
                if isinstance(info, ValidatorDecoratorInfo):
                    res.validators[var_name] = Decorator.build(
                        model_dc, cls_var_name=var_name, shim=var_value.shim, info=info
                    )
                elif isinstance(info, FieldValidatorDecoratorInfo):
                    res.field_validators[var_name] = Decorator.build(
                        model_dc, cls_var_name=var_name, shim=var_value.shim, info=info
                    )
                elif isinstance(info, RootValidatorDecoratorInfo):
                    res.root_validators[var_name] = Decorator.build(
                        model_dc, cls_var_name=var_name, shim=var_value.shim, info=info
                    )
                elif isinstance(info, FieldSerializerDecoratorInfo):
                    # check whether a serializer function is already registered for fields
                    for field_serializer_decorator in res.field_serializers.values():
                        # check that each field has at most one serializer function.
                        # serializer functions for the same field in subclasses are allowed,
                        # and are treated as overrides
                        if field_serializer_decorator.cls_var_name == var_name:
                            continue
                        for f in info.fields:
                            if f in field_serializer_decorator.info.fields:
                                raise PydanticUserError(
                                    'Multiple field serializer functions were defined '
                                    f'for field {f!r}, this is not allowed.',
                                    code='multiple-field-serializers',
                                )
                    res.field_serializers[var_name] = Decorator.build(
                        model_dc, cls_var_name=var_name, shim=var_value.shim, info=info
                    )
                elif isinstance(info, ModelValidatorDecoratorInfo):
                    res.model_validators[var_name] = Decorator.build(
                        model_dc, cls_var_name=var_name, shim=var_value.shim, info=info
                    )
                elif isinstance(info, ModelSerializerDecoratorInfo):
                    res.model_serializers[var_name] = Decorator.build(
                        model_dc, cls_var_name=var_name, shim=var_value.shim, info=info
                    )
                else:
                    from ..fields import ComputedFieldInfo

                    isinstance(var_value, ComputedFieldInfo)
                    res.computed_fields[var_name] = Decorator.build(
                        model_dc, cls_var_name=var_name, shim=None, info=info
                    )
                to_replace.append((var_name, var_value.wrapped))
        if to_replace:
            # If we can save `__pydantic_decorators__` on the class we'll be able to check for it above
            # so then we don't need to re-process the type, which means we can discard our descriptor wrappers
            # and replace them with the thing they are wrapping (see the other setattr call below)
            # which allows validator class methods to also function as regular class methods
            model_dc.__pydantic_decorators__ = res
            for name, value in to_replace:
                setattr(model_dc, name, value)
        return res


def inspect_validator(validator: Callable[..., Any], mode: FieldValidatorModes) -> bool:
    """Look at a field or model validator function and determine whether it takes an info argument.

    An error is raised if the function has an invalid signature.

    Args:
        validator: The validator function to inspect.
        mode: The proposed validator mode.

    Returns:
        Whether the validator takes an info argument.
    """
    try:
        sig = signature(validator)
    except (ValueError, TypeError):
        # `inspect.signature` might not be able to infer a signature, e.g. with C objects.
        # In this case, we assume no info argument is present:
        return False
    n_positional = count_positional_required_params(sig)
    if mode == 'wrap':
        if n_positional == 3:
            return True
        elif n_positional == 2:
            return False
    else:
        assert mode in {'before', 'after', 'plain'}, f"invalid mode: {mode!r}, expected 'before', 'after' or 'plain"
        if n_positional == 2:
            return True
        elif n_positional == 1:
            return False

    raise PydanticUserError(
        f'Unrecognized field_validator function signature for {validator} with `mode={mode}`:{sig}',
        code='validator-signature',
    )


def inspect_field_serializer(serializer: Callable[..., Any], mode: Literal['plain', 'wrap']) -> tuple[bool, bool]:
    """Look at a field serializer function and determine if it is a field serializer,
    and whether it takes an info argument.

    An error is raised if the function has an invalid signature.

    Args:
        serializer: The serializer function to inspect.
        mode: The serializer mode, either 'plain' or 'wrap'.

    Returns:
        Tuple of (is_field_serializer, info_arg).
    """
    try:
        sig = signature(serializer)
    except (ValueError, TypeError):
        # `inspect.signature` might not be able to infer a signature, e.g. with C objects.
        # In this case, we assume no info argument is present and this is not a method:
        return (False, False)

    first = next(iter(sig.parameters.values()), None)
    is_field_serializer = first is not None and first.name == 'self'

    n_positional = count_positional_required_params(sig)
    if is_field_serializer:
        # -1 to correct for self parameter
        info_arg = _serializer_info_arg(mode, n_positional - 1)
    else:
        info_arg = _serializer_info_arg(mode, n_positional)

    if info_arg is None:
        raise PydanticUserError(
            f'Unrecognized field_serializer function signature for {serializer} with `mode={mode}`:{sig}',
            code='field-serializer-signature',
        )

    return is_field_serializer, info_arg


def inspect_annotated_serializer(serializer: Callable[..., Any], mode: Literal['plain', 'wrap']) -> bool:
    """Look at a serializer function used via `Annotated` and determine whether it takes an info argument.

    An error is raised if the function has an invalid signature.

    Args:
        serializer: The serializer function to check.
        mode: The serializer mode, either 'plain' or 'wrap'.

    Returns:
        info_arg
    """
    try:
        sig = signature(serializer)
    except (ValueError, TypeError):
        # `inspect.signature` might not be able to infer a signature, e.g. with C objects.
        # In this case, we assume no info argument is present:
        return False
    info_arg = _serializer_info_arg(mode, count_positional_required_params(sig))
    if info_arg is None:
        raise PydanticUserError(
            f'Unrecognized field_serializer function signature for {serializer} with `mode={mode}`:{sig}',
            code='field-serializer-signature',
        )
    else:
        return info_arg


def inspect_model_serializer(serializer: Callable[..., Any], mode: Literal['plain', 'wrap']) -> bool:
    """Look at a model serializer function and determine whether it takes an info argument.

    An error is raised if the function has an invalid signature.

    Args:
        serializer: The serializer function to check.
        mode: The serializer mode, either 'plain' or 'wrap'.

    Returns:
        `info_arg` - whether the function expects an info argument.
    """
    if isinstance(serializer, (staticmethod, classmethod)) or not is_instance_method_from_sig(serializer):
        raise PydanticUserError(
            '`@model_serializer` must be applied to instance methods', code='model-serializer-instance-method'
        )

    sig = signature(serializer)
    info_arg = _serializer_info_arg(mode, count_positional_required_params(sig))
    if info_arg is None:
        raise PydanticUserError(
            f'Unrecognized model_serializer function signature for {serializer} with `mode={mode}`:{sig}',
            code='model-serializer-signature',
        )
    else:
        return info_arg


def _serializer_info_arg(mode: Literal['plain', 'wrap'], n_positional: int) -> bool | None:
    if mode == 'plain':
        if n_positional == 1:
            # (input_value: Any, /) -> Any
            return False
        elif n_positional == 2:
            # (model: Any, input_value: Any, /) -> Any
            return True
    else:
        assert mode == 'wrap', f"invalid mode: {mode!r}, expected 'plain' or 'wrap'"
        if n_positional == 2:
            # (input_value: Any, serializer: SerializerFunctionWrapHandler, /) -> Any
            return False
        elif n_positional == 3:
            # (input_value: Any, serializer: SerializerFunctionWrapHandler, info: SerializationInfo, /) -> Any
            return True

    return None


AnyDecoratorCallable: TypeAlias = (
    'Union[classmethod[Any, Any, Any], staticmethod[Any, Any], partialmethod[Any], Callable[..., Any]]'
)


def is_instance_method_from_sig(function: AnyDecoratorCallable) -> bool:
    """Whether the function is an instance method.

    It will consider a function as instance method if the first parameter of
    function is `self`.

    Args:
        function: The function to check.

    Returns:
        `True` if the function is an instance method, `False` otherwise.
    """
    sig = signature(unwrap_wrapped_function(function))
    first = next(iter(sig.parameters.values()), None)
    if first and first.name == 'self':
        return True
    return False


def ensure_classmethod_based_on_signature(function: AnyDecoratorCallable) -> Any:
    """Apply the `@classmethod` decorator on the function.

    Args:
        function: The function to apply the decorator on.

    Return:
        The `@classmethod` decorator applied function.
    """
    if not isinstance(
        unwrap_wrapped_function(function, unwrap_class_static_method=False), classmethod
    ) and _is_classmethod_from_sig(function):
        return classmethod(function)  # type: ignore[arg-type]
    return function


def _is_classmethod_from_sig(function: AnyDecoratorCallable) -> bool:
    sig = signature(unwrap_wrapped_function(function))
    first = next(iter(sig.parameters.values()), None)
    if first and first.name == 'cls':
        return True
    return False


def unwrap_wrapped_function(
    func: Any,
    *,
    unwrap_partial: bool = True,
    unwrap_class_static_method: bool = True,
) -> Any:
    """Recursively unwraps a wrapped function until the underlying function is reached.
    This handles property, functools.partial, functools.partialmethod, staticmethod, and classmethod.

    Args:
        func: The function to unwrap.
        unwrap_partial: If True (default), unwrap partial and partialmethod decorators.
        unwrap_class_static_method: If True (default), also unwrap classmethod and staticmethod
            decorators. If False, only unwrap partial and partialmethod decorators.

    Returns:
        The underlying function of the wrapped function.
    """
    # Define the types we want to check against as a single tuple.
    unwrap_types = (
        (property, cached_property)
        + ((partial, partialmethod) if unwrap_partial else ())
        + ((staticmethod, classmethod) if unwrap_class_static_method else ())
    )

    while isinstance(func, unwrap_types):
        if unwrap_class_static_method and isinstance(func, (classmethod, staticmethod)):
            func = func.__func__
        elif isinstance(func, (partial, partialmethod)):
            func = func.func
        elif isinstance(func, property):
            func = func.fget  # arbitrary choice, convenient for computed fields
        else:
            # Make coverage happy as it can only get here in the last possible case
            assert isinstance(func, cached_property)
            func = func.func  # type: ignore

    return func


_function_like = (
    partial,
    partialmethod,
    types.FunctionType,
    types.BuiltinFunctionType,
    types.MethodType,
    types.WrapperDescriptorType,
    types.MethodWrapperType,
    types.MemberDescriptorType,
)


def get_callable_return_type(
    callable_obj: Any,
    globalns: GlobalsNamespace | None = None,
    localns: MappingNamespace | None = None,
) -> Any | PydanticUndefinedType:
    """Get the callable return type.

    Args:
        callable_obj: The callable to analyze.
        globalns: The globals namespace to use during type annotation evaluation.
        localns: The locals namespace to use during type annotation evaluation.

    Returns:
        The function return type.
    """
    if isinstance(callable_obj, type):
        # types are callables, and we assume the return type
        # is the type itself (e.g. `int()` results in an instance of `int`).
        return callable_obj

    if not isinstance(callable_obj, _function_like):
        call_func = getattr(type(callable_obj), '__call__', None)  # noqa: B004
        if call_func is not None:
            callable_obj = call_func

    hints = get_function_type_hints(
        unwrap_wrapped_function(callable_obj),
        include_keys={'return'},
        globalns=globalns,
        localns=localns,
    )
    return hints.get('return', PydanticUndefined)


def count_positional_required_params(sig: Signature) -> int:
    """Get the number of positional (required) arguments of a signature.

    This function should only be used to inspect signatures of validation and serialization functions.
    The first argument (the value being serialized or validated) is counted as a required argument
    even if a default value exists.

    Returns:
        The number of positional arguments of a signature.
    """
    parameters = list(sig.parameters.values())
    return sum(
        1
        for param in parameters
        if can_be_positional(param)
        # First argument is the value being validated/serialized, and can have a default value
        # (e.g. `float`, which has signature `(x=0, /)`). We assume other parameters (the info arg
        # for instance) should be required, and thus without any default value.
        and (param.default is Parameter.empty or param is parameters[0])
    )


def ensure_property(f: Any) -> Any:
    """Ensure that a function is a `property` or `cached_property`, or is a valid descriptor.

    Args:
        f: The function to check.

    Returns:
        The function, or a `property` or `cached_property` instance wrapping the function.
    """
    if ismethoddescriptor(f) or isdatadescriptor(f):
        return f
    else:
        return property(f)

# === NexusCore/openenv\Lib\site-packages\win32comext\propsys\pscon.py ===
# hand generated from propsys.h

## PROPENUMTYPE, used with IPropertyEnumType
PET_DISCRETEVALUE = 0
PET_RANGEDVALUE = 1
PET_DEFAULTVALUE = 2
PET_ENDRANGE = 3

PDTF_DEFAULT = 0
PDTF_MULTIPLEVALUES = 0x1
PDTF_ISINNATE = 0x2
PDTF_ISGROUP = 0x4
PDTF_CANGROUPBY = 0x8
PDTF_CANSTACKBY = 0x10
PDTF_ISTREEPROPERTY = 0x20
PDTF_INCLUDEINFULLTEXTQUERY = 0x40
PDTF_ISVIEWABLE = 0x80
PDTF_ISQUERYABLE = 0x100
PDTF_ISSYSTEMPROPERTY = 0x80000000
PDTF_MASK_ALL = 0x800001FF

PDVF_DEFAULT = 0
PDVF_CENTERALIGN = 0x1
PDVF_RIGHTALIGN = 0x2
PDVF_BEGINNEWGROUP = 0x4
PDVF_FILLAREA = 0x8
PDVF_SORTDESCENDING = 0x10
PDVF_SHOWONLYIFPRESENT = 0x20
PDVF_SHOWBYDEFAULT = 0x40
PDVF_SHOWINPRIMARYLIST = 0x80
PDVF_SHOWINSECONDARYLIST = 0x100
PDVF_HIDELABEL = 0x200
PDVF_HIDDEN = 0x800
PDVF_CANWRAP = 0x1000
PDVF_MASK_ALL = 0x1BFF

PDDT_STRING = 0
PDDT_NUMBER = 1
PDDT_BOOLEAN = 2
PDDT_DATETIME = 3
PDDT_ENUMERATED = 4

PDGR_DISCRETE = 0
PDGR_ALPHANUMERIC = 1
PDGR_SIZE = 2
PDGR_DYNAMIC = 3
PDGR_DATE = 4
PDGR_PERCENT = 5
PDGR_ENUMERATED = 6

## PROPDESC_FORMAT_FLAGS
PDFF_DEFAULT = 0
PDFF_PREFIXNAME = 0x1
PDFF_FILENAME = 0x2
PDFF_ALWAYSKB = 0x4
PDFF_RESERVED_RIGHTTOLEFT = 0x8
PDFF_SHORTTIME = 0x10
PDFF_LONGTIME = 0x20
PDFF_HIDETIME = 0x40
PDFF_SHORTDATE = 0x80
PDFF_LONGDATE = 0x100
PDFF_HIDEDATE = 0x200
PDFF_RELATIVEDATE = 0x400
PDFF_USEEDITINVITATION = 0x800
PDFF_READONLY = 0x1000
PDFF_NOAUTOREADINGORDER = 0x2000

PDSD_GENERAL = 0
PDSD_A_Z = 1
PDSD_LOWEST_HIGHEST = 2
PDSD_SMALLEST_BIGGEST = 3
PDSD_OLDEST_NEWEST = 4

PDRDT_GENERAL = 0
PDRDT_DATE = 1
PDRDT_SIZE = 2
PDRDT_COUNT = 3
PDRDT_REVISION = 4
PDRDT_LENGTH = 5
PDRDT_DURATION = 6
PDRDT_SPEED = 7
PDRDT_RATE = 8
PDRDT_RATING = 9
PDRDT_PRIORITY = 10

PDAT_DEFAULT = 0
PDAT_FIRST = 1
PDAT_SUM = 2
PDAT_AVERAGE = 3
PDAT_DATERANGE = 4
PDAT_UNION = 5
PDAT_MAX = 6
PDAT_MIN = 7

PDCOT_NONE = 0
PDCOT_STRING = 1
PDCOT_SIZE = 2
PDCOT_DATETIME = 3
PDCOT_BOOLEAN = 4
PDCOT_NUMBER = 5

PDSIF_DEFAULT = 0
PDSIF_ININVERTEDINDEX = 0x1
PDSIF_ISCOLUMN = 0x2
PDSIF_ISCOLUMNSPARSE = 0x4
PDCIT_NONE = 0
PDCIT_ONDISK = 1
PDCIT_INMEMORY = 2

## PROPDESC_ENUMFILTER, used with IPropertySystem::EnumeratePropertyDescriptions
PDEF_ALL = 0
PDEF_SYSTEM = 1
PDEF_NONSYSTEM = 2
PDEF_VIEWABLE = 3
PDEF_QUERYABLE = 4
PDEF_INFULLTEXTQUERY = 5
PDEF_COLUMN = 6

## PSC_STATE, used with IPropertyStoreCache
PSC_NORMAL = 0
PSC_NOTINSOURCE = 1
PSC_DIRTY = 2

## CONDITION_OPERATION
COP_IMPLICIT = 0
COP_EQUAL = 1
COP_NOTEQUAL = 2
COP_LESSTHAN = 3
COP_GREATERTHAN = 4
COP_LESSTHANOREQUAL = 5
COP_GREATERTHANOREQUAL = 6
COP_VALUE_STARTSWITH = 7
COP_VALUE_ENDSWITH = 8
COP_VALUE_CONTAINS = 9
COP_VALUE_NOTCONTAINS = 10
COP_DOSWILDCARDS = 11
COP_WORD_EQUAL = 12
COP_WORD_STARTSWITH = 13
COP_APPLICATION_SPECIFIC = 14

## PERSIST_SPROPSTORE_FLAGS, used with IPersistSerializedPropStorage
FPSPS_READONLY = 1

PKEY_PIDSTR_MAX = 10  # will take care of any long integer value
# define GUIDSTRING_MAX      (1 + 8 + 1 + 4 + 1 + 4 + 1 + 4 + 1 + 12 + 1 + 1)  // "{12345678-1234-1234-1234-123456789012}"
GUIDSTRING_MAX = 1 + 8 + 1 + 4 + 1 + 4 + 1 + 4 + 1 + 12 + 1 + 1  # hrm ???
# define PKEYSTR_MAX         (GUIDSTRING_MAX + 1 + PKEY_PIDSTR_MAX)
PKEYSTR_MAX = GUIDSTRING_MAX + 1 + PKEY_PIDSTR_MAX

## Property keys from propkey.h
from pywintypes import IID

PKEY_Audio_ChannelCount = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 7)
PKEY_Audio_Compression = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 10)
PKEY_Audio_EncodingBitrate = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 4)
PKEY_Audio_Format = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 2)
PKEY_Audio_IsVariableBitRate = (IID("{E6822FEE-8C17-4D62-823C-8E9CFCBD1D5C}"), 100)
PKEY_Audio_PeakValue = (IID("{2579E5D0-1116-4084-BD9A-9B4F7CB4DF5E}"), 100)
PKEY_Audio_SampleRate = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 5)
PKEY_Audio_SampleSize = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 6)
PKEY_Audio_StreamName = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 9)
PKEY_Audio_StreamNumber = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 8)
PKEY_Calendar_Duration = (IID("{293CA35A-09AA-4DD2-B180-1FE245728A52}"), 100)
PKEY_Calendar_IsOnline = (IID("{BFEE9149-E3E2-49A7-A862-C05988145CEC}"), 100)
PKEY_Calendar_IsRecurring = (IID("{315B9C8D-80A9-4EF9-AE16-8E746DA51D70}"), 100)
PKEY_Calendar_Location = (IID("{F6272D18-CECC-40B1-B26A-3911717AA7BD}"), 100)
PKEY_Calendar_OptionalAttendeeAddresses = (
    IID("{D55BAE5A-3892-417A-A649-C6AC5AAAEAB3}"),
    100,
)
PKEY_Calendar_OptionalAttendeeNames = (
    IID("{09429607-582D-437F-84C3-DE93A2B24C3C}"),
    100,
)
PKEY_Calendar_OrganizerAddress = (IID("{744C8242-4DF5-456C-AB9E-014EFB9021E3}"), 100)
PKEY_Calendar_OrganizerName = (IID("{AAA660F9-9865-458E-B484-01BC7FE3973E}"), 100)
PKEY_Calendar_ReminderTime = (IID("{72FC5BA4-24F9-4011-9F3F-ADD27AFAD818}"), 100)
PKEY_Calendar_RequiredAttendeeAddresses = (
    IID("{0BA7D6C3-568D-4159-AB91-781A91FB71E5}"),
    100,
)
PKEY_Calendar_RequiredAttendeeNames = (
    IID("{B33AF30B-F552-4584-936C-CB93E5CDA29F}"),
    100,
)
PKEY_Calendar_Resources = (IID("{00F58A38-C54B-4C40-8696-97235980EAE1}"), 100)
PKEY_Calendar_ShowTimeAs = (IID("{5BF396D4-5EB2-466F-BDE9-2FB3F2361D6E}"), 100)
PKEY_Calendar_ShowTimeAsText = (IID("{53DA57CF-62C0-45C4-81DE-7610BCEFD7F5}"), 100)
PKEY_Communication_AccountName = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 9)
PKEY_Communication_Suffix = (IID("{807B653A-9E91-43EF-8F97-11CE04EE20C5}"), 100)
PKEY_Communication_TaskStatus = (IID("{BE1A72C6-9A1D-46B7-AFE7-AFAF8CEF4999}"), 100)
PKEY_Communication_TaskStatusText = (IID("{A6744477-C237-475B-A075-54F34498292A}"), 100)
PKEY_Computer_DecoratedFreeSpace = (IID("{9B174B35-40FF-11D2-A27E-00C04FC30871}"), 7)
PKEY_Contact_Anniversary = (IID("{9AD5BADB-CEA7-4470-A03D-B84E51B9949E}"), 100)
PKEY_Contact_AssistantName = (IID("{CD102C9C-5540-4A88-A6F6-64E4981C8CD1}"), 100)
PKEY_Contact_AssistantTelephone = (IID("{9A93244D-A7AD-4FF8-9B99-45EE4CC09AF6}"), 100)
PKEY_Contact_Birthday = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 47)
PKEY_Contact_BusinessAddress = (IID("{730FB6DD-CF7C-426B-A03F-BD166CC9EE24}"), 100)
PKEY_Contact_BusinessAddressCity = (IID("{402B5934-EC5A-48C3-93E6-85E86A2D934E}"), 100)
PKEY_Contact_BusinessAddressCountry = (
    IID("{B0B87314-FCF6-4FEB-8DFF-A50DA6AF561C}"),
    100,
)
PKEY_Contact_BusinessAddressPostalCode = (
    IID("{E1D4A09E-D758-4CD1-B6EC-34A8B5A73F80}"),
    100,
)
PKEY_Contact_BusinessAddressPostOfficeBox = (
    IID("{BC4E71CE-17F9-48D5-BEE9-021DF0EA5409}"),
    100,
)
PKEY_Contact_BusinessAddressState = (IID("{446F787F-10C4-41CB-A6C4-4D0343551597}"), 100)
PKEY_Contact_BusinessAddressStreet = (
    IID("{DDD1460F-C0BF-4553-8CE4-10433C908FB0}"),
    100,
)
PKEY_Contact_BusinessFaxNumber = (IID("{91EFF6F3-2E27-42CA-933E-7C999FBE310B}"), 100)
PKEY_Contact_BusinessHomePage = (IID("{56310920-2491-4919-99CE-EADB06FAFDB2}"), 100)
PKEY_Contact_BusinessTelephone = (IID("{6A15E5A0-0A1E-4CD7-BB8C-D2F1B0C929BC}"), 100)
PKEY_Contact_CallbackTelephone = (IID("{BF53D1C3-49E0-4F7F-8567-5A821D8AC542}"), 100)
PKEY_Contact_CarTelephone = (IID("{8FDC6DEA-B929-412B-BA90-397A257465FE}"), 100)
PKEY_Contact_Children = (IID("{D4729704-8EF1-43EF-9024-2BD381187FD5}"), 100)
PKEY_Contact_CompanyMainTelephone = (IID("{8589E481-6040-473D-B171-7FA89C2708ED}"), 100)
PKEY_Contact_Department = (IID("{FC9F7306-FF8F-4D49-9FB6-3FFE5C0951EC}"), 100)
PKEY_Contact_EmailAddress = (IID("{F8FA7FA3-D12B-4785-8A4E-691A94F7A3E7}"), 100)
PKEY_Contact_EmailAddress2 = (IID("{38965063-EDC8-4268-8491-B7723172CF29}"), 100)
PKEY_Contact_EmailAddress3 = (IID("{644D37B4-E1B3-4BAD-B099-7E7C04966ACA}"), 100)
PKEY_Contact_EmailAddresses = (IID("{84D8F337-981D-44B3-9615-C7596DBA17E3}"), 100)
PKEY_Contact_EmailName = (IID("{CC6F4F24-6083-4BD4-8754-674D0DE87AB8}"), 100)
PKEY_Contact_FileAsName = (IID("{F1A24AA7-9CA7-40F6-89EC-97DEF9FFE8DB}"), 100)
PKEY_Contact_FirstName = (IID("{14977844-6B49-4AAD-A714-A4513BF60460}"), 100)
PKEY_Contact_FullName = (IID("{635E9051-50A5-4BA2-B9DB-4ED056C77296}"), 100)
PKEY_Contact_Gender = (IID("{3C8CEE58-D4F0-4CF9-B756-4E5D24447BCD}"), 100)
PKEY_Contact_Hobbies = (IID("{5DC2253F-5E11-4ADF-9CFE-910DD01E3E70}"), 100)
PKEY_Contact_HomeAddress = (IID("{98F98354-617A-46B8-8560-5B1B64BF1F89}"), 100)
PKEY_Contact_HomeAddressCity = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 65)
PKEY_Contact_HomeAddressCountry = (IID("{08A65AA1-F4C9-43DD-9DDF-A33D8E7EAD85}"), 100)
PKEY_Contact_HomeAddressPostalCode = (
    IID("{8AFCC170-8A46-4B53-9EEE-90BAE7151E62}"),
    100,
)
PKEY_Contact_HomeAddressPostOfficeBox = (
    IID("{7B9F6399-0A3F-4B12-89BD-4ADC51C918AF}"),
    100,
)
PKEY_Contact_HomeAddressState = (IID("{C89A23D0-7D6D-4EB8-87D4-776A82D493E5}"), 100)
PKEY_Contact_HomeAddressStreet = (IID("{0ADEF160-DB3F-4308-9A21-06237B16FA2A}"), 100)
PKEY_Contact_HomeFaxNumber = (IID("{660E04D6-81AB-4977-A09F-82313113AB26}"), 100)
PKEY_Contact_HomeTelephone = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 20)
PKEY_Contact_IMAddress = (IID("{D68DBD8A-3374-4B81-9972-3EC30682DB3D}"), 100)
PKEY_Contact_Initials = (IID("{F3D8F40D-50CB-44A2-9718-40CB9119495D}"), 100)
PKEY_Contact_JA_CompanyNamePhonetic = (IID("{897B3694-FE9E-43E6-8066-260F590C0100}"), 2)
PKEY_Contact_JA_FirstNamePhonetic = (IID("{897B3694-FE9E-43E6-8066-260F590C0100}"), 3)
PKEY_Contact_JA_LastNamePhonetic = (IID("{897B3694-FE9E-43E6-8066-260F590C0100}"), 4)
PKEY_Contact_JobTitle = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 6)
PKEY_Contact_Label = (IID("{97B0AD89-DF49-49CC-834E-660974FD755B}"), 100)
PKEY_Contact_LastName = (IID("{8F367200-C270-457C-B1D4-E07C5BCD90C7}"), 100)
PKEY_Contact_MailingAddress = (IID("{C0AC206A-827E-4650-95AE-77E2BB74FCC9}"), 100)
PKEY_Contact_MiddleName = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 71)
PKEY_Contact_MobileTelephone = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 35)
PKEY_Contact_NickName = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 74)
PKEY_Contact_OfficeLocation = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 7)
PKEY_Contact_OtherAddress = (IID("{508161FA-313B-43D5-83A1-C1ACCF68622C}"), 100)
PKEY_Contact_OtherAddressCity = (IID("{6E682923-7F7B-4F0C-A337-CFCA296687BF}"), 100)
PKEY_Contact_OtherAddressCountry = (IID("{8F167568-0AAE-4322-8ED9-6055B7B0E398}"), 100)
PKEY_Contact_OtherAddressPostalCode = (
    IID("{95C656C1-2ABF-4148-9ED3-9EC602E3B7CD}"),
    100,
)
PKEY_Contact_OtherAddressPostOfficeBox = (
    IID("{8B26EA41-058F-43F6-AECC-4035681CE977}"),
    100,
)
PKEY_Contact_OtherAddressState = (IID("{71B377D6-E570-425F-A170-809FAE73E54E}"), 100)
PKEY_Contact_OtherAddressStreet = (IID("{FF962609-B7D6-4999-862D-95180D529AEA}"), 100)
PKEY_Contact_PagerTelephone = (IID("{D6304E01-F8F5-4F45-8B15-D024A6296789}"), 100)
PKEY_Contact_PersonalTitle = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 69)
PKEY_Contact_PrimaryAddressCity = (IID("{C8EA94F0-A9E3-4969-A94B-9C62A95324E0}"), 100)
PKEY_Contact_PrimaryAddressCountry = (
    IID("{E53D799D-0F3F-466E-B2FF-74634A3CB7A4}"),
    100,
)
PKEY_Contact_PrimaryAddressPostalCode = (
    IID("{18BBD425-ECFD-46EF-B612-7B4A6034EDA0}"),
    100,
)
PKEY_Contact_PrimaryAddressPostOfficeBox = (
    IID("{DE5EF3C7-46E1-484E-9999-62C5308394C1}"),
    100,
)
PKEY_Contact_PrimaryAddressState = (IID("{F1176DFE-7138-4640-8B4C-AE375DC70A6D}"), 100)
PKEY_Contact_PrimaryAddressStreet = (IID("{63C25B20-96BE-488F-8788-C09C407AD812}"), 100)
PKEY_Contact_PrimaryEmailAddress = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 48)
PKEY_Contact_PrimaryTelephone = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 25)
PKEY_Contact_Profession = (IID("{7268AF55-1CE4-4F6E-A41F-B6E4EF10E4A9}"), 100)
PKEY_Contact_SpouseName = (IID("{9D2408B6-3167-422B-82B0-F583B7A7CFE3}"), 100)
PKEY_Contact_Suffix = (IID("{176DC63C-2688-4E89-8143-A347800F25E9}"), 73)
PKEY_Contact_TelexNumber = (IID("{C554493C-C1F7-40C1-A76C-EF8C0614003E}"), 100)
PKEY_Contact_TTYTDDTelephone = (IID("{AAF16BAC-2B55-45E6-9F6D-415EB94910DF}"), 100)
PKEY_Contact_WebPage = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 18)
PKEY_AcquisitionID = (IID("{65A98875-3C80-40AB-ABBC-EFDAF77DBEE2}"), 100)
PKEY_ApplicationName = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 18)
PKEY_Author = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 4)
PKEY_Capacity = (IID("{9B174B35-40FF-11D2-A27E-00C04FC30871}"), 3)
PKEY_Category = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 2)
PKEY_Comment = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 6)
PKEY_Company = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 15)
PKEY_ComputerName = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 5)
PKEY_ContainedItems = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 29)
PKEY_ContentStatus = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 27)
PKEY_ContentType = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 26)
PKEY_Copyright = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 11)
PKEY_DateAccessed = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 16)
PKEY_DateAcquired = (IID("{2CBAA8F5-D81F-47CA-B17A-F8D822300131}"), 100)
PKEY_DateArchived = (IID("{43F8D7B7-A444-4F87-9383-52271C9B915C}"), 100)
PKEY_DateCompleted = (IID("{72FAB781-ACDA-43E5-B155-B2434F85E678}"), 100)
PKEY_DateCreated = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 15)
PKEY_DateImported = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 18258)
PKEY_DateModified = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 14)
PKEY_DueDate = (IID("{3F8472B5-E0AF-4DB2-8071-C53FE76AE7CE}"), 100)
PKEY_EndDate = (IID("{C75FAA05-96FD-49E7-9CB4-9F601082D553}"), 100)
PKEY_FileAllocationSize = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 18)
PKEY_FileAttributes = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 13)
PKEY_FileCount = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 12)
PKEY_FileDescription = (IID("{0CEF7D53-FA64-11D1-A203-0000F81FEDEE}"), 3)
PKEY_FileExtension = (IID("{E4F10A3C-49E6-405D-8288-A23BD4EEAA6C}"), 100)
PKEY_FileFRN = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 21)
PKEY_FileName = (IID("{41CF5AE0-F75A-4806-BD87-59C7D9248EB9}"), 100)
PKEY_FileOwner = (IID("{9B174B34-40FF-11D2-A27E-00C04FC30871}"), 4)
PKEY_FileVersion = (IID("{0CEF7D53-FA64-11D1-A203-0000F81FEDEE}"), 4)
PKEY_FindData = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 0)
PKEY_FlagColor = (IID("{67DF94DE-0CA7-4D6F-B792-053A3E4F03CF}"), 100)
PKEY_FlagColorText = (IID("{45EAE747-8E2A-40AE-8CBF-CA52ABA6152A}"), 100)
PKEY_FlagStatus = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 12)
PKEY_FlagStatusText = (IID("{DC54FD2E-189D-4871-AA01-08C2F57A4ABC}"), 100)
PKEY_FreeSpace = (IID("{9B174B35-40FF-11D2-A27E-00C04FC30871}"), 2)
PKEY_Identity = (IID("{A26F4AFC-7346-4299-BE47-EB1AE613139F}"), 100)
PKEY_Importance = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 11)
PKEY_ImportanceText = (IID("{A3B29791-7713-4E1D-BB40-17DB85F01831}"), 100)
PKEY_IsAttachment = (IID("{F23F425C-71A1-4FA8-922F-678EA4A60408}"), 100)
PKEY_IsDeleted = (IID("{5CDA5FC8-33EE-4FF3-9094-AE7BD8868C4D}"), 100)
PKEY_IsFlagged = (IID("{5DA84765-E3FF-4278-86B0-A27967FBDD03}"), 100)
PKEY_IsFlaggedComplete = (IID("{A6F360D2-55F9-48DE-B909-620E090A647C}"), 100)
PKEY_IsIncomplete = (IID("{346C8BD1-2E6A-4C45-89A4-61B78E8E700F}"), 100)
PKEY_IsRead = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 10)
PKEY_IsSendToTarget = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 33)
PKEY_IsShared = (IID("{EF884C5B-2BFE-41BB-AAE5-76EEDF4F9902}"), 100)
PKEY_ItemAuthors = (IID("{D0A04F0A-462A-48A4-BB2F-3706E88DBD7D}"), 100)
PKEY_ItemDate = (IID("{F7DB74B4-4287-4103-AFBA-F1B13DCD75CF}"), 100)
PKEY_ItemFolderNameDisplay = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 2)
PKEY_ItemFolderPathDisplay = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 6)
PKEY_ItemFolderPathDisplayNarrow = (IID("{DABD30ED-0043-4789-A7F8-D013A4736622}"), 100)
PKEY_ItemName = (IID("{6B8DA074-3B5C-43BC-886F-0A2CDCE00B6F}"), 100)
PKEY_ItemNameDisplay = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 10)
PKEY_ItemNamePrefix = (IID("{D7313FF1-A77A-401C-8C99-3DBDD68ADD36}"), 100)
PKEY_ItemParticipants = (IID("{D4D0AA16-9948-41A4-AA85-D97FF9646993}"), 100)
PKEY_ItemPathDisplay = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 7)
PKEY_ItemPathDisplayNarrow = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 8)
PKEY_ItemType = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 11)
PKEY_ItemTypeText = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 4)
PKEY_ItemUrl = (IID("{49691C90-7E17-101A-A91C-08002B2ECDA9}"), 9)
PKEY_Keywords = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 5)
PKEY_Kind = (IID("{1E3EE840-BC2B-476C-8237-2ACD1A839B22}"), 3)
PKEY_KindText = (IID("{F04BEF95-C585-4197-A2B7-DF46FDC9EE6D}"), 100)
PKEY_Language = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 28)
PKEY_MileageInformation = (IID("{FDF84370-031A-4ADD-9E91-0D775F1C6605}"), 100)
PKEY_MIMEType = (IID("{0B63E350-9CCC-11D0-BCDB-00805FCCCE04}"), 5)
PKEY_Null = (IID("{00000000-0000-0000-0000-000000000000}"), 0)
PKEY_OfflineAvailability = (IID("{A94688B6-7D9F-4570-A648-E3DFC0AB2B3F}"), 100)
PKEY_OfflineStatus = (IID("{6D24888F-4718-4BDA-AFED-EA0FB4386CD8}"), 100)
PKEY_OriginalFileName = (IID("{0CEF7D53-FA64-11D1-A203-0000F81FEDEE}"), 6)
PKEY_ParentalRating = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 21)
PKEY_ParentalRatingReason = (IID("{10984E0A-F9F2-4321-B7EF-BAF195AF4319}"), 100)
PKEY_ParentalRatingsOrganization = (IID("{A7FE0840-1344-46F0-8D37-52ED712A4BF9}"), 100)
PKEY_ParsingBindContext = (IID("{DFB9A04D-362F-4CA3-B30B-0254B17B5B84}"), 100)
PKEY_ParsingName = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 24)
PKEY_ParsingPath = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 30)
PKEY_PerceivedType = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 9)
PKEY_PercentFull = (IID("{9B174B35-40FF-11D2-A27E-00C04FC30871}"), 5)
PKEY_Priority = (IID("{9C1FCF74-2D97-41BA-B4AE-CB2E3661A6E4}"), 5)
PKEY_PriorityText = (IID("{D98BE98B-B86B-4095-BF52-9D23B2E0A752}"), 100)
PKEY_Project = (IID("{39A7F922-477C-48DE-8BC8-B28441E342E3}"), 100)
PKEY_ProviderItemID = (IID("{F21D9941-81F0-471A-ADEE-4E74B49217ED}"), 100)
PKEY_Rating = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 9)
PKEY_RatingText = (IID("{90197CA7-FD8F-4E8C-9DA3-B57E1E609295}"), 100)
PKEY_Sensitivity = (IID("{F8D3F6AC-4874-42CB-BE59-AB454B30716A}"), 100)
PKEY_SensitivityText = (IID("{D0C7F054-3F72-4725-8527-129A577CB269}"), 100)
PKEY_SFGAOFlags = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 25)
PKEY_SharedWith = (IID("{EF884C5B-2BFE-41BB-AAE5-76EEDF4F9902}"), 200)
PKEY_ShareUserRating = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 12)
PKEY_Shell_OmitFromView = (IID("{DE35258C-C695-4CBC-B982-38B0AD24CED0}"), 2)
PKEY_SimpleRating = (IID("{A09F084E-AD41-489F-8076-AA5BE3082BCA}"), 100)
PKEY_Size = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 12)
PKEY_SoftwareUsed = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 305)
PKEY_SourceItem = (IID("{668CDFA5-7A1B-4323-AE4B-E527393A1D81}"), 100)
PKEY_StartDate = (IID("{48FD6EC8-8A12-4CDF-A03E-4EC5A511EDDE}"), 100)
PKEY_Status = (IID("{000214A1-0000-0000-C000-000000000046}"), 9)
PKEY_Subject = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 3)
PKEY_Thumbnail = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 17)
PKEY_ThumbnailCacheId = (IID("{446D16B1-8DAD-4870-A748-402EA43D788C}"), 100)
PKEY_ThumbnailStream = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 27)
PKEY_Title = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 2)
PKEY_TotalFileSize = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 14)
PKEY_Trademarks = (IID("{0CEF7D53-FA64-11D1-A203-0000F81FEDEE}"), 9)
PKEY_Document_ByteCount = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 4)
PKEY_Document_CharacterCount = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 16)
PKEY_Document_ClientID = (IID("{276D7BB0-5B34-4FB0-AA4B-158ED12A1809}"), 100)
PKEY_Document_Contributor = (IID("{F334115E-DA1B-4509-9B3D-119504DC7ABB}"), 100)
PKEY_Document_DateCreated = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 12)
PKEY_Document_DatePrinted = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 11)
PKEY_Document_DateSaved = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 13)
PKEY_Document_Division = (IID("{1E005EE6-BF27-428B-B01C-79676ACD2870}"), 100)
PKEY_Document_DocumentID = (IID("{E08805C8-E395-40DF-80D2-54F0D6C43154}"), 100)
PKEY_Document_HiddenSlideCount = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 9)
PKEY_Document_LastAuthor = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 8)
PKEY_Document_LineCount = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 5)
PKEY_Document_Manager = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 14)
PKEY_Document_MultimediaClipCount = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 10)
PKEY_Document_NoteCount = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 8)
PKEY_Document_PageCount = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 14)
PKEY_Document_ParagraphCount = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 6)
PKEY_Document_PresentationFormat = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 3)
PKEY_Document_RevisionNumber = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 9)
PKEY_Document_Security = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 19)
PKEY_Document_SlideCount = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 7)
PKEY_Document_Template = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 7)
PKEY_Document_TotalEditingTime = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 10)
PKEY_Document_Version = (IID("{D5CDD502-2E9C-101B-9397-08002B2CF9AE}"), 29)
PKEY_Document_WordCount = (IID("{F29F85E0-4FF9-1068-AB91-08002B27B3D9}"), 15)
PKEY_DRM_DatePlayExpires = (IID("{AEAC19E4-89AE-4508-B9B7-BB867ABEE2ED}"), 6)
PKEY_DRM_DatePlayStarts = (IID("{AEAC19E4-89AE-4508-B9B7-BB867ABEE2ED}"), 5)
PKEY_DRM_Description = (IID("{AEAC19E4-89AE-4508-B9B7-BB867ABEE2ED}"), 3)
PKEY_DRM_IsProtected = (IID("{AEAC19E4-89AE-4508-B9B7-BB867ABEE2ED}"), 2)
PKEY_DRM_PlayCount = (IID("{AEAC19E4-89AE-4508-B9B7-BB867ABEE2ED}"), 4)
PKEY_GPS_Altitude = (IID("{827EDB4F-5B73-44A7-891D-FDFFABEA35CA}"), 100)
PKEY_GPS_AltitudeDenominator = (IID("{78342DCB-E358-4145-AE9A-6BFE4E0F9F51}"), 100)
PKEY_GPS_AltitudeNumerator = (IID("{2DAD1EB7-816D-40D3-9EC3-C9773BE2AADE}"), 100)
PKEY_GPS_AltitudeRef = (IID("{46AC629D-75EA-4515-867F-6DC4321C5844}"), 100)
PKEY_GPS_AreaInformation = (IID("{972E333E-AC7E-49F1-8ADF-A70D07A9BCAB}"), 100)
PKEY_GPS_Date = (IID("{3602C812-0F3B-45F0-85AD-603468D69423}"), 100)
PKEY_GPS_DestBearing = (IID("{C66D4B3C-E888-47CC-B99F-9DCA3EE34DEA}"), 100)
PKEY_GPS_DestBearingDenominator = (IID("{7ABCF4F8-7C3F-4988-AC91-8D2C2E97ECA5}"), 100)
PKEY_GPS_DestBearingNumerator = (IID("{BA3B1DA9-86EE-4B5D-A2A4-A271A429F0CF}"), 100)
PKEY_GPS_DestBearingRef = (IID("{9AB84393-2A0F-4B75-BB22-7279786977CB}"), 100)
PKEY_GPS_DestDistance = (IID("{A93EAE04-6804-4F24-AC81-09B266452118}"), 100)
PKEY_GPS_DestDistanceDenominator = (IID("{9BC2C99B-AC71-4127-9D1C-2596D0D7DCB7}"), 100)
PKEY_GPS_DestDistanceNumerator = (IID("{2BDA47DA-08C6-4FE1-80BC-A72FC517C5D0}"), 100)
PKEY_GPS_DestDistanceRef = (IID("{ED4DF2D3-8695-450B-856F-F5C1C53ACB66}"), 100)
PKEY_GPS_DestLatitude = (IID("{9D1D7CC5-5C39-451C-86B3-928E2D18CC47}"), 100)
PKEY_GPS_DestLatitudeDenominator = (IID("{3A372292-7FCA-49A7-99D5-E47BB2D4E7AB}"), 100)
PKEY_GPS_DestLatitudeNumerator = (IID("{ECF4B6F6-D5A6-433C-BB92-4076650FC890}"), 100)
PKEY_GPS_DestLatitudeRef = (IID("{CEA820B9-CE61-4885-A128-005D9087C192}"), 100)
PKEY_GPS_DestLongitude = (IID("{47A96261-CB4C-4807-8AD3-40B9D9DBC6BC}"), 100)
PKEY_GPS_DestLongitudeDenominator = (IID("{425D69E5-48AD-4900-8D80-6EB6B8D0AC86}"), 100)
PKEY_GPS_DestLongitudeNumerator = (IID("{A3250282-FB6D-48D5-9A89-DBCACE75CCCF}"), 100)
PKEY_GPS_DestLongitudeRef = (IID("{182C1EA6-7C1C-4083-AB4B-AC6C9F4ED128}"), 100)
PKEY_GPS_Differential = (IID("{AAF4EE25-BD3B-4DD7-BFC4-47F77BB00F6D}"), 100)
PKEY_GPS_DOP = (IID("{0CF8FB02-1837-42F1-A697-A7017AA289B9}"), 100)
PKEY_GPS_DOPDenominator = (IID("{A0BE94C5-50BA-487B-BD35-0654BE8881ED}"), 100)
PKEY_GPS_DOPNumerator = (IID("{47166B16-364F-4AA0-9F31-E2AB3DF449C3}"), 100)
PKEY_GPS_ImgDirection = (IID("{16473C91-D017-4ED9-BA4D-B6BAA55DBCF8}"), 100)
PKEY_GPS_ImgDirectionDenominator = (IID("{10B24595-41A2-4E20-93C2-5761C1395F32}"), 100)
PKEY_GPS_ImgDirectionNumerator = (IID("{DC5877C7-225F-45F7-BAC7-E81334B6130A}"), 100)
PKEY_GPS_ImgDirectionRef = (IID("{A4AAA5B7-1AD0-445F-811A-0F8F6E67F6B5}"), 100)
PKEY_GPS_Latitude = (IID("{8727CFFF-4868-4EC6-AD5B-81B98521D1AB}"), 100)
PKEY_GPS_LatitudeDenominator = (IID("{16E634EE-2BFF-497B-BD8A-4341AD39EEB9}"), 100)
PKEY_GPS_LatitudeNumerator = (IID("{7DDAAAD1-CCC8-41AE-B750-B2CB8031AEA2}"), 100)
PKEY_GPS_LatitudeRef = (IID("{029C0252-5B86-46C7-ACA0-2769FFC8E3D4}"), 100)
PKEY_GPS_Longitude = (IID("{C4C4DBB2-B593-466B-BBDA-D03D27D5E43A}"), 100)
PKEY_GPS_LongitudeDenominator = (IID("{BE6E176C-4534-4D2C-ACE5-31DEDAC1606B}"), 100)
PKEY_GPS_LongitudeNumerator = (IID("{02B0F689-A914-4E45-821D-1DDA452ED2C4}"), 100)
PKEY_GPS_LongitudeRef = (IID("{33DCF22B-28D5-464C-8035-1EE9EFD25278}"), 100)
PKEY_GPS_MapDatum = (IID("{2CA2DAE6-EDDC-407D-BEF1-773942ABFA95}"), 100)
PKEY_GPS_MeasureMode = (IID("{A015ED5D-AAEA-4D58-8A86-3C586920EA0B}"), 100)
PKEY_GPS_ProcessingMethod = (IID("{59D49E61-840F-4AA9-A939-E2099B7F6399}"), 100)
PKEY_GPS_Satellites = (IID("{467EE575-1F25-4557-AD4E-B8B58B0D9C15}"), 100)
PKEY_GPS_Speed = (IID("{DA5D0862-6E76-4E1B-BABD-70021BD25494}"), 100)
PKEY_GPS_SpeedDenominator = (IID("{7D122D5A-AE5E-4335-8841-D71E7CE72F53}"), 100)
PKEY_GPS_SpeedNumerator = (IID("{ACC9CE3D-C213-4942-8B48-6D0820F21C6D}"), 100)
PKEY_GPS_SpeedRef = (IID("{ECF7F4C9-544F-4D6D-9D98-8AD79ADAF453}"), 100)
PKEY_GPS_Status = (IID("{125491F4-818F-46B2-91B5-D537753617B2}"), 100)
PKEY_GPS_Track = (IID("{76C09943-7C33-49E3-9E7E-CDBA872CFADA}"), 100)
PKEY_GPS_TrackDenominator = (IID("{C8D1920C-01F6-40C0-AC86-2F3A4AD00770}"), 100)
PKEY_GPS_TrackNumerator = (IID("{702926F4-44A6-43E1-AE71-45627116893B}"), 100)
PKEY_GPS_TrackRef = (IID("{35DBE6FE-44C3-4400-AAAE-D2C799C407E8}"), 100)
PKEY_GPS_VersionID = (IID("{22704DA4-C6B2-4A99-8E56-F16DF8C92599}"), 100)
PKEY_Image_BitDepth = (IID("{6444048F-4C8B-11D1-8B70-080036B11A03}"), 7)
PKEY_Image_ColorSpace = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 40961)
PKEY_Image_CompressedBitsPerPixel = (IID("{364B6FA9-37AB-482A-BE2B-AE02F60D4318}"), 100)
PKEY_Image_CompressedBitsPerPixelDenominator = (
    IID("{1F8844E1-24AD-4508-9DFD-5326A415CE02}"),
    100,
)
PKEY_Image_CompressedBitsPerPixelNumerator = (
    IID("{D21A7148-D32C-4624-8900-277210F79C0F}"),
    100,
)
PKEY_Image_Compression = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 259)
PKEY_Image_CompressionText = (IID("{3F08E66F-2F44-4BB9-A682-AC35D2562322}"), 100)
PKEY_Image_Dimensions = (IID("{6444048F-4C8B-11D1-8B70-080036B11A03}"), 13)
PKEY_Image_HorizontalResolution = (IID("{6444048F-4C8B-11D1-8B70-080036B11A03}"), 5)
PKEY_Image_HorizontalSize = (IID("{6444048F-4C8B-11D1-8B70-080036B11A03}"), 3)
PKEY_Image_ImageID = (IID("{10DABE05-32AA-4C29-BF1A-63E2D220587F}"), 100)
PKEY_Image_ResolutionUnit = (IID("{19B51FA6-1F92-4A5C-AB48-7DF0ABD67444}"), 100)
PKEY_Image_VerticalResolution = (IID("{6444048F-4C8B-11D1-8B70-080036B11A03}"), 6)
PKEY_Image_VerticalSize = (IID("{6444048F-4C8B-11D1-8B70-080036B11A03}"), 4)
PKEY_Journal_Contacts = (IID("{DEA7C82C-1D89-4A66-9427-A4E3DEBABCB1}"), 100)
PKEY_Journal_EntryType = (IID("{95BEB1FC-326D-4644-B396-CD3ED90E6DDF}"), 100)
PKEY_Link_Comment = (IID("{B9B4B3FC-2B51-4A42-B5D8-324146AFCF25}"), 5)
PKEY_Link_DateVisited = (IID("{5CBF2787-48CF-4208-B90E-EE5E5D420294}"), 23)
PKEY_Link_Description = (IID("{5CBF2787-48CF-4208-B90E-EE5E5D420294}"), 21)
PKEY_Link_Status = (IID("{B9B4B3FC-2B51-4A42-B5D8-324146AFCF25}"), 3)
PKEY_Link_TargetExtension = (IID("{7A7D76F4-B630-4BD7-95FF-37CC51A975C9}"), 2)
PKEY_Link_TargetParsingPath = (IID("{B9B4B3FC-2B51-4A42-B5D8-324146AFCF25}"), 2)
PKEY_Link_TargetSFGAOFlags = (IID("{B9B4B3FC-2B51-4A42-B5D8-324146AFCF25}"), 8)
PKEY_Media_AuthorUrl = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 32)
PKEY_Media_AverageLevel = (IID("{09EDD5B6-B301-43C5-9990-D00302EFFD46}"), 100)
PKEY_Media_ClassPrimaryID = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 13)
PKEY_Media_ClassSecondaryID = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 14)
PKEY_Media_CollectionGroupID = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 24)
PKEY_Media_CollectionID = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 25)
PKEY_Media_ContentDistributor = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 18)
PKEY_Media_ContentID = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 26)
PKEY_Media_CreatorApplication = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 27)
PKEY_Media_CreatorApplicationVersion = (
    IID("{64440492-4C8B-11D1-8B70-080036B11A03}"),
    28,
)
PKEY_Media_DateEncoded = (IID("{2E4B640D-5019-46D8-8881-55414CC5CAA0}"), 100)
PKEY_Media_DateReleased = (IID("{DE41CC29-6971-4290-B472-F59F2E2F31E2}"), 100)
PKEY_Media_Duration = (IID("{64440490-4C8B-11D1-8B70-080036B11A03}"), 3)
PKEY_Media_DVDID = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 15)
PKEY_Media_EncodedBy = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 36)
PKEY_Media_EncodingSettings = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 37)
PKEY_Media_FrameCount = (IID("{6444048F-4C8B-11D1-8B70-080036B11A03}"), 12)
PKEY_Media_MCDI = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 16)
PKEY_Media_MetadataContentProvider = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 17)
PKEY_Media_Producer = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 22)
PKEY_Media_PromotionUrl = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 33)
PKEY_Media_ProtectionType = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 38)
PKEY_Media_ProviderRating = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 39)
PKEY_Media_ProviderStyle = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 40)
PKEY_Media_Publisher = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 30)
PKEY_Media_SubscriptionContentId = (IID("{9AEBAE7A-9644-487D-A92C-657585ED751A}"), 100)
PKEY_Media_SubTitle = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 38)
PKEY_Media_UniqueFileIdentifier = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 35)
PKEY_Media_UserNoAutoInfo = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 41)
PKEY_Media_UserWebUrl = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 34)
PKEY_Media_Writer = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 23)
PKEY_Media_Year = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 5)
PKEY_Message_AttachmentContents = (IID("{3143BF7C-80A8-4854-8880-E2E40189BDD0}"), 100)
PKEY_Message_AttachmentNames = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 21)
PKEY_Message_BccAddress = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 2)
PKEY_Message_BccName = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 3)
PKEY_Message_CcAddress = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 4)
PKEY_Message_CcName = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 5)
PKEY_Message_ConversationID = (IID("{DC8F80BD-AF1E-4289-85B6-3DFC1B493992}"), 100)
PKEY_Message_ConversationIndex = (IID("{DC8F80BD-AF1E-4289-85B6-3DFC1B493992}"), 101)
PKEY_Message_DateReceived = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 20)
PKEY_Message_DateSent = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 19)
PKEY_Message_FromAddress = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 13)
PKEY_Message_FromName = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 14)
PKEY_Message_HasAttachments = (IID("{9C1FCF74-2D97-41BA-B4AE-CB2E3661A6E4}"), 8)
PKEY_Message_IsFwdOrReply = (IID("{9A9BC088-4F6D-469E-9919-E705412040F9}"), 100)
PKEY_Message_MessageClass = (IID("{CD9ED458-08CE-418F-A70E-F912C7BB9C5C}"), 103)
PKEY_Message_SenderAddress = (IID("{0BE1C8E7-1981-4676-AE14-FDD78F05A6E7}"), 100)
PKEY_Message_SenderName = (IID("{0DA41CFA-D224-4A18-AE2F-596158DB4B3A}"), 100)
PKEY_Message_Store = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 15)
PKEY_Message_ToAddress = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 16)
PKEY_Message_ToDoTitle = (IID("{BCCC8A3C-8CEF-42E5-9B1C-C69079398BC7}"), 100)
PKEY_Message_ToName = (IID("{E3E0584C-B788-4A5A-BB20-7F5A44C9ACDD}"), 17)
PKEY_Music_AlbumArtist = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 13)
PKEY_Music_AlbumTitle = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 4)
PKEY_Music_Artist = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 2)
PKEY_Music_BeatsPerMinute = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 35)
PKEY_Music_Composer = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 19)
PKEY_Music_Conductor = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 36)
PKEY_Music_ContentGroupDescription = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 33)
PKEY_Music_Genre = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 11)
PKEY_Music_InitialKey = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 34)
PKEY_Music_Lyrics = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 12)
PKEY_Music_Mood = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 39)
PKEY_Music_PartOfSet = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 37)
PKEY_Music_Period = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 31)
PKEY_Music_SynchronizedLyrics = (IID("{6B223B6A-162E-4AA9-B39F-05D678FC6D77}"), 100)
PKEY_Music_TrackNumber = (IID("{56A3372E-CE9C-11D2-9F0E-006097C686F6}"), 7)
PKEY_Note_Color = (IID("{4776CAFA-BCE4-4CB1-A23E-265E76D8EB11}"), 100)
PKEY_Note_ColorText = (IID("{46B4E8DE-CDB2-440D-885C-1658EB65B914}"), 100)
PKEY_Photo_Aperture = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37378)
PKEY_Photo_ApertureDenominator = (IID("{E1A9A38B-6685-46BD-875E-570DC7AD7320}"), 100)
PKEY_Photo_ApertureNumerator = (IID("{0337ECEC-39FB-4581-A0BD-4C4CC51E9914}"), 100)
PKEY_Photo_Brightness = (IID("{1A701BF6-478C-4361-83AB-3701BB053C58}"), 100)
PKEY_Photo_BrightnessDenominator = (IID("{6EBE6946-2321-440A-90F0-C043EFD32476}"), 100)
PKEY_Photo_BrightnessNumerator = (IID("{9E7D118F-B314-45A0-8CFB-D654B917C9E9}"), 100)
PKEY_Photo_CameraManufacturer = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 271)
PKEY_Photo_CameraModel = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 272)
PKEY_Photo_CameraSerialNumber = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 273)
PKEY_Photo_Contrast = (IID("{2A785BA9-8D23-4DED-82E6-60A350C86A10}"), 100)
PKEY_Photo_ContrastText = (IID("{59DDE9F2-5253-40EA-9A8B-479E96C6249A}"), 100)
PKEY_Photo_DateTaken = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 36867)
PKEY_Photo_DigitalZoom = (IID("{F85BF840-A925-4BC2-B0C4-8E36B598679E}"), 100)
PKEY_Photo_DigitalZoomDenominator = (IID("{745BAF0E-E5C1-4CFB-8A1B-D031A0A52393}"), 100)
PKEY_Photo_DigitalZoomNumerator = (IID("{16CBB924-6500-473B-A5BE-F1599BCBE413}"), 100)
PKEY_Photo_Event = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 18248)
PKEY_Photo_EXIFVersion = (IID("{D35F743A-EB2E-47F2-A286-844132CB1427}"), 100)
PKEY_Photo_ExposureBias = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37380)
PKEY_Photo_ExposureBiasDenominator = (
    IID("{AB205E50-04B7-461C-A18C-2F233836E627}"),
    100,
)
PKEY_Photo_ExposureBiasNumerator = (IID("{738BF284-1D87-420B-92CF-5834BF6EF9ED}"), 100)
PKEY_Photo_ExposureIndex = (IID("{967B5AF8-995A-46ED-9E11-35B3C5B9782D}"), 100)
PKEY_Photo_ExposureIndexDenominator = (
    IID("{93112F89-C28B-492F-8A9D-4BE2062CEE8A}"),
    100,
)
PKEY_Photo_ExposureIndexNumerator = (IID("{CDEDCF30-8919-44DF-8F4C-4EB2FFDB8D89}"), 100)
PKEY_Photo_ExposureProgram = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 34850)
PKEY_Photo_ExposureProgramText = (IID("{FEC690B7-5F30-4646-AE47-4CAAFBA884A3}"), 100)
PKEY_Photo_ExposureTime = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 33434)
PKEY_Photo_ExposureTimeDenominator = (
    IID("{55E98597-AD16-42E0-B624-21599A199838}"),
    100,
)
PKEY_Photo_ExposureTimeNumerator = (IID("{257E44E2-9031-4323-AC38-85C552871B2E}"), 100)
PKEY_Photo_Flash = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37385)
PKEY_Photo_FlashEnergy = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 41483)
PKEY_Photo_FlashEnergyDenominator = (IID("{D7B61C70-6323-49CD-A5FC-C84277162C97}"), 100)
PKEY_Photo_FlashEnergyNumerator = (IID("{FCAD3D3D-0858-400F-AAA3-2F66CCE2A6BC}"), 100)
PKEY_Photo_FlashManufacturer = (IID("{AABAF6C9-E0C5-4719-8585-57B103E584FE}"), 100)
PKEY_Photo_FlashModel = (IID("{FE83BB35-4D1A-42E2-916B-06F3E1AF719E}"), 100)
PKEY_Photo_FlashText = (IID("{6B8B68F6-200B-47EA-8D25-D8050F57339F}"), 100)
PKEY_Photo_FNumber = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 33437)
PKEY_Photo_FNumberDenominator = (IID("{E92A2496-223B-4463-A4E3-30EABBA79D80}"), 100)
PKEY_Photo_FNumberNumerator = (IID("{1B97738A-FDFC-462F-9D93-1957E08BE90C}"), 100)
PKEY_Photo_FocalLength = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37386)
PKEY_Photo_FocalLengthDenominator = (IID("{305BC615-DCA1-44A5-9FD4-10C0BA79412E}"), 100)
PKEY_Photo_FocalLengthInFilm = (IID("{A0E74609-B84D-4F49-B860-462BD9971F98}"), 100)
PKEY_Photo_FocalLengthNumerator = (IID("{776B6B3B-1E3D-4B0C-9A0E-8FBAF2A8492A}"), 100)
PKEY_Photo_FocalPlaneXResolution = (IID("{CFC08D97-C6F7-4484-89DD-EBEF4356FE76}"), 100)
PKEY_Photo_FocalPlaneXResolutionDenominator = (
    IID("{0933F3F5-4786-4F46-A8E8-D64DD37FA521}"),
    100,
)
PKEY_Photo_FocalPlaneXResolutionNumerator = (
    IID("{DCCB10AF-B4E2-4B88-95F9-031B4D5AB490}"),
    100,
)
PKEY_Photo_FocalPlaneYResolution = (IID("{4FFFE4D0-914F-4AC4-8D6F-C9C61DE169B1}"), 100)
PKEY_Photo_FocalPlaneYResolutionDenominator = (
    IID("{1D6179A6-A876-4031-B013-3347B2B64DC8}"),
    100,
)
PKEY_Photo_FocalPlaneYResolutionNumerator = (
    IID("{A2E541C5-4440-4BA8-867E-75CFC06828CD}"),
    100,
)
PKEY_Photo_GainControl = (IID("{FA304789-00C7-4D80-904A-1E4DCC7265AA}"), 100)
PKEY_Photo_GainControlDenominator = (IID("{42864DFD-9DA4-4F77-BDED-4AAD7B256735}"), 100)
PKEY_Photo_GainControlNumerator = (IID("{8E8ECF7C-B7B8-4EB8-A63F-0EE715C96F9E}"), 100)
PKEY_Photo_GainControlText = (IID("{C06238B2-0BF9-4279-A723-25856715CB9D}"), 100)
PKEY_Photo_ISOSpeed = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 34855)
PKEY_Photo_LensManufacturer = (IID("{E6DDCAF7-29C5-4F0A-9A68-D19412EC7090}"), 100)
PKEY_Photo_LensModel = (IID("{E1277516-2B5F-4869-89B1-2E585BD38B7A}"), 100)
PKEY_Photo_LightSource = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37384)
PKEY_Photo_MakerNote = (IID("{FA303353-B659-4052-85E9-BCAC79549B84}"), 100)
PKEY_Photo_MakerNoteOffset = (IID("{813F4124-34E6-4D17-AB3E-6B1F3C2247A1}"), 100)
PKEY_Photo_MaxAperture = (IID("{08F6D7C2-E3F2-44FC-AF1E-5AA5C81A2D3E}"), 100)
PKEY_Photo_MaxApertureDenominator = (IID("{C77724D4-601F-46C5-9B89-C53F93BCEB77}"), 100)
PKEY_Photo_MaxApertureNumerator = (IID("{C107E191-A459-44C5-9AE6-B952AD4B906D}"), 100)
PKEY_Photo_MeteringMode = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37383)
PKEY_Photo_MeteringModeText = (IID("{F628FD8C-7BA8-465A-A65B-C5AA79263A9E}"), 100)
PKEY_Photo_Orientation = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 274)
PKEY_Photo_OrientationText = (IID("{A9EA193C-C511-498A-A06B-58E2776DCC28}"), 100)
PKEY_Photo_PhotometricInterpretation = (
    IID("{341796F1-1DF9-4B1C-A564-91BDEFA43877}"),
    100,
)
PKEY_Photo_PhotometricInterpretationText = (
    IID("{821437D6-9EAB-4765-A589-3B1CBBD22A61}"),
    100,
)
PKEY_Photo_ProgramMode = (IID("{6D217F6D-3F6A-4825-B470-5F03CA2FBE9B}"), 100)
PKEY_Photo_ProgramModeText = (IID("{7FE3AA27-2648-42F3-89B0-454E5CB150C3}"), 100)
PKEY_Photo_RelatedSoundFile = (IID("{318A6B45-087F-4DC2-B8CC-05359551FC9E}"), 100)
PKEY_Photo_Saturation = (IID("{49237325-A95A-4F67-B211-816B2D45D2E0}"), 100)
PKEY_Photo_SaturationText = (IID("{61478C08-B600-4A84-BBE4-E99C45F0A072}"), 100)
PKEY_Photo_Sharpness = (IID("{FC6976DB-8349-4970-AE97-B3C5316A08F0}"), 100)
PKEY_Photo_SharpnessText = (IID("{51EC3F47-DD50-421D-8769-334F50424B1E}"), 100)
PKEY_Photo_ShutterSpeed = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37377)
PKEY_Photo_ShutterSpeedDenominator = (
    IID("{E13D8975-81C7-4948-AE3F-37CAE11E8FF7}"),
    100,
)
PKEY_Photo_ShutterSpeedNumerator = (IID("{16EA4042-D6F4-4BCA-8349-7C78D30FB333}"), 100)
PKEY_Photo_SubjectDistance = (IID("{14B81DA1-0135-4D31-96D9-6CBFC9671A99}"), 37382)
PKEY_Photo_SubjectDistanceDenominator = (
    IID("{0C840A88-B043-466D-9766-D4B26DA3FA77}"),
    100,
)
PKEY_Photo_SubjectDistanceNumerator = (
    IID("{8AF4961C-F526-43E5-AA81-DB768219178D}"),
    100,
)
PKEY_Photo_TranscodedForSync = (IID("{9A8EBB75-6458-4E82-BACB-35C0095B03BB}"), 100)
PKEY_Photo_WhiteBalance = (IID("{EE3D3D8A-5381-4CFA-B13B-AAF66B5F4EC9}"), 100)
PKEY_Photo_WhiteBalanceText = (IID("{6336B95E-C7A7-426D-86FD-7AE3D39C84B4}"), 100)
PKEY_PropGroup_Advanced = (IID("{900A403B-097B-4B95-8AE2-071FDAEEB118}"), 100)
PKEY_PropGroup_Audio = (IID("{2804D469-788F-48AA-8570-71B9C187E138}"), 100)
PKEY_PropGroup_Calendar = (IID("{9973D2B5-BFD8-438A-BA94-5349B293181A}"), 100)
PKEY_PropGroup_Camera = (IID("{DE00DE32-547E-4981-AD4B-542F2E9007D8}"), 100)
PKEY_PropGroup_Contact = (IID("{DF975FD3-250A-4004-858F-34E29A3E37AA}"), 100)
PKEY_PropGroup_Content = (IID("{D0DAB0BA-368A-4050-A882-6C010FD19A4F}"), 100)
PKEY_PropGroup_Description = (IID("{8969B275-9475-4E00-A887-FF93B8B41E44}"), 100)
PKEY_PropGroup_FileSystem = (IID("{E3A7D2C1-80FC-4B40-8F34-30EA111BDC2E}"), 100)
PKEY_PropGroup_General = (IID("{CC301630-B192-4C22-B372-9F4C6D338E07}"), 100)
PKEY_PropGroup_GPS = (IID("{F3713ADA-90E3-4E11-AAE5-FDC17685B9BE}"), 100)
PKEY_PropGroup_Image = (IID("{E3690A87-0FA8-4A2A-9A9F-FCE8827055AC}"), 100)
PKEY_PropGroup_Media = (IID("{61872CF7-6B5E-4B4B-AC2D-59DA84459248}"), 100)
PKEY_PropGroup_MediaAdvanced = (IID("{8859A284-DE7E-4642-99BA-D431D044B1EC}"), 100)
PKEY_PropGroup_Message = (IID("{7FD7259D-16B4-4135-9F97-7C96ECD2FA9E}"), 100)
PKEY_PropGroup_Music = (IID("{68DD6094-7216-40F1-A029-43FE7127043F}"), 100)
PKEY_PropGroup_Origin = (IID("{2598D2FB-5569-4367-95DF-5CD3A177E1A5}"), 100)
PKEY_PropGroup_PhotoAdvanced = (IID("{0CB2BF5A-9EE7-4A86-8222-F01E07FDADAF}"), 100)
PKEY_PropGroup_RecordedTV = (IID("{E7B33238-6584-4170-A5C0-AC25EFD9DA56}"), 100)
PKEY_PropGroup_Video = (IID("{BEBE0920-7671-4C54-A3EB-49FDDFC191EE}"), 100)
PKEY_PropList_ConflictPrompt = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 11)
PKEY_PropList_ExtendedTileInfo = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 9)
PKEY_PropList_FileOperationPrompt = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 10)
PKEY_PropList_FullDetails = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 2)
PKEY_PropList_InfoTip = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 4)
PKEY_PropList_NonPersonal = (IID("{49D1091F-082E-493F-B23F-D2308AA9668C}"), 100)
PKEY_PropList_PreviewDetails = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 8)
PKEY_PropList_PreviewTitle = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 6)
PKEY_PropList_QuickTip = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 5)
PKEY_PropList_TileInfo = (IID("{C9944A21-A406-48FE-8225-AEC7E24C211B}"), 3)
PKEY_PropList_XPDetailsPanel = (IID("{F2275480-F782-4291-BD94-F13693513AEC}"), 0)
PKEY_RecordedTV_ChannelNumber = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 7)
PKEY_RecordedTV_Credits = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 4)
PKEY_RecordedTV_DateContentExpires = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 15)
PKEY_RecordedTV_EpisodeName = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 2)
PKEY_RecordedTV_IsATSCContent = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 16)
PKEY_RecordedTV_IsClosedCaptioningAvailable = (
    IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"),
    12,
)
PKEY_RecordedTV_IsDTVContent = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 17)
PKEY_RecordedTV_IsHDContent = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 18)
PKEY_RecordedTV_IsRepeatBroadcast = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 13)
PKEY_RecordedTV_IsSAP = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 14)
PKEY_RecordedTV_NetworkAffiliation = (
    IID("{2C53C813-FB63-4E22-A1AB-0B331CA1E273}"),
    100,
)
PKEY_RecordedTV_OriginalBroadcastDate = (
    IID("{4684FE97-8765-4842-9C13-F006447B178C}"),
    100,
)
PKEY_RecordedTV_ProgramDescription = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 3)
PKEY_RecordedTV_RecordingTime = (IID("{A5477F61-7A82-4ECA-9DDE-98B69B2479B3}"), 100)
PKEY_RecordedTV_StationCallSign = (IID("{6D748DE2-8D38-4CC3-AC60-F009B057C557}"), 5)
PKEY_RecordedTV_StationName = (IID("{1B5439E7-EBA1-4AF8-BDD7-7AF1D4549493}"), 100)
PKEY_Search_AutoSummary = (IID("{560C36C0-503A-11CF-BAA1-00004C752A9A}"), 2)
PKEY_Search_ContainerHash = (IID("{BCEEE283-35DF-4D53-826A-F36A3EEFC6BE}"), 100)
PKEY_Search_Contents = (IID("{B725F130-47EF-101A-A5F1-02608C9EEBAC}"), 19)
PKEY_Search_EntryID = (IID("{49691C90-7E17-101A-A91C-08002B2ECDA9}"), 5)
PKEY_Search_GatherTime = (IID("{0B63E350-9CCC-11D0-BCDB-00805FCCCE04}"), 8)
PKEY_Search_IsClosedDirectory = (IID("{0B63E343-9CCC-11D0-BCDB-00805FCCCE04}"), 23)
PKEY_Search_IsFullyContained = (IID("{0B63E343-9CCC-11D0-BCDB-00805FCCCE04}"), 24)
PKEY_Search_QueryFocusedSummary = (IID("{560C36C0-503A-11CF-BAA1-00004C752A9A}"), 3)
PKEY_Search_Rank = (IID("{49691C90-7E17-101A-A91C-08002B2ECDA9}"), 3)
PKEY_Search_Store = (IID("{A06992B3-8CAF-4ED7-A547-B259E32AC9FC}"), 100)
PKEY_Search_UrlToIndex = (IID("{0B63E343-9CCC-11D0-BCDB-00805FCCCE04}"), 2)
PKEY_Search_UrlToIndexWithModificationTime = (
    IID("{0B63E343-9CCC-11D0-BCDB-00805FCCCE04}"),
    12,
)
PKEY_DescriptionID = (IID("{28636AA6-953D-11D2-B5D6-00C04FD918D0}"), 2)
PKEY_Link_TargetSFGAOFlagsStrings = (IID("{D6942081-D53B-443D-AD47-5E059D9CD27A}"), 3)
PKEY_Link_TargetUrl = (IID("{5CBF2787-48CF-4208-B90E-EE5E5D420294}"), 2)
PKEY_Shell_SFGAOFlagsStrings = (IID("{D6942081-D53B-443D-AD47-5E059D9CD27A}"), 2)
PKEY_Software_DateLastUsed = (IID("{841E4F90-FF59-4D16-8947-E81BBFFAB36D}"), 16)
PKEY_Software_ProductName = (IID("{0CEF7D53-FA64-11D1-A203-0000F81FEDEE}"), 7)
PKEY_Sync_Comments = (IID("{7BD5533E-AF15-44DB-B8C8-BD6624E1D032}"), 13)
PKEY_Sync_ConflictDescription = (IID("{CE50C159-2FB8-41FD-BE68-D3E042E274BC}"), 4)
PKEY_Sync_ConflictFirstLocation = (IID("{CE50C159-2FB8-41FD-BE68-D3E042E274BC}"), 6)
PKEY_Sync_ConflictSecondLocation = (IID("{CE50C159-2FB8-41FD-BE68-D3E042E274BC}"), 7)
PKEY_Sync_HandlerCollectionID = (IID("{7BD5533E-AF15-44DB-B8C8-BD6624E1D032}"), 2)
PKEY_Sync_HandlerID = (IID("{7BD5533E-AF15-44DB-B8C8-BD6624E1D032}"), 3)
PKEY_Sync_HandlerName = (IID("{CE50C159-2FB8-41FD-BE68-D3E042E274BC}"), 2)
PKEY_Sync_HandlerType = (IID("{7BD5533E-AF15-44DB-B8C8-BD6624E1D032}"), 8)
PKEY_Sync_HandlerTypeLabel = (IID("{7BD5533E-AF15-44DB-B8C8-BD6624E1D032}"), 9)
PKEY_Sync_ItemID = (IID("{7BD5533E-AF15-44DB-B8C8-BD6624E1D032}"), 6)
PKEY_Sync_ItemName = (IID("{CE50C159-2FB8-41FD-BE68-D3E042E274BC}"), 3)
PKEY_Task_BillingInformation = (IID("{D37D52C6-261C-4303-82B3-08B926AC6F12}"), 100)
PKEY_Task_CompletionStatus = (IID("{084D8A0A-E6D5-40DE-BF1F-C8820E7C877C}"), 100)
PKEY_Task_Owner = (IID("{08C7CC5F-60F2-4494-AD75-55E3E0B5ADD0}"), 100)
PKEY_Video_Compression = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 10)
PKEY_Video_Director = (IID("{64440492-4C8B-11D1-8B70-080036B11A03}"), 20)
PKEY_Video_EncodingBitrate = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 8)
PKEY_Video_FourCC = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 44)
PKEY_Video_FrameHeight = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 4)
PKEY_Video_FrameRate = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 6)
PKEY_Video_FrameWidth = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 3)
PKEY_Video_HorizontalAspectRatio = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 42)
PKEY_Video_SampleSize = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 9)
PKEY_Video_StreamName = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 2)
PKEY_Video_StreamNumber = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 11)
PKEY_Video_TotalBitrate = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 43)
PKEY_Video_VerticalAspectRatio = (IID("{64440491-4C8B-11D1-8B70-080036B11A03}"), 45)
PKEY_Volume_FileSystem = (IID("{9B174B35-40FF-11D2-A27E-00C04FC30871}"), 4)
PKEY_Volume_IsMappedDrive = (IID("{149C0B69-2C2D-48FC-808F-D318D78C4636}"), 2)
PKEY_Volume_IsRoot = (IID("{9B174B35-40FF-11D2-A27E-00C04FC30871}"), 10)

PKEY_AppUserModel_RelaunchCommand = (IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 2)
PKEY_AppUserModel_RelaunchIconResource = (
    IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"),
    3,
)
PKEY_AppUserModel_RelaunchDisplayNameResource = (
    IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"),
    4,
)
PKEY_AppUserModel_ID = (IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 5)
PKEY_AppUserModel_IsDestListSeparator = (
    IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"),
    6,
)
PKEY_AppUserModel_ExcludeFromShowInNewInstall = (
    IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"),
    8,
)
PKEY_AppUserModel_PreventPinning = (IID("{9F4C2855-9F79-4B39-A8D0-E1D42DE1D5F3}"), 9)

# PKA_FLAGS, used with IPropertyChange
PKA_SET = 0
PKA_APPEND = 1
PKA_DELETE = 2

# === NexusCore/openenv\Lib\site-packages\litellm\responses\main.py ===
import asyncio
import contextvars
from functools import partial
from typing import Any, Coroutine, Dict, Iterable, List, Literal, Optional, Union

import httpx

import litellm
from litellm.constants import request_timeout
from litellm.litellm_core_utils.litellm_logging import Logging as LiteLLMLoggingObj
from litellm.llms.base_llm.responses.transformation import BaseResponsesAPIConfig
from litellm.llms.custom_httpx.llm_http_handler import BaseLLMHTTPHandler
from litellm.responses.litellm_completion_transformation.handler import (
    LiteLLMCompletionTransformationHandler,
)
from litellm.responses.utils import ResponsesAPIRequestUtils
from litellm.types.llms.openai import (
    PromptObject,
    Reasoning,
    ResponseIncludable,
    ResponseInputParam,
    ResponsesAPIOptionalRequestParams,
    ResponsesAPIResponse,
    ResponseTextConfigParam,
    ToolChoice,
    ToolParam,
)
from litellm.types.responses.main import *
from litellm.types.router import GenericLiteLLMParams
from litellm.utils import ProviderConfigManager, client

from .streaming_iterator import BaseResponsesAPIStreamingIterator

####### ENVIRONMENT VARIABLES ###################
# Initialize any necessary instances or variables here
base_llm_http_handler = BaseLLMHTTPHandler()
litellm_completion_transformation_handler = LiteLLMCompletionTransformationHandler()
#################################################


def mock_responses_api_response(
    mock_response: str = "In a peaceful grove beneath a silver moon, a unicorn named Lumina discovered a hidden pool that reflected the stars. As she dipped her horn into the water, the pool began to shimmer, revealing a pathway to a magical realm of endless night skies. Filled with wonder, Lumina whispered a wish for all who dream to find their own hidden magic, and as she glanced back, her hoofprints sparkled like stardust.",
):
    return ResponsesAPIResponse(
        **{  # type: ignore
            "id": "resp_67ccd2bed1ec8190b14f964abc0542670bb6a6b452d3795b",
            "object": "response",
            "created_at": 1741476542,
            "status": "completed",
            "error": None,
            "incomplete_details": None,
            "instructions": None,
            "max_output_tokens": None,
            "model": "gpt-4.1-2025-04-14",
            "output": [
                {
                    "type": "message",
                    "id": "msg_67ccd2bf17f0819081ff3bb2cf6508e60bb6a6b452d3795b",
                    "status": "completed",
                    "role": "assistant",
                    "content": [
                        {
                            "type": "output_text",
                            "text": mock_response,
                            "annotations": [],
                        }
                    ],
                }
            ],
            "parallel_tool_calls": True,
            "previous_response_id": None,
            "reasoning": {"effort": None, "summary": None},
            "store": True,
            "temperature": 1.0,
            "text": {"format": {"type": "text"}},
            "tool_choice": "auto",
            "tools": [],
            "top_p": 1.0,
            "truncation": "disabled",
            "usage": {
                "input_tokens": 36,
                "input_tokens_details": {"cached_tokens": 0},
                "output_tokens": 87,
                "output_tokens_details": {"reasoning_tokens": 0},
                "total_tokens": 123,
            },
            "user": None,
            "metadata": {},
        }
    )


@client
async def aresponses(
    input: Union[str, ResponseInputParam],
    model: str,
    include: Optional[List[ResponseIncludable]] = None,
    instructions: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    prompt: Optional[PromptObject] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parallel_tool_calls: Optional[bool] = None,
    previous_response_id: Optional[str] = None,
    reasoning: Optional[Reasoning] = None,
    store: Optional[bool] = None,
    background: Optional[bool] = None,
    stream: Optional[bool] = None,
    temperature: Optional[float] = None,
    text: Optional[ResponseTextConfigParam] = None,
    tool_choice: Optional[ToolChoice] = None,
    tools: Optional[Iterable[ToolParam]] = None,
    top_p: Optional[float] = None,
    truncation: Optional[Literal["auto", "disabled"]] = None,
    user: Optional[str] = None,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[ResponsesAPIResponse, BaseResponsesAPIStreamingIterator]:
    """
    Async: Handles responses API requests by reusing the synchronous function
    """
    local_vars = locals()
    try:
        loop = asyncio.get_event_loop()
        kwargs["aresponses"] = True

        # get custom llm provider so we can use this for mapping exceptions
        if custom_llm_provider is None:
            _, custom_llm_provider, _, _ = litellm.get_llm_provider(
                model=model, api_base=local_vars.get("base_url", None)
            )

        func = partial(
            responses,
            input=input,
            model=model,
            include=include,
            instructions=instructions,
            max_output_tokens=max_output_tokens,
            prompt=prompt,
            metadata=metadata,
            parallel_tool_calls=parallel_tool_calls,
            previous_response_id=previous_response_id,
            reasoning=reasoning,
            store=store,
            background=background,
            stream=stream,
            temperature=temperature,
            text=text,
            tool_choice=tool_choice,
            tools=tools,
            top_p=top_p,
            truncation=truncation,
            user=user,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
            custom_llm_provider=custom_llm_provider,
            **kwargs,
        )

        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)

        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response

        # Update the responses_api_response_id with the model_id
        if isinstance(response, ResponsesAPIResponse):
            response = ResponsesAPIRequestUtils._update_responses_api_response_id_with_model_id(
                responses_api_response=response,
                litellm_metadata=kwargs.get("litellm_metadata", {}),
                custom_llm_provider=custom_llm_provider,
            )
        return response
    except Exception as e:
        raise litellm.exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
def responses(
    input: Union[str, ResponseInputParam],
    model: str,
    include: Optional[List[ResponseIncludable]] = None,
    instructions: Optional[str] = None,
    max_output_tokens: Optional[int] = None,
    prompt: Optional[PromptObject] = None,
    metadata: Optional[Dict[str, Any]] = None,
    parallel_tool_calls: Optional[bool] = None,
    previous_response_id: Optional[str] = None,
    reasoning: Optional[Reasoning] = None,
    store: Optional[bool] = None,
    background: Optional[bool] = None,
    stream: Optional[bool] = None,
    temperature: Optional[float] = None,
    text: Optional[ResponseTextConfigParam] = None,
    tool_choice: Optional[ToolChoice] = None,
    tools: Optional[Iterable[ToolParam]] = None,
    top_p: Optional[float] = None,
    truncation: Optional[Literal["auto", "disabled"]] = None,
    user: Optional[str] = None,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
):
    """
    Synchronous version of the Responses API.
    Uses the synchronous HTTP handler to make requests.
    """
    local_vars = locals()
    try:
        litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
        litellm_call_id: Optional[str] = kwargs.get("litellm_call_id", None)
        _is_async = kwargs.pop("aresponses", False) is True

        # get llm provider logic
        litellm_params = GenericLiteLLMParams(**kwargs)

        ## MOCK RESPONSE LOGIC
        if litellm_params.mock_response and isinstance(
            litellm_params.mock_response, str
        ):
            return mock_responses_api_response(
                mock_response=litellm_params.mock_response
            )

        (
            model,
            custom_llm_provider,
            dynamic_api_key,
            dynamic_api_base,
        ) = litellm.get_llm_provider(
            model=model,
            custom_llm_provider=custom_llm_provider,
            api_base=litellm_params.api_base,
            api_key=litellm_params.api_key,
        )

        # get provider config
        responses_api_provider_config: Optional[BaseResponsesAPIConfig] = (
            ProviderConfigManager.get_provider_responses_api_config(
                model=model,
                provider=litellm.LlmProviders(custom_llm_provider),
            )
        )

        local_vars.update(kwargs)
        # Get ResponsesAPIOptionalRequestParams with only valid parameters
        response_api_optional_params: ResponsesAPIOptionalRequestParams = (
            ResponsesAPIRequestUtils.get_requested_response_api_optional_param(
                local_vars
            )
        )

        if responses_api_provider_config is None:
            return litellm_completion_transformation_handler.response_api_handler(
                model=model,
                input=input,
                responses_api_request=response_api_optional_params,
                custom_llm_provider=custom_llm_provider,
                _is_async=_is_async,
                stream=stream,
                **kwargs,
            )

        # Get optional parameters for the responses API
        responses_api_request_params: Dict = (
            ResponsesAPIRequestUtils.get_optional_params_responses_api(
                model=model,
                responses_api_provider_config=responses_api_provider_config,
                response_api_optional_params=response_api_optional_params,
            )
        )

        # Pre Call logging
        litellm_logging_obj.update_environment_variables(
            model=model,
            user=user,
            optional_params=dict(responses_api_request_params),
            litellm_params={
                "litellm_call_id": litellm_call_id,
                **responses_api_request_params,
            },
            custom_llm_provider=custom_llm_provider,
        )

        # Call the handler with _is_async flag instead of directly calling the async handler
        response = base_llm_http_handler.response_api_handler(
            model=model,
            input=input,
            responses_api_provider_config=responses_api_provider_config,
            response_api_optional_request_params=responses_api_request_params,
            custom_llm_provider=custom_llm_provider,
            litellm_params=litellm_params,
            logging_obj=litellm_logging_obj,
            extra_headers=extra_headers,
            extra_body=extra_body,
            timeout=timeout or request_timeout,
            _is_async=_is_async,
            client=kwargs.get("client"),
            fake_stream=responses_api_provider_config.should_fake_stream(
                model=model, stream=stream, custom_llm_provider=custom_llm_provider
            ),
            litellm_metadata=kwargs.get("litellm_metadata", {}),
        )

        # Update the responses_api_response_id with the model_id
        if isinstance(response, ResponsesAPIResponse):
            response = ResponsesAPIRequestUtils._update_responses_api_response_id_with_model_id(
                responses_api_response=response,
                litellm_metadata=kwargs.get("litellm_metadata", {}),
                custom_llm_provider=custom_llm_provider,
            )

        return response
    except Exception as e:
        raise litellm.exception_type(
            model=model,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
async def adelete_responses(
    response_id: str,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> DeleteResponseResult:
    """
    Async version of the DELETE Responses API

    DELETE /v1/responses/{response_id} endpoint in the responses API

    """
    local_vars = locals()
    try:
        loop = asyncio.get_event_loop()
        kwargs["adelete_responses"] = True

        # get custom llm provider from response_id
        decoded_response_id: DecodedResponseId = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(
                response_id=response_id,
            )
        )
        response_id = decoded_response_id.get("response_id") or response_id
        custom_llm_provider = (
            decoded_response_id.get("custom_llm_provider") or custom_llm_provider
        )

        func = partial(
            delete_responses,
            response_id=response_id,
            custom_llm_provider=custom_llm_provider,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
            **kwargs,
        )

        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)

        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response
    except Exception as e:
        raise litellm.exception_type(
            model=None,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
def delete_responses(
    response_id: str,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[DeleteResponseResult, Coroutine[Any, Any, DeleteResponseResult]]:
    """
    Synchronous version of the DELETE Responses API

    DELETE /v1/responses/{response_id} endpoint in the responses API

    """
    local_vars = locals()
    try:
        litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
        litellm_call_id: Optional[str] = kwargs.get("litellm_call_id", None)
        _is_async = kwargs.pop("adelete_responses", False) is True

        # get llm provider logic
        litellm_params = GenericLiteLLMParams(**kwargs)

        # get custom llm provider from response_id
        decoded_response_id: DecodedResponseId = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(
                response_id=response_id,
            )
        )
        response_id = decoded_response_id.get("response_id") or response_id
        custom_llm_provider = (
            decoded_response_id.get("custom_llm_provider") or custom_llm_provider
        )

        if custom_llm_provider is None:
            raise ValueError("custom_llm_provider is required but passed as None")

        # get provider config
        responses_api_provider_config: Optional[BaseResponsesAPIConfig] = (
            ProviderConfigManager.get_provider_responses_api_config(
                model=None,
                provider=litellm.LlmProviders(custom_llm_provider),
            )
        )

        if responses_api_provider_config is None:
            raise ValueError(
                f"DELETE responses is not supported for {custom_llm_provider}"
            )

        local_vars.update(kwargs)

        # Pre Call logging
        litellm_logging_obj.update_environment_variables(
            model=None,
            optional_params={
                "response_id": response_id,
            },
            litellm_params={
                "litellm_call_id": litellm_call_id,
            },
            custom_llm_provider=custom_llm_provider,
        )

        # Call the handler with _is_async flag instead of directly calling the async handler
        response = base_llm_http_handler.delete_response_api_handler(
            response_id=response_id,
            custom_llm_provider=custom_llm_provider,
            responses_api_provider_config=responses_api_provider_config,
            litellm_params=litellm_params,
            logging_obj=litellm_logging_obj,
            extra_headers=extra_headers,
            extra_body=extra_body,
            timeout=timeout or request_timeout,
            _is_async=_is_async,
            client=kwargs.get("client"),
        )

        return response
    except Exception as e:
        raise litellm.exception_type(
            model=None,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
async def aget_responses(
    response_id: str,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> ResponsesAPIResponse:
    """
    Async: Fetch a response by its ID.

    GET /v1/responses/{response_id} endpoint in the responses API

    Args:
        response_id: The ID of the response to fetch.
        custom_llm_provider: Optional provider name. If not specified, will be decoded from response_id.

    Returns:
        The response object with complete information about the stored response.
    """
    local_vars = locals()
    try:
        loop = asyncio.get_event_loop()
        kwargs["aget_responses"] = True

        # get custom llm provider from response_id
        decoded_response_id: DecodedResponseId = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(
                response_id=response_id,
            )
        )
        response_id = decoded_response_id.get("response_id") or response_id
        custom_llm_provider = (
            decoded_response_id.get("custom_llm_provider") or custom_llm_provider
        )

        func = partial(
            get_responses,
            response_id=response_id,
            custom_llm_provider=custom_llm_provider,
            extra_headers=extra_headers,
            extra_query=extra_query,
            extra_body=extra_body,
            timeout=timeout,
            **kwargs,
        )

        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)

        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response

        # Update the responses_api_response_id with the model_id
        if isinstance(response, ResponsesAPIResponse):
            response = ResponsesAPIRequestUtils._update_responses_api_response_id_with_model_id(
                responses_api_response=response,
                litellm_metadata=kwargs.get("litellm_metadata", {}),
                custom_llm_provider=custom_llm_provider,
            )
        return response
    except Exception as e:
        raise litellm.exception_type(
            model=None,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
def get_responses(
    response_id: str,
    # Use the following arguments if you need to pass additional parameters to the API that aren't available via kwargs.
    # The extra values given here take precedence over values defined on the client or passed to this method.
    extra_headers: Optional[Dict[str, Any]] = None,
    extra_query: Optional[Dict[str, Any]] = None,
    extra_body: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    # LiteLLM specific params,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[ResponsesAPIResponse, Coroutine[Any, Any, ResponsesAPIResponse]]:
    """
    Fetch a response by its ID.

    GET /v1/responses/{response_id} endpoint in the responses API

    Args:
        response_id: The ID of the response to fetch.
        custom_llm_provider: Optional provider name. If not specified, will be decoded from response_id.

    Returns:
        The response object with complete information about the stored response.
    """
    local_vars = locals()
    try:
        litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
        litellm_call_id: Optional[str] = kwargs.get("litellm_call_id", None)
        _is_async = kwargs.pop("aget_responses", False) is True

        # get llm provider logic
        litellm_params = GenericLiteLLMParams(**kwargs)

        # get custom llm provider from response_id
        decoded_response_id: DecodedResponseId = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(
                response_id=response_id,
            )
        )
        response_id = decoded_response_id.get("response_id") or response_id
        custom_llm_provider = (
            decoded_response_id.get("custom_llm_provider") or custom_llm_provider
        )

        if custom_llm_provider is None:
            raise ValueError("custom_llm_provider is required but passed as None")

        # get provider config
        responses_api_provider_config: Optional[BaseResponsesAPIConfig] = (
            ProviderConfigManager.get_provider_responses_api_config(
                model=None,
                provider=litellm.LlmProviders(custom_llm_provider),
            )
        )

        if responses_api_provider_config is None:
            raise ValueError(
                f"GET responses is not supported for {custom_llm_provider}"
            )

        local_vars.update(kwargs)

        # Pre Call logging
        litellm_logging_obj.update_environment_variables(
            model=None,
            optional_params={
                "response_id": response_id,
            },
            litellm_params={
                "litellm_call_id": litellm_call_id,
            },
            custom_llm_provider=custom_llm_provider,
        )

        # Call the handler with _is_async flag instead of directly calling the async handler
        response = base_llm_http_handler.get_responses(
            response_id=response_id,
            custom_llm_provider=custom_llm_provider,
            responses_api_provider_config=responses_api_provider_config,
            litellm_params=litellm_params,
            logging_obj=litellm_logging_obj,
            extra_headers=extra_headers,
            extra_body=extra_body,
            timeout=timeout or request_timeout,
            _is_async=_is_async,
            client=kwargs.get("client"),
        )

        # Update the responses_api_response_id with the model_id
        if isinstance(response, ResponsesAPIResponse):
            response = ResponsesAPIRequestUtils._update_responses_api_response_id_with_model_id(
                responses_api_response=response,
                litellm_metadata=kwargs.get("litellm_metadata", {}),
                custom_llm_provider=custom_llm_provider,
            )

        return response
    except Exception as e:
        raise litellm.exception_type(
            model=None,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
async def alist_input_items(
    response_id: str,
    after: Optional[str] = None,
    before: Optional[str] = None,
    include: Optional[List[str]] = None,
    limit: int = 20,
    order: Literal["asc", "desc"] = "desc",
    extra_headers: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Dict:
    """Async: List input items for a response"""
    local_vars = locals()
    try:
        loop = asyncio.get_event_loop()
        kwargs["alist_input_items"] = True

        decoded_response_id = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(
                response_id=response_id
            )
        )
        response_id = decoded_response_id.get("response_id") or response_id
        custom_llm_provider = (
            decoded_response_id.get("custom_llm_provider") or custom_llm_provider
        )

        func = partial(
            list_input_items,
            response_id=response_id,
            after=after,
            before=before,
            include=include,
            limit=limit,
            order=order,
            extra_headers=extra_headers,
            timeout=timeout,
            custom_llm_provider=custom_llm_provider,
            **kwargs,
        )

        ctx = contextvars.copy_context()
        func_with_context = partial(ctx.run, func)
        init_response = await loop.run_in_executor(None, func_with_context)

        if asyncio.iscoroutine(init_response):
            response = await init_response
        else:
            response = init_response
        return response
    except Exception as e:
        raise litellm.exception_type(
            model=None,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )


@client
def list_input_items(
    response_id: str,
    after: Optional[str] = None,
    before: Optional[str] = None,
    include: Optional[List[str]] = None,
    limit: int = 20,
    order: Literal["asc", "desc"] = "desc",
    extra_headers: Optional[Dict[str, Any]] = None,
    timeout: Optional[Union[float, httpx.Timeout]] = None,
    custom_llm_provider: Optional[str] = None,
    **kwargs,
) -> Union[Dict, Coroutine[Any, Any, Dict]]:
    """List input items for a response"""
    local_vars = locals()
    try:
        litellm_logging_obj: LiteLLMLoggingObj = kwargs.get("litellm_logging_obj")  # type: ignore
        litellm_call_id: Optional[str] = kwargs.get("litellm_call_id", None)
        _is_async = kwargs.pop("alist_input_items", False) is True

        litellm_params = GenericLiteLLMParams(**kwargs)

        decoded_response_id = (
            ResponsesAPIRequestUtils._decode_responses_api_response_id(
                response_id=response_id
            )
        )
        response_id = decoded_response_id.get("response_id") or response_id
        custom_llm_provider = (
            decoded_response_id.get("custom_llm_provider") or custom_llm_provider
        )

        if custom_llm_provider is None:
            raise ValueError("custom_llm_provider is required but passed as None")

        responses_api_provider_config: Optional[BaseResponsesAPIConfig] = (
            ProviderConfigManager.get_provider_responses_api_config(
                model=None,
                provider=litellm.LlmProviders(custom_llm_provider),
            )
        )

        if responses_api_provider_config is None:
            raise ValueError(
                f"list_input_items is not supported for {custom_llm_provider}"
            )

        local_vars.update(kwargs)

        litellm_logging_obj.update_environment_variables(
            model=None,
            optional_params={"response_id": response_id},
            litellm_params={"litellm_call_id": litellm_call_id},
            custom_llm_provider=custom_llm_provider,
        )

        response = base_llm_http_handler.list_responses_input_items(
            response_id=response_id,
            custom_llm_provider=custom_llm_provider,
            responses_api_provider_config=responses_api_provider_config,
            litellm_params=litellm_params,
            logging_obj=litellm_logging_obj,
            after=after,
            before=before,
            include=include,
            limit=limit,
            order=order,
            extra_headers=extra_headers,
            timeout=timeout or request_timeout,
            _is_async=_is_async,
            client=kwargs.get("client"),
        )

        return response
    except Exception as e:
        raise litellm.exception_type(
            model=None,
            custom_llm_provider=custom_llm_provider,
            original_exception=e,
            completion_kwargs=local_vars,
            extra_kwargs=kwargs,
        )

# === NexusCore/openenv\Lib\site-packages\fontTools\ttLib\tables\E_B_D_T_.py ===
from fontTools.misc import sstruct
from fontTools.misc.textTools import (
    bytechr,
    byteord,
    bytesjoin,
    strjoin,
    safeEval,
    readHex,
    hexStr,
    deHexStr,
)
from .BitmapGlyphMetrics import (
    BigGlyphMetrics,
    bigGlyphMetricsFormat,
    SmallGlyphMetrics,
    smallGlyphMetricsFormat,
)
from . import DefaultTable
import itertools
import os
import struct
import logging


log = logging.getLogger(__name__)

ebdtTableVersionFormat = """
	> # big endian
	version: 16.16F
"""

ebdtComponentFormat = """
	> # big endian
	glyphCode: H
	xOffset:   b
	yOffset:   b
"""


class table_E_B_D_T_(DefaultTable.DefaultTable):
    """Embedded Bitmap Data table

    The ``EBDT`` table contains monochrome or grayscale bitmap data for
    glyphs. It must be used in concert with the ``EBLC`` table.

    See also https://learn.microsoft.com/en-us/typography/opentype/spec/ebdt
    """

    # Keep a reference to the name of the data locator table.
    locatorName = "EBLC"

    # This method can be overridden in subclasses to support new formats
    # without changing the other implementation. Also can be used as a
    # convenience method for coverting a font file to an alternative format.
    def getImageFormatClass(self, imageFormat):
        return ebdt_bitmap_classes[imageFormat]

    def decompile(self, data, ttFont):
        # Get the version but don't advance the slice.
        # Most of the lookup for this table is done relative
        # to the begining so slice by the offsets provided
        # in the EBLC table.
        sstruct.unpack2(ebdtTableVersionFormat, data, self)

        # Keep a dict of glyphs that have been seen so they aren't remade.
        # This dict maps intervals of data to the BitmapGlyph.
        glyphDict = {}

        # Pull out the EBLC table and loop through glyphs.
        # A strike is a concept that spans both tables.
        # The actual bitmap data is stored in the EBDT.
        locator = ttFont[self.__class__.locatorName]
        self.strikeData = []
        for curStrike in locator.strikes:
            bitmapGlyphDict = {}
            self.strikeData.append(bitmapGlyphDict)
            for indexSubTable in curStrike.indexSubTables:
                dataIter = zip(indexSubTable.names, indexSubTable.locations)
                for curName, curLoc in dataIter:
                    # Don't create duplicate data entries for the same glyphs.
                    # Instead just use the structures that already exist if they exist.
                    if curLoc in glyphDict:
                        curGlyph = glyphDict[curLoc]
                    else:
                        curGlyphData = data[slice(*curLoc)]
                        imageFormatClass = self.getImageFormatClass(
                            indexSubTable.imageFormat
                        )
                        curGlyph = imageFormatClass(curGlyphData, ttFont)
                        glyphDict[curLoc] = curGlyph
                    bitmapGlyphDict[curName] = curGlyph

    def compile(self, ttFont):
        dataList = []
        dataList.append(sstruct.pack(ebdtTableVersionFormat, self))
        dataSize = len(dataList[0])

        # Keep a dict of glyphs that have been seen so they aren't remade.
        # This dict maps the id of the BitmapGlyph to the interval
        # in the data.
        glyphDict = {}

        # Go through the bitmap glyph data. Just in case the data for a glyph
        # changed the size metrics should be recalculated. There are a variety
        # of formats and they get stored in the EBLC table. That is why
        # recalculation is defered to the EblcIndexSubTable class and just
        # pass what is known about bitmap glyphs from this particular table.
        locator = ttFont[self.__class__.locatorName]
        for curStrike, curGlyphDict in zip(locator.strikes, self.strikeData):
            for curIndexSubTable in curStrike.indexSubTables:
                dataLocations = []
                for curName in curIndexSubTable.names:
                    # Handle the data placement based on seeing the glyph or not.
                    # Just save a reference to the location if the glyph has already
                    # been saved in compile. This code assumes that glyphs will only
                    # be referenced multiple times from indexFormat5. By luck the
                    # code may still work when referencing poorly ordered fonts with
                    # duplicate references. If there is a font that is unlucky the
                    # respective compile methods for the indexSubTables will fail
                    # their assertions. All fonts seem to follow this assumption.
                    # More complicated packing may be needed if a counter-font exists.
                    glyph = curGlyphDict[curName]
                    objectId = id(glyph)
                    if objectId not in glyphDict:
                        data = glyph.compile(ttFont)
                        data = curIndexSubTable.padBitmapData(data)
                        startByte = dataSize
                        dataSize += len(data)
                        endByte = dataSize
                        dataList.append(data)
                        dataLoc = (startByte, endByte)
                        glyphDict[objectId] = dataLoc
                    else:
                        dataLoc = glyphDict[objectId]
                    dataLocations.append(dataLoc)
                # Just use the new data locations in the indexSubTable.
                # The respective compile implementations will take care
                # of any of the problems in the convertion that may arise.
                curIndexSubTable.locations = dataLocations

        return bytesjoin(dataList)

    def toXML(self, writer, ttFont):
        # When exporting to XML if one of the data export formats
        # requires metrics then those metrics may be in the locator.
        # In this case populate the bitmaps with "export metrics".
        if ttFont.bitmapGlyphDataFormat in ("row", "bitwise"):
            locator = ttFont[self.__class__.locatorName]
            for curStrike, curGlyphDict in zip(locator.strikes, self.strikeData):
                for curIndexSubTable in curStrike.indexSubTables:
                    for curName in curIndexSubTable.names:
                        glyph = curGlyphDict[curName]
                        # I'm not sure which metrics have priority here.
                        # For now if both metrics exist go with glyph metrics.
                        if hasattr(glyph, "metrics"):
                            glyph.exportMetrics = glyph.metrics
                        else:
                            glyph.exportMetrics = curIndexSubTable.metrics
                        glyph.exportBitDepth = curStrike.bitmapSizeTable.bitDepth

        writer.simpletag("header", [("version", self.version)])
        writer.newline()
        locator = ttFont[self.__class__.locatorName]
        for strikeIndex, bitmapGlyphDict in enumerate(self.strikeData):
            writer.begintag("strikedata", [("index", strikeIndex)])
            writer.newline()
            for curName, curBitmap in bitmapGlyphDict.items():
                curBitmap.toXML(strikeIndex, curName, writer, ttFont)
            writer.endtag("strikedata")
            writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        if name == "header":
            self.version = safeEval(attrs["version"])
        elif name == "strikedata":
            if not hasattr(self, "strikeData"):
                self.strikeData = []
            strikeIndex = safeEval(attrs["index"])

            bitmapGlyphDict = {}
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                if name[4:].startswith(_bitmapGlyphSubclassPrefix[4:]):
                    imageFormat = safeEval(name[len(_bitmapGlyphSubclassPrefix) :])
                    glyphName = attrs["name"]
                    imageFormatClass = self.getImageFormatClass(imageFormat)
                    curGlyph = imageFormatClass(None, None)
                    curGlyph.fromXML(name, attrs, content, ttFont)
                    assert glyphName not in bitmapGlyphDict, (
                        "Duplicate glyphs with the same name '%s' in the same strike."
                        % glyphName
                    )
                    bitmapGlyphDict[glyphName] = curGlyph
                else:
                    log.warning("%s being ignored by %s", name, self.__class__.__name__)

            # Grow the strike data array to the appropriate size. The XML
            # format allows the strike index value to be out of order.
            if strikeIndex >= len(self.strikeData):
                self.strikeData += [None] * (strikeIndex + 1 - len(self.strikeData))
            assert (
                self.strikeData[strikeIndex] is None
            ), "Duplicate strike EBDT indices."
            self.strikeData[strikeIndex] = bitmapGlyphDict


class EbdtComponent(object):
    def toXML(self, writer, ttFont):
        writer.begintag("ebdtComponent", [("name", self.name)])
        writer.newline()
        for componentName in sstruct.getformat(ebdtComponentFormat)[1][1:]:
            writer.simpletag(componentName, value=getattr(self, componentName))
            writer.newline()
        writer.endtag("ebdtComponent")
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.name = attrs["name"]
        componentNames = set(sstruct.getformat(ebdtComponentFormat)[1][1:])
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attrs, content = element
            if name in componentNames:
                vars(self)[name] = safeEval(attrs["value"])
            else:
                log.warning("unknown name '%s' being ignored by EbdtComponent.", name)


# Helper functions for dealing with binary.


def _data2binary(data, numBits):
    binaryList = []
    for curByte in data:
        value = byteord(curByte)
        numBitsCut = min(8, numBits)
        for i in range(numBitsCut):
            if value & 0x1:
                binaryList.append("1")
            else:
                binaryList.append("0")
            value = value >> 1
        numBits -= numBitsCut
    return strjoin(binaryList)


def _binary2data(binary):
    byteList = []
    for bitLoc in range(0, len(binary), 8):
        byteString = binary[bitLoc : bitLoc + 8]
        curByte = 0
        for curBit in reversed(byteString):
            curByte = curByte << 1
            if curBit == "1":
                curByte |= 1
        byteList.append(bytechr(curByte))
    return bytesjoin(byteList)


def _memoize(f):
    class memodict(dict):
        def __missing__(self, key):
            ret = f(key)
            if isinstance(key, int) or len(key) == 1:
                self[key] = ret
            return ret

    return memodict().__getitem__


# 00100111 -> 11100100 per byte, not to be confused with little/big endian.
# Bitmap data per byte is in the order that binary is written on the page
# with the least significant bit as far right as possible. This is the
# opposite of what makes sense algorithmically and hence this function.
@_memoize
def _reverseBytes(data):
    r"""
    >>> bin(ord(_reverseBytes(0b00100111)))
    '0b11100100'
    >>> _reverseBytes(b'\x00\xf0')
    b'\x00\x0f'
    """
    if isinstance(data, bytes) and len(data) != 1:
        return bytesjoin(map(_reverseBytes, data))
    byte = byteord(data)
    result = 0
    for i in range(8):
        result = result << 1
        result |= byte & 1
        byte = byte >> 1
    return bytechr(result)


# This section of code is for reading and writing image data to/from XML.


def _writeRawImageData(strikeIndex, glyphName, bitmapObject, writer, ttFont):
    writer.begintag("rawimagedata")
    writer.newline()
    writer.dumphex(bitmapObject.imageData)
    writer.endtag("rawimagedata")
    writer.newline()


def _readRawImageData(bitmapObject, name, attrs, content, ttFont):
    bitmapObject.imageData = readHex(content)


def _writeRowImageData(strikeIndex, glyphName, bitmapObject, writer, ttFont):
    metrics = bitmapObject.exportMetrics
    del bitmapObject.exportMetrics
    bitDepth = bitmapObject.exportBitDepth
    del bitmapObject.exportBitDepth

    writer.begintag(
        "rowimagedata", bitDepth=bitDepth, width=metrics.width, height=metrics.height
    )
    writer.newline()
    for curRow in range(metrics.height):
        rowData = bitmapObject.getRow(curRow, bitDepth=bitDepth, metrics=metrics)
        writer.simpletag("row", value=hexStr(rowData))
        writer.newline()
    writer.endtag("rowimagedata")
    writer.newline()


def _readRowImageData(bitmapObject, name, attrs, content, ttFont):
    bitDepth = safeEval(attrs["bitDepth"])
    metrics = SmallGlyphMetrics()
    metrics.width = safeEval(attrs["width"])
    metrics.height = safeEval(attrs["height"])

    dataRows = []
    for element in content:
        if not isinstance(element, tuple):
            continue
        name, attr, content = element
        # Chop off 'imagedata' from the tag to get just the option.
        if name == "row":
            dataRows.append(deHexStr(attr["value"]))
    bitmapObject.setRows(dataRows, bitDepth=bitDepth, metrics=metrics)


def _writeBitwiseImageData(strikeIndex, glyphName, bitmapObject, writer, ttFont):
    metrics = bitmapObject.exportMetrics
    del bitmapObject.exportMetrics
    bitDepth = bitmapObject.exportBitDepth
    del bitmapObject.exportBitDepth

    # A dict for mapping binary to more readable/artistic ASCII characters.
    binaryConv = {"0": ".", "1": "@"}

    writer.begintag(
        "bitwiseimagedata",
        bitDepth=bitDepth,
        width=metrics.width,
        height=metrics.height,
    )
    writer.newline()
    for curRow in range(metrics.height):
        rowData = bitmapObject.getRow(
            curRow, bitDepth=1, metrics=metrics, reverseBytes=True
        )
        rowData = _data2binary(rowData, metrics.width)
        # Make the output a readable ASCII art form.
        rowData = strjoin(map(binaryConv.get, rowData))
        writer.simpletag("row", value=rowData)
        writer.newline()
    writer.endtag("bitwiseimagedata")
    writer.newline()


def _readBitwiseImageData(bitmapObject, name, attrs, content, ttFont):
    bitDepth = safeEval(attrs["bitDepth"])
    metrics = SmallGlyphMetrics()
    metrics.width = safeEval(attrs["width"])
    metrics.height = safeEval(attrs["height"])

    # A dict for mapping from ASCII to binary. All characters are considered
    # a '1' except space, period and '0' which maps to '0'.
    binaryConv = {" ": "0", ".": "0", "0": "0"}

    dataRows = []
    for element in content:
        if not isinstance(element, tuple):
            continue
        name, attr, content = element
        if name == "row":
            mapParams = zip(attr["value"], itertools.repeat("1"))
            rowData = strjoin(itertools.starmap(binaryConv.get, mapParams))
            dataRows.append(_binary2data(rowData))

    bitmapObject.setRows(
        dataRows, bitDepth=bitDepth, metrics=metrics, reverseBytes=True
    )


def _writeExtFileImageData(strikeIndex, glyphName, bitmapObject, writer, ttFont):
    try:
        folder = os.path.dirname(writer.file.name)
    except AttributeError:
        # fall back to current directory if output file's directory isn't found
        folder = "."
    folder = os.path.join(folder, "bitmaps")
    filename = glyphName + bitmapObject.fileExtension
    if not os.path.isdir(folder):
        os.makedirs(folder)
    folder = os.path.join(folder, "strike%d" % strikeIndex)
    if not os.path.isdir(folder):
        os.makedirs(folder)

    fullPath = os.path.join(folder, filename)
    writer.simpletag("extfileimagedata", value=fullPath)
    writer.newline()

    with open(fullPath, "wb") as file:
        file.write(bitmapObject.imageData)


def _readExtFileImageData(bitmapObject, name, attrs, content, ttFont):
    fullPath = attrs["value"]
    with open(fullPath, "rb") as file:
        bitmapObject.imageData = file.read()


# End of XML writing code.

# Important information about the naming scheme. Used for identifying formats
# in XML.
_bitmapGlyphSubclassPrefix = "ebdt_bitmap_format_"


class BitmapGlyph(object):
    # For the external file format. This can be changed in subclasses. This way
    # when the extfile option is turned on files have the form: glyphName.ext
    # The default is just a flat binary file with no meaning.
    fileExtension = ".bin"

    # Keep track of reading and writing of various forms.
    xmlDataFunctions = {
        "raw": (_writeRawImageData, _readRawImageData),
        "row": (_writeRowImageData, _readRowImageData),
        "bitwise": (_writeBitwiseImageData, _readBitwiseImageData),
        "extfile": (_writeExtFileImageData, _readExtFileImageData),
    }

    def __init__(self, data, ttFont):
        self.data = data
        self.ttFont = ttFont
        # TODO Currently non-lazy decompilation is untested here...
        # if not ttFont.lazy:
        # 	self.decompile()
        # 	del self.data

    def __getattr__(self, attr):
        # Allow lazy decompile.
        if attr[:2] == "__":
            raise AttributeError(attr)
        if attr == "data":
            raise AttributeError(attr)
        self.decompile()
        del self.data
        return getattr(self, attr)

    def ensureDecompiled(self, recurse=False):
        if hasattr(self, "data"):
            self.decompile()
            del self.data

    # Not a fan of this but it is needed for safer safety checking.
    def getFormat(self):
        return safeEval(self.__class__.__name__[len(_bitmapGlyphSubclassPrefix) :])

    def toXML(self, strikeIndex, glyphName, writer, ttFont):
        writer.begintag(self.__class__.__name__, [("name", glyphName)])
        writer.newline()

        self.writeMetrics(writer, ttFont)
        # Use the internal write method to write using the correct output format.
        self.writeData(strikeIndex, glyphName, writer, ttFont)

        writer.endtag(self.__class__.__name__)
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.readMetrics(name, attrs, content, ttFont)
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attr, content = element
            if not name.endswith("imagedata"):
                continue
            # Chop off 'imagedata' from the tag to get just the option.
            option = name[: -len("imagedata")]
            assert option in self.__class__.xmlDataFunctions
            self.readData(name, attr, content, ttFont)

    # Some of the glyphs have the metrics. This allows for metrics to be
    # added if the glyph format has them. Default behavior is to do nothing.
    def writeMetrics(self, writer, ttFont):
        pass

    # The opposite of write metrics.
    def readMetrics(self, name, attrs, content, ttFont):
        pass

    def writeData(self, strikeIndex, glyphName, writer, ttFont):
        try:
            writeFunc, readFunc = self.__class__.xmlDataFunctions[
                ttFont.bitmapGlyphDataFormat
            ]
        except KeyError:
            writeFunc = _writeRawImageData
        writeFunc(strikeIndex, glyphName, self, writer, ttFont)

    def readData(self, name, attrs, content, ttFont):
        # Chop off 'imagedata' from the tag to get just the option.
        option = name[: -len("imagedata")]
        writeFunc, readFunc = self.__class__.xmlDataFunctions[option]
        readFunc(self, name, attrs, content, ttFont)


# A closure for creating a mixin for the two types of metrics handling.
# Most of the code is very similar so its easier to deal with here.
# Everything works just by passing the class that the mixin is for.
def _createBitmapPlusMetricsMixin(metricsClass):
    # Both metrics names are listed here to make meaningful error messages.
    metricStrings = [BigGlyphMetrics.__name__, SmallGlyphMetrics.__name__]
    curMetricsName = metricsClass.__name__
    # Find which metrics this is for and determine the opposite name.
    metricsId = metricStrings.index(curMetricsName)
    oppositeMetricsName = metricStrings[1 - metricsId]

    class BitmapPlusMetricsMixin(object):
        def writeMetrics(self, writer, ttFont):
            self.metrics.toXML(writer, ttFont)

        def readMetrics(self, name, attrs, content, ttFont):
            for element in content:
                if not isinstance(element, tuple):
                    continue
                name, attrs, content = element
                if name == curMetricsName:
                    self.metrics = metricsClass()
                    self.metrics.fromXML(name, attrs, content, ttFont)
                elif name == oppositeMetricsName:
                    log.warning(
                        "Warning: %s being ignored in format %d.",
                        oppositeMetricsName,
                        self.getFormat(),
                    )

    return BitmapPlusMetricsMixin


# Since there are only two types of mixin's just create them here.
BitmapPlusBigMetricsMixin = _createBitmapPlusMetricsMixin(BigGlyphMetrics)
BitmapPlusSmallMetricsMixin = _createBitmapPlusMetricsMixin(SmallGlyphMetrics)


# Data that is bit aligned can be tricky to deal with. These classes implement
# helper functionality for dealing with the data and getting a particular row
# of bitwise data. Also helps implement fancy data export/import in XML.
class BitAlignedBitmapMixin(object):
    def _getBitRange(self, row, bitDepth, metrics):
        rowBits = bitDepth * metrics.width
        bitOffset = row * rowBits
        return (bitOffset, bitOffset + rowBits)

    def getRow(self, row, bitDepth=1, metrics=None, reverseBytes=False):
        if metrics is None:
            metrics = self.metrics
        assert 0 <= row and row < metrics.height, "Illegal row access in bitmap"

        # Loop through each byte. This can cover two bytes in the original data or
        # a single byte if things happen to be aligned. The very last entry might
        # not be aligned so take care to trim the binary data to size and pad with
        # zeros in the row data. Bit aligned data is somewhat tricky.
        #
        # Example of data cut. Data cut represented in x's.
        # '|' represents byte boundary.
        # data = ...0XX|XXXXXX00|000... => XXXXXXXX
        # 		or
        # data = ...0XX|XXXX0000|000... => XXXXXX00
        #   or
        # data = ...000|XXXXXXXX|000... => XXXXXXXX
        #   or
        # data = ...000|00XXXX00|000... => XXXX0000
        #
        dataList = []
        bitRange = self._getBitRange(row, bitDepth, metrics)
        stepRange = bitRange + (8,)
        for curBit in range(*stepRange):
            endBit = min(curBit + 8, bitRange[1])
            numBits = endBit - curBit
            cutPoint = curBit % 8
            firstByteLoc = curBit // 8
            secondByteLoc = endBit // 8
            if firstByteLoc < secondByteLoc:
                numBitsCut = 8 - cutPoint
            else:
                numBitsCut = endBit - curBit
            curByte = _reverseBytes(self.imageData[firstByteLoc])
            firstHalf = byteord(curByte) >> cutPoint
            firstHalf = ((1 << numBitsCut) - 1) & firstHalf
            newByte = firstHalf
            if firstByteLoc < secondByteLoc and secondByteLoc < len(self.imageData):
                curByte = _reverseBytes(self.imageData[secondByteLoc])
                secondHalf = byteord(curByte) << numBitsCut
                newByte = (firstHalf | secondHalf) & ((1 << numBits) - 1)
            dataList.append(bytechr(newByte))

        # The way the data is kept is opposite the algorithm used.
        data = bytesjoin(dataList)
        if not reverseBytes:
            data = _reverseBytes(data)
        return data

    def setRows(self, dataRows, bitDepth=1, metrics=None, reverseBytes=False):
        if metrics is None:
            metrics = self.metrics
        if not reverseBytes:
            dataRows = list(map(_reverseBytes, dataRows))

        # Keep track of a list of ordinal values as they are easier to modify
        # than a list of strings. Map to actual strings later.
        numBytes = (self._getBitRange(len(dataRows), bitDepth, metrics)[0] + 7) // 8
        ordDataList = [0] * numBytes
        for row, data in enumerate(dataRows):
            bitRange = self._getBitRange(row, bitDepth, metrics)
            stepRange = bitRange + (8,)
            for curBit, curByte in zip(range(*stepRange), data):
                endBit = min(curBit + 8, bitRange[1])
                cutPoint = curBit % 8
                firstByteLoc = curBit // 8
                secondByteLoc = endBit // 8
                if firstByteLoc < secondByteLoc:
                    numBitsCut = 8 - cutPoint
                else:
                    numBitsCut = endBit - curBit
                curByte = byteord(curByte)
                firstByte = curByte & ((1 << numBitsCut) - 1)
                ordDataList[firstByteLoc] |= firstByte << cutPoint
                if firstByteLoc < secondByteLoc and secondByteLoc < numBytes:
                    secondByte = (curByte >> numBitsCut) & ((1 << 8 - numBitsCut) - 1)
                    ordDataList[secondByteLoc] |= secondByte

        # Save the image data with the bits going the correct way.
        self.imageData = _reverseBytes(bytesjoin(map(bytechr, ordDataList)))


class ByteAlignedBitmapMixin(object):
    def _getByteRange(self, row, bitDepth, metrics):
        rowBytes = (bitDepth * metrics.width + 7) // 8
        byteOffset = row * rowBytes
        return (byteOffset, byteOffset + rowBytes)

    def getRow(self, row, bitDepth=1, metrics=None, reverseBytes=False):
        if metrics is None:
            metrics = self.metrics
        assert 0 <= row and row < metrics.height, "Illegal row access in bitmap"
        byteRange = self._getByteRange(row, bitDepth, metrics)
        data = self.imageData[slice(*byteRange)]
        if reverseBytes:
            data = _reverseBytes(data)
        return data

    def setRows(self, dataRows, bitDepth=1, metrics=None, reverseBytes=False):
        if metrics is None:
            metrics = self.metrics
        if reverseBytes:
            dataRows = map(_reverseBytes, dataRows)
        self.imageData = bytesjoin(dataRows)


class ebdt_bitmap_format_1(
    ByteAlignedBitmapMixin, BitmapPlusSmallMetricsMixin, BitmapGlyph
):
    def decompile(self):
        self.metrics = SmallGlyphMetrics()
        dummy, data = sstruct.unpack2(smallGlyphMetricsFormat, self.data, self.metrics)
        self.imageData = data

    def compile(self, ttFont):
        data = sstruct.pack(smallGlyphMetricsFormat, self.metrics)
        return data + self.imageData


class ebdt_bitmap_format_2(
    BitAlignedBitmapMixin, BitmapPlusSmallMetricsMixin, BitmapGlyph
):
    def decompile(self):
        self.metrics = SmallGlyphMetrics()
        dummy, data = sstruct.unpack2(smallGlyphMetricsFormat, self.data, self.metrics)
        self.imageData = data

    def compile(self, ttFont):
        data = sstruct.pack(smallGlyphMetricsFormat, self.metrics)
        return data + self.imageData


class ebdt_bitmap_format_5(BitAlignedBitmapMixin, BitmapGlyph):
    def decompile(self):
        self.imageData = self.data

    def compile(self, ttFont):
        return self.imageData


class ebdt_bitmap_format_6(
    ByteAlignedBitmapMixin, BitmapPlusBigMetricsMixin, BitmapGlyph
):
    def decompile(self):
        self.metrics = BigGlyphMetrics()
        dummy, data = sstruct.unpack2(bigGlyphMetricsFormat, self.data, self.metrics)
        self.imageData = data

    def compile(self, ttFont):
        data = sstruct.pack(bigGlyphMetricsFormat, self.metrics)
        return data + self.imageData


class ebdt_bitmap_format_7(
    BitAlignedBitmapMixin, BitmapPlusBigMetricsMixin, BitmapGlyph
):
    def decompile(self):
        self.metrics = BigGlyphMetrics()
        dummy, data = sstruct.unpack2(bigGlyphMetricsFormat, self.data, self.metrics)
        self.imageData = data

    def compile(self, ttFont):
        data = sstruct.pack(bigGlyphMetricsFormat, self.metrics)
        return data + self.imageData


class ComponentBitmapGlyph(BitmapGlyph):
    def toXML(self, strikeIndex, glyphName, writer, ttFont):
        writer.begintag(self.__class__.__name__, [("name", glyphName)])
        writer.newline()

        self.writeMetrics(writer, ttFont)

        writer.begintag("components")
        writer.newline()
        for curComponent in self.componentArray:
            curComponent.toXML(writer, ttFont)
        writer.endtag("components")
        writer.newline()

        writer.endtag(self.__class__.__name__)
        writer.newline()

    def fromXML(self, name, attrs, content, ttFont):
        self.readMetrics(name, attrs, content, ttFont)
        for element in content:
            if not isinstance(element, tuple):
                continue
            name, attr, content = element
            if name == "components":
                self.componentArray = []
                for compElement in content:
                    if not isinstance(compElement, tuple):
                        continue
                    name, attrs, content = compElement
                    if name == "ebdtComponent":
                        curComponent = EbdtComponent()
                        curComponent.fromXML(name, attrs, content, ttFont)
                        self.componentArray.append(curComponent)
                    else:
                        log.warning("'%s' being ignored in component array.", name)


class ebdt_bitmap_format_8(BitmapPlusSmallMetricsMixin, ComponentBitmapGlyph):
    def decompile(self):
        self.metrics = SmallGlyphMetrics()
        dummy, data = sstruct.unpack2(smallGlyphMetricsFormat, self.data, self.metrics)
        data = data[1:]

        (numComponents,) = struct.unpack(">H", data[:2])
        data = data[2:]
        self.componentArray = []
        for i in range(numComponents):
            curComponent = EbdtComponent()
            dummy, data = sstruct.unpack2(ebdtComponentFormat, data, curComponent)
            curComponent.name = self.ttFont.getGlyphName(curComponent.glyphCode)
            self.componentArray.append(curComponent)

    def compile(self, ttFont):
        dataList = []
        dataList.append(sstruct.pack(smallGlyphMetricsFormat, self.metrics))
        dataList.append(b"\0")
        dataList.append(struct.pack(">H", len(self.componentArray)))
        for curComponent in self.componentArray:
            curComponent.glyphCode = ttFont.getGlyphID(curComponent.name)
            dataList.append(sstruct.pack(ebdtComponentFormat, curComponent))
        return bytesjoin(dataList)


class ebdt_bitmap_format_9(BitmapPlusBigMetricsMixin, ComponentBitmapGlyph):
    def decompile(self):
        self.metrics = BigGlyphMetrics()
        dummy, data = sstruct.unpack2(bigGlyphMetricsFormat, self.data, self.metrics)
        (numComponents,) = struct.unpack(">H", data[:2])
        data = data[2:]
        self.componentArray = []
        for i in range(numComponents):
            curComponent = EbdtComponent()
            dummy, data = sstruct.unpack2(ebdtComponentFormat, data, curComponent)
            curComponent.name = self.ttFont.getGlyphName(curComponent.glyphCode)
            self.componentArray.append(curComponent)

    def compile(self, ttFont):
        dataList = []
        dataList.append(sstruct.pack(bigGlyphMetricsFormat, self.metrics))
        dataList.append(struct.pack(">H", len(self.componentArray)))
        for curComponent in self.componentArray:
            curComponent.glyphCode = ttFont.getGlyphID(curComponent.name)
            dataList.append(sstruct.pack(ebdtComponentFormat, curComponent))
        return bytesjoin(dataList)


# Dictionary of bitmap formats to the class representing that format
# currently only the ones listed in this map are the ones supported.
ebdt_bitmap_classes = {
    1: ebdt_bitmap_format_1,
    2: ebdt_bitmap_format_2,
    5: ebdt_bitmap_format_5,
    6: ebdt_bitmap_format_6,
    7: ebdt_bitmap_format_7,
    8: ebdt_bitmap_format_8,
    9: ebdt_bitmap_format_9,
}

# === NexusCore/openenv\Lib\site-packages\nltk\sem\glue.py ===
# Natural Language Toolkit: Glue Semantics
#
# Author: Dan Garrette <dhgarrette@gmail.com>
#
# Copyright (C) 2001-2024 NLTK Project
# URL: <https://www.nltk.org/>
# For license information, see LICENSE.TXT

import os
from itertools import chain

import nltk
from nltk.internals import Counter
from nltk.sem import drt, linearlogic
from nltk.sem.logic import (
    AbstractVariableExpression,
    Expression,
    LambdaExpression,
    Variable,
    VariableExpression,
)
from nltk.tag import BigramTagger, RegexpTagger, TrigramTagger, UnigramTagger

SPEC_SEMTYPES = {
    "a": "ex_quant",
    "an": "ex_quant",
    "every": "univ_quant",
    "the": "def_art",
    "no": "no_quant",
    "default": "ex_quant",
}

OPTIONAL_RELATIONSHIPS = ["nmod", "vmod", "punct"]


class GlueFormula:
    def __init__(self, meaning, glue, indices=None):
        if not indices:
            indices = set()

        if isinstance(meaning, str):
            self.meaning = Expression.fromstring(meaning)
        elif isinstance(meaning, Expression):
            self.meaning = meaning
        else:
            raise RuntimeError(
                "Meaning term neither string or expression: %s, %s"
                % (meaning, meaning.__class__)
            )

        if isinstance(glue, str):
            self.glue = linearlogic.LinearLogicParser().parse(glue)
        elif isinstance(glue, linearlogic.Expression):
            self.glue = glue
        else:
            raise RuntimeError(
                "Glue term neither string or expression: %s, %s"
                % (glue, glue.__class__)
            )

        self.indices = indices

    def applyto(self, arg):
        """self = (\\x.(walk x), (subj -o f))
        arg  = (john        ,  subj)
        returns ((walk john),          f)
        """
        if self.indices & arg.indices:  # if the sets are NOT disjoint
            raise linearlogic.LinearLogicApplicationException(
                f"'{self}' applied to '{arg}'.  Indices are not disjoint."
            )
        else:  # if the sets ARE disjoint
            return_indices = self.indices | arg.indices

        try:
            return_glue = linearlogic.ApplicationExpression(
                self.glue, arg.glue, arg.indices
            )
        except linearlogic.LinearLogicApplicationException as e:
            raise linearlogic.LinearLogicApplicationException(
                f"'{self.simplify()}' applied to '{arg.simplify()}'"
            ) from e

        arg_meaning_abstracted = arg.meaning
        if return_indices:
            for dep in self.glue.simplify().antecedent.dependencies[
                ::-1
            ]:  # if self.glue is (A -o B), dep is in A.dependencies
                arg_meaning_abstracted = self.make_LambdaExpression(
                    Variable("v%s" % dep), arg_meaning_abstracted
                )
        return_meaning = self.meaning.applyto(arg_meaning_abstracted)

        return self.__class__(return_meaning, return_glue, return_indices)

    def make_VariableExpression(self, name):
        return VariableExpression(name)

    def make_LambdaExpression(self, variable, term):
        return LambdaExpression(variable, term)

    def lambda_abstract(self, other):
        assert isinstance(other, GlueFormula)
        assert isinstance(other.meaning, AbstractVariableExpression)
        return self.__class__(
            self.make_LambdaExpression(other.meaning.variable, self.meaning),
            linearlogic.ImpExpression(other.glue, self.glue),
        )

    def compile(self, counter=None):
        """From Iddo Lev's PhD Dissertation p108-109"""
        if not counter:
            counter = Counter()
        (compiled_glue, new_forms) = self.glue.simplify().compile_pos(
            counter, self.__class__
        )
        return new_forms + [
            self.__class__(self.meaning, compiled_glue, {counter.get()})
        ]

    def simplify(self):
        return self.__class__(
            self.meaning.simplify(), self.glue.simplify(), self.indices
        )

    def __eq__(self, other):
        return (
            self.__class__ == other.__class__
            and self.meaning == other.meaning
            and self.glue == other.glue
        )

    def __ne__(self, other):
        return not self == other

    # sorting for use in doctests which must be deterministic
    def __lt__(self, other):
        return str(self) < str(other)

    def __str__(self):
        assert isinstance(self.indices, set)
        accum = f"{self.meaning} : {self.glue}"
        if self.indices:
            accum += (
                " : {" + ", ".join(str(index) for index in sorted(self.indices)) + "}"
            )
        return accum

    def __repr__(self):
        return "%s" % self


class GlueDict(dict):
    def __init__(self, filename, encoding=None):
        self.filename = filename
        self.file_encoding = encoding
        self.read_file()

    def read_file(self, empty_first=True):
        if empty_first:
            self.clear()

        try:
            contents = nltk.data.load(
                self.filename, format="text", encoding=self.file_encoding
            )
            # TODO: the above can't handle zip files, but this should anyway be fixed in nltk.data.load()
        except LookupError as e:
            try:
                contents = nltk.data.load(
                    "file:" + self.filename, format="text", encoding=self.file_encoding
                )
            except LookupError:
                raise e
        lines = contents.splitlines()

        for line in lines:  # example: 'n : (\\x.(<word> x), (v-or))'
            #     lambdacalc -^  linear logic -^
            line = line.strip()  # remove trailing newline
            if not len(line):
                continue  # skip empty lines
            if line[0] == "#":
                continue  # skip commented out lines

            parts = line.split(
                " : ", 2
            )  # ['verb', '(\\x.(<word> x), ( subj -o f ))', '[subj]']

            glue_formulas = []
            paren_count = 0
            tuple_start = 0
            tuple_comma = 0

            relationships = None

            if len(parts) > 1:
                for i, c in enumerate(parts[1]):
                    if c == "(":
                        if paren_count == 0:  # if it's the first '(' of a tuple
                            tuple_start = i + 1  # then save the index
                        paren_count += 1
                    elif c == ")":
                        paren_count -= 1
                        if paren_count == 0:  # if it's the last ')' of a tuple
                            meaning_term = parts[1][
                                tuple_start:tuple_comma
                            ]  # '\\x.(<word> x)'
                            glue_term = parts[1][tuple_comma + 1 : i]  # '(v-r)'
                            glue_formulas.append(
                                [meaning_term, glue_term]
                            )  # add the GlueFormula to the list
                    elif c == ",":
                        if (
                            paren_count == 1
                        ):  # if it's a comma separating the parts of the tuple
                            tuple_comma = i  # then save the index
                    elif c == "#":  # skip comments at the ends of lines
                        if (
                            paren_count != 0
                        ):  # if the line hasn't parsed correctly so far
                            raise RuntimeError(
                                "Formula syntax is incorrect for entry " + line
                            )
                        break  # break to the next line

            if len(parts) > 2:  # if there is a relationship entry at the end
                rel_start = parts[2].index("[") + 1
                rel_end = parts[2].index("]")
                if rel_start == rel_end:
                    relationships = frozenset()
                else:
                    relationships = frozenset(
                        r.strip() for r in parts[2][rel_start:rel_end].split(",")
                    )

            try:
                start_inheritance = parts[0].index("(")
                end_inheritance = parts[0].index(")")
                sem = parts[0][:start_inheritance].strip()
                supertype = parts[0][start_inheritance + 1 : end_inheritance]
            except:
                sem = parts[0].strip()
                supertype = None

            if sem not in self:
                self[sem] = {}

            if (
                relationships is None
            ):  # if not specified for a specific relationship set
                # add all relationship entries for parents
                if supertype:
                    for rels in self[supertype]:
                        if rels not in self[sem]:
                            self[sem][rels] = []
                        glue = self[supertype][rels]
                        self[sem][rels].extend(glue)
                        self[sem][rels].extend(
                            glue_formulas
                        )  # add the glue formulas to every rel entry
                else:
                    if None not in self[sem]:
                        self[sem][None] = []
                    self[sem][None].extend(
                        glue_formulas
                    )  # add the glue formulas to every rel entry
            else:
                if relationships not in self[sem]:
                    self[sem][relationships] = []
                if supertype:
                    self[sem][relationships].extend(self[supertype][relationships])
                self[sem][relationships].extend(
                    glue_formulas
                )  # add the glue entry to the dictionary

    def __str__(self):
        accum = ""
        for pos in self:
            str_pos = "%s" % pos
            for relset in self[pos]:
                i = 1
                for gf in self[pos][relset]:
                    if i == 1:
                        accum += str_pos + ": "
                    else:
                        accum += " " * (len(str_pos) + 2)
                    accum += "%s" % gf
                    if relset and i == len(self[pos][relset]):
                        accum += " : %s" % relset
                    accum += "\n"
                    i += 1
        return accum

    def to_glueformula_list(self, depgraph, node=None, counter=None, verbose=False):
        if node is None:
            # TODO: should it be depgraph.root? Is this code tested?
            top = depgraph.nodes[0]
            depList = list(chain.from_iterable(top["deps"].values()))
            root = depgraph.nodes[depList[0]]

            return self.to_glueformula_list(depgraph, root, Counter(), verbose)

        glueformulas = self.lookup(node, depgraph, counter)
        for dep_idx in chain.from_iterable(node["deps"].values()):
            dep = depgraph.nodes[dep_idx]
            glueformulas.extend(
                self.to_glueformula_list(depgraph, dep, counter, verbose)
            )
        return glueformulas

    def lookup(self, node, depgraph, counter):
        semtype_names = self.get_semtypes(node)

        semtype = None
        for name in semtype_names:
            if name in self:
                semtype = self[name]
                break
        if semtype is None:
            # raise KeyError, "There is no GlueDict entry for sem type '%s' (for '%s')" % (sem, word)
            return []

        self.add_missing_dependencies(node, depgraph)

        lookup = self._lookup_semtype_option(semtype, node, depgraph)

        if not len(lookup):
            raise KeyError(
                "There is no GlueDict entry for sem type of '%s' "
                "with tag '%s', and rel '%s'" % (node["word"], node["tag"], node["rel"])
            )

        return self.get_glueformulas_from_semtype_entry(
            lookup, node["word"], node, depgraph, counter
        )

    def add_missing_dependencies(self, node, depgraph):
        rel = node["rel"].lower()

        if rel == "main":
            headnode = depgraph.nodes[node["head"]]
            subj = self.lookup_unique("subj", headnode, depgraph)
            relation = subj["rel"]
            node["deps"].setdefault(relation, [])
            node["deps"][relation].append(subj["address"])
            # node['deps'].append(subj['address'])

    def _lookup_semtype_option(self, semtype, node, depgraph):
        relationships = frozenset(
            depgraph.nodes[dep]["rel"].lower()
            for dep in chain.from_iterable(node["deps"].values())
            if depgraph.nodes[dep]["rel"].lower() not in OPTIONAL_RELATIONSHIPS
        )

        try:
            lookup = semtype[relationships]
        except KeyError:
            # An exact match is not found, so find the best match where
            # 'best' is defined as the glue entry whose relationship set has the
            # most relations of any possible relationship set that is a subset
            # of the actual depgraph
            best_match = frozenset()
            for relset_option in set(semtype) - {None}:
                if (
                    len(relset_option) > len(best_match)
                    and relset_option < relationships
                ):
                    best_match = relset_option
            if not best_match:
                if None in semtype:
                    best_match = None
                else:
                    return None
            lookup = semtype[best_match]

        return lookup

    def get_semtypes(self, node):
        """
        Based on the node, return a list of plausible semtypes in order of
        plausibility.
        """
        rel = node["rel"].lower()
        word = node["word"].lower()

        if rel == "spec":
            if word in SPEC_SEMTYPES:
                return [SPEC_SEMTYPES[word]]
            else:
                return [SPEC_SEMTYPES["default"]]
        elif rel in ["nmod", "vmod"]:
            return [node["tag"], rel]
        else:
            return [node["tag"]]

    def get_glueformulas_from_semtype_entry(
        self, lookup, word, node, depgraph, counter
    ):
        glueformulas = []

        glueFormulaFactory = self.get_GlueFormula_factory()
        for meaning, glue in lookup:
            gf = glueFormulaFactory(self.get_meaning_formula(meaning, word), glue)
            if not len(glueformulas):
                gf.word = word
            else:
                gf.word = f"{word}{len(glueformulas) + 1}"

            gf.glue = self.initialize_labels(gf.glue, node, depgraph, counter.get())

            glueformulas.append(gf)
        return glueformulas

    def get_meaning_formula(self, generic, word):
        """
        :param generic: A meaning formula string containing the
            parameter "<word>"
        :param word: The actual word to be replace "<word>"
        """
        word = word.replace(".", "")
        return generic.replace("<word>", word)

    def initialize_labels(self, expr, node, depgraph, unique_index):
        if isinstance(expr, linearlogic.AtomicExpression):
            name = self.find_label_name(expr.name.lower(), node, depgraph, unique_index)
            if name[0].isupper():
                return linearlogic.VariableExpression(name)
            else:
                return linearlogic.ConstantExpression(name)
        else:
            return linearlogic.ImpExpression(
                self.initialize_labels(expr.antecedent, node, depgraph, unique_index),
                self.initialize_labels(expr.consequent, node, depgraph, unique_index),
            )

    def find_label_name(self, name, node, depgraph, unique_index):
        try:
            dot = name.index(".")

            before_dot = name[:dot]
            after_dot = name[dot + 1 :]
            if before_dot == "super":
                return self.find_label_name(
                    after_dot, depgraph.nodes[node["head"]], depgraph, unique_index
                )
            else:
                return self.find_label_name(
                    after_dot,
                    self.lookup_unique(before_dot, node, depgraph),
                    depgraph,
                    unique_index,
                )
        except ValueError:
            lbl = self.get_label(node)
            if name == "f":
                return lbl
            elif name == "v":
                return "%sv" % lbl
            elif name == "r":
                return "%sr" % lbl
            elif name == "super":
                return self.get_label(depgraph.nodes[node["head"]])
            elif name == "var":
                return f"{lbl.upper()}{unique_index}"
            elif name == "a":
                return self.get_label(self.lookup_unique("conja", node, depgraph))
            elif name == "b":
                return self.get_label(self.lookup_unique("conjb", node, depgraph))
            else:
                return self.get_label(self.lookup_unique(name, node, depgraph))

    def get_label(self, node):
        """
        Pick an alphabetic character as identifier for an entity in the model.

        :param value: where to index into the list of characters
        :type value: int
        """
        value = node["address"]

        letter = [
            "f",
            "g",
            "h",
            "i",
            "j",
            "k",
            "l",
            "m",
            "n",
            "o",
            "p",
            "q",
            "r",
            "s",
            "t",
            "u",
            "v",
            "w",
            "x",
            "y",
            "z",
            "a",
            "b",
            "c",
            "d",
            "e",
        ][value - 1]
        num = int(value) // 26
        if num > 0:
            return letter + str(num)
        else:
            return letter

    def lookup_unique(self, rel, node, depgraph):
        """
        Lookup 'key'. There should be exactly one item in the associated relation.
        """
        deps = [
            depgraph.nodes[dep]
            for dep in chain.from_iterable(node["deps"].values())
            if depgraph.nodes[dep]["rel"].lower() == rel.lower()
        ]

        if len(deps) == 0:
            raise KeyError(
                "'{}' doesn't contain a feature '{}'".format(node["word"], rel)
            )
        elif len(deps) > 1:
            raise KeyError(
                "'{}' should only have one feature '{}'".format(node["word"], rel)
            )
        else:
            return deps[0]

    def get_GlueFormula_factory(self):
        return GlueFormula


class Glue:
    def __init__(
        self, semtype_file=None, remove_duplicates=False, depparser=None, verbose=False
    ):
        self.verbose = verbose
        self.remove_duplicates = remove_duplicates
        self.depparser = depparser

        from nltk import Prover9

        self.prover = Prover9()

        if semtype_file:
            self.semtype_file = semtype_file
        else:
            self.semtype_file = os.path.join(
                "grammars", "sample_grammars", "glue.semtype"
            )

    def train_depparser(self, depgraphs=None):
        if depgraphs:
            self.depparser.train(depgraphs)
        else:
            self.depparser.train_from_file(
                nltk.data.find(
                    os.path.join("grammars", "sample_grammars", "glue_train.conll")
                )
            )

    def parse_to_meaning(self, sentence):
        readings = []
        for agenda in self.parse_to_compiled(sentence):
            readings.extend(self.get_readings(agenda))
        return readings

    def get_readings(self, agenda):
        readings = []
        agenda_length = len(agenda)
        atomics = dict()
        nonatomics = dict()
        while agenda:  # is not empty
            cur = agenda.pop()
            glue_simp = cur.glue.simplify()
            if isinstance(
                glue_simp, linearlogic.ImpExpression
            ):  # if cur.glue is non-atomic
                for key in atomics:
                    try:
                        if isinstance(cur.glue, linearlogic.ApplicationExpression):
                            bindings = cur.glue.bindings
                        else:
                            bindings = linearlogic.BindingDict()
                        glue_simp.antecedent.unify(key, bindings)
                        for atomic in atomics[key]:
                            if not (
                                cur.indices & atomic.indices
                            ):  # if the sets of indices are disjoint
                                try:
                                    agenda.append(cur.applyto(atomic))
                                except linearlogic.LinearLogicApplicationException:
                                    pass
                    except linearlogic.UnificationException:
                        pass
                try:
                    nonatomics[glue_simp.antecedent].append(cur)
                except KeyError:
                    nonatomics[glue_simp.antecedent] = [cur]

            else:  # else cur.glue is atomic
                for key in nonatomics:
                    for nonatomic in nonatomics[key]:
                        try:
                            if isinstance(
                                nonatomic.glue, linearlogic.ApplicationExpression
                            ):
                                bindings = nonatomic.glue.bindings
                            else:
                                bindings = linearlogic.BindingDict()
                            glue_simp.unify(key, bindings)
                            if not (
                                cur.indices & nonatomic.indices
                            ):  # if the sets of indices are disjoint
                                try:
                                    agenda.append(nonatomic.applyto(cur))
                                except linearlogic.LinearLogicApplicationException:
                                    pass
                        except linearlogic.UnificationException:
                            pass
                try:
                    atomics[glue_simp].append(cur)
                except KeyError:
                    atomics[glue_simp] = [cur]

        for entry in atomics:
            for gf in atomics[entry]:
                if len(gf.indices) == agenda_length:
                    self._add_to_reading_list(gf, readings)
        for entry in nonatomics:
            for gf in nonatomics[entry]:
                if len(gf.indices) == agenda_length:
                    self._add_to_reading_list(gf, readings)
        return readings

    def _add_to_reading_list(self, glueformula, reading_list):
        add_reading = True
        if self.remove_duplicates:
            for reading in reading_list:
                try:
                    if reading.equiv(glueformula.meaning, self.prover):
                        add_reading = False
                        break
                except Exception as e:
                    # if there is an exception, the syntax of the formula
                    # may not be understandable by the prover, so don't
                    # throw out the reading.
                    print("Error when checking logical equality of statements", e)

        if add_reading:
            reading_list.append(glueformula.meaning)

    def parse_to_compiled(self, sentence):
        gfls = [self.depgraph_to_glue(dg) for dg in self.dep_parse(sentence)]
        return [self.gfl_to_compiled(gfl) for gfl in gfls]

    def dep_parse(self, sentence):
        """
        Return a dependency graph for the sentence.

        :param sentence: the sentence to be parsed
        :type sentence: list(str)
        :rtype: DependencyGraph
        """

        # Lazy-initialize the depparser
        if self.depparser is None:
            from nltk.parse import MaltParser

            self.depparser = MaltParser(tagger=self.get_pos_tagger())
        if not self.depparser._trained:
            self.train_depparser()
        return self.depparser.parse(sentence, verbose=self.verbose)

    def depgraph_to_glue(self, depgraph):
        return self.get_glue_dict().to_glueformula_list(depgraph)

    def get_glue_dict(self):
        return GlueDict(self.semtype_file)

    def gfl_to_compiled(self, gfl):
        index_counter = Counter()
        return_list = []
        for gf in gfl:
            return_list.extend(gf.compile(index_counter))

        if self.verbose:
            print("Compiled Glue Premises:")
            for cgf in return_list:
                print(cgf)

        return return_list

    def get_pos_tagger(self):
        from nltk.corpus import brown

        regexp_tagger = RegexpTagger(
            [
                (r"^-?[0-9]+(\.[0-9]+)?$", "CD"),  # cardinal numbers
                (r"(The|the|A|a|An|an)$", "AT"),  # articles
                (r".*able$", "JJ"),  # adjectives
                (r".*ness$", "NN"),  # nouns formed from adjectives
                (r".*ly$", "RB"),  # adverbs
                (r".*s$", "NNS"),  # plural nouns
                (r".*ing$", "VBG"),  # gerunds
                (r".*ed$", "VBD"),  # past tense verbs
                (r".*", "NN"),  # nouns (default)
            ]
        )
        brown_train = brown.tagged_sents(categories="news")
        unigram_tagger = UnigramTagger(brown_train, backoff=regexp_tagger)
        bigram_tagger = BigramTagger(brown_train, backoff=unigram_tagger)
        trigram_tagger = TrigramTagger(brown_train, backoff=bigram_tagger)

        # Override particular words
        main_tagger = RegexpTagger(
            [(r"(A|a|An|an)$", "ex_quant"), (r"(Every|every|All|all)$", "univ_quant")],
            backoff=trigram_tagger,
        )

        return main_tagger


class DrtGlueFormula(GlueFormula):
    def __init__(self, meaning, glue, indices=None):
        if not indices:
            indices = set()

        if isinstance(meaning, str):
            self.meaning = drt.DrtExpression.fromstring(meaning)
        elif isinstance(meaning, drt.DrtExpression):
            self.meaning = meaning
        else:
            raise RuntimeError(
                "Meaning term neither string or expression: %s, %s"
                % (meaning, meaning.__class__)
            )

        if isinstance(glue, str):
            self.glue = linearlogic.LinearLogicParser().parse(glue)
        elif isinstance(glue, linearlogic.Expression):
            self.glue = glue
        else:
            raise RuntimeError(
                "Glue term neither string or expression: %s, %s"
                % (glue, glue.__class__)
            )

        self.indices = indices

    def make_VariableExpression(self, name):
        return drt.DrtVariableExpression(name)

    def make_LambdaExpression(self, variable, term):
        return drt.DrtLambdaExpression(variable, term)


class DrtGlueDict(GlueDict):
    def get_GlueFormula_factory(self):
        return DrtGlueFormula


class DrtGlue(Glue):
    def __init__(
        self, semtype_file=None, remove_duplicates=False, depparser=None, verbose=False
    ):
        if not semtype_file:
            semtype_file = os.path.join(
                "grammars", "sample_grammars", "drt_glue.semtype"
            )
        Glue.__init__(self, semtype_file, remove_duplicates, depparser, verbose)

    def get_glue_dict(self):
        return DrtGlueDict(self.semtype_file)


def demo(show_example=-1):
    from nltk.parse import MaltParser

    examples = [
        "David sees Mary",
        "David eats a sandwich",
        "every man chases a dog",
        "every man believes a dog sleeps",
        "John gives David a sandwich",
        "John chases himself",
    ]
    #                'John persuades David to order a pizza',
    #                'John tries to go',
    #                'John tries to find a unicorn',
    #                'John seems to vanish',
    #                'a unicorn seems to approach',
    #                'every big cat leaves',
    #                'every gray cat leaves',
    #                'every big gray cat leaves',
    #                'a former senator leaves',

    print("============== DEMO ==============")

    tagger = RegexpTagger(
        [
            ("^(David|Mary|John)$", "NNP"),
            (
                "^(sees|eats|chases|believes|gives|sleeps|chases|persuades|tries|seems|leaves)$",
                "VB",
            ),
            ("^(go|order|vanish|find|approach)$", "VB"),
            ("^(a)$", "ex_quant"),
            ("^(every)$", "univ_quant"),
            ("^(sandwich|man|dog|pizza|unicorn|cat|senator)$", "NN"),
            ("^(big|gray|former)$", "JJ"),
            ("^(him|himself)$", "PRP"),
        ]
    )

    depparser = MaltParser(tagger=tagger)
    glue = Glue(depparser=depparser, verbose=False)

    for i, sentence in enumerate(examples):
        if i == show_example or show_example == -1:
            print(f"[[[Example {i}]]]  {sentence}")
            for reading in glue.parse_to_meaning(sentence.split()):
                print(reading.simplify())
            print("")


if __name__ == "__main__":
    demo()

# === NexusCore/myenv\Lib\site-packages\pip\_vendor\requests\sessions.py ===
"""
requests.sessions
~~~~~~~~~~~~~~~~~

This module provides a Session object to manage and persist settings across
requests (cookies, auth, proxies).
"""
import os
import sys
import time
from collections import OrderedDict
from datetime import timedelta

from ._internal_utils import to_native_string
from .adapters import HTTPAdapter
from .auth import _basic_auth_str
from .compat import Mapping, cookielib, urljoin, urlparse
from .cookies import (
    RequestsCookieJar,
    cookiejar_from_dict,
    extract_cookies_to_jar,
    merge_cookies,
)
from .exceptions import (
    ChunkedEncodingError,
    ContentDecodingError,
    InvalidSchema,
    TooManyRedirects,
)
from .hooks import default_hooks, dispatch_hook

# formerly defined here, reexposed here for backward compatibility
from .models import (  # noqa: F401
    DEFAULT_REDIRECT_LIMIT,
    REDIRECT_STATI,
    PreparedRequest,
    Request,
)
from .status_codes import codes
from .structures import CaseInsensitiveDict
from .utils import (  # noqa: F401
    DEFAULT_PORTS,
    default_headers,
    get_auth_from_url,
    get_environ_proxies,
    get_netrc_auth,
    requote_uri,
    resolve_proxies,
    rewind_body,
    should_bypass_proxies,
    to_key_val_list,
)

# Preferred clock, based on which one is more accurate on a given system.
if sys.platform == "win32":
    preferred_clock = time.perf_counter
else:
    preferred_clock = time.time


def merge_setting(request_setting, session_setting, dict_class=OrderedDict):
    """Determines appropriate setting for a given request, taking into account
    the explicit setting on that request, and the setting in the session. If a
    setting is a dictionary, they will be merged together using `dict_class`
    """

    if session_setting is None:
        return request_setting

    if request_setting is None:
        return session_setting

    # Bypass if not a dictionary (e.g. verify)
    if not (
        isinstance(session_setting, Mapping) and isinstance(request_setting, Mapping)
    ):
        return request_setting

    merged_setting = dict_class(to_key_val_list(session_setting))
    merged_setting.update(to_key_val_list(request_setting))

    # Remove keys that are set to None. Extract keys first to avoid altering
    # the dictionary during iteration.
    none_keys = [k for (k, v) in merged_setting.items() if v is None]
    for key in none_keys:
        del merged_setting[key]

    return merged_setting


def merge_hooks(request_hooks, session_hooks, dict_class=OrderedDict):
    """Properly merges both requests and session hooks.

    This is necessary because when request_hooks == {'response': []}, the
    merge breaks Session hooks entirely.
    """
    if session_hooks is None or session_hooks.get("response") == []:
        return request_hooks

    if request_hooks is None or request_hooks.get("response") == []:
        return session_hooks

    return merge_setting(request_hooks, session_hooks, dict_class)


class SessionRedirectMixin:
    def get_redirect_target(self, resp):
        """Receives a Response. Returns a redirect URI or ``None``"""
        # Due to the nature of how requests processes redirects this method will
        # be called at least once upon the original response and at least twice
        # on each subsequent redirect response (if any).
        # If a custom mixin is used to handle this logic, it may be advantageous
        # to cache the redirect location onto the response object as a private
        # attribute.
        if resp.is_redirect:
            location = resp.headers["location"]
            # Currently the underlying http module on py3 decode headers
            # in latin1, but empirical evidence suggests that latin1 is very
            # rarely used with non-ASCII characters in HTTP headers.
            # It is more likely to get UTF8 header rather than latin1.
            # This causes incorrect handling of UTF8 encoded location headers.
            # To solve this, we re-encode the location in latin1.
            location = location.encode("latin1")
            return to_native_string(location, "utf8")
        return None

    def should_strip_auth(self, old_url, new_url):
        """Decide whether Authorization header should be removed when redirecting"""
        old_parsed = urlparse(old_url)
        new_parsed = urlparse(new_url)
        if old_parsed.hostname != new_parsed.hostname:
            return True
        # Special case: allow http -> https redirect when using the standard
        # ports. This isn't specified by RFC 7235, but is kept to avoid
        # breaking backwards compatibility with older versions of requests
        # that allowed any redirects on the same host.
        if (
            old_parsed.scheme == "http"
            and old_parsed.port in (80, None)
            and new_parsed.scheme == "https"
            and new_parsed.port in (443, None)
        ):
            return False

        # Handle default port usage corresponding to scheme.
        changed_port = old_parsed.port != new_parsed.port
        changed_scheme = old_parsed.scheme != new_parsed.scheme
        default_port = (DEFAULT_PORTS.get(old_parsed.scheme, None), None)
        if (
            not changed_scheme
            and old_parsed.port in default_port
            and new_parsed.port in default_port
        ):
            return False

        # Standard case: root URI must match
        return changed_port or changed_scheme

    def resolve_redirects(
        self,
        resp,
        req,
        stream=False,
        timeout=None,
        verify=True,
        cert=None,
        proxies=None,
        yield_requests=False,
        **adapter_kwargs,
    ):
        """Receives a Response. Returns a generator of Responses or Requests."""

        hist = []  # keep track of history

        url = self.get_redirect_target(resp)
        previous_fragment = urlparse(req.url).fragment
        while url:
            prepared_request = req.copy()

            # Update history and keep track of redirects.
            # resp.history must ignore the original request in this loop
            hist.append(resp)
            resp.history = hist[1:]

            try:
                resp.content  # Consume socket so it can be released
            except (ChunkedEncodingError, ContentDecodingError, RuntimeError):
                resp.raw.read(decode_content=False)

            if len(resp.history) >= self.max_redirects:
                raise TooManyRedirects(
                    f"Exceeded {self.max_redirects} redirects.", response=resp
                )

            # Release the connection back into the pool.
            resp.close()

            # Handle redirection without scheme (see: RFC 1808 Section 4)
            if url.startswith("//"):
                parsed_rurl = urlparse(resp.url)
                url = ":".join([to_native_string(parsed_rurl.scheme), url])

            # Normalize url case and attach previous fragment if needed (RFC 7231 7.1.2)
            parsed = urlparse(url)
            if parsed.fragment == "" and previous_fragment:
                parsed = parsed._replace(fragment=previous_fragment)
            elif parsed.fragment:
                previous_fragment = parsed.fragment
            url = parsed.geturl()

            # Facilitate relative 'location' headers, as allowed by RFC 7231.
            # (e.g. '/path/to/resource' instead of 'http://domain.tld/path/to/resource')
            # Compliant with RFC3986, we percent encode the url.
            if not parsed.netloc:
                url = urljoin(resp.url, requote_uri(url))
            else:
                url = requote_uri(url)

            prepared_request.url = to_native_string(url)

            self.rebuild_method(prepared_request, resp)

            # https://github.com/psf/requests/issues/1084
            if resp.status_code not in (
                codes.temporary_redirect,
                codes.permanent_redirect,
            ):
                # https://github.com/psf/requests/issues/3490
                purged_headers = ("Content-Length", "Content-Type", "Transfer-Encoding")
                for header in purged_headers:
                    prepared_request.headers.pop(header, None)
                prepared_request.body = None

            headers = prepared_request.headers
            headers.pop("Cookie", None)

            # Extract any cookies sent on the response to the cookiejar
            # in the new request. Because we've mutated our copied prepared
            # request, use the old one that we haven't yet touched.
            extract_cookies_to_jar(prepared_request._cookies, req, resp.raw)
            merge_cookies(prepared_request._cookies, self.cookies)
            prepared_request.prepare_cookies(prepared_request._cookies)

            # Rebuild auth and proxy information.
            proxies = self.rebuild_proxies(prepared_request, proxies)
            self.rebuild_auth(prepared_request, resp)

            # A failed tell() sets `_body_position` to `object()`. This non-None
            # value ensures `rewindable` will be True, allowing us to raise an
            # UnrewindableBodyError, instead of hanging the connection.
            rewindable = prepared_request._body_position is not None and (
                "Content-Length" in headers or "Transfer-Encoding" in headers
            )

            # Attempt to rewind consumed file-like object.
            if rewindable:
                rewind_body(prepared_request)

            # Override the original request.
            req = prepared_request

            if yield_requests:
                yield req
            else:
                resp = self.send(
                    req,
                    stream=stream,
                    timeout=timeout,
                    verify=verify,
                    cert=cert,
                    proxies=proxies,
                    allow_redirects=False,
                    **adapter_kwargs,
                )

                extract_cookies_to_jar(self.cookies, prepared_request, resp.raw)

                # extract redirect url, if any, for the next loop
                url = self.get_redirect_target(resp)
                yield resp

    def rebuild_auth(self, prepared_request, response):
        """When being redirected we may want to strip authentication from the
        request to avoid leaking credentials. This method intelligently removes
        and reapplies authentication where possible to avoid credential loss.
        """
        headers = prepared_request.headers
        url = prepared_request.url

        if "Authorization" in headers and self.should_strip_auth(
            response.request.url, url
        ):
            # If we get redirected to a new host, we should strip out any
            # authentication headers.
            del headers["Authorization"]

        # .netrc might have more auth for us on our new host.
        new_auth = get_netrc_auth(url) if self.trust_env else None
        if new_auth is not None:
            prepared_request.prepare_auth(new_auth)

    def rebuild_proxies(self, prepared_request, proxies):
        """This method re-evaluates the proxy configuration by considering the
        environment variables. If we are redirected to a URL covered by
        NO_PROXY, we strip the proxy configuration. Otherwise, we set missing
        proxy keys for this URL (in case they were stripped by a previous
        redirect).

        This method also replaces the Proxy-Authorization header where
        necessary.

        :rtype: dict
        """
        headers = prepared_request.headers
        scheme = urlparse(prepared_request.url).scheme
        new_proxies = resolve_proxies(prepared_request, proxies, self.trust_env)

        if "Proxy-Authorization" in headers:
            del headers["Proxy-Authorization"]

        try:
            username, password = get_auth_from_url(new_proxies[scheme])
        except KeyError:
            username, password = None, None

        # urllib3 handles proxy authorization for us in the standard adapter.
        # Avoid appending this to TLS tunneled requests where it may be leaked.
        if not scheme.startswith("https") and username and password:
            headers["Proxy-Authorization"] = _basic_auth_str(username, password)

        return new_proxies

    def rebuild_method(self, prepared_request, response):
        """When being redirected we may want to change the method of the request
        based on certain specs or browser behavior.
        """
        method = prepared_request.method

        # https://tools.ietf.org/html/rfc7231#section-6.4.4
        if response.status_code == codes.see_other and method != "HEAD":
            method = "GET"

        # Do what the browsers do, despite standards...
        # First, turn 302s into GETs.
        if response.status_code == codes.found and method != "HEAD":
            method = "GET"

        # Second, if a POST is responded to with a 301, turn it into a GET.
        # This bizarre behaviour is explained in Issue 1704.
        if response.status_code == codes.moved and method == "POST":
            method = "GET"

        prepared_request.method = method


class Session(SessionRedirectMixin):
    """A Requests session.

    Provides cookie persistence, connection-pooling, and configuration.

    Basic Usage::

      >>> import requests
      >>> s = requests.Session()
      >>> s.get('https://httpbin.org/get')
      <Response [200]>

    Or as a context manager::

      >>> with requests.Session() as s:
      ...     s.get('https://httpbin.org/get')
      <Response [200]>
    """

    __attrs__ = [
        "headers",
        "cookies",
        "auth",
        "proxies",
        "hooks",
        "params",
        "verify",
        "cert",
        "adapters",
        "stream",
        "trust_env",
        "max_redirects",
    ]

    def __init__(self):
        #: A case-insensitive dictionary of headers to be sent on each
        #: :class:`Request <Request>` sent from this
        #: :class:`Session <Session>`.
        self.headers = default_headers()

        #: Default Authentication tuple or object to attach to
        #: :class:`Request <Request>`.
        self.auth = None

        #: Dictionary mapping protocol or protocol and host to the URL of the proxy
        #: (e.g. {'http': 'foo.bar:3128', 'http://host.name': 'foo.bar:4012'}) to
        #: be used on each :class:`Request <Request>`.
        self.proxies = {}

        #: Event-handling hooks.
        self.hooks = default_hooks()

        #: Dictionary of querystring data to attach to each
        #: :class:`Request <Request>`. The dictionary values may be lists for
        #: representing multivalued query parameters.
        self.params = {}

        #: Stream response content default.
        self.stream = False

        #: SSL Verification default.
        #: Defaults to `True`, requiring requests to verify the TLS certificate at the
        #: remote end.
        #: If verify is set to `False`, requests will accept any TLS certificate
        #: presented by the server, and will ignore hostname mismatches and/or
        #: expired certificates, which will make your application vulnerable to
        #: man-in-the-middle (MitM) attacks.
        #: Only set this to `False` for testing.
        self.verify = True

        #: SSL client certificate default, if String, path to ssl client
        #: cert file (.pem). If Tuple, ('cert', 'key') pair.
        self.cert = None

        #: Maximum number of redirects allowed. If the request exceeds this
        #: limit, a :class:`TooManyRedirects` exception is raised.
        #: This defaults to requests.models.DEFAULT_REDIRECT_LIMIT, which is
        #: 30.
        self.max_redirects = DEFAULT_REDIRECT_LIMIT

        #: Trust environment settings for proxy configuration, default
        #: authentication and similar.
        self.trust_env = True

        #: A CookieJar containing all currently outstanding cookies set on this
        #: session. By default it is a
        #: :class:`RequestsCookieJar <requests.cookies.RequestsCookieJar>`, but
        #: may be any other ``cookielib.CookieJar`` compatible object.
        self.cookies = cookiejar_from_dict({})

        # Default connection adapters.
        self.adapters = OrderedDict()
        self.mount("https://", HTTPAdapter())
        self.mount("http://", HTTPAdapter())

    def __enter__(self):
        return self

    def __exit__(self, *args):
        self.close()

    def prepare_request(self, request):
        """Constructs a :class:`PreparedRequest <PreparedRequest>` for
        transmission and returns it. The :class:`PreparedRequest` has settings
        merged from the :class:`Request <Request>` instance and those of the
        :class:`Session`.

        :param request: :class:`Request` instance to prepare with this
            session's settings.
        :rtype: requests.PreparedRequest
        """
        cookies = request.cookies or {}

        # Bootstrap CookieJar.
        if not isinstance(cookies, cookielib.CookieJar):
            cookies = cookiejar_from_dict(cookies)

        # Merge with session cookies
        merged_cookies = merge_cookies(
            merge_cookies(RequestsCookieJar(), self.cookies), cookies
        )

        # Set environment's basic authentication if not explicitly set.
        auth = request.auth
        if self.trust_env and not auth and not self.auth:
            auth = get_netrc_auth(request.url)

        p = PreparedRequest()
        p.prepare(
            method=request.method.upper(),
            url=request.url,
            files=request.files,
            data=request.data,
            json=request.json,
            headers=merge_setting(
                request.headers, self.headers, dict_class=CaseInsensitiveDict
            ),
            params=merge_setting(request.params, self.params),
            auth=merge_setting(auth, self.auth),
            cookies=merged_cookies,
            hooks=merge_hooks(request.hooks, self.hooks),
        )
        return p

    def request(
        self,
        method,
        url,
        params=None,
        data=None,
        headers=None,
        cookies=None,
        files=None,
        auth=None,
        timeout=None,
        allow_redirects=True,
        proxies=None,
        hooks=None,
        stream=None,
        verify=None,
        cert=None,
        json=None,
    ):
        """Constructs a :class:`Request <Request>`, prepares it and sends it.
        Returns :class:`Response <Response>` object.

        :param method: method for the new :class:`Request` object.
        :param url: URL for the new :class:`Request` object.
        :param params: (optional) Dictionary or bytes to be sent in the query
            string for the :class:`Request`.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the
            :class:`Request`.
        :param headers: (optional) Dictionary of HTTP Headers to send with the
            :class:`Request`.
        :param cookies: (optional) Dict or CookieJar object to send with the
            :class:`Request`.
        :param files: (optional) Dictionary of ``'filename': file-like-objects``
            for multipart encoding upload.
        :param auth: (optional) Auth tuple or callable to enable
            Basic/Digest/Custom HTTP Auth.
        :param timeout: (optional) How long to wait for the server to send
            data before giving up, as a float, or a :ref:`(connect timeout,
            read timeout) <timeouts>` tuple.
        :type timeout: float or tuple
        :param allow_redirects: (optional) Set to True by default.
        :type allow_redirects: bool
        :param proxies: (optional) Dictionary mapping protocol or protocol and
            hostname to the URL of the proxy.
        :param hooks: (optional) Dictionary mapping hook name to one event or
            list of events, event must be callable.
        :param stream: (optional) whether to immediately download the response
            content. Defaults to ``False``.
        :param verify: (optional) Either a boolean, in which case it controls whether we verify
            the server's TLS certificate, or a string, in which case it must be a path
            to a CA bundle to use. Defaults to ``True``. When set to
            ``False``, requests will accept any TLS certificate presented by
            the server, and will ignore hostname mismatches and/or expired
            certificates, which will make your application vulnerable to
            man-in-the-middle (MitM) attacks. Setting verify to ``False``
            may be useful during local development or testing.
        :param cert: (optional) if String, path to ssl client cert file (.pem).
            If Tuple, ('cert', 'key') pair.
        :rtype: requests.Response
        """
        # Create the Request.
        req = Request(
            method=method.upper(),
            url=url,
            headers=headers,
            files=files,
            data=data or {},
            json=json,
            params=params or {},
            auth=auth,
            cookies=cookies,
            hooks=hooks,
        )
        prep = self.prepare_request(req)

        proxies = proxies or {}

        settings = self.merge_environment_settings(
            prep.url, proxies, stream, verify, cert
        )

        # Send the request.
        send_kwargs = {
            "timeout": timeout,
            "allow_redirects": allow_redirects,
        }
        send_kwargs.update(settings)
        resp = self.send(prep, **send_kwargs)

        return resp

    def get(self, url, **kwargs):
        r"""Sends a GET request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", True)
        return self.request("GET", url, **kwargs)

    def options(self, url, **kwargs):
        r"""Sends a OPTIONS request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", True)
        return self.request("OPTIONS", url, **kwargs)

    def head(self, url, **kwargs):
        r"""Sends a HEAD request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        kwargs.setdefault("allow_redirects", False)
        return self.request("HEAD", url, **kwargs)

    def post(self, url, data=None, json=None, **kwargs):
        r"""Sends a POST request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param json: (optional) json to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("POST", url, data=data, json=json, **kwargs)

    def put(self, url, data=None, **kwargs):
        r"""Sends a PUT request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("PUT", url, data=data, **kwargs)

    def patch(self, url, data=None, **kwargs):
        r"""Sends a PATCH request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param data: (optional) Dictionary, list of tuples, bytes, or file-like
            object to send in the body of the :class:`Request`.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("PATCH", url, data=data, **kwargs)

    def delete(self, url, **kwargs):
        r"""Sends a DELETE request. Returns :class:`Response` object.

        :param url: URL for the new :class:`Request` object.
        :param \*\*kwargs: Optional arguments that ``request`` takes.
        :rtype: requests.Response
        """

        return self.request("DELETE", url, **kwargs)

    def send(self, request, **kwargs):
        """Send a given PreparedRequest.

        :rtype: requests.Response
        """
        # Set defaults that the hooks can utilize to ensure they always have
        # the correct parameters to reproduce the previous request.
        kwargs.setdefault("stream", self.stream)
        kwargs.setdefault("verify", self.verify)
        kwargs.setdefault("cert", self.cert)
        if "proxies" not in kwargs:
            kwargs["proxies"] = resolve_proxies(request, self.proxies, self.trust_env)

        # It's possible that users might accidentally send a Request object.
        # Guard against that specific failure case.
        if isinstance(request, Request):
            raise ValueError("You can only send PreparedRequests.")

        # Set up variables needed for resolve_redirects and dispatching of hooks
        allow_redirects = kwargs.pop("allow_redirects", True)
        stream = kwargs.get("stream")
        hooks = request.hooks

        # Get the appropriate adapter to use
        adapter = self.get_adapter(url=request.url)

        # Start time (approximately) of the request
        start = preferred_clock()

        # Send the request
        r = adapter.send(request, **kwargs)

        # Total elapsed time of the request (approximately)
        elapsed = preferred_clock() - start
        r.elapsed = timedelta(seconds=elapsed)

        # Response manipulation hooks
        r = dispatch_hook("response", hooks, r, **kwargs)

        # Persist cookies
        if r.history:
            # If the hooks create history then we want those cookies too
            for resp in r.history:
                extract_cookies_to_jar(self.cookies, resp.request, resp.raw)

        extract_cookies_to_jar(self.cookies, request, r.raw)

        # Resolve redirects if allowed.
        if allow_redirects:
            # Redirect resolving generator.
            gen = self.resolve_redirects(r, request, **kwargs)
            history = [resp for resp in gen]
        else:
            history = []

        # Shuffle things around if there's history.
        if history:
            # Insert the first (original) request at the start
            history.insert(0, r)
            # Get the last request made
            r = history.pop()
            r.history = history

        # If redirects aren't being followed, store the response on the Request for Response.next().
        if not allow_redirects:
            try:
                r._next = next(
                    self.resolve_redirects(r, request, yield_requests=True, **kwargs)
                )
            except StopIteration:
                pass

        if not stream:
            r.content

        return r

    def merge_environment_settings(self, url, proxies, stream, verify, cert):
        """
        Check the environment and merge it with some settings.

        :rtype: dict
        """
        # Gather clues from the surrounding environment.
        if self.trust_env:
            # Set environment's proxies.
            no_proxy = proxies.get("no_proxy") if proxies is not None else None
            env_proxies = get_environ_proxies(url, no_proxy=no_proxy)
            for k, v in env_proxies.items():
                proxies.setdefault(k, v)

            # Look for requests environment configuration
            # and be compatible with cURL.
            if verify is True or verify is None:
                verify = (
                    os.environ.get("REQUESTS_CA_BUNDLE")
                    or os.environ.get("CURL_CA_BUNDLE")
                    or verify
                )

        # Merge all the kwargs.
        proxies = merge_setting(proxies, self.proxies)
        stream = merge_setting(stream, self.stream)
        verify = merge_setting(verify, self.verify)
        cert = merge_setting(cert, self.cert)

        return {"proxies": proxies, "stream": stream, "verify": verify, "cert": cert}

    def get_adapter(self, url):
        """
        Returns the appropriate connection adapter for the given URL.

        :rtype: requests.adapters.BaseAdapter
        """
        for prefix, adapter in self.adapters.items():
            if url.lower().startswith(prefix.lower()):
                return adapter

        # Nothing matches :-/
        raise InvalidSchema(f"No connection adapters were found for {url!r}")

    def close(self):
        """Closes all adapters and as such the session"""
        for v in self.adapters.values():
            v.close()

    def mount(self, prefix, adapter):
        """Registers a connection adapter to a prefix.

        Adapters are sorted in descending order by prefix length.
        """
        self.adapters[prefix] = adapter
        keys_to_move = [k for k in self.adapters if len(k) < len(prefix)]

        for key in keys_to_move:
            self.adapters[key] = self.adapters.pop(key)

    def __getstate__(self):
        state = {attr: getattr(self, attr, None) for attr in self.__attrs__}
        return state

    def __setstate__(self, state):
        for attr, value in state.items():
            setattr(self, attr, value)


def session():
    """
    Returns a :class:`Session` for context-management.

    .. deprecated:: 1.0.0

        This method has been deprecated since version 1.0.0 and is only kept for
        backwards compatibility. New code should use :class:`~requests.sessions.Session`
        to create a session. This may be removed at a future date.

    :rtype: Session
    """
    return Session()

# === NexusCore/openenv\Lib\site-packages\litellm\exceptions.py ===
# +-----------------------------------------------+
# |                                               |
# |           Give Feedback / Get Help            |
# | https://github.com/BerriAI/litellm/issues/new |
# |                                               |
# +-----------------------------------------------+
#
#  Thank you users! We ❤️ you! - Krrish & Ishaan

## LiteLLM versions of the OpenAI Exception Types

from typing import Optional

import httpx
import openai

from litellm.types.utils import LiteLLMCommonStrings


class AuthenticationError(openai.AuthenticationError):  # type: ignore
    def __init__(
        self,
        message,
        llm_provider,
        model,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 401
        self.message = "litellm.AuthenticationError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        self.response = response or httpx.Response(
            status_code=self.status_code,
            request=httpx.Request(
                method="GET", url="https://litellm.ai"
            ),  # mock request object
        )
        super().__init__(
            self.message, response=self.response, body=None
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


# raise when invalid models passed, example gpt-8
class NotFoundError(openai.NotFoundError):  # type: ignore
    def __init__(
        self,
        message,
        model,
        llm_provider,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 404
        self.message = "litellm.NotFoundError: {}".format(message)
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        self.response = response or httpx.Response(
            status_code=self.status_code,
            request=httpx.Request(
                method="GET", url="https://litellm.ai"
            ),  # mock request object
        )
        super().__init__(
            self.message, response=self.response, body=None
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class BadRequestError(openai.BadRequestError):  # type: ignore
    def __init__(
        self,
        message,
        model,
        llm_provider,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
        body: Optional[dict] = None,
    ):
        self.status_code = 400
        self.message = "litellm.BadRequestError: {}".format(message)
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        response = httpx.Response(
            status_code=self.status_code,
            request=httpx.Request(
                method="GET", url="https://litellm.ai"
            ),  # mock request object
        )
        self.max_retries = max_retries
        self.num_retries = num_retries
        super().__init__(
            self.message, response=response, body=body
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class UnprocessableEntityError(openai.UnprocessableEntityError):  # type: ignore
    def __init__(
        self,
        message,
        model,
        llm_provider,
        response: httpx.Response,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 422
        self.message = "litellm.UnprocessableEntityError: {}".format(message)
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        super().__init__(
            self.message, response=response, body=None
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class Timeout(openai.APITimeoutError):  # type: ignore
    def __init__(
        self,
        message,
        model,
        llm_provider,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
        headers: Optional[dict] = None,
        exception_status_code: Optional[int] = None,
    ):
        request = httpx.Request(
            method="POST",
            url="https://api.openai.com/v1",
        )
        super().__init__(
            request=request
        )  # Call the base class constructor with the parameters it needs
        self.status_code = exception_status_code or 408
        self.message = "litellm.Timeout: {}".format(message)
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        self.headers = headers

    # custom function to convert to str
    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class PermissionDeniedError(openai.PermissionDeniedError):  # type:ignore
    def __init__(
        self,
        message,
        llm_provider,
        model,
        response: httpx.Response,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 403
        self.message = "litellm.PermissionDeniedError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        super().__init__(
            self.message, response=response, body=None
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class RateLimitError(openai.RateLimitError):  # type: ignore
    def __init__(
        self,
        message,
        llm_provider,
        model,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 429
        self.message = "litellm.RateLimitError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        _response_headers = (
            getattr(response, "headers", None) if response is not None else None
        )
        self.response = httpx.Response(
            status_code=429,
            headers=_response_headers,
            request=httpx.Request(
                method="POST",
                url=" https://cloud.google.com/vertex-ai/",
            ),
        )
        super().__init__(
            self.message, response=self.response, body=None
        )  # Call the base class constructor with the parameters it needs
        self.code = "429"
        self.type = "throttling_error"

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


# sub class of rate limit error - meant to give more granularity for error handling context window exceeded errors
class ContextWindowExceededError(BadRequestError):  # type: ignore
    def __init__(
        self,
        message,
        model,
        llm_provider,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
    ):
        self.status_code = 400
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        self.response = httpx.Response(status_code=400, request=request)
        super().__init__(
            message=message,
            model=self.model,  # type: ignore
            llm_provider=self.llm_provider,  # type: ignore
            response=self.response,
            litellm_debug_info=self.litellm_debug_info,
        )  # Call the base class constructor with the parameters it needs

        # set after, to make it clear the raised error is a context window exceeded error
        self.message = "litellm.ContextWindowExceededError: {}".format(self.message)

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


# sub class of bad request error - meant to help us catch guardrails-related errors on proxy.
class RejectedRequestError(BadRequestError):  # type: ignore
    def __init__(
        self,
        message,
        model,
        llm_provider,
        request_data: dict,
        litellm_debug_info: Optional[str] = None,
    ):
        self.status_code = 400
        self.message = "litellm.RejectedRequestError: {}".format(message)
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        self.request_data = request_data
        request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        response = httpx.Response(status_code=400, request=request)
        super().__init__(
            message=self.message,
            model=self.model,  # type: ignore
            llm_provider=self.llm_provider,  # type: ignore
            response=response,
            litellm_debug_info=self.litellm_debug_info,
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class ContentPolicyViolationError(BadRequestError):  # type: ignore
    #  Error code: 400 - {'error': {'code': 'content_policy_violation', 'message': 'Your request was rejected as a result of our safety system. Image descriptions generated from your prompt may contain text that is not allowed by our safety system. If you believe this was done in error, your request may succeed if retried, or by adjusting your prompt.', 'param': None, 'type': 'invalid_request_error'}}
    def __init__(
        self,
        message,
        model,
        llm_provider,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
    ):
        self.status_code = 400
        self.message = "litellm.ContentPolicyViolationError: {}".format(message)
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        self.response = httpx.Response(status_code=400, request=request)
        super().__init__(
            message=self.message,
            model=self.model,  # type: ignore
            llm_provider=self.llm_provider,  # type: ignore
            response=self.response,
            litellm_debug_info=self.litellm_debug_info,
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class ServiceUnavailableError(openai.APIStatusError):  # type: ignore
    def __init__(
        self,
        message,
        llm_provider,
        model,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 503
        self.message = "litellm.ServiceUnavailableError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        self.response = httpx.Response(
            status_code=self.status_code,
            request=httpx.Request(
                method="POST",
                url=" https://cloud.google.com/vertex-ai/",
            ),
        )
        super().__init__(
            self.message, response=self.response, body=None
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class InternalServerError(openai.InternalServerError):  # type: ignore
    def __init__(
        self,
        message,
        llm_provider,
        model,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 500
        self.message = "litellm.InternalServerError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        self.response = httpx.Response(
            status_code=self.status_code,
            request=httpx.Request(
                method="POST",
                url=" https://cloud.google.com/vertex-ai/",
            ),
        )
        super().__init__(
            self.message, response=self.response, body=None
        )  # Call the base class constructor with the parameters it needs

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


# raise this when the API returns an invalid response object - https://github.com/openai/openai-python/blob/1be14ee34a0f8e42d3f9aa5451aa4cb161f1781f/openai/api_requestor.py#L401
class APIError(openai.APIError):  # type: ignore
    def __init__(
        self,
        status_code: int,
        message,
        llm_provider,
        model,
        request: Optional[httpx.Request] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = status_code
        self.message = "litellm.APIError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        if request is None:
            request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        super().__init__(self.message, request=request, body=None)  # type: ignore

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


# raised if an invalid request (not get, delete, put, post) is made
class APIConnectionError(openai.APIConnectionError):  # type: ignore
    def __init__(
        self,
        message,
        llm_provider,
        model,
        request: Optional[httpx.Request] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.message = "litellm.APIConnectionError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.status_code = 500
        self.litellm_debug_info = litellm_debug_info
        self.request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        self.max_retries = max_retries
        self.num_retries = num_retries
        super().__init__(message=self.message, request=self.request)

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


# raised if an invalid request (not get, delete, put, post) is made
class APIResponseValidationError(openai.APIResponseValidationError):  # type: ignore
    def __init__(
        self,
        message,
        llm_provider,
        model,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.message = "litellm.APIResponseValidationError: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        response = httpx.Response(status_code=500, request=request)
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        super().__init__(response=response, body=None, message=message)

    def __str__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message

    def __repr__(self):
        _message = self.message
        if self.num_retries:
            _message += f" LiteLLM Retried: {self.num_retries} times"
        if self.max_retries:
            _message += f", LiteLLM Max Retries: {self.max_retries}"
        return _message


class JSONSchemaValidationError(APIResponseValidationError):
    def __init__(
        self, model: str, llm_provider: str, raw_response: str, schema: str
    ) -> None:
        self.raw_response = raw_response
        self.schema = schema
        self.model = model
        message = "litellm.JSONSchemaValidationError: model={}, returned an invalid response={}, for schema={}.\nAccess raw response with `e.raw_response`".format(
            model, raw_response, schema
        )
        self.message = message
        super().__init__(model=model, message=message, llm_provider=llm_provider)


class OpenAIError(openai.OpenAIError):  # type: ignore
    def __init__(self, original_exception=None):
        super().__init__()
        self.llm_provider = "openai"


class UnsupportedParamsError(BadRequestError):
    def __init__(
        self,
        message,
        llm_provider: Optional[str] = None,
        model: Optional[str] = None,
        status_code: int = 400,
        response: Optional[httpx.Response] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = 400
        self.message = "litellm.UnsupportedParamsError: {}".format(message)
        self.model = model
        self.llm_provider = llm_provider
        self.litellm_debug_info = litellm_debug_info
        response = response or httpx.Response(
            status_code=self.status_code,
            request=httpx.Request(
                method="GET", url="https://litellm.ai"
            ),  # mock request object
        )
        self.max_retries = max_retries
        self.num_retries = num_retries


LITELLM_EXCEPTION_TYPES = [
    AuthenticationError,
    NotFoundError,
    BadRequestError,
    UnprocessableEntityError,
    UnsupportedParamsError,
    Timeout,
    PermissionDeniedError,
    RateLimitError,
    ContextWindowExceededError,
    RejectedRequestError,
    ContentPolicyViolationError,
    InternalServerError,
    ServiceUnavailableError,
    APIError,
    APIConnectionError,
    APIResponseValidationError,
    OpenAIError,
    InternalServerError,
    JSONSchemaValidationError,
]


class BudgetExceededError(Exception):
    def __init__(
        self, current_cost: float, max_budget: float, message: Optional[str] = None
    ):
        self.current_cost = current_cost
        self.max_budget = max_budget
        message = (
            message
            or f"Budget has been exceeded! Current cost: {current_cost}, Max budget: {max_budget}"
        )
        self.message = message
        super().__init__(message)


## DEPRECATED ##
class InvalidRequestError(openai.BadRequestError):  # type: ignore
    def __init__(self, message, model, llm_provider):
        self.status_code = 400
        self.message = message
        self.model = model
        self.llm_provider = llm_provider
        self.response = httpx.Response(
            status_code=400,
            request=httpx.Request(
                method="GET", url="https://litellm.ai"
            ),  # mock request object
        )
        super().__init__(
            message=self.message, response=self.response, body=None
        )  # Call the base class constructor with the parameters it needs


class MockException(openai.APIError):
    # used for testing
    def __init__(
        self,
        status_code: int,
        message,
        llm_provider,
        model,
        request: Optional[httpx.Request] = None,
        litellm_debug_info: Optional[str] = None,
        max_retries: Optional[int] = None,
        num_retries: Optional[int] = None,
    ):
        self.status_code = status_code
        self.message = "litellm.MockException: {}".format(message)
        self.llm_provider = llm_provider
        self.model = model
        self.litellm_debug_info = litellm_debug_info
        self.max_retries = max_retries
        self.num_retries = num_retries
        if request is None:
            request = httpx.Request(method="POST", url="https://api.openai.com/v1")
        super().__init__(self.message, request=request, body=None)  # type: ignore


class LiteLLMUnknownProvider(BadRequestError):
    def __init__(self, model: str, custom_llm_provider: Optional[str] = None):
        self.message = LiteLLMCommonStrings.llm_provider_not_provided.value.format(
            model=model, custom_llm_provider=custom_llm_provider
        )
        super().__init__(
            self.message, model=model, llm_provider=custom_llm_provider, response=None
        )

    def __str__(self):
        return self.message


class GuardrailRaisedException(Exception):
    def __init__(self, guardrail_name: Optional[str] = None, message: str = ""):
        self.guardrail_name = guardrail_name
        self.message = f"Guardrail raised an exception, Guardrail: {guardrail_name}, Message: {message}"
        super().__init__(self.message)


class BlockedPiiEntityError(Exception):
    def __init__(
        self,
        entity_type: str,
        guardrail_name: Optional[str] = None,
    ):
        """
        Raised when a blocked entity is detected by a guardrail.
        """
        self.entity_type = entity_type
        self.guardrail_name = guardrail_name
        self.message = f"Blocked entity detected: {entity_type} by Guardrail: {guardrail_name}. This entity is not allowed to be used in this request."
        super().__init__(self.message)