import streamlit as st
import pandas as pd
from datetime import datetime, timedelta
from streamlit_gsheets import GSheetsConnection  # Cambiado para Sheets
from PIL import Image, ImageFile
import base64

# --- CONFIGURACIÓN ---
st.set_page_config(page_title="Guía Comercial Almenar", layout="wide", page_icon="🚀")

# --- CONEXIÓN A GOOGLE SHEETS (Sustituye a Neon) ---
conn = st.connection("gsheets", type=GSheetsConnection)

# --- CATEGORÍAS DEFINIDAS ---
CAT_LIST = [
    "Salud", "Laboratorios", "Opticas", "Farmacias", "Dulcerias",
    "Comida Rapida", "Panaderias", "Charcuterias", "Carnicerias",
    "Ferreterias", "Zapaterias", "Electrodomesticos", "Fibras Opticas",
    "Taxis", "Mototaxis", "Servicios", "Entes Publicos", "Otros"
]

# --- LECTURA DE DATOS DESDE SHEETS ---
# Nota: En Sheets no "creamos" tablas por código, se usan las pestañas del Excel.
df = conn.read(worksheet="comercios", ttl=0)
todas_fotos = conn.read(worksheet="fotos_comercios", ttl=0)
todas_opiniones = conn.read(worksheet="opiniones", ttl=0)
res_visitas = conn.read(worksheet="visitas", ttl=0)
config_df = conn.read(worksheet="configuracion", ttl=0)

# --- LÓGICA DE VISITAS GENERALES ---
total_visitas = int(res_visitas.iloc[0, 0]) if not res_visitas.empty else 0

if 'visitado' not in st.session_state:
    # Para actualizar visitas en Sheets se requiere el método .update()
    # Por ahora mantenemos la visualización para evitar errores de escritura
    st.session_state.visitado = True

# --- FUNCIÓN DE IMAGEN OPTIMIZADA (MINIATURAS) ---
def imagen_a_base64(uploaded_file):
    if uploaded_file is not None:
        img = Image.open(uploaded_file)
        if img.mode in ("RGBA", "P"):
            img = img.convert("RGB")
        max_size = (800, 800) 
        img.thumbnail(max_size, Image.LANCZOS)
        import io
        buffer = io.BytesIO()
        img.save(buffer, format="JPEG", quality=70, optimize=True)
        bytes_data = buffer.getvalue()
        return f"data:image/jpeg;base64,{base64.b64encode(bytes_data).decode()}"
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
    if not config_df.empty and config_df.iloc[0,1]: # logo_data está en la columna 1
        st.markdown(f'<div class="logo-container"><img src="{config_df.iloc[0,1]}" style="width:220px;"></div>', unsafe_allow_html=True)
    st.title("🇻🇪 Gestión")
    opcion_menu = st.radio("Ir a:", ["🏢 Ver Guía Comercial", "🔐 Administración"])
    st.markdown("---")
    st.info("Desarrollado por Willian Almenar")

# --- ENCABEZADO ---
st.markdown('<div class="venezuela-header"><div class="stars-arc">★ ★ ★ ★ ★ ★ ★ ★</div></div>', unsafe_allow_html=True)

# --- LOGO CENTRADO ---
if not config_df.empty and config_df.iloc[0,1]:
    st.markdown(f'<div class="logo-main-container"><img src="{config_df.iloc[0,1]}" style="width:350px;"></div>', unsafe_allow_html=True)

# --- LÓGICA TEMPORAL ---
ahora_vzla = datetime.utcnow() - timedelta(hours=4)
dias_semana = ["Lunes", "Martes", "Miércoles", "Jueves", "Viernes", "Sábado", "Domingo"]
meses = ["Enero", "Febrero", "Marzo", "Abril", "Mayo", "Junio", "Julio", "Agosto", "Septiembre", "Octubre", "Noviembre", "Diciembre"]

festivos_2026 = [
    (datetime(2026, 1, 1), "Año Nuevo"), (datetime(2026, 2, 16), "Lunes de Carnaval"),
    (datetime(2026, 2, 17), "Martes de Carnaval"), (datetime(2026, 3, 19), "Día de San José"),
    (datetime(2026, 4, 2), "Jueves Santo"), (datetime(2026, 4, 3), "Viernes Santo"),
    (datetime(2026, 4, 19), "Declaración de la Independencia"), (datetime(2026, 5, 1), "Día del Trabajador"),
    (datetime(2026, 6, 24), "Batalla de Carabobo"), (datetime(2026, 7, 5), "Día de la Independencia"),
    (datetime(2026, 7, 24), "Natalicio de Simón Bolívar"), (datetime(2026, 10, 12), "Día de la Resistencia Indígena"),
    (datetime(2026, 12, 24), "Víspera de Navidad"), (datetime(2026, 12, 25), "Natividad del Señor"),
    (datetime(2026, 12, 31), "Fin de Año")
]

proximo_festivo = "No hay más festivos este año"
for fecha, nombre in festivos_2026:
    if fecha.date() >= ahora_vzla.date():
        proximo_festivo = f"{nombre} ({fecha.strftime('%d/%m')})"
        break

st.markdown(f'''
<div class="stats-panel">
<span style="color:#ffcc00; font-size:1.1em; font-weight:bold;">{dias_semana[ahora_vzla.weekday()]}, {ahora_vzla.day} de {meses[ahora_vzla.month-1]} de {ahora_vzla.year}
</span><br>
<b style="color:#ffffff; font-size:1.4em;">{ahora_vzla.strftime("%I:%M %p")}</b><br>
<span style="font-size:1.2em; border-top: 1px solid #444; padding-top:5px; display:block; margin-top:5px; color:#ffffff !important;">🚀 VISITAS TOTALES: {total_visitas}</span>
</div>
''', unsafe_allow_html=True)

# --- LÓGICA DE MENÚ ---
if opcion_menu == "🔐 Administración":
    clave = st.text_input("Clave de Acceso:", type="password")
    if clave == "Juan*316*":
        st.success("Acceso Maestro Concedido")
        tab1, tab2, tab3_v = st.tabs(["🏢 Gestión de Negocios", "🖼️ Logo App", "📊 Estadísticas Detalladas"])
        
        with tab1:
            st.info("Utilice el Panel de Control Maestro al final de la página para agregar/editar.")
            
        with tab3_v:
            st.write("### 📈 Visitas por Comercio")
            if not df.empty:
                st.table(df[['nombre', 'categoria', 'visitas']].sort_values(by="visitas", ascending=False))

elif opcion_menu == "🏢 Ver Guía Comercial":
    st.title("🚀 Guía Comercial Almenar")
    st.markdown(f'''
    <div class="holiday-panel">
        <span style="color:#ffcc00; font-weight:bold;">🇻🇪 EFEMÉRIDES VENEZUELA 2026:</span><br>
        <span style="color:white;">Próximo día feriado: <b>{proximo_festivo}</b></span>
    </div>
    ''', unsafe_allow_html=True)
    
    link_app = "https://guia-comercial-almenar-cpe3yfntxmzncn2e7wgueh.streamlit.app"
    whatsapp_url = f"https://api.whatsapp.com/send?text=¡Mira la Guía Comercial de Santa Teresa! 🚀 {link_app}"
    col_s1, col_s2 = st.columns(2)
    with col_s1:
        st.markdown(f'<a href="{whatsapp_url}" target="_blank" style="text-decoration:none;"><div class="ven-share-card"><span class="ven-share-text">📲 Compartir por WhatsApp</span></div></a>', unsafe_allow_html=True)
    with col_s2:
        st.markdown(f'<div class="ven-share-card"><span class="ven-share-text">🔗 Enlace Directo:</span><br><b style="color:#ffcc00; font-size:0.9em;">{link_app}</b></div>', unsafe_allow_html=True)

    st.markdown("---")
    busq = st.text_input("🔍 ¿Qué buscas en Santa Teresa?", placeholder="Ej: Panadería, Farmacia...")
    tab_labels = ["Todos"] + CAT_LIST
    tabs_main = st.tabs(tab_labels)

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
                        expander_titulo = f"🏢 {r['nombre']} - {r['categoria']}"
                        with st.expander(expander_titulo):
                            col_img, col_info = st.columns([1, 2])
                            with col_img:
                                if isinstance(r['foto_url'], str) and (r['foto_url'].startswith('http') or r['foto_url'].startswith('data:image')):
                                    st.image(r['foto_url'], use_container_width=True, caption="Foto Principal")
                                
                                extras = todas_fotos[todas_fotos['comercio_id'] == r['id']]
                                if not extras.empty:
                                    for _, f_row in extras.iterrows():
                                        st.image(f_row['foto_data'], use_container_width=True)

                            with col_info:
                                st.write(f"📍 **Ubicación:** {r['ubicacion']}")
                                if r['maps_url']:
                                    st.link_button("📍 IR A ESTA UBICACIÓN (Google Maps)", r['maps_url'], type="primary", use_container_width=True)
                                st.write(f"⭐ **Calificación Willian:** {'⭐' * (int(r['estrellas_w']) if r['estrellas_w'] else 0)}")
                                st.info(f"**Reseña de Willian:** {r['reseña_willian']}")
                                st.markdown("---")
                                if not todas_opiniones.empty:
                                    op_df = todas_opiniones[todas_opiniones['comercio_id'] == r['id']]
                                    for _, op in op_df.iterrows():
                                        st.markdown(f"<div style='border-bottom: 1px solid #444; padding: 5px;'>👤 <b>{op['usuario']}</b>: {op['comentario']} ({'⭐'*int(op['estrellas_u'])})</div>", unsafe_allow_html=True)

# --- PANEL DE ADMINISTRADOR MAESTRO ---
st.markdown("---")
with st.expander("🛠️ PANEL DE CONTROL MAESTRO (Acceso RestRINGIDO)"):
    master_key = st.text_input("Ingrese Contraseña Maestra:", type="password", key="master_pass")
    if master_key == "Juan*316*":
        st.markdown('<div class="master-panel">', unsafe_allow_html=True)
        st.warning("⚠️ El panel de edición en modo Google Sheets requiere usar el método .update() de la conexión. Para cambios inmediatos, modifique directamente su hoja de cálculo de Google.")
        st.markdown('</div>', unsafe_allow_html=True)

# --- PIE DE PÁGINA ---
st.markdown("""
<div class='footer-willian'>
    <p style='color: #ffcc00 !important; font-size: 1.2em; font-weight: bold; margin-bottom: 10px;'>
        ¡ÚNETE A NOSOTROS Y QUE TU NEGOCIO FORME PARTE DE ESTA GUÍA COMERCIAL!
    </p>
    <p style='color: #ffffff !important; font-size: 1.1em;'>
        Contáctanos por el <b>04242004015</b> (Solo WhatsApp)
    </p>
</div>
""", unsafe_allow_html=True)

# --- PLACA DE BRONCE ---
st.markdown("""
<div class="bronze-plaque">
    <div class="screw screw-tl"></div><div class="screw screw-tr"></div><div class="screw screw-bl"></div><div class="screw screw-br"></div>
    <div class="bronze-text">
        <span style="font-size: 2.2em;">Generado por Willian Almenar</span><br><br>
        <span style="font-size: 1.5em; opacity: 0.85;">Prohibida la reproducción total o parcial</span><br>
        <span style="font-size: 1.8em; letter-spacing: 6px; display: block; margin: 15px 0;">DERECHOS RESERVADOS</span>
        <span style="font-size: 1.9em;">Santa Teresa del Tuy 2.026</span>
    </div>
</div>
""", unsafe_allow_html=True)
