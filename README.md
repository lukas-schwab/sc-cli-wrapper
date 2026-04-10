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
    - You MUST set the `SC_API_KEY` environment variable in `docker-compose.yml`.
    - Without this key, the application will refuse to start.
    - **Note on Layered Security**: Access to your account relies on two distinct auth layers. The **API Key** (Layer 1) protects the wrapper (preventing strangers from calling the API), while the **CLI Login** (Layer 2) handles the actual encrypted session with Scalable Capital. The latter is handled by the official [Scalable CLI](https://github.com/ScalableCapital/scalable-cli) and remains untouched by this project. Ideally, you may also ensure that the API is never exposed to the public internet (Layer 3).
- **Session Data**: Your session tokens are stored in the `scalable_config` Docker volume.
- **Sources**: Binarys are downloaded from the official [Scalable CLI](https://github.com/ScalableCapital/scalable-cli).

## Features

- **Dynamic Commands**: Call ANY `sc` command via URL path mapping and flag conversion.
- **Validated Trading**: Specialized, safe buy/sell flows with confirmation IDs and pre-flight checks.
- **Search & Identity**: Convenient endpoints for instrument search and session verification.
- **Docker Ready**: Automatic architecture detection (only tested on x86_64 WSL) and persistent sessions.

## Quick Start (Docker)

The easiest way to run the API is via Docker Compose.

1.  **Configure API Key**:
    Edit `docker-compose.yml` and set a secure value for `SC_API_KEY`.
    ```yaml
    environment:
      - SC_API_KEY=your-secret-key
    ```

2.  **Build and Start**:
    ```bash
    docker-compose up -d --build
    ```

3.  **Authenticate with Scalable**:
    The CLI inside the container needs a one-time login. You can execute the login command inside the running container:
    ```bash
    docker-compose exec scalable-api sc login
    ```
    Follow the device-code instructions in your browser.
    
    > [!TIP]
    > Authentication will only work if your scalable account is approved for CLI use. Read the official [Scalable CLI](https://github.com/ScalableCapital/scalable-cli) docs to learn more.

4.  **Access the API**:
    Open [http://localhost:8000/docs](http://localhost:8000/docs) in your browser to view the interactive Swagger documentation.

## Usage

### Dynamic Commands (Universal Access)

The API dynamically maps URL paths to `sc` subcommands. Query parameters or POST JSON bodies are converted to CLI flags.

- **Pattern**: `GET /<cmd>/<subcmd>?flag=value`
- **Security News**: `curl "http://localhost:8000/broker/security-news?isin=IE00B4L5Y983"`
- **Portfolio Analytics**: `curl http://localhost:8000/broker/analytics`
- **Boolean Flags**: `?dry-run=true` becomes `--dry-run`.

### Authentication
All requests must include the `X-API-Key` header with the value you configured in your `docker-compose.yml`:
```bash
curl -H "X-API-Key: your-secret-key" "http://localhost:8000/broker/analytics"
```

### Specialized Examples

**Get Portfolio Overview:**
```bash
curl -H "X-API-Key: your-secret-key" http://localhost:8000/broker/overview
```

**Search for Apple:**
```bash
curl -H "X-API-Key: your-secret-key" "http://localhost:8000/broker/search?query=apple"
```

**Execute a Trade (Step 1: Preview):**
```bash
curl -H "X-API-Key: your-secret-key" -X POST "http://localhost:8000/broker/trade/buy?isin=US0378331005&amount=100"
```
*Returns a `confirmation_id`.*

> [!CAUTION]
> It is highly advised that you treat this confirmation workflow as an actual human-in-the-loop approach. Spreads, fees, and other costs do apply and may add unexpectedly to the final cost of the trade. Ensure that all of information is clearly displayed to the end user before confirmation is given.

**Execute a Trade (Step 2: Confirm):**
```bash
curl -H "X-API-Key: your-secret-key" -X POST "http://localhost:8000/broker/trade/buy?isin=US0378331005&amount=100&confirm=XYZ-123"
```

## Configuration

You can customize the CLI version by changing the `SC_VERSION` build argument in `docker-compose.yml`.

```yaml
args:
  - SC_VERSION=latest  # or specify a version like v0.1.0
```