# CI/CD

**Sprint 6 · Fase 5 — CENTINELA**

---

## 1. El problema que se arrastraba

`deploy-network.yml` se autenticaba así:

```yaml
- uses: azure/login@v1
  with:
    creds: ${{ secrets.AZURE_CREDENTIALS }}
```

`AZURE_CREDENTIALS` es un **service principal con `clientSecret`** guardado en
GitHub. Contradice de frente la regla del sprint —cero credenciales en el
pipeline— y es exactamente el tipo de secreto que peor envejece:

- no caduca solo, así que sigue siendo válido hasta que alguien lo revoque;
- tiene permisos amplios sobre la suscripción;
- cualquiera con acceso de escritura al repositorio puede usarlo desde un
  workflow que él mismo añada.

Estaba ahí desde antes del Sprint 6. Esta fase lo sustituye.

## 2. OIDC federado: no hay nada que filtrar

GitHub emite un token de vida corta **por ejecución** y Entra ID lo canjea
comprobando de dónde viene.

| | `AZURE_CREDENTIALS` | OIDC federado |
|---|---|---|
| Secreto almacenado | Sí, permanente | **Ninguno** |
| Si se filtra | Válido hasta revocarlo | No hay qué filtrar |
| Vida del token | Indefinida | Minutos |
| Alcance | La suscripción | Solo el repo/rama/entorno declarado |

Lo que ata el token a un origen concreto es el `subject` de la credencial
federada; sin él, cualquier repositorio de GitHub podría pedir un token para
esta aplicación:

```
repo:marespi21/CENTINELA:environment:dev
repo:marespi21/CENTINELA:environment:prod
repo:marespi21/CENTINELA:ref:refs/heads/develop
repo:marespi21/CENTINELA:ref:refs/heads/main
```

**RBAC acotado al grupo de recursos**, no a la suscripción: el pipeline puede
desplegar Centinela y nada más. Sin `Owner` ni `User Access Administrator`, así
que tampoco puede repartirse permisos a sí mismo.

### Variables, no secrets

`AZURE_CLIENT_ID`, `AZURE_TENANT_ID`, `AZURE_SUBSCRIPTION_ID` y `AZURE_SUFFIX`
son **identificadores públicos**. Van en *Variables*, no en *Secrets*: sin la
federación configurada no sirven para autenticarse. Guardarlos como secrets
daría una falsa sensación de que ahí hay algo que proteger.

## 3. La cadena

```
push a develop
   └─ Contenedores: pruebas → build → auditoría de secretos → publica en GHCR
        └─ Desplegar (solo si lo anterior fue verde)
             ├─ login OIDC
             ├─ containerapps.sh con la etiqueta sha-xxxxxxx
             ├─ comprobación de salud
             └─ si la salud falla → rollback automático
```

Dos salvaguardas que conviene señalar:

- **No se despliega una imagen que no pasó las pruebas.** El evento
  `workflow_run` se dispara tanto si el pipeline pasó como si falló, así que hay
  una condición explícita sobre `conclusion == 'success'`. Sin ella se
  desplegaría precisamente la imagen rota.
- **Se despliega por SHA, nunca por `latest`.** Una etiqueta móvil puede cambiar
  bajo los pies de una revisión ya desplegada y vuelve irreproducible el
  rollback.

## 4. Gates de aprobación

Se apoyan en *GitHub Environments*: el workflow declara `environment: dev|prod`
y las reglas se configuran en `Settings → Environments`. Activando **Required
reviewers** en `prod`, el job queda en espera hasta que alguien apruebe.

El mismo nombre de entorno es el que aparece en el `subject` de la credencial
federada, así que la protección de GitHub y la de Entra ID hablan de lo mismo.

## 5. Rollback

### Por imagen, no repartiendo tráfico

Las apps están en modo de revisión **única** (el de por defecto): solo hay una
revisión activa a la vez, así que `ingress traffic set` no aplica. Volver atrás
es, literalmente, volver a desplegar la imagen anterior — que además funciona
igual para el worker, que no tiene ingress ni tráfico que repartir.

`infra/rollback.sh` lee el historial de revisiones de Container Apps, toma la
segunda más reciente y actualiza la imagen a la suya.

### Dos caminos

| Camino | Cuándo |
|---|---|
| **Automático**, dentro de `deploy.yml` | La comprobación de salud falla tras desplegar. Un despliegue que deja el servicio caído se deshace solo, sin esperar a que alguien se dé cuenta |
| **Manual**, `rollback.yml` | Una regresión funcional que una sonda HTTP no puede ver. Admite etiqueta explícita o «la anterior» |

El rollback **verifica la salud después de revertir**: un rollback que deja el
servicio caído no es un rollback.

## 6. Puesta en marcha

```bash
export SUFFIX=sp5x1
bash infra/github-oidc.sh
```

El script imprime las cuatro variables a configurar. Después:

1. `Settings → Secrets and variables → Actions → Variables`: añade las cuatro.
2. `Settings → Environments`: crea `dev` y `prod`; en `prod` activa
   **Required reviewers**.
3. `Settings → Secrets → Actions`: **borra `AZURE_CREDENTIALS`**. Con OIDC en
   marcha, mantenerlo solo deja superficie de ataque abierta.

## 7. Aviso sobre permisos

`infra/github-oidc.sh` necesita permiso para **registrar aplicaciones en Entra
ID**. En suscripciones de estudiante eso suele estar restringido. Si falla, el
script lo dice explícitamente y sugiere las salidas: pedirlo a un administrador
del tenant, o mantener el despliegue manual con `az login`.

Todo lo demás de esta fase —`containerapps.sh`, `rollback.sh`— funciona igual
ejecutado a mano.

## 8. Estado

Escrito y validado sintácticamente. **Sin ejecutar**: probar la federación
requiere crear la aplicación en Entra ID y disparar el workflow, y el despliegue
sigue pendiente de que los paquetes de GHCR pasen a públicos.
