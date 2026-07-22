# Seguridad — CENTINELA (módulo Lukas)

## Objetivo

Autorización por roles en la API, identidad sin credenciales en código
(Managed Identity) y secretos en Key Vault.

## Roles

`administrador` · `analista` · `auditor` · `servicio`
(ver [`role.py`](../backend/app/domain/value_objects/role.py)).

## Autorización en la API

- Dependency [`require_roles(...)`](../backend/app/presentation/api/dependencies/security.py).
- Se envía la clave en el header **`X-API-Key`**.
- Los endpoints de escritura (`POST /transactions`, `POST /documents`) exigen
  rol `servicio` o `administrador`.
- Respuestas: **401** (`UNAUTHORIZED`) si falta/invalida la clave; **403**
  (`FORBIDDEN`) si el rol no aplica.

### Configuración

| Variable | Uso |
|----------|-----|
| `AUTH_ENABLED` | `false` en local (no exige clave), `true` en Azure |
| `API_KEYS` | mapa `clave:rol` separado por comas; en Azure viene de Key Vault |
| `KEY_VAULT_URL` | URL del Key Vault |

Con `AUTH_ENABLED=false` la API no bloquea (rol `servicio` por defecto), para
no frenar el desarrollo local.

## Key Vault + RBAC

[`infra/security.sh`](../infra/security.sh):

- Crea el Key Vault (RBAC authorization).
- Asigna a la Managed Identity de la Web App, con **menor privilegio**:
  `Storage Blob Data Contributor`, `Storage Queue Data Contributor`,
  `Key Vault Secrets User`.
- Guarda las API keys de la app como secreto (`api-keys`).

Adaptadores de secretos: puerto
[`SecretProvider`](../backend/app/domain/repositories/secret_provider.py),
con `InMemorySecretProvider` (dev) y
[`AzureKeyVaultSecretProvider`](../backend/app/infrastructure/azure/key_vault.py).

## Pruebas

[`tests/integration/test_authorization.py`](../backend/tests/integration/test_authorization.py):
401 sin clave, 403 rol incorrecto, 202 rol válido, y bypass con auth
deshabilitada.
