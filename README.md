<h1 align="center">(Unofficial) Scalable CLI Wrapper</h1>

<p align="center"><strong>A portable, Dockerized REST API for the Scalable CLI.</strong></p>

<p align="center">This unofficial project wraps the official Scalable CLI (`sc`) into a FastAPI web service, seeking to extend upon the spirit of automation that Scalable kindly chose to provide with their CLI.</p>

<br />

## Affiliation

This project is **not** affiliated with Scalable Capital. It is a personal project. **If you are Scalable Capital and want me to take this project down, please open an Issue and I will comply immediately.** That said, I'd appreciate it if the community is allowed to build upon the CLI as it is common practice in the tech world.

The wrapper just uses the official [Scalable CLI](https://github.com/ScalableCapital/scalable-cli). For more information on the underlying capabilities, refer to the original documentation or the `capabilities` command.

## Security

> [!CAUTION]
> This API has full power over your Scalable Capital account.
>   - Do **NOT** rely on this code for anything but your personal projects.
>   - Do **NOT** use this code unless you understand every line yourself.
>   - **YOU** are responsible for all of your actions. (Algorithmic) Trading is risky and I discourage everyone to use this API for anything beyond a hobby automation project.

- **Security Layer**: This API **requires** an `X-API-Key` header for all requests.
    - **Automatic Generation**: On the first start, a secure random API key is generated and saved to your persistent volume. 
    - **Persistence**: The key is stored in the `config` volume. You can also manually set it using a CLI command inside the container.
    - **Manual Override**: You can still provide an `SC_API_KEY` via environment variables or a `.env` file for explicit control.
    - **Note on Layered Security**: Access to your account relies on two distinct auth layers. The **API Key** (Layer 1) protects the wrapper (preventing strangers from calling the API), while the **CLI Login** (Layer 2) handles the actual encrypted session with Scalable Capital. The latter is handled by the official [Scalable CLI](https://github.com/ScalableCapital/scalable-cli) and remains untouched by this project. Ideally, you may also ensure that the API is never exposed to the public internet (Layer 3).
- **Session & Key Data**: Both your session tokens and your API key are stored in the `config` Docker volume.
- **Sources**: Binarys are downloaded from the official [Scalable CLI](https://github.com/ScalableCapital/scalable-cli).

## Features

- **Zero-Config Start**: Automatically generates a secure API key if none is provided.
- **Dynamic Commands**: Call ANY `sc` command via URL path mapping and flag conversion.
- **Validated Trading**: Specialized, safe buy/sell flows with confirmation IDs and pre-flight checks.
- **Search & Identity**: Convenient endpoints for instrument search and session verification.
- **Docker Ready**: Automatic architecture detection and persistent sessions/keys.

## Quick Start (Docker)

The easiest way to run the API is via Docker.

1.  **Build and Start**:
    ```bash
    docker compose up -d --build
    ```

2.  **Get your API Key**:
    Check the container logs to find your automatically generated API key:
    ```bash
    docker compose logs | grep "YOUR API KEY IS"
    ```
    *Alternatively, you can set your own key (see below).*

3.  **Authenticate with Scalable**:
    The CLI inside the container needs a one-time login:
    ```bash
    docker compose exec api sc login
    ```
    Follow the device-code instructions in your browser.

4.  **Access the API**:
    Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the interactive Swagger documentation.

> [!TIP]
> Authentication will only work if your Scalable account is approved for CLI use. Read the official [Scalable CLI](https://github.com/ScalableCapital/scalable-cli) docs to learn more.

## Manual Key Configuration

If you want to set a specific API key without using environment variables:
```bash
docker compose exec api python main.py set-key YOUR_CUSTOM_KEY
```

## Usage

### Dynamic Commands (Universal Access)

The API dynamically maps URL paths to `sc` subcommands. Query parameters or POST JSON bodies are converted to CLI flags.

- **Pattern**: `GET /<cmd>/<subcmd>?flag=value`
- **Security News**: `curl "http://localhost:8000/broker/security-news?isin=IE00B4L5Y983"`
- **Portfolio Analytics**: `curl http://localhost:8000/broker/analytics`
- **Boolean Flags**: `?dry-run=true` becomes `--dry-run`.

### Authentication
All requests must include the `X-API-Key` header:
```bash
curl -H "X-API-Key: your-generated-key" "http://localhost:8000/broker/analytics"
```

### Specialized Examples

**Get Portfolio Overview:**
```bash
curl -H "X-API-Key: your-generated-key" http://localhost:8000/broker/overview
```

**Search for Apple:**
```bash
curl -H "X-API-Key: your-generated-key" "http://localhost:8000/broker/search?query=apple"
```

**Execute a Trade (Step 1: Preview):**
```bash
curl -H "X-API-Key: your-generated-key" -X POST "http://localhost:8000/broker/trade/buy?isin=US0378331005&amount=100"
```
*Returns a `confirmation_id`.*

> [!CAUTION]
> It is highly advised that you treat this confirmation workflow as an actual human-in-the-loop approach. Spreads, fees, and other costs do apply and may add unexpectedly to the final cost of the trade. Ensure that all of information is clearly displayed to the end user before confirmation is given.

**Execute a Trade (Step 2: Confirm):**
```bash
curl -H "X-API-Key: your-generated-key" -X POST "http://localhost:8000/broker/trade/buy?isin=US0378331005&amount=100&confirm=XYZ-123"
```

## Configuration

You can customize the CLI version by changing the `SC_VERSION` build argument in `docker compose`.

```yaml
args:
  - SC_VERSION=latest  # or specify a version like v0.1.0
```
