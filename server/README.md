# LUMA Local Game Server

Java 21 + Spring Boot 3.x + Spring JDBC + PostgreSQL + Flyway.

See [local setup, schema, API, transactions and tests](../docs/game-backend-v01.md).
Use a dedicated LUMA database. Set LUMA_DB_PASSWORD locally; no password is shipped.

```sh
./gradlew bootRun
```

Run from this directory with Java 21 configured. PostgreSQL can run locally or via
`docker compose -f compose.yml up -d` after exporting LUMA_DB_PASSWORD.
Tests require a separate *_test database and LUMA_TEST_DB_* environment variables.
