# Roles y permisos — Cerebro Laboral HG

La aplicación tiene **dos roles**, y el rol del usuario en sesión **determina la vista**.
La sesión vive en el cliente (`frontend/lib/auth.ts`, localStorage `hg_session`); en
producción sería JWT contra el backend con la misma forma.

| Rol | Quién es | Vista | Qué puede hacer |
|---|---|---|---|
| **`abogado`** | Firma — Hurtado Gandini (p.ej. *Dra. Juliana Pardo*) | **Firma**: Inicio (exposición consolidada), Compliance en lote, Disciplinario Blindado | Analiza contratos, corre diligencias, **firma** documentos (acta/decisión), envía la citación por WhatsApp en su nombre |
| **`rrhh`** | Empresa cliente (p.ej. *Andrés Marín*, Jefe de Personal) | **Empresa**: Alertas y equipo (accionable, baja densidad) | Ve y resuelve alertas operativas; **no** firma ni accede a los motores jurídicos |

## Dónde se usa el nombre del usuario
- **RRHH** → saludo personalizado (*"Hola, Andrés"*).
- **Abogado** → **firma** del acta de descargos (`lawyer_name` → instructor del proceso).
- **WhatsApp** al trabajador → indica qué abogado lleva el proceso
  (*"El proceso es conducido por Dra. Juliana Pardo…"*), para que sepa con quién trata.

## Cómo se determina la vista
`frontend/components/shell/persona-context.tsx` lee el rol de la sesión y fija la
`persona` (= vista). El `PersonaSwitch` queda como **override de demostración** para
revisar ambas vistas sin volver a iniciar sesión; en producción la vista está fija por rol.

## Credenciales demo (por rol)
- Abogado (Firma): `abogado@hurtadogandini.co`
- RRHH (Empresa): `rrhh@empresacliente.co`
- Contraseña: `Demo2026!`

## Logout
Botón de cerrar sesión en el pie del sidebar → limpia la sesión y vuelve a `/login`.

## Pendiente (nota honesta)
La firma del abogado ya va en el **acta disciplinaria** y en el **WhatsApp**. Falta
llevarla también al documento de **subsanación (otrosí) de Compliance** (M5) — es un
cambio aparte en el generador de remediación.
