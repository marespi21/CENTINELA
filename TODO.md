# Key Vault Migration — Implementation Plan ✅

## Status: COMPLETE

### Step 1 ✅: Add `get_secret_provider()` factory in `dependencies/__init__.py`
- Created `app/presentation/api/dependencies/__init__.py` with `get_secret_provider()` that returns:
  - `AzureKeyVaultSecretProvider` if `KEY_VAULT_URL` is set
  - `InMemorySecretProvider` otherwise (dev/test fallback)

### Step 2 ✅: Update `dependencies/documents.py` — fetch storage conn string from Key Vault
- Added `_resolve_storage_connection_string()` helper with priority:
  1. Key Vault secret `storage-connection-string`
  2. Env var `STORAGE_CONNECTION_STRING`
- Used in both `get_blob_storage()` and `get_document_queue()`

### Step 3 ✅: Update `dependencies/security.py` — fetch API keys from Key Vault
- `AuthPolicy.from_settings()` now accepts optional `SecretProvider` parameter
- If provider has `api-keys` secret, it takes priority over env var `API_KEYS`
- `get_auth_policy()` injects the secret provider from the composition root

### Step 4 ✅: Update `tests/unit/test_security.py`
- Added 4 new tests covering:
  - `from_settings()` without SecretProvider
  - Fallback to env when vault has no `api-keys`
  - Vault keys override env vars
  - `auth_enabled` flag still from settings, not vault

### Step 5 ✅: All 45 tests pass
- `python -m pytest backend/tests/ -v --tb=short` → **45 passed**


