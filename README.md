# Whatsapp-PA

A Dockerized Python service that receives WA-AKG webhooks, generates a reply
with an OpenAI-compatible LLM, and sends that reply through WA-AKG.

## Start the bot

1. Copy `.env.example` to `.env` and replace the WA-AKG and LLM values with
   your real credentials.
2. Edit `data/context.md` and, optionally, `data/contacts.json`.
3. Set `WA_BASE_URL` to an address the **bot container** can reach:

   * If WA-AKG is running on the same Docker host on port 3000, use
     `WA_BASE_URL=http://host.docker.internal:3000`. The included Compose file
     maps this hostname to the Docker host on Linux.
   * If WA-AKG is on another server, use its LAN/public address, for example
     `WA_BASE_URL=http://144.24.138.161:3000`.
   * Do **not** use `http://localhost:3000` or `http://127.0.0.1:3000`: inside
     the bot container those addresses refer to the bot container itself, not
     WA-AKG.

4. Start the services from this repository root:

   ```bash
   docker compose up -d --build
   docker compose logs -f bot
   ```

5. Configure WA-AKG to deliver the `message.received` event to an address it
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
* `Connection refused` after `Requesting LLM reply` means the LLM worked and
  the bot reached the send step, but `WA_BASE_URL` is not reachable **from the
  bot container**. Set it using step 3, rebuild the bot, then verify it from
  inside the container:

  ```bash
  docker compose up -d --build bot
  docker compose exec bot python -c "import httpx; print(httpx.get('http://host.docker.internal:3000/docs', timeout=5).status_code)"
  ```

  Replace the URL in that command with your configured `WA_BASE_URL`. A `200`
  confirms networking; a `401` still confirms the gateway is reachable.
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
