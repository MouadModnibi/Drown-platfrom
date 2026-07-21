# drown-cli

**CLI tool for managing apps on Drown Platform** - a self-hosted PaaS (Platform as a Service).

Deploy and manage containerized applications with simple commands, similar to Heroku CLI but for your own infrastructure.

## Installation

```bash
pip install drown
```

## Quick Start

```bash
# Login to your Drown Platform instance
drown login

# List your apps
drown apps

# Create a new app
drown create my-app

# Scale your app
drown scale my-app 3

# View logs
drown logs my-app

# Check metrics
drown metrics my-app

# Logout
drown logout
```

## Commands

### `drown login`
Authenticate with your Drown Platform instance. You'll be prompted for your username and password.

```bash
drown login
```

Credentials are saved to `~/.drown/config.json` for subsequent commands.

### `drown logout`
Remove saved credentials.

```bash
drown logout
```

### `drown apps`
List all your deployed applications.

```bash
drown apps
```

Output:
```
NAME           DOMAIN                    STATUS    REPLICAS
my-app         my-app.dr0wn.duckdns.org  running   3
web-frontend   web.dr0wn.duckdns.org     running   1
```

### `drown create <app-name>`
Create a new application.

```bash
drown create my-new-app
```

If run from a git repository, automatically adds a `platform` git remote. Then deploy with:
```bash
git push platform main
```

### `drown scale <app-name> <count>`
Scale the number of replicas for an application.

```bash
drown scale my-app 5
```

### `drown logs <app-name>`
View application logs.

```bash
drown logs my-app
```

### `drown metrics <app-name>`
View resource usage metrics (CPU, memory) for all replicas.

```bash
drown metrics my-app
```

Output:
```
REPLICA    PORT    STATUS    CPU      MEMORY
0          8001    running   2.1%     64MiB
1          8002    running   1.8%     62MiB
2          8003    running   2.4%     65MiB
```

## Configuration

### API URL
By default, the CLI connects to `https://dashboard.dr0wn.duckdns.org`.

To use a custom instance, set the `DROWN_API_URL` environment variable:

```bash
export DROWN_API_URL=https://your-instance.com
drown login
```

### Config File
Authentication token is stored in `~/.drown/config.json`:

```json
{
  "token": "your-jwt-token",
  "username": "your-username",
  "api_base": "https://dashboard.dr0wn.duckdns.org"
}
```

## Requirements

- Python 3.7+
- Git (optional, for `drown create` auto-remote feature)

## Development

```bash
git clone https://github.com/drownplatform/drown-cli.git
cd drown-cli
pip install -e .
```

## License

MIT License - see [LICENSE](LICENSE) file for details.

## Links

- **Platform**: [dashboard.dr0wn.duckdns.org](https://dashboard.dr0wn.duckdns.org)
- **GitHub**: [github.com/drownplatform/drown-cli](https://github.com/drownplatform/drown-cli)
- **PyPI**: [pypi.org/project/drown-cli](https://pypi.org/project/drown-cli)

## Support

For issues or questions, please open an issue on [GitHub](https://github.com/drownplatform/drown-cli/issues).
