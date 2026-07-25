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

## Migración de secretos a Key Vault (estrategia)

Objetivo: **ninguna** credencial en código, repositorio ni app settings en claro.

- Secretos centralizados en Key Vault: `api-keys` (mapa clave→rol) y
  `storage-connection-string` (solo si se usa; en prod el Storage va por Managed
  Identity, sin connection string).
- Composition root
  [`get_secret_provider()`](../backend/app/presentation/api/dependencies/__init__.py):
  `AzureKeyVaultSecretProvider` (Managed Identity) cuando `KEY_VAULT_URL` está
  configurado; `InMemorySecretProvider` (entorno) en dev/test.
- La autorización lee las API keys **de Key Vault con prioridad** y cae a la
  variable de entorno solo como fallback
  ([`security.py`](../backend/app/presentation/api/dependencies/security.py)).
- Sin credencial para obtener credenciales: la identidad de la Web App tiene
  `Key Vault Secrets User` por RBAC (ver [`infra/security.sh`](../infra/security.sh)).

Ver decisión completa en [`decisions.md`](./decisions.md) (ADR-012).

## Verificación del historial de git

- `.env` está en `.gitignore` y **nunca** se versionó; solo se versiona
  `.env.example` con placeholders.
- Se auditó el historial completo (`git log --all -p`) buscando patrones de
  secretos (`AccountKey=`, `password=`, claves privadas, tokens).
- **Resultado:** sin secretos reales. El único hallazgo es la clave por defecto
  del emulador **Azurite** (`AccountName=devstoreaccount1`) en un `.env.example`
  antiguo — clave pública y universal del emulador local, no un secreto real, y
  ya fuera de `HEAD`.
- Procedimiento ante un secreto real: rotarlo de inmediato y reescribir el
  historial (git filter-repo / BFG).

## Rate limiting (protección ante saturación)

- Middleware por **IP de origen** con **ventana deslizante en memoria**
  ([`rate_limit.py`](../backend/app/presentation/api/middlewares/rate_limit.py)).
- Al exceder el límite responde **HTTP 429** con
  `{"code": "RATE_LIMIT_EXCEEDED"}`.

| Variable | Default | Uso |
|----------|---------|-----|
| `RATE_LIMIT_ENABLED` | `true` | Activa/desactiva el limitador |
| `RATE_LIMIT_MAX_REQUESTS` | `10` | Máx. peticiones por IP en la ventana |
| `RATE_LIMIT_WINDOW_SECONDS` | `60` | Tamaño de la ventana en segundos |

**Justificación:** 10 req/60 s por IP es un umbral conservador que protege la
disponibilidad del servicio de crédito ante saturación —permite el uso normal de
un cliente y corta ráfagas anómalas—, ajustable por app setting sin redeploy.

**Limitaciones conocidas:** estado en memoria por instancia/worker (el límite se
multiplica con scale-out; un límite global requeriría Redis); detrás de un
proxy/Front Door conviene usar `X-Forwarded-For` como origen. Ver
[`decisions.md`](./decisions.md) (ADR-013).

## Pruebas

[`tests/integration/test_authorization.py`](../backend/tests/integration/test_authorization.py):
401 sin clave, 403 rol incorrecto, 202 rol válido, y bypass con auth
deshabilitada.
[`tests/unit/test_rate_limit.py`](../backend/tests/unit/test_rate_limit.py):
excede→429, reinicio tras la ventana, y deshabilitado.
