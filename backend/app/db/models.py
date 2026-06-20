"""
Modelos ORM — tablas núcleo del Reto 4 (ver icesi-playbook/DISENO-BD-RETO4.md).

UNA sola BD; cada tabla operativa lleva `tenant_id` (string, p.ej. "empresa-001")
que coincide con TenantContext. El aislamiento es por fila. Las normas NO viven aquí:
se referencian con `norma_ref` (string que resuelve al grafo/corpus compartido).
"""
from __future__ import annotations

from datetime import date, datetime
from typing import Optional

from sqlalchemy import String, Integer, BigInteger, Float, Boolean, Date, DateTime, ForeignKey, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from app.db.base import Base


class BatchSnapshot(Base):
    """Snapshot completo de un lote de compliance (M1→M5) en JSON, por tenant.

    Persiste el lote para que sobreviva a reinicios del backend: el frontend ya no
    pierde los contratos al refrescar. Se guarda el estado serializable completo
    (results con summary + full por contrato), igual que lo devuelven los endpoints.
    """
    __tablename__ = "batch_snapshot"
    __table_args__ = (UniqueConstraint("tenant_id", "batch_id", name="uq_batch_tenant"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    batch_id: Mapped[str] = mapped_column(String, index=True)
    data_json: Mapped[str] = mapped_column(Text)               # batch serializado (jsonable)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                 onupdate=datetime.utcnow)


class ExposureSnapshot(Base):
    """Exposición agregada de la empresa (número mágico + alertas) en JSON, por tenant.

    Hace que el dashboard de Inicio (abogado y RRHH) lea datos REALES del último
    análisis aunque el backend se reinicie — en vez de caer al dataset demo.
    """
    __tablename__ = "exposure_snapshot"
    tenant_id: Mapped[str] = mapped_column(String, primary_key=True)   # 1 por empresa
    data_json: Mapped[str] = mapped_column(Text)                       # ExposureRequest jsonable
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                 onupdate=datetime.utcnow)


class Tenant(Base):
    __tablename__ = "tenant"
    id: Mapped[str] = mapped_column(String, primary_key=True)   # "empresa-001"
    nombre: Mapped[str] = mapped_column(String)
    nit: Mapped[str] = mapped_column(String, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Documento(Base):
    __tablename__ = "documento"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenant.id"), index=True)
    doc_id: Mapped[str] = mapped_column(String)
    filename: Mapped[str] = mapped_column(String)
    tipo_doc: Mapped[str] = mapped_column(String, default="contrato")  # contrato|RIT|politica|nomina
    status: Mapped[str] = mapped_column(String)                        # digital|ocr|needs_human
    confidence: Mapped[float] = mapped_column(Float, default=0.0)
    contenido: Mapped[str] = mapped_column(Text, default="")
    uploaded_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Empleado(Base):
    __tablename__ = "empleado"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenant.id"), index=True)
    nombre: Mapped[str] = mapped_column(String)
    documento: Mapped[str] = mapped_column(String, default="")   # cédula
    cargo: Mapped[str] = mapped_column(String, default="")
    activo: Mapped[bool] = mapped_column(Boolean, default=True)
    contratos: Mapped[list["Contrato"]] = relationship(back_populates="empleado")


class Contrato(Base):
    __tablename__ = "contrato"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenant.id"), index=True)
    empleado_id: Mapped[int] = mapped_column(Integer, ForeignKey("empleado.id"))
    documento_id: Mapped[Optional[int]] = mapped_column(Integer, ForeignKey("documento.id"), nullable=True)
    tipo_vinculo: Mapped[str] = mapped_column(String)            # termino_fijo|indefinido|obra|prestacion_servicios
    salario_base: Mapped[int] = mapped_column(BigInteger, default=0)  # COP
    salario_variable: Mapped[bool] = mapped_column(Boolean, default=False)  # -> liquidar con promedio
    auxilio_transporte: Mapped[int] = mapped_column(BigInteger, default=0)  # cuenta p/ cesantías y prima, NO p/ vacaciones
    periodicidad: Mapped[str] = mapped_column(String, default="mensual")
    jornada_horas_semana: Mapped[int] = mapped_column(Integer, default=0)
    fecha_inicio: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    fecha_fin: Mapped[Optional[date]] = mapped_column(Date, nullable=True)   # null = indefinido
    fecha_retiro: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    estado: Mapped[str] = mapped_column(String, default="vigente")
    empleado: Mapped["Empleado"] = relationship(back_populates="contratos")


class Gap(Base):
    __tablename__ = "gap"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenant.id"), index=True)
    contrato_id: Mapped[int] = mapped_column(Integer, ForeignKey("contrato.id"))
    tipo: Mapped[str] = mapped_column(String)                    # jornada|reclasificacion|ss_mora
    descripcion: Mapped[str] = mapped_column(String)
    severidad: Mapped[str] = mapped_column(String, default="media")
    norma_ref: Mapped[str] = mapped_column(String, default="")   # "Ley 2101/2021:art. 3" -> corpus
    remedy_type: Mapped[str] = mapped_column(String, default="otrosi")
    estado: Mapped[str] = mapped_column(String, default="detectado")
    detected_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class Liquidacion(Base):
    __tablename__ = "liquidacion"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenant.id"), index=True)
    empleado_id: Mapped[int] = mapped_column(Integer, ForeignKey("empleado.id"))
    contrato_id: Mapped[int] = mapped_column(Integer, ForeignKey("contrato.id"))
    motivo_terminacion: Mapped[str] = mapped_column(String, default="")  # renuncia|justa_causa|sin_justa_causa|mutuo_acuerdo|transaccion
    bonificacion: Mapped[int] = mapped_column(BigInteger, default=0)      # acuerdo de transacción / mera liberalidad
    fecha_calculo: Mapped[date] = mapped_column(Date, default=date.today)
    cesantias: Mapped[int] = mapped_column(BigInteger, default=0)
    intereses_cesantias: Mapped[int] = mapped_column(BigInteger, default=0)
    prima: Mapped[int] = mapped_column(BigInteger, default=0)
    vacaciones: Mapped[int] = mapped_column(BigInteger, default=0)
    indemnizacion: Mapped[int] = mapped_column(BigInteger, default=0)
    total: Mapped[int] = mapped_column(BigInteger, default=0)
    diferencia_vs_pagado: Mapped[int] = mapped_column(BigInteger, default=0)
    es_correcta: Mapped[bool] = mapped_column(Boolean, default=True)


class WorkerContact(Base):
    """Número de WhatsApp del trabajador por lote, indexado por (tenant_id, doc_id).

    `doc_id` coincide con el BatchItem.doc_id que produce el pipeline M1→M5.
    El campo `phone` se rellena desde RRHH; la extracción OCR no captura celulares.
    """
    __tablename__ = "worker_contact"
    __table_args__ = (UniqueConstraint("tenant_id", "doc_id", name="uq_worker_tenant_doc"),)
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, index=True)
    doc_id: Mapped[str] = mapped_column(String, index=True)
    nombre: Mapped[str] = mapped_column(String, default="")
    phone: Mapped[str] = mapped_column(String, default="")   # E.164 o formato CO
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow,
                                                 onupdate=datetime.utcnow)


class Alerta(Base):
    __tablename__ = "alerta"
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    tenant_id: Mapped[str] = mapped_column(String, ForeignKey("tenant.id"), index=True)
    empleado_id: Mapped[int] = mapped_column(Integer, ForeignKey("empleado.id"))
    tipo: Mapped[str] = mapped_column(String)                    # vencimiento_contrato|vacaciones_vencidas|ss_mora
    severidad: Mapped[str] = mapped_column(String, default="media")
    fecha_vencimiento: Mapped[Optional[date]] = mapped_column(Date, nullable=True)
    mensaje: Mapped[str] = mapped_column(String, default="")
    responsable_email: Mapped[str] = mapped_column(String, default="")
    estado: Mapped[str] = mapped_column(String, default="activa")
