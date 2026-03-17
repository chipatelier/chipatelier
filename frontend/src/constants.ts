/** Job status polling interval in milliseconds. */
export const POLL_INTERVAL_MS = 3000;

/** xterm.js scrollback buffer size. */
export const LOG_SCROLLBACK = 50_000;

/** Initial WebSocket reconnect delay in milliseconds. */
export const WS_RECONNECT_BASE_MS = 1000;

/** Maximum WebSocket reconnect delay in milliseconds. */
export const WS_RECONNECT_MAX_MS = 30_000;

/** Maximum number of WebSocket reconnect attempts before giving up. */
export const WS_MAX_RECONNECT_ATTEMPTS = 10;

/** JWT expiry buffer in seconds — refresh proactively before expiry. */
export const TOKEN_EXPIRY_BUFFER_SECS = 60;

/** Default storage quota in GB (fallback when institution quota is missing). */
export const DEFAULT_QUOTA_GB = 5;

/** Copy-to-clipboard confirmation duration in milliseconds. */
export const COPY_FEEDBACK_MS = 2000;
