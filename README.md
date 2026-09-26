# Whatsapp-PA

A Dockerized Python service that receives WA-AKG webhooks, generates a reply
with an OpenAI-compatible LLM, and sends that reply through WA-AKG.

## Start the bot

1. Copy `.env.example` to `.env` and replace the WA-AKG and LLM values with
   your real credentials.
2. Edit `data/context.md` and, optionally, `data/contacts.json`.
3. Start the services from this repository root:

   ```bash
   docker compose up -d --build
   docker compose logs -f bot
   ```

4. Configure WA-AKG to deliver the `message.received` event to an address it
   can reach, for example `http://YOUR_BOT_HOST_IP:3001/webhook`. Do **not**
   use `localhost` unless WA-AKG runs in the same network namespace as the
   bot. The WA-AKG dashboard can create this webhook, or use its API:

   ```bash
   curl -X POST "$WA_BASE_URL/api/webhooks/$WA_SESSION_ID" \
     -H "X-API-Key: $WA_API_KEY" \
     -H "Content-Type: application/json" \
     -d '{"name":"LLM bot","url":"http://YOUR_BOT_HOST_IP:3001/webhook","events":["message.received"]}'
   ```

   The bot does not use a webhook secret or `X-Webhook-Signature`.

## Verify and troubleshoot

* `curl http://YOUR_BOT_HOST_IP:3001/health` should return `{"ok":true,...}`.
* Use WA-AKG's webhook test action after creating the webhook. The bot log
  should first show `Received WA-AKG webhook`. A real text message then logs
  `Processing incoming`, `Requesting LLM reply`, and `Sent WA-AKG reply`.
* The Postgres message **"database directory appears to contain a database;
  Skipping initialization"** is normal for an existing `pgdata` volume.
  PostgreSQL runs `db/init.sql` only when the volume is created. For a fresh,
  disposable local installation, recreate it with
  `docker compose down -v && docker compose up -d --build`. This deletes all
  stored conversations. For an existing volume that is missing the tables,
  apply the schema without deleting data:

  ```bash
  docker compose exec -T postgres psql -U botuser -d botdb < db/init.sql
  ```
