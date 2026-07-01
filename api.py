### IMPORTS ###

import os
import urllib.parse
from datetime import datetime, timedelta
import requests
from pathlib import Path
from dotenv import load_dotenv

from fastapi import FastAPI, HTTPException, Depends, Request
from fastapi.responses import Response, HTMLResponse, RedirectResponse
from fastapi.security import OAuth2PasswordRequestForm
from fastapi.templating import Jinja2Templates
from fastapi.staticfiles import StaticFiles
from fastapi.middleware.cors import CORSMiddleware

from sqlalchemy.orm import Session
from prometheus_client import Gauge, generate_latest, CONTENT_TYPE_LATEST
from apscheduler.schedulers.background import BackgroundScheduler
from contextlib import asynccontextmanager

from database import Base, engine, get_db
import models
from auth import generar_hash_password, verificar_password, crear_access_token, obtener_usuario_actual

# Cargar variables de entorno
load_dotenv()

WITHINGS_CLIENT_ID = os.getenv("WITHINGS_CLIENT_ID")
WITHINGS_CLIENT_SECRET = os.getenv("WITHINGS_CLIENT_SECRET")

CALLBACK_HOST = os.getenv("APP_HOST", "localhost")
CALLBACK_PORT = os.getenv("APP_PORT", "8000")

WITHINGS_CALLBACK_PATH = "/proveedores/withings/callback"
WITHINGS_REDIRECT_URI = f"http://{CALLBACK_HOST}:{CALLBACK_PORT}{WITHINGS_CALLBACK_PATH}"

WITHINGS_TOKEN_URL = "https://wbsapi.withings.net/v2/oauth2"
WITHINGS_AUTHORIZE_URL = "https://account.withings.com/oauth2_user/authorize2"
WITHINGS_MEASURE_URL = "https://wbsapi.withings.net/measure"
WITHINGS_USER_URL = "https://wbsapi.withings.net/v2/user"
WITHINGS_SCOPES = "user.info,user.metrics"

# Datos necesarios para prometheus
medida_gauge = Gauge(
    "constante_biometrica",
    "Valor de una constante biometrica obtenida desde un dispositivo",
    ["proveedor", "dispositivo", "tipo_medida"]
)

# Tareas periódicas
scheduler = BackgroundScheduler()

@asynccontextmanager
async def lifespan(app: FastAPI):

    scheduler.add_job(
        sincronizar_todos_los_usuarios,
        "interval",
        minutes=5,
        id="sincronizacion_periodica",
        replace_existing=True
    )

    scheduler.start()

    yield

    scheduler.shutdown()

# Inicialización de API
app = FastAPI(
    title="Vitals API",
    description="API to expose biomedical data acquired from Withings.",
    version="1.0.0",
    lifespan=lifespan,
)

# Configurar middleware CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Inicialización de Base de datos
Base.metadata.create_all(bind=engine)
BASE_DIR = Path(__file__).resolve().parent
templates = Jinja2Templates(directory=str(BASE_DIR / "templates"))
app.mount("/static", StaticFiles(directory=str(BASE_DIR / "static")), name="static")

@app.post("/debug/peso")
def insertar_peso_prueba(
    valor: float,
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    proveedor = db.query(models.Proveedor).filter(
        models.Proveedor.usuario_id == usuario_actual.id,
        models.Proveedor.nombre == "withings"
    ).first()

    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail="User does not have a connected Withings provider"
        )

    dispositivo = db.query(models.Dispositivo).filter(
        models.Dispositivo.proveedor_id == proveedor.id,
        models.Dispositivo.nombre == "Báscula de prueba"
    ).first()

    if not dispositivo:
        dispositivo = models.Dispositivo(
            proveedor_id=proveedor.id,
            nombre="Báscula de prueba",
            identificador_externo="debug_scale",
            activo=True
        )
        db.add(dispositivo)
        db.flush()

    metrica = db.query(models.Metrica).filter(
        models.Metrica.dispositivo_id == dispositivo.id,
        models.Metrica.nombre == "peso"
    ).first()

    if not metrica:
        metrica = models.Metrica(
            dispositivo_id=dispositivo.id,
            nombre="peso",
            codigo_api="1",
            unidad="kg",
            activa=True
        )
        db.add(metrica)
        db.flush()

    medicion = models.Medicion(
        metrica_id=metrica.id,
        valor=valor,
        fecha_medicion=datetime.utcnow()
    )

    db.add(medicion)
    proveedor.ultima_sincronizacion = datetime.utcnow()

    db.commit()

    return {
        "status": "ok",
        "message": "Weight test inserted successfully",
        "device": dispositivo.nombre,
        "metric": metrica.nombre,
        "value": valor,
        "unit": metrica.unidad
    }

### Gestión de Usuarios ###

# Registro de nuevo usuario
@app.post("/auth/registro")
def registrar_usuario(
    username: str,
    password: str,
    db: Session = Depends(get_db)
):
    if len(password.encode("utf-8")) > 72:
        raise HTTPException(
            status_code=400,
            detail="Password cannot exceed 72 bytes"
        )

    usuario_existente = db.query(models.Usuario).filter(
        models.Usuario.username == username
    ).first()

    if usuario_existente:
        raise HTTPException(
            status_code=400,
            detail="User already exists"
        )

    usuario = models.Usuario(
        username=username,
        password_hash=generar_hash_password(password)
    )

    db.add(usuario)
    db.commit()
    db.refresh(usuario)

    return {
        "status": "ok",
        "user_id": usuario.id,
        "username": usuario.username
    }

# Inicio de sesión
@app.post("/auth/login")
def login(
    form_data: OAuth2PasswordRequestForm = Depends(),
    db: Session = Depends(get_db)
):
    usuario = db.query(models.Usuario).filter(
        models.Usuario.username == form_data.username
    ).first()

    if not usuario:
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    if not verificar_password(form_data.password, usuario.password_hash):
        raise HTTPException(
            status_code=401,
            detail="Incorrect username or password"
        )

    access_token = crear_access_token(
        data={"sub": str(usuario.id)}
    )

    return {
        "access_token": access_token,
        "token_type": "bearer"
    }

# Usuario actual
@app.get("/auth/me")
def obtener_mi_usuario(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual)
):
    return {
        "id": usuario_actual.id,
        "username": usuario_actual.username,
        "created_at": usuario_actual.creado_en
    }

# Página de inicio de sesión
@app.get("/login", response_class=HTMLResponse)
def login_page(request: Request):
    return templates.TemplateResponse(
        request,
        "login.html",
        {}
    )

# Página principal de la aplicación
@app.get("/dashboard", response_class=HTMLResponse)
def dashboard_page(request: Request):
    return templates.TemplateResponse(
        request,
        "dashboard.html",
        {}
    )

### Gestión de dispositivos ###

# Mostrar página de dispositivos
@app.get("/dispositivos", response_class=HTMLResponse)
def dispositivos_page(request: Request):
    return templates.TemplateResponse(
        request,
        "dispositivos.html",
        {}
    )

# Obtener proveedores compatibles
@app.get("/catalogo/proveedores")
def obtener_proveedores_compatibles(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    proveedores = (
        db.query(models.CatalogoDispositivo.proveedor)
        .distinct()
        .order_by(models.CatalogoDispositivo.proveedor.asc())
        .all()
    )

    return [proveedor[0] for proveedor in proveedores]

# Conectar con la api de withings
@app.get("/proveedores/withings/conectar")
def conectar_withings(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual)
):
    params = {
        "response_type": "code",
        "client_id": WITHINGS_CLIENT_ID,
        "scope": WITHINGS_SCOPES,
        "redirect_uri": WITHINGS_REDIRECT_URI,
        "state": str(usuario_actual.id),
    }

    auth_url = WITHINGS_AUTHORIZE_URL + "?" + urllib.parse.urlencode(params)

    return {
        "auth_url": auth_url
    }

# Guardar el proveedor de withings con el usuario correspondiente
def guardar_proveedor_withings_bd(tokens: dict, db: Session, usuario_id: int):
    body = tokens["body"]

    proveedor = db.query(models.Proveedor).filter(
        models.Proveedor.usuario_id == usuario_id,
        models.Proveedor.nombre == "withings"
    ).first()

    if not proveedor:
        proveedor = models.Proveedor(
            usuario_id=usuario_id,
            nombre="withings",
            access_token=body["access_token"],
            refresh_token=body["refresh_token"],
            token_expira_en=datetime.utcnow() + timedelta(
                seconds=body.get("expires_in", 10800)
            ),
            activo=True
        )

        db.add(proveedor)

    else:
        proveedor.access_token = body["access_token"]
        proveedor.refresh_token = body["refresh_token"]
        proveedor.token_expira_en = datetime.utcnow() + timedelta(
            seconds=body.get("expires_in", 10800)
        )
        proveedor.activo = True

    db.commit()
    db.refresh(proveedor)

    return proveedor

@app.get("/proveedores/withings/callback")
def callback_withings(
    code: str,
    state: str,
    db: Session = Depends(get_db)
):
    try:
        usuario_id = int(state)
    except ValueError:
        raise HTTPException(
            status_code=400,
            detail="Invalid state parameter"
        )

    data = {
        "action": "requesttoken",
        "grant_type": "authorization_code",
        "client_id": WITHINGS_CLIENT_ID,
        "client_secret": WITHINGS_CLIENT_SECRET,
        "code": code,
        "redirect_uri": WITHINGS_REDIRECT_URI,
    }

    response = requests.post(
        WITHINGS_TOKEN_URL,
        data=data,
        headers={"Accept": "application/json"},
        timeout=30,
    )

    payload = response.json()

    if "body" not in payload or "access_token" not in payload["body"]:
        raise HTTPException(status_code=400, detail=payload)

    proveedor = guardar_proveedor_withings_bd(
        tokens=payload,
        db=db,
        usuario_id=usuario_id
    )

    if "body" not in payload or "access_token" not in payload["body"]:
        return RedirectResponse(
            url="/dispositivos?estado=error&proveedor=withings"
        )

    return RedirectResponse(
        url="/dispositivos?estado=ok&proveedor=withings"
    )

# Sincronizar los dispositivos con el usuario
@app.post("/proveedores/withings/sincronizar_dispositivos")
def sincronizar_dispositivos_withings(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    proveedor = db.query(models.Proveedor).filter(
        models.Proveedor.usuario_id == usuario_actual.id,
        models.Proveedor.nombre == "withings",
        models.Proveedor.activo == True
    ).first()

    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail="User does not have Withings connected"
        )
    
    access_token = obtener_access_token_proveedor(
        db=db,
        usuario_id=usuario_actual.id,
        nombre_proveedor="withings"
    )

    response = requests.get(
        WITHINGS_USER_URL,
        headers={
            "Authorization": f"Bearer {access_token}"
        },
        params={
            "action": "getdevice"
        },
        timeout=30
    )

    data = response.json()

    if data.get("status") != 0:
        raise HTTPException(status_code=400, detail=data)

    dispositivos_api = data.get("body", {}).get("devices", [])

    sincronizados = []

    for device in dispositivos_api:
        device_id = str(
            device.get("deviceid")
            or device.get("hash_deviceid")
            or ""
        )

        modelo_api = device.get("model")

        if not device_id or not modelo_api:
            continue

        dispositivo_compatible = db.query(models.CatalogoDispositivo).filter(
            models.CatalogoDispositivo.proveedor == "withings",
            models.CatalogoDispositivo.modelo_api == modelo_api
        ).first()

        if not dispositivo_compatible:
            continue

        dispositivo = db.query(models.Dispositivo).filter(
            models.Dispositivo.proveedor_id == proveedor.id,
            models.Dispositivo.identificador_externo == device_id
        ).first()

        if not dispositivo:
            dispositivo = models.Dispositivo(
                proveedor_id=proveedor.id,
                nombre=dispositivo_compatible.nombre_comercial,
                identificador_externo=device_id,
                activo=True
            )
            db.add(dispositivo)
        else:
            dispositivo.nombre = dispositivo_compatible.nombre_comercial
            dispositivo.activo = True

        db.flush()

        metricas_creadas = registrar_metricas_dispositivo_bd(
            db=db,
            dispositivo=dispositivo,
            catalogo_dispositivo=dispositivo_compatible
        )

        sincronizados.append({
            "device": dispositivo_compatible.nombre_comercial,
            "created_metrics": metricas_creadas
        })

    db.commit()

    return {
        "status": "ok",
        "synchronized_devices": sincronizados
    }

# Listar dispositivos conectados
@app.get("/mis_dispositivos")
def obtener_mis_dispositivos(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    dispositivos = (
        db.query(models.Dispositivo)
        .join(models.Proveedor)
        .filter(
            models.Proveedor.usuario_id == usuario_actual.id
        )
        .all()
    )

    return [
        {
            "id": d.id,
            "name": d.nombre,
            "external_id": d.identificador_externo,
            "active": d.activo
        }
        for d in dispositivos
    ]

# Refrescar token en caso de caducidad
def refrescar_token_proveedor(proveedor: models.Proveedor, db: Session) -> str:
    if proveedor.nombre != "withings":
        raise HTTPException(
            status_code=400,
            detail=f"Token refresh not implemented for {proveedor.nombre}"
        )

    data = {
        "action": "requesttoken",
        "grant_type": "refresh_token",
        "client_id": WITHINGS_CLIENT_ID,
        "client_secret": WITHINGS_CLIENT_SECRET,
        "refresh_token": proveedor.refresh_token,
    }

    response = requests.post(
        WITHINGS_TOKEN_URL,
        data=data,
        headers={"Accept": "application/json"},
        timeout=30,
    )

    payload = response.json()

    if "body" not in payload or "access_token" not in payload["body"]:
        raise HTTPException(
            status_code=401,
            detail=f"Could not refresh token for {proveedor.nombre}: {payload}"
        )

    body = payload["body"]

    proveedor.access_token = body["access_token"]
    proveedor.refresh_token = body["refresh_token"]
    proveedor.token_expira_en = datetime.utcnow() + timedelta(
        seconds=body.get("expires_in", 10800)
    )
    proveedor.activo = True

    db.commit()
    db.refresh(proveedor)

    return proveedor.access_token

# Obtener token de acceso
def obtener_access_token_proveedor(
    db: Session,
    usuario_id: int,
    nombre_proveedor: str
) -> str:
    proveedor = db.query(models.Proveedor).filter(
        models.Proveedor.usuario_id == usuario_id,
        models.Proveedor.nombre == nombre_proveedor,
        models.Proveedor.activo == True
    ).first()

    if not proveedor:
        raise HTTPException(
            status_code=404,
            detail=f"User does not have provider {nombre_proveedor} connected"
        )

    if not proveedor.access_token:
        raise HTTPException(
            status_code=401,
            detail=f"Provider {nombre_proveedor} does not have access_token"
        )

    if proveedor.token_expira_en is None or proveedor.token_expira_en <= datetime.utcnow():
        return refrescar_token_proveedor(proveedor, db)

    return proveedor.access_token

### Gestión de métricas ###

# Registrar métricas disponibles para el usuario
def registrar_metricas_dispositivo_bd(
    db: Session,
    dispositivo: models.Dispositivo,
    catalogo_dispositivo: models.CatalogoDispositivo
):
    relaciones = db.query(models.CatalogoDispositivoMetrica).filter(
        models.CatalogoDispositivoMetrica.catalogo_dispositivo_id == catalogo_dispositivo.id
    ).all()

    metricas_creadas = []

    for relacion in relaciones:
        catalogo_metrica = db.query(models.CatalogoMetrica).filter(
            models.CatalogoMetrica.id == relacion.catalogo_metrica_id
        ).first()

        if not catalogo_metrica:
            continue

        metrica = db.query(models.Metrica).filter(
            models.Metrica.dispositivo_id == dispositivo.id,
            models.Metrica.codigo_api == catalogo_metrica.codigo_api
        ).first()

        if metrica:
            metrica.nombre = catalogo_metrica.nombre
            metrica.unidad = catalogo_metrica.unidad
            metrica.activa = True
        else:
            metrica = models.Metrica(
                dispositivo_id=dispositivo.id,
                nombre=catalogo_metrica.nombre,
                codigo_api=catalogo_metrica.codigo_api,
                unidad=catalogo_metrica.unidad,
                activa=True
            )
            db.add(metrica)
            metricas_creadas.append(catalogo_metrica.nombre)

    return metricas_creadas

# Listar métricas del usuario
@app.get("/mis_metricas")
def obtener_mis_metricas(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    metricas = (
        db.query(models.Metrica, models.Dispositivo)
        .join(models.Dispositivo, models.Metrica.dispositivo_id == models.Dispositivo.id)
        .join(models.Proveedor, models.Dispositivo.proveedor_id == models.Proveedor.id)
        .filter(
            models.Proveedor.usuario_id == usuario_actual.id,
            models.Metrica.activa == True
        )
        .all()
    )

    return [
        {
            "id": metrica.id,
            "name": metrica.nombre,
            "api_code": metrica.codigo_api,
            "unit": metrica.unidad,
            "device": dispositivo.nombre,
            "device_id": dispositivo.id,
            "provider": dispositivo.proveedor.nombre if hasattr(dispositivo, "proveedor") else None
        }
        for metrica, dispositivo in metricas
    ]

### Gestión de medidas ###

# Función para convertir valores en las unidades correspondientes
def convertir_valor(value: int, unit: int) -> float:
    return value * (10 ** unit)

# Obtener las métricas del usuario
def obtener_metricas_usuario(db: Session, usuario_id: int, proveedor_nombre: str = "withings"):
    return (
        db.query(models.Metrica, models.Dispositivo, models.Proveedor)
        .join(models.Dispositivo, models.Metrica.dispositivo_id == models.Dispositivo.id)
        .join(models.Proveedor, models.Dispositivo.proveedor_id == models.Proveedor.id)
        .filter(
            models.Proveedor.usuario_id == usuario_id,
            models.Proveedor.nombre == proveedor_nombre,
            models.Metrica.activa == True,
            models.Dispositivo.activo == True,
            models.Proveedor.activo == True,
        )
        .all()
    )

# Sincronizar las medidas con la api de withings
@app.post("/medidas/sincronizar")
def sincronizar_medidas(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    return sincronizar_medidas_usuario(
        db=db,
        usuario_id=usuario_actual.id
    )
    
def sincronizar_medidas_usuario(db: Session, usuario_id: int):
    metricas_usuario = obtener_metricas_usuario(
        db=db,
        usuario_id=usuario_id,
        proveedor_nombre="withings"
    )

    if not metricas_usuario:
        raise HTTPException(
            status_code=404,
            detail="No active metrics found for this user"
        )

    codigos_api = sorted({
        metrica.codigo_api
        for metrica, dispositivo, proveedor in metricas_usuario
    })

    meastype = ",".join(codigos_api)

    access_token = obtener_access_token_proveedor(
        db=db,
        usuario_id=usuario_id,
        nombre_proveedor="withings"
    )

    response = requests.get(
        WITHINGS_MEASURE_URL,
        headers={"Authorization": f"Bearer {access_token}"},
        params={
            "action": "getmeas",
            "meastype": meastype,
        },
        timeout=30
    )

    data = response.json()

    if data.get("status") != 0:
        raise HTTPException(status_code=400, detail=data)

    mapa_metricas = {
        metrica.codigo_api: metrica
        for metrica, dispositivo, proveedor in metricas_usuario
    }

    mediciones_guardadas = 0

    for grupo in data.get("body", {}).get("measuregrps", []):
        fecha_unix = grupo.get("date")

        if not fecha_unix:
            continue

        fecha_medicion = datetime.fromtimestamp(fecha_unix)

        for medida in grupo.get("measures", []):
            codigo_api = str(medida.get("type"))
            metrica = mapa_metricas.get(codigo_api)

            if not metrica:
                continue

            valor = convertir_valor(
                medida.get("value"),
                medida.get("unit")
            )

            medicion_existente = db.query(models.Medicion).filter(
                models.Medicion.metrica_id == metrica.id,
                models.Medicion.fecha_medicion == fecha_medicion
            ).first()

            if medicion_existente:
                continue

            medicion = models.Medicion(
                metrica_id=metrica.id,
                valor=valor,
                fecha_medicion=fecha_medicion
            )

            db.add(medicion)
            mediciones_guardadas += 1

    db.commit()

    return {
        "status": "ok",
        "message": (
            "Measurements synchronized successfully"
            if mediciones_guardadas > 0
            else "No new measurements available"
        ),
        "saved_measurements": mediciones_guardadas
    }

# Función periódica de actualización de métricas
def sincronizar_todos_los_usuarios():
    db = next(get_db())

    try:
        proveedores = db.query(models.Proveedor).filter(
            models.Proveedor.activo == True
        ).all()

        for proveedor in proveedores:
            try:
                sincronizar_medidas_usuario(
                    db=db,
                    usuario_id=proveedor.usuario_id
                )
            except Exception as e:
                print(f"Error sincronizando usuario {proveedor.usuario_id}: {e}")

    finally:
        db.close()

# Obtener histórico de todas las medidas
@app.get("/medidas/historico")
def obtener_historico_medidas(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    resultados = (
        db.query(models.Medicion, models.Metrica, models.Dispositivo, models.Proveedor)
        .join(models.Metrica, models.Medicion.metrica_id == models.Metrica.id)
        .join(models.Dispositivo, models.Metrica.dispositivo_id == models.Dispositivo.id)
        .join(models.Proveedor, models.Dispositivo.proveedor_id == models.Proveedor.id)
        .filter(models.Proveedor.usuario_id == usuario_actual.id)
        .order_by(models.Medicion.fecha_medicion.asc())
        .all()
    )

    if not resultados:
        raise HTTPException(
            status_code=404,
            detail="No saved measurements found"
        )

    return [
        {
            "provider": proveedor.nombre,
            "device": dispositivo.nombre,
            "metric": metrica.nombre,
            "unit": metrica.unidad,
            "value": medicion.valor,
            "measurement_date": medicion.fecha_medicion,
            "registration_date": medicion.fecha_registro,
        }
        for medicion, metrica, dispositivo, proveedor in resultados
    ]

# Obtener últimas medidas
@app.get("/medidas/ultimas")
def obtener_ultimas_medidas(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    metricas_usuario = obtener_metricas_usuario(
        db=db,
        usuario_id=usuario_actual.id,
        proveedor_nombre="withings"
    )

    ultimas = []

    for metrica, dispositivo, proveedor in metricas_usuario:
        medicion = (
            db.query(models.Medicion)
            .filter(models.Medicion.metrica_id == metrica.id)
            .order_by(models.Medicion.fecha_medicion.desc())
            .first()
        )

        if not medicion:
            continue

        ultimas.append({
            "provider": proveedor.nombre,
            "device": dispositivo.nombre,
            "metric": metrica.nombre,
            "unit": metrica.unidad,
            "value": medicion.valor,
            "measurement_date": medicion.fecha_medicion,
            "registration_date": medicion.fecha_registro,
        })

    if not ultimas:
        raise HTTPException(
            status_code=404,
            detail="No recent measurements available"
        )

    return ultimas


### FHIR/HL7 Integration Endpoints ###

LOINC_CODES = {
    "peso": {
        "code": "29463-7",
        "display": "Body weight",
        "ucum": "kg"
    },
    "frecuencia_cardiaca": {
        "code": "8867-4",
        "display": "Heart rate",
        "ucum": "/min"
    },
    "presion_diastolica": {
        "code": "8462-4",
        "display": "Diastolic blood pressure",
        "ucum": "mm[Hg]"
    },
    "presion_sistolica": {
        "code": "8480-6",
        "display": "Systolic blood pressure",
        "ucum": "mm[Hg]"
    }
}

@app.get("/fhir/Patient/me")
def get_fhir_patient(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual)
):
    return {
        "resourceType": "Patient",
        "id": str(usuario_actual.id),
        "active": True,
        "name": [
            {
                "use": "official",
                "text": usuario_actual.username
            }
        ]
    }

@app.get("/fhir/Device")
def get_fhir_devices(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    dispositivos = (
        db.query(models.Dispositivo)
        .join(models.Proveedor)
        .filter(models.Proveedor.usuario_id == usuario_actual.id)
        .all()
    )

    entries = []
    for d in dispositivos:
        device_resource = {
            "resourceType": "Device",
            "id": str(d.id),
            "status": "active" if d.activo else "inactive",
            "modelNumber": d.nombre,
            "identifier": [
                {
                    "system": "http://withings.com/deviceid",
                    "value": d.identificador_externo
                }
            ] if d.identificador_externo else [],
            "owner": {
                "reference": f"Patient/{usuario_actual.id}"
            }
        }
        entries.append({
            "fullUrl": f"/fhir/Device/{d.id}",
            "resource": device_resource
        })

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(entries),
        "entry": entries
    }

@app.get("/fhir/Observation")
def get_fhir_observations(
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    resultados = (
        db.query(models.Medicion, models.Metrica, models.Dispositivo, models.Proveedor)
        .join(models.Metrica, models.Medicion.metrica_id == models.Metrica.id)
        .join(models.Dispositivo, models.Metrica.dispositivo_id == models.Dispositivo.id)
        .join(models.Proveedor, models.Dispositivo.proveedor_id == models.Proveedor.id)
        .filter(models.Proveedor.usuario_id == usuario_actual.id)
        .order_by(models.Medicion.fecha_medicion.desc())
        .all()
    )

    entries = []
    for medicion, metrica, dispositivo, proveedor in resultados:
        key = metrica.nombre.lower()
        loinc_info = LOINC_CODES.get(key, {
            "code": "82810-3",
            "display": metrica.nombre,
            "ucum": metrica.unidad or ""
        })

        obs_resource = {
            "resourceType": "Observation",
            "id": str(medicion.id),
            "status": "final",
            "category": [
                {
                    "coding": [
                        {
                            "system": "http://terminology.hl7.org/CodeSystem/observation-category",
                            "code": "vital-signs",
                            "display": "Vital Signs"
                        }
                    ]
                }
            ],
            "code": {
                "coding": [
                    {
                        "system": "http://loinc.org",
                        "code": loinc_info["code"],
                        "display": loinc_info["display"]
                    }
                ],
                "text": loinc_info["display"]
            },
            "subject": {
                "reference": f"Patient/{usuario_actual.id}"
            },
            "effectiveDateTime": medicion.fecha_medicion.isoformat(),
            "valueQuantity": {
                "value": medicion.valor,
                "unit": metrica.unidad or "",
                "system": "http://unitsofmeasure.org",
                "code": loinc_info["ucum"]
            },
            "device": {
                "reference": f"Device/{dispositivo.id}"
            }
        }
        entries.append({
            "fullUrl": f"/fhir/Observation/{medicion.id}",
            "resource": obs_resource
        })

    return {
        "resourceType": "Bundle",
        "type": "searchset",
        "total": len(entries),
        "entry": entries
    }


@app.post("/dispositivos/custom")
def registrar_dispositivo_custom(
    payload: dict,
    usuario_actual: models.Usuario = Depends(obtener_usuario_actual),
    db: Session = Depends(get_db)
):
    resource_type = payload.get("resourceType")
    
    device_name = None
    external_id = None
    is_active = True
    
    if resource_type == "Device":
        device_name = payload.get("modelNumber")
        if not device_name:
            device_names = payload.get("deviceName", [])
            if device_names and isinstance(device_names, list):
                device_name = device_names[0].get("name")
        if not device_name:
            device_name = "FHIR Device"
            
        identifiers = payload.get("identifier", [])
        if identifiers and isinstance(identifiers, list):
            external_id = identifiers[0].get("value")
            
        status = payload.get("status")
        is_active = (status == "active")
    else:
        device_name = payload.get("name") or payload.get("nombre")
        external_id = payload.get("external_id") or payload.get("identificador_externo")
        is_active = payload.get("active", payload.get("activo", True))
        
    if not device_name:
        raise HTTPException(
            status_code=400,
            detail="Device name is required (modelNumber/deviceName in FHIR, or name/nombre in plain JSON)"
        )
        
    proveedor = db.query(models.Proveedor).filter(
        models.Proveedor.usuario_id == usuario_actual.id,
        models.Proveedor.nombre == "custom"
    ).first()
    
    if not proveedor:
        proveedor = models.Proveedor(
            usuario_id=usuario_actual.id,
            nombre="custom",
            activo=True
        )
        db.add(proveedor)
        db.flush()
        
    dispositivo_existente = None
    if external_id:
        dispositivo_existente = db.query(models.Dispositivo).filter(
            models.Dispositivo.proveedor_id == proveedor.id,
            models.Dispositivo.identificador_externo == str(external_id)
        ).first()
        
    if dispositivo_existente:
        dispositivo_existente.nombre = device_name
        dispositivo_existente.activo = is_active
        db.commit()
        return {
            "status": "ok",
            "message": "Custom device updated successfully",
            "device": {
                "id": dispositivo_existente.id,
                "name": dispositivo_existente.nombre,
                "external_id": dispositivo_existente.identificador_externo,
                "active": dispositivo_existente.activo
            }
        }
    else:
        nuevo_dispositivo = models.Dispositivo(
            proveedor_id=proveedor.id,
            nombre=device_name,
            identificador_externo=str(external_id) if external_id else None,
            activo=is_active
        )
        db.add(nuevo_dispositivo)
        db.commit()
        db.refresh(nuevo_dispositivo)
        return {
            "status": "ok",
            "message": "Custom device registered successfully",
            "device": {
                "id": nuevo_dispositivo.id,
                "name": nuevo_dispositivo.nombre,
                "external_id": nuevo_dispositivo.identificador_externo,
                "active": nuevo_dispositivo.activo
            }
        }
