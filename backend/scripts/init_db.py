"""
Crea la BD (SQLite) y la siembra con una empresa demo: empleados, contratos, un gap
y una alerta. Permite ver el dashboard con datos sin esperar el pipeline completo.

Uso:
    cd cerebro-laboral-hg/backend && source .venv/bin/activate
    python scripts/init_db.py
"""
from __future__ import annotations

import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from app.db.base import init_db, SessionLocal
from app.db import models as m


def seed() -> None:
    init_db()
    db = SessionLocal()
    if db.get(m.Tenant, "empresa-001"):
        print("Ya existe la empresa demo; no se re-siembra.")
        db.close()
        return

    db.add(m.Tenant(id="empresa-001", nombre="Empresa Cliente SAS", nit="900.123.456-7"))

    e1 = m.Empleado(tenant_id="empresa-001", nombre="Juan Pérez", documento="1.144.000.000", cargo="Asesor comercial")
    e2 = m.Empleado(tenant_id="empresa-001", nombre="María Gómez", documento="31.999.888", cargo="Coordinadora")
    db.add_all([e1, e2]); db.commit()

    c1 = m.Contrato(tenant_id="empresa-001", empleado_id=e1.id, tipo_vinculo="termino_fijo",
                    salario_base=2_500_000, jornada_horas_semana=48,
                    fecha_inicio=date(2024, 2, 1), fecha_fin=date(2025, 1, 31))
    c2 = m.Contrato(tenant_id="empresa-001", empleado_id=e2.id, tipo_vinculo="termino_indefinido",
                    salario_base=3_800_000, jornada_horas_semana=46, fecha_inicio=date(2022, 3, 15))
    db.add_all([c1, c2]); db.commit()

    db.add(m.Gap(tenant_id="empresa-001", contrato_id=c1.id, tipo="jornada",
                 descripcion="Jornada de 48h excede el máximo de 42h", severidad="alta",
                 norma_ref="Ley 2101/2021:art. 3", remedy_type="otrosi"))
    db.add(m.Alerta(tenant_id="empresa-001", empleado_id=e1.id, tipo="vencimiento_contrato",
                    severidad="alta", fecha_vencimiento=date(2025, 1, 31),
                    mensaje="El contrato a término fijo vence pronto", responsable_email="rh@empresacliente.co"))
    db.commit()

    print("BD creada y sembrada:")
    print(f"  Tenant   : empresa-001 (Empresa Cliente SAS)")
    print(f"  Empleados: {db.query(m.Empleado).count()}")
    print(f"  Contratos: {db.query(m.Contrato).count()}")
    print(f"  Gaps     : {db.query(m.Gap).count()}")
    print(f"  Alertas  : {db.query(m.Alerta).count()}")
    db.close()


if __name__ == "__main__":
    seed()
