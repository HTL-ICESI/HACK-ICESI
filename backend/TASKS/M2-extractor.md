# TAREA — M2: Extractor con cita

> Spec autocontenida para construir M2. Cualquier instancia de Claude (o miembro del
> equipo) puede ejecutar esto sin re-derivar el diseño. Sigue los pasos en orden.

## Contexto mínimo (lee esto primero)
- Producto y arquitectura: `icesi-playbook/DISENO-SOLUCION-RETO4.md`
- Contrato del endpoint: `icesi-playbook/contracts.json` → bloque `id: "M2"`
- Reglas de arquitectura: `cerebro-laboral-hg/backend/README.md`
- Flujo de ramas: `icesi-playbook/RAMAS-Y-FLUJO.md`

## Qué hace M2
Toma el `texto` ingerido por M1 y devuelve un `DocumentRecord`: extrae los campos del
contrato laboral (tipo de vínculo, salario, fechas, jornada, cargo, empleador), **cada uno
con su `source` (span en el texto + confianza)**.

## Regla de oro (anti-alucinación) — NO LA ROMPAS
- Campos con **formato predecible** (salario, fechas, jornada en horas) → extráelos con
  **regex determinista**. Es plata: NO los decide el LLM.
- Campos de **redacción variable** (tipo de vínculo, cargo) → puede usar el LLM, **pero**
  cada valor DEBE traer su `source` (offset donde lo encontró). Sin span → `status="not_found"`.
- Ningún número que vaya a alimentar la liquidación sale "afirmado" por el LLM sin span.

## Dónde va el código (respeta las capas)
- **Lógica de extracción regex (determinista)** → `app/domain/extraction/` (NUEVO, puro, sin I/O).
- **Orquestación (regex + llamada LLM + armado del DocumentRecord)** → `app/services/extraction_service.py`.
- **Adapter LLM** (ya existe, complétalo) → `app/adapters/llm/claude_client.py` (`extract_soft_fields`).
- **Router** → `app/api/routers/extraction.py` → `POST /api/extract` (mira cómo lo hace `ingest.py`).
- **Registrar** el router en `app/main.py` y el service en `app/api/deps.py`.

## Contrato (input → output)
Input: `{ "doc_id": str, "text": str }`
Output: el `record` con la shape EXACTA de `contracts.json` → M2 → `response_example`.
Tipos ya definidos en `app/domain/models.py` (`DocumentRecord`, `Field`, `Source`, `Money`...).

## Tests obligatorios (sin esto NO se mergea)
Crea `tests/domain/test_extraction.py` y `tests/services/test_extraction_service.py`:
1. Dado un texto con "salario mensual: 2.500.000", el regex extrae `2500000` con su span.
2. Campo ausente en el texto → `status="not_found"`, sin valor inventado.
3. La extracción de salario es **determinista** (mismo texto → mismo valor + mismo span).
4. (service) Si el LLM no devuelve span para un campo blando → ese campo va a `needs_human`.

## Criterios de aceptación
- [ ] `pytest` 100% verde (incluye los tests nuevos).
- [ ] `POST /api/extract` devuelve la shape de `contracts.json` M2.
- [ ] Todo `Field` con valor numérico tiene `source` no nulo.
- [ ] El dominio (`app/domain/extraction/`) no importa nada de `app/` ni llama al LLM.

## Flujo git
```bash
git checkout main && git pull
git checkout -b feat/m2-extractor
# ... construir + tests verdes ...
git add -A && git commit -m "feat(m2): extractor de campos con cita (regex + LLM validado)"
# mergear solo con pytest verde
```

## Bloqueador conocido
Para tests con datos reales, pedir a David el **caso gold** (contrato + valores correctos
de cada campo). Mientras tanto, usar el `response_example` de `contracts.json` como fixture.
