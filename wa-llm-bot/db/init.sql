CREATE TABLE contacts (
  jid TEXT PRIMARY KEY,
  display_name TEXT,
  last_seen TIMESTAMPTZ DEFAULT NOW()
);

CREATE TABLE messages (
  id BIGSERIAL PRIMARY KEY,
  jid TEXT NOT NULL REFERENCES contacts(jid) ON DELETE CASCADE,
  role TEXT NOT NULL CHECK (role IN ('user', 'assistant')),
  content TEXT NOT NULL,
  wa_msg_id TEXT,
  created_at TIMESTAMPTZ NOT NULL DEFAULT NOW()
);

CREATE UNIQUE INDEX idx_messages_wa_id ON messages (wa_msg_id);
CREATE INDEX idx_messages_jid_created ON messages (jid, created_at DESC);
