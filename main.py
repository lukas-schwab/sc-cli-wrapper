import subprocess
import json
import os
import logging
from typing import Optional, List
from fastapi import FastAPI, HTTPException, Query, Request, Security, Depends
from fastapi.security.api_key import APIKeyHeader
from fastapi.responses import JSONResponse

SC_PATH = os.getenv("SC_PATH", "sc")
import secrets
from pathlib import Path
from dotenv import load_dotenv

# Load .env file if it exists
load_dotenv()

SC_PATH = os.getenv("SC_PATH", "sc")
CONFIG_DIR = os.getenv("SC_CONFIG_DIR", "/root/.config/scalable-cli")
API_KEY_FILE = Path(CONFIG_DIR) / "api_key"

FORBIDDEN_KEYS = ["your-secret-key", ""]

# Setup logging
logging.basicConfig(
    level=logging.INFO,
    format="%(levelname)s:     %(message)s"
)
logger = logging.getLogger("scalable-api")

def get_or_create_api_key():
    """
    Retrieves the API key from:
    1. Environment variable (SC_API_KEY)
    2. Persistent file (api_key)
    3. Auto-generation (stored in persistent file)
    """
    # 1. Check environment
    env_key = os.getenv("SC_API_KEY")
    if env_key and env_key.lower() not in FORBIDDEN_KEYS:
        return env_key, "env"

    # 2. Check persistent file
    if API_KEY_FILE.exists():
        file_key = API_KEY_FILE.read_text().strip()
        if file_key and file_key.lower() not in FORBIDDEN_KEYS:
            return file_key, "file"

    # 3. Generate new key
    new_key = secrets.token_hex(16)
    try:
        os.makedirs(CONFIG_DIR, exist_ok=True)
        API_KEY_FILE.write_text(new_key)
        return new_key, "generated"
    except Exception as e:
        logger.error(f"Failed to save generated API key to {API_KEY_FILE}: {e}")
        # Return the key anyway so the app can start, but it won't persist
        return new_key, "ephemeral"

SC_API_KEY, key_source = get_or_create_api_key()

if key_source == "generated":
    logger.warning("!------------------------------------------------------------!")
    logger.warning("! NO API KEY FOUND. A NEW ONE HAS BEEN AUTOMATICALLY GENERATED !")
    logger.warning(f"! YOUR API KEY IS: {SC_API_KEY} ")
    logger.warning("! PLEASE SAVE THIS KEY. YOU WILL NEED IT FOR ALL API REQUESTS. !")
    logger.warning("!------------------------------------------------------------!")
elif key_source == "ephemeral":
    logger.error("!------------------------------------------------------------!")
    logger.error("! COULD NOT SAVE KEY TO DISK. USING EPHEMERAL KEY FOR THIS RUN !")
    logger.error(f"! YOUR API KEY IS: {SC_API_KEY} ")
    logger.error("!------------------------------------------------------------!")
elif key_source == "file":
    logger.info(f"Using API key from persistent storage: {API_KEY_FILE}")
else:
    logger.info("Using API key from environment (SC_API_KEY).")

api_key_header = APIKeyHeader(name="X-API-Key", auto_error=False)

async def verify_api_key(api_key: str = Depends(api_key_header)):
    """Verifies the mandatory API key."""
    if not api_key or api_key != SC_API_KEY:
        raise HTTPException(
            status_code=403,
            detail="Could not validate credentials. Please provide a valid X-API-Key header."
        )
    return api_key

app = FastAPI(
    title="Scalable Capital API Wrapper",
    description="A portable REST API wrapper around the Scalable CLI (sc). Supports all sc commands dynamically via path and query parameters.",
    version="0.3.0",
    dependencies=[Depends(verify_api_key)]
)

def run_sc_command(args: List[str]):
    """Helper to execute sc commands and return JSON output."""
    try:
        # Always append --json for machine-readable output
        # Filter out '--json' if already present to avoid duplicates
        cmd_args = [arg for arg in args if arg != "--json"]
        
        # If --confirm is present, insert --json BEFORE it to match the phase 1 snapshot.
        # Otherwise, the CLI complains that the fresh pre-trade values differ from the snapshot.
        if "--confirm" in cmd_args:
            idx = cmd_args.index("--confirm")
            full_args = [SC_PATH] + cmd_args[:idx] + ["--json"] + cmd_args[idx:]
        else:
            full_args = [SC_PATH] + cmd_args + ["--json"]

        logger.info(f"Executing: {' '.join(full_args)}")
        
        result = subprocess.run(full_args, capture_output=True, text=True, check=True)
        if result.stdout.strip():
            logger.debug(f"CLI Output: {result.stdout.strip()}")

        if not result.stdout.strip():
            return {"status": "success", "message": "Command executed successfully (no output)"}

        return json.loads(result.stdout)
    except subprocess.CalledProcessError as e:
        # Standard error usually contains the helpful message
        error_msg = e.stderr.strip() or e.stdout.strip() or "CLI execution failed"
        raise HTTPException(status_code=500, detail=error_msg)
    except json.JSONDecodeError:
        raise HTTPException(status_code=500, detail="Invalid JSON output from CLI")

@app.get("/")
async def root():
    return {
        "name": "Scalable Capital API Wrapper",
        "status": "running",
        "docs": "/docs"
    }

@app.get("/whoami")
async def whoami():
    """Returns the current authenticated user session info."""
    return run_sc_command(["whoami"])

@app.get("/capabilities")
async def capabilities():
    """Lists all machine-readable capabilities of the CLI."""
    return run_sc_command(["capabilities"])

@app.get("/broker/search")
async def search(query: str = Query(..., description="The search term (e.g. 'apple' or ISIN)")):
    """
    Searches for instruments. 
    Mapped to: sc broker search <query>
    """
    return run_sc_command(["broker", "search", query])


@app.get("/broker/context")
async def get_context():
    """Returns the currently active broker context (alias for broker/context/show)."""
    return run_sc_command(["broker", "context", "show"])


@app.post("/broker/trade/buy")
async def trade_buy(
    isin: str, 
    amount: Optional[str] = None, 
    order_type: str = "market", 
    limit: Optional[str] = None,
    stop: Optional[str] = None,
    confirm: Optional[str] = None
):
    """
    Buy an instrument. 
    First call without 'confirm' returns a preview and confirmation ID.
    Second call with '--confirm <ID>' executes the trade.
    """
    args = ["broker", "trade", "buy", "--isin", isin, "--order-type", order_type]
    
    if amount:
        args.extend(["--amount", amount])
    else:
        raise HTTPException(status_code=400, detail="'amount' must be provided.")
        
    if limit: args.extend(["--limit", limit])
    if stop: args.extend(["--stop", stop])
    if confirm: args.extend(["--confirm", confirm])

    return run_sc_command(args)

@app.post("/broker/trade/sell")
async def trade_sell(
    isin: str, 
    amount: Optional[str] = None, 
    order_type: str = "market", 
    limit: Optional[str] = None,
    stop: Optional[str] = None,
    confirm: Optional[str] = None
):
    """
    Sell an instrument.
    First call without 'confirm' returns a preview and confirmation ID.
    Second call with '--confirm <ID>' executes the trade.
    """
    args = ["broker", "trade", "sell", "--isin", isin, "--order-type", order_type]
    
    if amount:
        args.extend(["--amount", amount])
    else:
        raise HTTPException(status_code=400, detail="'amount' must be provided.")
        
    if limit: args.extend(["--limit", limit])
    if stop: args.extend(["--stop", stop])
    if confirm: args.extend(["--confirm", confirm])
    
    return run_sc_command(args)

@app.api_route("/{path:path}", methods=["GET", "POST"])
async def dynamic_proxy(path: str, request: Request):
    """
    Catch-all endpoint that dynamically maps URL paths and parameters to sc commands.
    
    Examples:
    - GET /broker/security-news?isin=IE00B4L5Y983 -> sc broker security-news --isin IE00B4L5Y983 --json
    - GET /broker/analytics -> sc broker analytics --json
    - POST /broker/context/select?portfolio-id=XYZ -> sc broker context select --portfolio-id XYZ --json
    """
    # 0. Ignore common noisy browser requests
    if path in ["favicon.ico", "robots.txt", "apple-touch-icon.png"]:
        raise HTTPException(status_code=404)

    # Split path to get subcommands (e.g., "broker/holdings" -> ["broker", "holdings"])
    args = [p for p in path.split("/") if p]
    
    if not args:
        return await root()

    # 1. Add query parameters as flags
    for key, value in request.query_params.items():
        flag = f"--{key.replace('_', '-')}"
        # Handle boolean flags represented as "true" (no value needed)
        if value.lower() == "true":
            args.append(flag)
        elif value.lower() == "false":
            continue
        else:
            args.extend([flag, str(value)])

    # 2. Add JSON body parameters as flags (for POST)
    if request.method == "POST":
        try:
            body = await request.json()
            if isinstance(body, dict):
                for key, value in body.items():
                    flag = f"--{key.replace('_', '-')}"
                    if value is True:
                        args.append(flag)
                    elif value is False:
                        continue
                    elif value is not None:
                        args.extend([flag, str(value)])
        except:
            # Not a JSON body or empty, ignore
            pass

    return run_sc_command(args)

if __name__ == "__main__":
    import sys
    import uvicorn
    
    # Simple CLI for managing the API key
    if len(sys.argv) > 1 and sys.argv[1] == "set-key":
        if len(sys.argv) < 3:
            print("Usage: python main.py set-key <new-key>")
            sys.exit(1)
        
        new_key = sys.argv[2]
        try:
            os.makedirs(CONFIG_DIR, exist_ok=True)
            API_KEY_FILE.write_text(new_key)
            print(f"✅ API key updated successfully in {API_KEY_FILE}")
            sys.exit(0)
        except Exception as e:
            print(f"❌ Failed to update API key: {e}")
            sys.exit(1)

    uvicorn.run(app, host="0.0.0.0", port=8000)
