import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from sqlalchemy import text
from PIL import Image, ImageFile
import base64
import io
import uuid

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Guía Comercial Almenar", layout="wide", page_icon="🚀")

# --- CONEXIÓN A NEON (POSTGRESQL) ---
try:
    # Verificar si existe la configuración de conexión
    if "postgresql" not in st.secrets:
        st.error("""
        ERROR DE CONFIGURACION: No se encontró la configuración de la base de datos.
        
        Por favor, asegúrate de haber configurado los secretos en Streamlit Cloud:
        
        1. Ve a tu app en Streamlit Cloud
        2. Haz clic en "Settings" -> "Secrets"
        3. Agrega la siguiente configuración:
        
        [connections.postgresql]
        dialect = "postgresql"
        host = "tu-host.neon.tech"
        port = "5432"
        database = "tu-base-de-datos"
        username = "tu-usuario"
        password = "tu-contraseña"
        
        O usa una URL directa:
        DATABASE_URL = "postgresql://usuario:contraseña@tu-host.neon.tech/tu-base-de-datos?sslmode=require"
        """)
        st.stop()
    
    # Intentar conectar
    conn = st.connection("postgresql", type="sql")
    
    # Probar la conexión
    test_query = conn.query("SELECT 1 as test", ttl=0)
    if test_query.empty:
        st.error("No se pudo verificar la conexión a la base de datos")
        st.stop()
        
except Exception as e:
    st.error(f"""
    ERROR DE CONEXION A LA BASE DE DATOS
    
    Detalles: {str(e)}
    
    Posibles soluciones:
    1. Verifica que los secretos estén correctamente configurados en Streamlit Cloud
    2. Asegúrate de que la base de datos en Neon esté activa
    3. Verifica que las credenciales sean correctas
    4. Comprueba que la IP de Streamlit Cloud esté permitida en Neon
    
    Para más ayuda, contacta al administrador.
    """)
    st.stop()

# --- CATEGORÍAS DEFINIDAS ---
CAT_LIST = [
    "Salud", "Laboratorios", "Opticas", "Farmacias", "Dulcerias",
    "Comida Rapida", "Panaderias", "Charcuterias", "Carnicerias",
    "Ferreterias", "Zapaterias", "Electrodomesticos", "Fibras Opticas",
    "Taxis", "Mototaxis", "Servicios", "Entes Publicos", "Otros"
]

# --- CREACIÓN DE TABLAS ---
try:
    with conn.session as s:
        # Verificar si la tabla comercios existe, si no, crearla
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS comercios (
            id SERIAL PRIMARY KEY,
            nombre VARCHAR(255),
            categoria VARCHAR(100),
            ubicacion TEXT,
            foto_url TEXT,
            reseña_willian TEXT,
            estrellas_w INTEGER,
            maps_url TEXT,
            visitas INTEGER DEFAULT 0
        )
        """))
        
        # Asegurar que todas las columnas existan (por si acaso)
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS nombre VARCHAR(255)"))
        except Exception:
            pass  # La columna ya existe
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS categoria VARCHAR(100)"))
        except Exception:
            pass
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS ubicacion TEXT"))
        except Exception:
            pass
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS foto_url TEXT"))
        except Exception:
            pass
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS reseña_willian TEXT"))
        except Exception:
            pass
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS estrellas_w INTEGER"))
        except Exception:
            pass
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS maps_url TEXT"))
        except Exception:
            pass
        try:
            s.execute(text("ALTER TABLE comercios ADD COLUMN IF NOT EXISTS visitas INTEGER DEFAULT 0"))
        except Exception:
            pass
        
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS fotos_comercios (
            id SERIAL PRIMARY KEY,
            comercio_id INTEGER,
            foto_data TEXT
        )
        """))
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS opiniones (
            id SERIAL PRIMARY KEY,
            comercio_id INTEGER,
            usuario VARCHAR(100),
            comentario TEXT,
            estrellas_u INTEGER,
            fecha VARCHAR(50)
        )
        """))
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS visitas (
            id INTEGER PRIMARY KEY,
            conteo INTEGER
        )
        """))
        s.execute(text("""
        CREATE TABLE IF NOT EXISTS denuncias (
            id SERIAL PRIMARY KEY,
            denunciante VARCHAR(255),
            comercio_afectado VARCHAR(255),
            motivo TEXT,
            fecha VARCHAR(50),
            estatus VARCHAR(50) DEFAULT 'Pendiente'
        )
        """))
        s.execute(text("CREATE TABLE IF NOT EXISTS configuracion (id INTEGER PRIMARY KEY, logo_data TEXT)"))
        
        res_v = s.execute(text("SELECT conteo FROM visitas WHERE id = 1")).fetchone()
        if not res_v:
            s.execute(text("INSERT INTO visitas (id, conteo) VALUES (1, 0)"))
        s.commit()
except Exception as e:
    st.error(f"ERROR al crear las tablas en la base de datos: {str(e)}")
    st.info("Por favor, verifica que la base de datos esté correctamente configurada y tengas permisos para crear tablas.")
    st.stop()

# --- LÓGICA DE VISITAS GENERALES ---
if 'visitado' not in st.session_state:
    try:
        with conn.session as s:
            s.execute(text("UPDATE visitas SET conteo = conteo + 1 WHERE id = 1"))
            s.commit()
        st.session_state.visitado = True
    except Exception as e:
        st.warning(f"Error al actualizar contador de visitas: {e}")

try:
    res_visitas = conn.query("SELECT conteo FROM visitas WHERE id = 1", ttl=0)
    total_visitas = res_visitas.iloc[0,0] if not res_visitas.empty else 0
except Exception as e:
    total_visitas = 0
    st.warning("No se pudo cargar el contador de visitas")

# --- FUNCIÓN DE IMAGEN OPTIMIZADA (MINIATURAS) ---
def imagen_a_base64(uploaded_file):
    if uploaded_file is not None:
        try:
            # Agregar límite de tamaño (5MB)
            if hasattr(uploaded_file, 'size') and uploaded_file.size > 5 * 1024 * 1024:
                st.error("La imagen es muy grande (máximo 5MB)")
                return None
            
            img = Image.open(uploaded_file)
            if img.mode in ("RGBA", "P"):
                img = img.convert("RGB")
            max_size = (800, 800) 
            # Corrección para compatibilidad con versiones de Pillow
            try:
                img.thumbnail(max_size, Image.LANCZOS)
            except AttributeError:
                img.thumbnail(max_size, Image.ANTIALIAS)
            buffer = io.BytesIO()
            img.save(buffer, format="JPEG", quality=70, optimize=True)
            bytes_data = buffer.getvalue()
            return f"data:image/jpeg;base64,{base64.b64encode(bytes_data).decode()}"
        except Exception as e:
            st.error(f"Error al procesar la imagen: {e}")
            return None
    return None

# --- ESTILO VENEZUELA ---
st.markdown("""
<style>
#MainMenu {display: none !important;}
footer {display: none !important;}
.stDeployButton {display: none !important;}
header {display: none !important;}
[data-testid="stToolbar"] {display: none !important;}
[data-testid="stDecoration"] {display: none !important;}
[data-testid="stStatusWidget"] {display: none !important;}
#manage-your-app-button {display: none !important;}
.viewerBadge_container__1QSob {display: none !important;}
.stAppDeployButton {display: none !important;}
[data-testid="stConnectionStatus"] {display: none !important;}

.stApp { background-color: #111827; color: #ffffff; }
p, span, label, .stMarkdown { color: #ffffff !important; font-weight: 500; }

[data-testid="stSidebar"] { background-color: #1f2937; border-right: 2px solid #ffcc00; }
[data-testid="stSidebar"] p, [data-testid="stSidebar"] span { color: #ffffff !important; font-weight: bold; }

button[data-baseweb="tab"] p { color: #ffffff !important; font-size: 1.1em !important; font-weight: bold !important; }
button[aria-selected="true"] p { color: #ffcc00 !important; }

.venezuela-header {
    text-align: center;
    padding: 60px 10px 40px 10px;
    background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
    border-radius: 100% 100% 25px 25px / 120% 120% 25px 25px;
    margin-bottom: 30px;
    box-shadow: 0px 10px 20px rgba(0,0,0,0.6);
    border: 1px solid rgba(255,255,255,0.1);
}

.logo-main-container {
    display: flex;
    justify-content: center;
    margin-bottom: 20px;
}

.logo-main-container img {
    mix-blend-mode: multiply;
    filter: contrast(120%) brightness(110%);
    background-color: transparent !important;
}

.logo-container {
    text-align: center;
    margin-bottom: 20px;
}

.logo-container img {
    mix-blend-mode: multiply;
    filter: contrast(110%) brightness(110%);
}

.stars-arc { color: white; font-size: 1.2em; letter-spacing: 5px; font-weight: bold; text-shadow: 2px 2px 4px #000; margin-top: -10px; }

.ven-share-card {
    background: linear-gradient(to bottom, #ffcc00 33%, #0033a0 33%, #0033a0 66%, #ce1126 66%);
    padding: 20px;
    border-radius: 15px;
    text-align: center;
    border: 2px solid #ffffff;
    box-shadow: 0px 5px 15px rgba(0,0,0,0.5);
    margin-bottom: 10px;
}
.ven-share-text { color: white !important; font-weight: bold; text-shadow: 2px 2px 4px #000; text-decoration: none; font-size: 1.1em; }

input, textarea, [data-baseweb="select"] { background-color: #ffffff !important; color: #000000 !important; font-weight: bold !important; }

.stats-panel { background: rgba(31, 41, 55, 0.9); padding: 15px; border-radius: 20px; border: 2px solid #ffcc00; text-align: center; margin-bottom: 20px; }
.holiday-panel { background: linear-gradient(135deg, #0033a0, #001a50); padding: 10px; border-radius: 10px; border-left: 5px solid #ffcc00; margin-bottom: 20px; }
.footer-willian { background: #000; padding: 30px; text-align: center; border-top: 4px solid #ffcc00; margin-top: 50px; }
.master-panel { background-color: #0033a0; border: 3px solid #ffcc00; padding: 20px; border-radius: 15px; }

.stExpander { border: 1px solid #ffcc00 !important; background-color: #1f2937 !important; }

.bronze-plaque {
    background: linear-gradient(145deg, #8c6a31, #5d431a);
    border: 5px solid #d4af37;
    padding: 50px 20px;
    border-radius: 15px;
    text-align: center;
    box-shadow: inset 2px 2px 8px rgba(255,255,255,0.3), 10px 10px 25px rgba(0,0,0,0.7);
    margin: 50px auto;
    max-width: 1000px;
    position: relative;
    overflow: hidden;
}
.bronze-text { color: #ffd700 !important; font-family: 'Times New Roman', serif; font-weight: bold; text-shadow: 2px 2px 4px rgba(0,0,0,0.9); }
.screw { position: absolute; width: 18px; height: 18px; background: radial-gradient(circle at 30% 30%, #999, #333); border-radius: 50%; box-shadow: 2px 2px 4px rgba(0,0,0,0.5); }
.screw::after { content: ''; position: absolute; top: 50%; left: 10%; width: 80%; height: 2px; background: #111; transform: translateY(-50%) rotate(45deg); }
.screw-tl { top: 15px; left: 15px; } .screw-tr { top: 15px; right: 15px; } .screw-bl { bottom: 15px; left: 15px; } .screw-br { bottom: 15px; right: 15px; }
</style>
""", unsafe_allow_html=True)

# --- PANEL LATERAL ---
with st.sidebar:
    try:
        logo_res = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
        if not logo_res.empty and logo_res.iloc[0,0]:
            st.markdown(f'<div class="logo-container"><img src="{logo_res.iloc[0,0]}" style="width:220px;"></div>', unsafe_allow_html=True)
    except Exception as e:
        st.warning("Logo no disponible temporalmente")
    st.title("Venezuela Gestion")
    opcion_menu = st.radio("Ir a:", ["Ver Guia Comercial", "Administracion"])
    st.markdown("---")
    st.info("Desarrollado por Willian Almenar")

# --- ENCABEZADO ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★ ★ ★ ★ ★ ★ ★ ★</div></div>', unsafe_allow_html=True)

# --- LOGO CENTRADO ---
try:
    logo_res_main = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
    if not logo_res_main.empty and logo_res_main.iloc[0,0]:
        st.markdown(f'<div class="logo-main-container"><img src="{logo_res_main.iloc[0,0]}" style="width:350px;"></div>', unsafe_allow_html=True)
except Exception as e:
    st.warning("Logo no disponible temporalmente")

# --- LÓGICA TEMPORAL ---
ahora_vzla = datetime.utcnow() - timedelta(hours=4)
dias_semana = ["Lunes", "Martes", "Miercoles", "Jueves", "Viernes", "Sabado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

festivos_2026 = [
    (datetime(2026, 1, 1), "Año Nuevo"), (datetime(2026, 2, 16), "Lunes de Carnaval"),
    (datetime(2026, 2, 17), "Martes de Carnaval"), (datetime(2026, 3, 19), "Dia de San Jose"),
    (datetime(2026, 4, 2), "Jueves Santo"), (datetime(2026, 4, 3), "Viernes Santo"),
    (datetime(2026, 4, 19), "Declaracion de la Independencia"), (datetime(2026, 5, 1), "Dia del Trabajador"),
    (datetime(2026, 6, 24), "Batalla de Carabobo"), (datetime(2026, 7, 5), "Dia de la Independencia"),
    (datetime(2026, 7, 24), "Natalicio de Simon Bolivar"), (datetime(2026, 10, 12), "Dia de la Resistencia Indigena"),
    (datetime(2026, 12, 24), "Vispera de Navidad"), (datetime(2026, 12, 25), "Natividad del Señor"),
    (datetime(2026, 12, 31), "Fin de Año")
]

proximo_festivo = "No hay mas festivos este año"
for fecha, nombre in festivos_2026:
    if fecha.date() >= ahora_vzla.date():
        proximo_festivo = f"{nombre} ({fecha.strftime('%d/%m')})"
        break

st.markdown(f'''
<div class="stats-panel">
<span style="color:#ffcc00; font-size:1.1em; font-weight:bold;">{dias_semana[ahora_vzla.weekday()]}, {ahora_vzla.day} de {meses[ahora_vzla.month-1]} de {ahora_vzla.year}
</span><br>
<b style="color:#ffffff; font-size:1.4em;">{ahora_vzla.strftime("%I:%M %p")}</b><br>
<span style="font-size:1.2em; border-top: 1px solid #444; padding-top:5px; display:block; margin-top:5px; color:#ffffff !important;">VISITAS TOTALES: {total_visitas}</span>
</div>
''', unsafe_allow_html=True)

# --- LÓGICA DE MENÚ ---
if opcion_menu == "Administracion":
    clave = st.text_input("Clave de Acceso:", type="password")
    if clave == "Juan*316*":
        st.success("Acceso Maestro Concedido")
        tab1, tab2, tab3_v = st.tabs(["Gestion de Negocios", "Logo App", "Estadisticas Detalladas"])
        
        with tab1:
            st.info("Utilice el Panel de Control Maestro al final de la pagina para agregar/editar.")
            
        with tab3_v:
            st.write("### Visitas por Comercio")
            try:
                stats_df = conn.query("SELECT nombre, categoria, visitas FROM comercios ORDER BY visitas DESC", ttl=0)
                if not stats_df.empty:
                    st.table(stats_df)
                else:
                    st.info("No hay datos de visitas disponibles")
            except Exception as e:
                st.error(f"Error al cargar estadisticas: {e}")

elif opcion_menu == "Ver Guia Comercial":
    st.title("Guia Comercial Almenar")
    st.markdown(f'''
    <div class="holiday-panel">
        <span style="color:#ffcc00; font-weight:bold;">EFEMERIDES VENEZUELA 2026:</span><br>
        <span style="color:white;">Proximo dia feriado: <b>{proximo_festivo}</b></span>
    </div>
    ''', unsafe_allow_html=True)
    
    # Usar URL dinámica o la hardcodeada - Enlace para visitantes (sin administración)
    try:
        # Este enlace lleva a la app como visitante normal
        link_app = "https://guia-comercial-almenar-cpe3yfntxmzncn2e7wgueh.streamlit.app/?embed=true"
    except:
        link_app = "https://guia-comercial-almenar-cpe3yfntxmzncn2e7wgueh.streamlit.app/?embed=true"
    
    whatsapp_url = f"https://api.whatsapp.com/send?text=Mira la Guia Comercial de Santa Teresa! {link_app}"
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(f'<a href="{whatsapp_url}" target="_blank" style="text-decoration:none;"><div class="ven-share-card"><span class="ven-share-text">Compartir por WhatsApp</span></div></a>', unsafe_allow_html=True)
    with col_s2:
        st.markdown(f'<div class="ven-share-card"><span class="ven-share-text">Enlace Directo:</span><br><b style="color:#ffcc00; font-size:0.9em;">{link_app}</b></div>', unsafe_allow_html=True)

    st.markdown("---")
    busq = st.text_input("Que buscas en Santa Teresa?", placeholder="Ej: Panaderia, Farmacia...")
    tab_labels = ["Todos"] + CAT_LIST
    tabs_main = st.tabs(tab_labels)
    try:
        df = conn.query("SELECT * FROM comercios", ttl=0)
    except Exception as e:
        st.error(f"Error al cargar comercios: {e}")
        df = pd.DataFrame()
    
    try:
        todas_opiniones = conn.query("SELECT * FROM opiniones ORDER BY id DESC", ttl=0)
    except Exception as e:
        st.error(f"Error al cargar opiniones: {e}")
        todas_opiniones = pd.DataFrame()
    
    try:
        todas_fotos = conn.query("SELECT * FROM fotos_comercios", ttl=0)
    except Exception as e:
        st.error(f"Error al cargar fotos: {e}")
        todas_fotos = pd.DataFrame()

    # Inicializar un contador único para formularios
    if 'form_counter' not in st.session_state:
        st.session_state.form_counter = 0

    for i, tab in enumerate(tabs_main):
        with tab:
            categoria_seleccionada = tab_labels[i]
            if not df.empty:
                filtrado = df[df['nombre'].str.contains(busq, case=False) | df['categoria'].str.contains(busq, case=False)]
                if categoria_seleccionada != "Todos":
                    filtrado = filtrado[filtrado['categoria'] == categoria_seleccionada]
                
                if filtrado.empty:
                    st.warning(f"No hay comercios registrados en {categoria_seleccionada}." if categoria_seleccionada != "Todos" else "No se encontraron resultados.")
                else:
                    for idx, r in filtrado.iterrows():
                        expander_titulo = f"{r['nombre']} - {r['categoria']}"
                        with st.expander(expander_titulo):
                            visit_key = f"visited_{r['id']}"
                            if visit_key not in st.session_state:
                                try:
                                    with conn.session as s:
                                        s.execute(text("UPDATE comercios SET visitas = visitas + 1 WHERE id = :id"), {"id": int(r['id'])})
                                        s.commit()
                                    st.session_state[visit_key] = True
                                except Exception as e:
                                    st.error(f"Error al registrar visita: {e}")

                            col_img, col_info = st.columns([1, 2])
                            with col_img:
                                if isinstance(r['foto_url'], str) and (r['foto_url'].startswith('http') or r['foto_url'].startswith('data:image')):
                                    st.image(r['foto_url'], use_container_width=True, caption="Foto Principal")
                                
                                extras = todas_fotos[todas_fotos['comercio_id'] == r['id']]
                                if not extras.empty:
                                    for _, f_row in extras.iterrows():
                                        try:
                                            st.image(f_row['foto_data'], use_container_width=True)
                                        except Exception as e:
                                            st.error(f"Error al cargar imagen adicional: {e}")

                            with col_info:
                                st.write(f"**Ubicacion:** {r['ubicacion']}")
                                if r['maps_url']:
                                    st.link_button("IR A ESTA UBICACION (Google Maps)", r['maps_url'], type="primary", use_container_width=True)
                                # Corrección para manejar valores nulos en estrellas
                                try:
                                    estrellas_w_val = int(r['estrellas_w']) if r['estrellas_w'] is not None and str(r['estrellas_w']).isdigit() else 0
                                    st.write(f"**Calificacion Willian:** {'*' * estrellas_w_val}")
                                except:
                                    st.write(f"**Calificacion Willian:** " + "*" * 0)
                                st.info(f"**Reseña de Willian:** {r['reseña_willian']}")
                                st.markdown("---")
                                if not todas_opiniones.empty:
                                    op_df = todas_opiniones[todas_opiniones['comercio_id'] == r['id']]
                                    for _, op in op_df.iterrows():
                                        try:
                                            estrellas_u_val = int(op['estrellas_u']) if op['estrellas_u'] is not None and str(op['estrellas_u']).isdigit() else 0
                                            st.markdown(f"<div style='border-bottom: 1px solid #444; padding: 5px;'><b>{op['usuario']}</b>: {op['comentario']} ({'*'*estrellas_u_val})</div>", unsafe_allow_html=True)
                                        except:
                                            st.markdown(f"<div style='border-bottom: 1px solid #444; padding: 5px;'><b>{op['usuario']}</b>: {op['comentario']}</div>", unsafe_allow_html=True)

                            # --- FORMULARIO DE OPINIÓN DEL USUARIO ---
                            st.markdown("##### Deja tu opinion")
                            # Generar una key única usando uuid para garantizar unicidad
                            unique_id = str(uuid.uuid4()).replace('-', '')[:8]
                            form_key = f"opinion_form_{r['id']}_{idx}_{i}_{unique_id}"
                            with st.form(key=form_key):
                                op_usuario = st.text_input("Tu nombre", key=f"op_user_{r['id']}_{idx}_{i}_{unique_id}")
                                op_comentario = st.text_area("Comentario", key=f"op_com_{r['id']}_{idx}_{i}_{unique_id}")
                                op_estrellas = st.slider("Tu calificacion", 1, 5, 5, key=f"op_est_{r['id']}_{idx}_{i}_{unique_id}")
                                if st.form_submit_button("Enviar opinion"):
                                    if op_usuario.strip() and op_comentario.strip():
                                        fecha_op = ahora_vzla.strftime("%d/%m/%Y")
                                        try:
                                            with conn.session as s:
                                                s.execute(text(
                                                    "INSERT INTO opiniones (comercio_id, usuario, comentario, estrellas_u, fecha) "
                                                    "VALUES (:cid, :u, :c, :e, :f)"
                                                ), {"cid": int(r['id']), "u": op_usuario.strip(), "c": op_comentario.strip(), "e": op_estrellas, "f": fecha_op})
                                                s.commit()
                                            st.success("Opinion enviada! Gracias.")
                                            st.rerun()
                                        except Exception as e:
                                            st.error(f"Error al guardar opinion: {e}")
                                    else:
                                        st.warning("Escribe tu nombre y comentario antes de enviar.")

# --- PANEL DE ADMINISTRADOR MAESTRO ---
st.markdown("---")
with st.expander("PANEL DE CONTROL MAESTRO (Acceso Restringido)"):
    master_key = st.text_input("Ingrese Contraseña Maestra:", type="password", key="master_pass")
    if master_key == "Juan*316*":
        st.markdown('<div class="master-panel">', unsafe_allow_html=True)
        m_tab1, m_tab2, m_tab3, m_tab4, m_tab_config = st.tabs(["Denuncias", "Agregar Comercio", "Modificar/Eliminar", "Opiniones", "Configurar App"])

        # --- TAB 1: DENUNCIAS ---
        with m_tab1:
            st.write("### Gestion de Denuncias")
            try:
                den_df = conn.query("SELECT * FROM denuncias ORDER BY id DESC", ttl=0)
                if not den_df.empty:
                    st.dataframe(den_df[['id','denunciante','comercio_afectado','motivo','fecha','estatus']], use_container_width=True)
                    st.markdown("**Cambiar estatus de una denuncia:**")
                    den_ids = den_df['id'].tolist()
                    sel_den_id = st.selectbox("Selecciona ID de denuncia", den_ids, key="sel_den")
                    nuevo_estatus = st.selectbox("Nuevo estatus", ["Pendiente", "En revision", "Resuelta", "Descartada"], key="nuevo_est_den")
                    if st.button("Actualizar estatus", key="btn_den_upd"):
                        try:
                            with conn.session as s:
                                s.execute(text("UPDATE denuncias SET estatus=:e WHERE id=:id"), {"e": nuevo_estatus, "id": int(sel_den_id)})
                                s.commit()
                            st.success("Estatus actualizado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al actualizar: {e}")
                    if st.button("Eliminar denuncia seleccionada", key="btn_den_del", type="secondary"):
                        try:
                            with conn.session as s:
                                s.execute(text("DELETE FROM denuncias WHERE id=:id"), {"id": int(sel_den_id)})
                                s.commit()
                            st.success("Denuncia eliminada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar: {e}")
                else:
                    st.info("No hay denuncias registradas aun.")
            except Exception as e:
                st.error(f"Error al cargar denuncias: {e}")
            
            st.markdown("---")
            st.write("### Registrar nueva denuncia")
            with st.form("form_denuncia"):
                den_nombre = st.text_input("Tu nombre")
                den_comercio = st.text_input("Comercio afectado")
                den_motivo = st.text_area("Motivo de la denuncia")
                if st.form_submit_button("Enviar denuncia"):
                    if den_nombre.strip() and den_comercio.strip() and den_motivo.strip():
                        try:
                            with conn.session as s:
                                s.execute(text(
                                    "INSERT INTO denuncias (denunciante, comercio_afectado, motivo, fecha) VALUES (:d, :c, :m, :f)"
                                ), {"d": den_nombre.strip(), "c": den_comercio.strip(), "m": den_motivo.strip(), "f": ahora_vzla.strftime("%d/%m/%Y")})
                                s.commit()
                            st.success("Denuncia registrada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al registrar denuncia: {e}")
                    else:
                        st.error("Completa todos los campos.")

        # --- TAB 2: AGREGAR COMERCIO ---
        with m_tab2:
            st.write("### Registrar Nuevo Comercio")
            with st.form("master_add_form"):
                add_n = st.text_input("Nombre del Negocio")
                add_cat = st.selectbox("Categoria", CAT_LIST, key="add_cat_m")
                add_ub = st.text_input("Ubicacion exacta")
                add_maps = st.text_input("Enlace Google Maps (URL)")
                add_res = st.text_area("Reseña de Willian")
                add_est = st.slider("Calificacion (Estrellas)", 1, 5, 5)
                add_fotos = st.file_uploader("Subir Imagenes", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
                
                if st.form_submit_button("Registrar Comercio"):
                    if add_n:
                        try:
                            with conn.session as s:
                                p_img = imagen_a_base64(add_fotos[0]) if add_fotos else None
                                # Verificar que la columna ubicacion existe antes de insertar
                                res_ins = s.execute(text("""
                                    INSERT INTO comercios (nombre, categoria, ubicacion, reseña_willian, estrellas_w, foto_url, maps_url, visitas) 
                                    VALUES (:n, :c, :u, :r, :e, :f, :m, 0) RETURNING id
                                """), {"n": add_n, "c": add_cat, "u": add_ub, "r": add_res, "e": add_est, "f": p_img, "m": add_maps})
                                
                                row = res_ins.fetchone()
                                new_id = row[0] if row else None
                                
                                if new_id and add_fotos and len(add_fotos) > 1:
                                    for extra in add_fotos[1:]:
                                        s.execute(text("INSERT INTO fotos_comercios (comercio_id, foto_data) VALUES (:cid, :fd)"),
                                                  {"cid": new_id, "fd": imagen_a_base64(extra)})
                                s.commit()
                            
                            st.write("Confirmando guardado en la nube...")
                            verificacion = conn.query("SELECT COUNT(*) FROM comercios", ttl=0)
                            st.write(f"Total de comercios actuales en la base de datos: {verificacion.iloc[0,0]}")
                            
                            st.success("Negocio y fotos añadidos con exito.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al registrar comercio: {e}")
                            # Mostrar más detalles del error para depuración
                            st.exception(e)
                    else:
                        st.error("El nombre del negocio es obligatorio.")

        # --- TAB 3: MODIFICAR / ELIMINAR ---
        with m_tab3:
            try:
                comercios_master = conn.query("SELECT * FROM comercios", ttl=0)
                if not comercios_master.empty:
                    opcion_edit = st.selectbox("Seleccione Comercio para gestionar:", comercios_master['nombre'].tolist())
                    target = comercios_master[comercios_master['nombre'] == opcion_edit].iloc[0]
                    
                    v_count = target.get('visitas', 0) or 0
                    st.write(f"**Visitas registradas para este local:** {v_count}")
                    
                    with st.form("master_edit_form"):
                        new_n = st.text_input("Nombre", value=target['nombre'] if target['nombre'] else "")
                        cat_idx = CAT_LIST.index(target['categoria']) if target['categoria'] in CAT_LIST else 0
                        new_cat = st.selectbox("Categoria", CAT_LIST, index=cat_idx)
                        new_ub = st.text_input("Ubicacion", value=target['ubicacion'] if target['ubicacion'] else "")
                        new_maps = st.text_input("Google Maps URL", value=target['maps_url'] if target['maps_url'] else "")
                        estrellas_actual = int(target['estrellas_w']) if target['estrellas_w'] is not None else 3
                        new_est = st.slider("Estrellas Willian", 1, 5, estrellas_actual)
                        new_res_text = st.text_area("Reseña de Willian", value=target['reseña_willian'] if target['reseña_willian'] else "")
                        new_fotos = st.file_uploader("Agregar mas fotos", type=["png", "jpg", "jpeg"], accept_multiple_files=True)
                        if st.form_submit_button("GUARDAR CAMBIOS"):
                            try:
                                with conn.session as s:
                                    s.execute(text("UPDATE comercios SET nombre=:n, categoria=:c, ubicacion=:u, reseña_willian=:r, estrellas_w=:e, maps_url=:m WHERE id=:id"),
                                            {"n": new_n, "c": new_cat, "u": new_ub, "r": new_res_text, "e": new_est, "m": new_maps, "id": int(target['id'])})
                                    if new_fotos:
                                        for f in new_fotos:
                                            s.execute(text("INSERT INTO fotos_comercios (comercio_id, foto_data) VALUES (:cid, :fd)"),
                                                      {"cid": int(target['id']), "fd": imagen_a_base64(f)})
                                    s.commit()
                                st.success("Actualizado correctamente.")
                                st.rerun()
                            except Exception as e:
                                st.error(f"Error al actualizar: {e}")

                    st.markdown("---")
                    st.warning(f"Seguro que deseas eliminar {opcion_edit}? Esta accion no se puede deshacer.")
                    if st.button("ELIMINAR COMERCIO", type="secondary", key="btn_eliminar"):
                        try:
                            with conn.session as s:
                                s.execute(text("DELETE FROM fotos_comercios WHERE comercio_id=:id"), {"id": int(target['id'])})
                                s.execute(text("DELETE FROM opiniones WHERE comercio_id=:id"), {"id": int(target['id'])})
                                s.execute(text("DELETE FROM comercios WHERE id=:id"), {"id": int(target['id'])})
                                s.commit()
                            st.success("Comercio eliminado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar: {e}")
                else:
                    st.info("No hay comercios registrados todavia.")
            except Exception as e:
                st.error(f"Error al cargar comercios: {e}")

        # --- TAB 4: OPINIONES ---
        with m_tab4:
            st.write("### Gestion de Opiniones de Usuarios")
            try:
                op_all = conn.query("""
                    SELECT o.id, c.nombre AS comercio, o.usuario, o.comentario, o.estrellas_u, o.fecha
                    FROM opiniones o
                    LEFT JOIN comercios c ON o.comercio_id = c.id
                    ORDER BY o.id DESC
                """, ttl=0)
                if not op_all.empty:
                    st.dataframe(op_all, use_container_width=True)
                    st.markdown("**Eliminar una opinion:**")
                    op_ids = op_all['id'].tolist()
                    sel_op_id = st.selectbox("Selecciona ID de opinion a eliminar", op_ids, key="sel_op_del")
                    fila_op = op_all[op_all['id'] == sel_op_id].iloc[0]
                    st.info(f"{fila_op['usuario']} sobre {fila_op['comercio']}: {fila_op['comentario']}")
                    if st.button("Eliminar esta opinion", type="secondary", key="btn_op_del"):
                        try:
                            with conn.session as s:
                                s.execute(text("DELETE FROM opiniones WHERE id=:id"), {"id": int(sel_op_id)})
                                s.commit()
                            st.success("Opinion eliminada.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar opinion: {e}")
                else:
                    st.info("No hay opiniones registradas todavia.")
            except Exception as e:
                st.error(f"Error al cargar opiniones: {e}")

        # --- TAB CONFIG: LOGO ---
        with m_tab_config:
            st.write("### Configurar Logo de la App")
            try:
                logo_actual = conn.query("SELECT logo_data FROM configuracion WHERE id = 1", ttl=0)
                if not logo_actual.empty and logo_actual.iloc[0,0]:
                    st.markdown("**Logo actual:**")
                    st.markdown(f'<img src="{logo_actual.iloc[0,0]}" style="width:200px; border:2px solid #ffcc00; border-radius:10px;">', unsafe_allow_html=True)
                    if st.button("Eliminar logo actual", type="secondary", key="btn_del_logo"):
                        try:
                            with conn.session as s:
                                s.execute(text("UPDATE configuracion SET logo_data=NULL WHERE id=1"))
                                s.commit()
                            st.success("Logo eliminado.")
                            st.rerun()
                        except Exception as e:
                            st.error(f"Error al eliminar logo: {e}")
                else:
                    st.info("No hay logo cargado actualmente.")
            except Exception as e:
                st.error(f"Error al cargar logo: {e}")
            
            st.markdown("---")
            nuevo_logo = st.file_uploader("Subir nuevo logo", type=["png", "jpg", "jpeg"], key="logo_uploader")
            if nuevo_logo and st.button("Guardar logo", key="btn_save_logo"):
                logo_b64 = imagen_a_base64(nuevo_logo)
                if logo_b64:
                    try:
                        with conn.session as s:
                            existe = s.execute(text("SELECT id FROM configuracion WHERE id=1")).fetchone()
                            if existe:
                                s.execute(text("UPDATE configuracion SET logo_data=:l WHERE id=1"), {"l": logo_b64})
                            else:
                                s.execute(text("INSERT INTO configuracion (id, logo_data) VALUES (1, :l)"), {"l": logo_b64})
                            s.commit()
                        st.success("Logo guardado correctamente.")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error al guardar logo: {e}")

        st.markdown('</div>', unsafe_allow_html=True)

# --- PIE DE PÁGINA ---
st.markdown("""
<div class='footer-willian'>
    <p style='color: #ffcc00 !important; font-size: 1.2em; font-weight: bold; margin-bottom: 10px;'>
        UNETE A NOSOTROS Y QUE TU NEGOCIO FORME PARTE DE ESTA GUIA COMERCIAL!
    </p>
    <p style='color: #ffffff !important; font-size: 1.1em;'>
        Contactanos por el 04242004015 (Solo WhatsApp)
    </p>
</div>
""", unsafe_allow_html=True)

# --- PLACA DE BRONCE ---
st.markdown("""
<div class="bronze-plaque">
    <div class="screw screw-tl"></div><div class="screw screw-tr"></div><div class="screw screw-bl"></div><div class="screw screw-br"></div>
    <div class="bronze-text">
        <span style="font-size: 2.2em;">Generado por Willian Almenar</span><br><br>
        <span style="font-size: 1.5em; opacity: 0.85;">Prohibida la reproduccion total o parcial</span><br>
        <span style="font-size: 1.8em; letter-spacing: 6px; display: block; margin: 15px 0;">DERECHOS RESERVADOS</span>
        <span style="font-size: 1.9em;">Santa Teresa del Tuy 2.026</span>
    </div>
</div>
""", unsafe_allow_html=True)
