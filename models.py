from sqlalchemy import Column, Integer, String, Float, DateTime, Boolean, ForeignKey, Text
from sqlalchemy.orm import relationship
from datetime import datetime

from database import Base


class Usuario(Base):
    __tablename__ = "usuarios"

    id = Column(Integer, primary_key=True, index=True)
    username = Column(String, unique=True, nullable=False)
    password_hash = Column(String, nullable=False)
    creado_en = Column(DateTime, default=datetime.utcnow)

    # Un usuario puede tener varias cuentas/proveedores conectados:
    # Withings, Garmin, Omron, etc.
    proveedores = relationship("Proveedor", back_populates="usuario")


class Proveedor(Base):
    __tablename__ = "proveedores"

    id = Column(Integer, primary_key=True, index=True)
    usuario_id = Column(Integer, ForeignKey("usuarios.id"), nullable=False)

    # Nombre lógico del proveedor externo: withings, garmin, omron...
    nombre = Column(String, nullable=False)

    # Identificador opcional de la cuenta externa si el proveedor lo ofrece.
    identificador_externo = Column(String, nullable=True)

    # Tokens OAuth asociados a este proveedor para este usuario.
    access_token = Column(Text, nullable=True)
    refresh_token = Column(Text, nullable=True)
    token_expira_en = Column(DateTime, nullable=True)

    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    usuario = relationship("Usuario", back_populates="proveedores")
    dispositivos = relationship("Dispositivo", back_populates="proveedor")


class Dispositivo(Base):
    __tablename__ = "dispositivos"

    id = Column(Integer, primary_key=True, index=True)
    proveedor_id = Column(Integer, ForeignKey("proveedores.id"), nullable=False)

    nombre = Column(String, nullable=False)  # BPM Connect, Body+, etc.
    identificador_externo = Column(String, nullable=True)

    activo = Column(Boolean, default=True)
    creado_en = Column(DateTime, default=datetime.utcnow)

    proveedor = relationship("Proveedor", back_populates="dispositivos")
    metricas = relationship("Metrica", back_populates="dispositivo")


class Metrica(Base):
    __tablename__ = "metricas"

    id = Column(Integer, primary_key=True, index=True)
    dispositivo_id = Column(Integer, ForeignKey("dispositivos.id"), nullable=False)

    nombre = Column(String, nullable=False)      # peso, frecuencia_cardiaca...
    codigo_api = Column(String, nullable=False)  # 1, 9, 10, 11...
    unidad = Column(String, nullable=True)       # kg, bpm, mmHg
    activa = Column(Boolean, default=True)

    dispositivo = relationship("Dispositivo", back_populates="metricas")
    mediciones = relationship("Medicion", back_populates="metrica")


class Medicion(Base):
    __tablename__ = "mediciones"

    id = Column(Integer, primary_key=True, index=True)
    metrica_id = Column(Integer, ForeignKey("metricas.id"), nullable=False)

    valor = Column(Float, nullable=False)
    fecha_medicion = Column(DateTime, nullable=False)
    fecha_registro = Column(DateTime, default=datetime.utcnow)

    metrica = relationship("Metrica", back_populates="mediciones")

# Catalogos de Dispositivos y Métricas compatibles
class CatalogoMetrica(Base):
    __tablename__ = "catalogo_metricas"

    id = Column(Integer, primary_key=True, index=True)

    proveedor = Column(String, nullable=False)       # withings, garmin, omron
    codigo_api = Column(String, nullable=False)      # 1, 9, 10, 11
    nombre = Column(String, nullable=False)          # peso, frecuencia_cardiaca
    unidad = Column(String, nullable=True)           # kg, bpm, mmHg
    descripcion = Column(String, nullable=True)

class CatalogoDispositivo(Base):
    __tablename__ = "catalogo_dispositivos"

    id = Column(Integer, primary_key=True, index=True)

    proveedor = Column(String, nullable=False)           # withings
    modelo_api = Column(String, nullable=False)          # BPM Connect
    nombre_comercial = Column(String, nullable=False)    # Withings BPM Connect
    descripcion = Column(String, nullable=True)

class CatalogoDispositivoMetrica(Base):
    __tablename__ = "catalogo_dispositivo_metricas"

    id = Column(Integer, primary_key=True, index=True)

    catalogo_dispositivo_id = Column(
        Integer,
        ForeignKey("catalogo_dispositivos.id"),
        nullable=False
    )

    catalogo_metrica_id = Column(
        Integer,
        ForeignKey("catalogo_metricas.id"),
        nullable=False
    )