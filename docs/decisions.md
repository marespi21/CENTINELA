# Decisiones de diseño (ADR) — CENTINELA

Registro de decisiones arquitectónicas relevantes.

---

## ADR-001: Clean Architecture

- **Estado:** Aceptada
- **Contexto:** Se necesita un backend mantenible, testeable y desacoplado de proveedores cloud.
- **Decisión:** Organizar el código en capas `domain`, `application`, `infrastructure` y `presentation`.
- **Consecuencias:** Mayor estructura inicial; menor acoplamiento a Azure/frameworks.

---

## ADR-002: FastAPI como framework de presentación

- **Estado:** Aceptada
- **Contexto:** Se requiere una API REST tipada y con documentación OpenAPI.
- **Decisión:** Usar FastAPI en `presentation`.
- **Consecuencias:** Dependencia del ecosistema ASGI; buena DX y tipado con Pydantic.

---

## ADR-003: Modelo Relacional y Auditoría Inmutable para Gestión de Casos

- **Estado:** Aceptada
- **Autor:** Juan José Guarín
- **Contexto:** La gestión de casos de fraude requiere integridad transaccional ACID, relaciones estructuradas entre entidades (Casos, Estados, Asignaciones, Resoluciones) y una trazabilidad inmutable sin posibilidad de alteración histórica.
- **Decisión:** Implementar un motor de base de datos relacional (PostgreSQL en Azure Flexible Server / Azure SQL) estructurado en modelo entidad-relación con FKs estrictas y una tabla `auditoria_casos` append-only resguardada por triggers plpgsql que bloquean `UPDATE` y `DELETE`.
- **Consecuencias:** Cumplimiento normativo y de auditoría estricto; prevención total de manipulación de historial de investigación de casos.

---

## ADR-004: Aislamiento Completo de Red para el Almacén de Casos

- **Estado:** Aceptada
- **Autor:** Juan José Guarín
- **Contexto:** Los almacenes de datos sensibles no deben ser accesibles directamente desde Internet para minimizar la superficie de ataque.
- **Decisión:** Desplegar la base de datos dentro de una subred dedicada (`subnet-data` - 10.0.2.0/24) con `Public Network Access = Disabled`. Integrar la comunicación exclusivamente desde la subred de aplicación (`subnet-app` - 10.0.1.0/24) mediante reglas de Network Security Group (NSG).
- **Consecuencias:** Cero acceso directo desde IP públicas; cualquier intento de conexión desde Internet resulta en rechazo o timeout.

---

## ADR-005: Estrategia de Respaldos Automáticos y Continuidad en Azure Free Tier

- **Estado:** Aceptada
- **Autor:** Juan José Guarín
- **Contexto:** Garantizar la continuidad del negocio y recuperación ante fallos dentro de las restricciones de cuota y costos del nivel gratuito (Free Tier).
- **Decisión:** Configurar **Automated Daily Backups** nativos de Azure con una retención de 7 días, habilitando **Point-In-Time Restore (PITR)** vía registros WAL (Write-Ahead Logging).
- **Consecuencias:** Objetivo de Punto de Recuperación (RPO) < 5 minutos y Objetivo de Tiempo de Recuperación (RTO) < 30 minutos sin incurrir en costos adicionales.

