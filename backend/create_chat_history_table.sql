-- Create chat_history table manually

CREATE TABLE IF NOT EXISTS chat_history (
    id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
    user_id UUID NOT NULL,
    role VARCHAR(50) NOT NULL,
    message_text TEXT NOT NULL,
    language VARCHAR(10),
    source_mode VARCHAR(50),
    created_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    updated_at TIMESTAMP WITHOUT TIME ZONE NOT NULL DEFAULT (NOW() AT TIME ZONE 'utc'),
    deleted_at TIMESTAMP WITHOUT TIME ZONE,
    
    CONSTRAINT fk_chat_history_user FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

-- Create index on user_id for efficient queries
CREATE INDEX IF NOT EXISTS ix_chat_history_user_id ON chat_history(user_id);

-- Create index on created_at for time-based queries
CREATE INDEX IF NOT EXISTS ix_chat_history_created_at ON chat_history(created_at DESC);

-- Display the table
\d chat_history;

-- Show all tables
\dt;
