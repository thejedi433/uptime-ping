# uptime-ping

Scheduled uptime monitor that pings URLs and sends Telegram alerts on failure.

Complements `pulse` (on-demand HTTP checks) with continuous background monitoring and notifications.

## Features

- Monitor multiple URLs with configurable intervals
- Telegram alerts on failure and recovery
- CLI for adding/removing/listing endpoints
- SQLite state persistence
- Lightweight daemon mode

## Installation

```bash
pip install -e .
```

## Usage

```bash
# Add endpoints
uptime-ping add https://example.com
uptime-ping add https://api.example.com/health --interval 60

# List monitored URLs
uptime-ping list

# Check all now
uptime-ping check

# Run daemon (checks every interval)
uptime-ping daemon

# Remove an endpoint
uptime-ping remove https://example.com
```

## Configuration

Set Telegram credentials via environment variables:

```bash
export UPTIME_PING_TELEGRAM_TOKEN="your-bot-token"
export UPTIME_PING_TELEGRAM_CHAT_ID="your-chat-id"
```

## Testing

```bash
pip install -e ".[dev]"
pytest
```

## License

MIT
