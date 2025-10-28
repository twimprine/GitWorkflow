# Contracts sample

This folder contains small, deterministic sample contracts for testing batch prompt caching and group selection.

Included:
- OpenAPI (ping endpoint)
- JSON Schema (OrderCreated event)
- gRPC proto (health check)
- GraphQL schema (ping)

Use with:

```bash
python scripts/collect-prp-context.py --groups contracts --dupe
```
