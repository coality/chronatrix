CREATE TABLE IF NOT EXISTS api_keys (
  id BIGINT AUTO_INCREMENT PRIMARY KEY,
  key_hash BINARY(32) NOT NULL UNIQUE,
  key_prefix VARCHAR(16) NOT NULL,
  label VARCHAR(64) NOT NULL,
  status ENUM('active', 'revoked') NOT NULL DEFAULT 'active',
  created_at DATETIME NOT NULL,
  revoked_at DATETIME NULL,
  last_used_at DATETIME NULL,
  rate_limit_rpm INT NULL,
  INDEX idx_api_keys_prefix (key_prefix)
);

CREATE TABLE IF NOT EXISTS api_cache (
  cache_key VARCHAR(255) PRIMARY KEY,
  payload_json LONGTEXT NOT NULL,
  expires_at DATETIME NOT NULL,
  created_at DATETIME NOT NULL,
  updated_at DATETIME NOT NULL,
  INDEX idx_api_cache_expires_at (expires_at)
);
