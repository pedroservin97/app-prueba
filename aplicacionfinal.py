import sys, os, subprocess, time, json, platform, traceback, io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QGridLayout, 
                             QLabel, QFileDialog, QFrame, QScrollArea, 
                             QSlider, QInputDialog, QMenu, QColorDialog, 
                             QAbstractItemView, QDialog, QListWidgetItem,
                             QMessageBox, QTabWidget, QLineEdit, QTextEdit,
                             QComboBox, QCheckBox, QGroupBox, QProgressBar,
                             QStackedWidget, QRadioButton,
                             QButtonGroup, QTextBrowser,
                             QSpinBox)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QThread, pyqtSignal, QBuffer, QPoint, QRect
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QIcon, QPixmap, QImage
# ========== IMPORTS ADICIONALES ==========
try:
    from reportlab.lib.pagesizes import A4, landscape
    from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image, PageBreak, Table, TableStyle
    from reportlab.lib.styles import getSampleStyleSheet
    from reportlab.lib.units import inch
    from reportlab.lib import colors
    HAS_REPORTLAB = True
except ImportError:
    HAS_REPORTLAB = True

def get_ffmpeg_path():
    """Extrae ffmpeg a disco y retorna ruta ejecutable - 100% SEGURO"""
    import tempfile
    import shutil
    import sys
    import os
    import platform
    
    # Ruta donde guardaremos ffmpeg (misma carpeta que el programa)
    if getattr(sys, 'frozen', False):
        base_dir = os.path.dirname(sys.executable)  # Carpeta del .exe/.app
    else:
        base_dir = os.path.dirname(os.path.abspath(__file__))  # Desarrollo
    
    # Nombre según sistema
    if platform.system() == "Windows":
        ffmpeg_name = "ffmpeg.exe"
        ffmpeg_source = "ffmpeg.exe"
    else:  # Mac
        ffmpeg_name = "ffmpeg"
        ffmpeg_source = "ffmpeg"
    
    # Ruta final (junto al programa)
    ffmpeg_final = os.path.join(base_dir, ffmpeg_name)
    
    # 1. Si YA EXISTE en la carpeta, usarlo
    if os.path.exists(ffmpeg_final):
        if platform.system() != "Windows":
            os.chmod(ffmpeg_final, 0o755)
        return ffmpeg_final
    
    # 2. Si es .exe/.app, extraer de los recursos
    if getattr(sys, 'frozen', False):
        try:
            # PyInstaller guarda recursos aquí
            base_path = sys._MEIPASS
            ffmpeg_in_package = os.path.join(base_path, ffmpeg_source)
            
            if os.path.exists(ffmpeg_in_package):
                # COPIAR a carpeta del programa
                shutil.copy2(ffmpeg_in_package, ffmpeg_final)
                
                # Hacer ejecutable en Mac
                if platform.system() != "Windows":
                    os.chmod(ffmpeg_final, 0o755)
                
                return ffmpeg_final
        except Exception as e:
            print(f"Error extrayendo ffmpeg: {e}")
    
    # 3. Buscar en sistema (solo desarrollo)
    try:
        which_ffmpeg = shutil.which("ffmpeg")
        if which_ffmpeg:
            return which_ffmpeg
    except:
        pass
    
    # 4. Error final
    if getattr(sys, 'frozen', False):
        from PyQt6.QtWidgets import QMessageBox, QApplication
        app = QApplication.instance() or QApplication([])
        
        error_msg = f"""
        ❌ ERROR: FFmpeg no encontrado
        
        1. Descarga ffmpeg de: https://www.gyan.dev/ffmpeg/builds/
        2. Coloca '{ffmpeg_name}' en esta carpeta:
           {base_dir}
        3. Reinicia el programa
        
        Contacto: pedroservin97@gmail.com
        """
        
        QMessageBox.critical(None, "Error FFmpeg", error_msg)
    
    return None

# ========== CONFIGURACIÓN MULTIPLATAFORMA ==========
def get_system_paths():
    """Obtiene rutas según el sistema operativo"""
    system = platform.system()
    home = os.path.expanduser("~")
    
    # En Windows y Mac usamos el Escritorio para que el usuario encuentre sus videos fácil
    desktop_path = os.path.join(home, "Desktop")
    base_dir = os.path.join(desktop_path, "MatchClipAnalyzer")
    
    return {
        "system": system,
        "base_dir": base_dir
    }

# Obtener configuración del sistema
SYS_CONFIG = get_system_paths()

# Configurar carpetas
CARPETA_RAIZ = SYS_CONFIG["base_dir"]
CARPETA_PROYECTOS = os.path.join(CARPETA_RAIZ, "Projects")
CARPETA_CAPTURAS = os.path.join(CARPETA_RAIZ, "Screenshots")
CARPETA_CORTES = os.path.join(CARPETA_RAIZ, "Clips")
CARPETA_EXPORT = os.path.join(CARPETA_RAIZ, "Exports")
CARPETA_DB = os.path.join(CARPETA_RAIZ, "Database")
ARCHIVO_CONFIG = os.path.join(CARPETA_RAIZ, "config.json")
ARCHIVO_EQUIPOS = os.path.join(CARPETA_DB, "teams.json")
ARCHIVO_TAGS = os.path.join(CARPETA_DB, "tags.json")

# Crear carpetas si no existen (con exist_ok=True para evitar errores)
for p in [CARPETA_RAIZ, CARPETA_PROYECTOS, CARPETA_CAPTURAS, CARPETA_CORTES, 
          CARPETA_EXPORT, CARPETA_DB]:
    os.makedirs(p, exist_ok=True)

# ========== SISTEMA DE IDIOMAS ==========
class LanguageManager:
    LANGUAGES = {
        "es": {
            "app_title": "Match Clip Analyzer",
            "new_project": "Nuevo Proyecto",
            "open_project": "Abrir Proyecto",
            "import_project": "Importar Proyecto",
            "settings": "Configuración",
            "exit": "Salir",
            "load_video": "Cargar Video",
            "export": "Exportar",
            "save": "Guardar",
            "play": "Reproducir",
            "pause": "Pausar",
            "team_local": "Equipo Local",
            "team_away": "Equipo Visitante",
            "clips": "Clips",
            "tags": "Etiquetas",
            "formations": "Formaciones",
            "playlist": "Playlist",
            "cut": "Cortar",
            "mark": "Marcar",
            "diagram": "Diagrama Táctico",
            "statistics": "Estadísticas",
            "config": "Configurar",
            "about": "Acerca de"
        },
        "en": {
            "app_title": "Match Clip Analyzer",
            "new_project": "New Project",
            "open_project": "Open Project",
            "import_project": "Import Project",
            "settings": "Settings",
            "exit": "Exit",
            "load_video": "Load Video",
            "export": "Export",
            "save": "Save",
            "play": "Play",
            "pause": "Pause",
            "team_local": "Home Team",
            "team_away": "Away Team",
            "clips": "Clips",
            "tags": "Tags",
            "formations": "Formations",
            "playlist": "Playlist",
            "cut": "Cut",
            "mark": "Mark",
            "diagram": "Tactical Diagram",
            "statistics": "Statistics",
            "config": "Configure",
            "about": "About"
        },
        "it": {
            "app_title": "Match Clip Analyzer",
            "new_project": "Nuovo Progetto",
            "open_project": "Apri Progetto",
            "import_project": "Importa Progetto",
            "settings": "Impostazioni",
            "exit": "Esci",
            "load_video": "Carica Video",
            "export": "Esporta",
            "save": "Salva",
            "play": "Reproduci",
            "pause": "Pausa",
            "team_local": "Squadra di Casa",
            "team_away": "Squadra Ospite",
            "clips": "Clip",
            "tags": "Etichette",
            "formations": "Formaciones",
            "playlist": "Playlist",
            "cut": "Taglia",
            "mark": "Marca",
            "diagram": "Diagramma Tattico",
            "statistics": "Statistiche",
            "config": "Configura",
            "about": "Informazioni"
        },
        "fr": {
            "app_title": "Match Clip Analyzer",
            "new_project": "Nouveau Projet",
            "open_project": "Ouvrir Projet",
            "import_project": "Importer Projet",
            "settings": "Paramètres",
            "exit": "Quitter",
            "load_video": "Charger Vidéo",
            "export": "Exporter",
            "save": "Sauvegarder",
            "play": "Jouer",
            "pause": "Pausa",
            "team_local": "Équipe Domicile",
            "team_away": "Équipe Visiteur",
            "clips": "Clips",
            "tags": "Étiquettes",
            "formations": "Formations",
            "playlist": "Playlist",
            "cut": "Couper",
            "mark": "Marquer",
            "diagram": "Diagramme Tactique",
            "statistics": "Statistiques",
            "config": "Configurer",
            "about": "À Propos"
        },
        "pt": {
            "app_title": "Match Clip Analyzer",
            "new_project": "Novo Projeto",
            "open_project": "Abrir Projeto",
            "import_project": "Importar Projeto",
            "settings": "Configurações",
            "exit": "Sair",
            "load_video": "Carregar Vídeo",
            "export": "Exportar",
            "save": "Salvar",
            "play": "Reproduzir",
            "pause": "Pausar",
            "team_local": "Time da Casa",
            "team_away": "Time Visitante",
            "clips": "Clipes",
            "tags": "Etiquetas",
            "formations": "Formaciones",
            "playlist": "Playlist",
            "cut": "Cortar",
            "mark": "Marcar",
            "diagram": "Diagrama Tático",
            "statistics": "Estatísticas",
            "config": "Configurar",
            "about": "Sobre"
        }
    }
    
    def __init__(self):
        self.current_lang = "es"
        self.load_settings()
    
    def load_settings(self):
        """Carga el idioma desde la configuración"""
        if os.path.exists(ARCHIVO_CONFIG):
            try:
                with open(ARCHIVO_CONFIG, 'r') as f:
                    config = json.load(f)
                    self.current_lang = config.get("language", "es")
            except:
                pass
    
    def save_settings(self):
        """Guarda el idioma en la configuración"""
        config = {"language": self.current_lang}
        with open(ARCHIVO_CONFIG, 'w') as f:
            json.dump(config, f, indent=2)
    
    def set_language(self, lang_code):
        """Cambia el idioma"""
        if lang_code in self.LANGUAGES:
            self.current_lang = lang_code
            self.save_settings()
            return True
        return False
    
    def get(self, key):
        """Obtiene texto traducido"""
        return self.LANGUAGES[self.current_lang].get(key, key)
    
    def get_languages(self):
        """Devuelve lista de idiomas disponibles"""
        return {
            "es": "Español",
            "en": "English",
            "it": "Italiano",
            "fr": "Français",
            "pt": "Português"
        }

# Instancia global del gestor de idiomas
LANG = LanguageManager()

# ========== SISTEMA DE ETIQUETAS (TAGS) ==========
class TagManager:
    def __init__(self):
        self.tags = []
        self.load_tags()
    
    def load_tags(self):
        """Carga etiquetas desde archivo"""
        if os.path.exists(ARCHIVO_TAGS):
            try:
                with open(ARCHIVO_TAGS, 'r') as f:
                    self.tags = json.load(f)
            except:
                self.tags = []
        else:
            # Etiquetas por defecto
            self.tags = [
                {"id": 1, "name": "Gol", "color": "#e74c3c", "category": "event"},
                {"id": 2, "name": "Falta", "color": "#f39c12", "category": "event"},
                {"id": 3, "name": "Tarjeta", "color": "#f1c40f", "category": "event"},
                {"id": 4, "name": "Tiro", "color": "#3498db", "category": "action"},
                {"id": 5, "name": "Pase", "color": "#2ecc71", "category": "action"},
                {"id": 6, "name": "Centro", "color": "#9b59b6", "category": "action"},
                {"id": 7, "name": "Defensa", "color": "#1abc9c", "category": "action"},
                {"id": 8, "name": "Transición", "color": "#34495e", "category": "phase"},
                {"id": 9, "name": "Contraataque", "color": "#d35400", "category": "phase"},
                {"id": 10, "name": "Jugada", "color": "#16a085", "category": "phase"}
            ]
            self.save_tags()
    
    def save_tags(self):
        """Guarda etiquetas en archivo"""
        with open(ARCHIVO_TAGS, 'w') as f:
            json.dump(self.tags, f, indent=2)
    
    def add_tag(self, name, color, category="custom"):
        """Agrega una nueva etiqueta"""
        new_id = max([t["id"] for t in self.tags], default=0) + 1
        self.tags.append({
            "id": new_id,
            "name": name,
            "color": color,
            "category": category
        })
        self.save_tags()
        return new_id
    
    def get_tags(self):
        """Devuelve todas las etiquetas"""
        return self.tags
    
    def get_tag_by_id(self, tag_id):
        """Busca etiqueta por ID"""
        for tag in self.tags:
            if tag["id"] == tag_id:
                return tag
        return None

# Instancia global del gestor de etiquetas
TAG_MANAGER = TagManager()

# ========== PANTALLA DE INICIO ==========
class StartupScreen(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Match Clip Analyzer")
        self.setFixedSize(800, 600)
        self.setStyleSheet("""
            QDialog {
                background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                          stop:0 #0c2461, stop:1 #1e3799);
            }
            QLabel {
                color: white;
                font-family: Arial, sans-serif;
            }
            QPushButton {
                font-size: 16px;
                padding: 15px;
                border-radius: 8px;
                border: 2px solid rgba(255, 255, 255, 0.2);
                font-weight: bold;
                min-width: 250px;
            }
            QComboBox {
                padding: 8px;
                border-radius: 5px;
                font-size: 14px;
            }
        """)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Logo/Título
        self.logo_label = QLabel("⚽")
        self.logo_label.setStyleSheet("""
            font-size: 120px;
            padding: 20px;
        """)
        self.logo_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.logo_label)
        
        self.title_label = QLabel("MATCH CLIP ANALYZER")
        self.title_label.setStyleSheet("""
            font-size: 42px;
            font-weight: bold;
            color: #f1c40f;
            padding: 10px;
            letter-spacing: 2px;
        """)
        self.title_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.title_label)
        
        self.subtitle_label = QLabel("Professional Video Analysis Tool")
        self.subtitle_label.setStyleSheet("""
            font-size: 18px;
            color: #ecf0f1;
            padding: 10px;
            opacity: 0.8;
        """)
        self.subtitle_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(self.subtitle_label)
        
        layout.addSpacing(40)
        
        # Botones principales
        self.btn_new = QPushButton("🆕  " + LANG.get("new_project"))
        self.btn_new.setStyleSheet("""
            QPushButton {
                background: #27ae60;
                color: white;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #2ecc71;
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
        """)
        self.btn_new.clicked.connect(lambda: self.accept_with_action("new"))
        
        self.btn_open = QPushButton("📂  " + LANG.get("open_project"))
        self.btn_open.setStyleSheet("""
            QPushButton {
                background: #2980b9;
                color: white;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #3498db;
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
        """)
        self.btn_open.clicked.connect(lambda: self.accept_with_action("open"))
        
        self.btn_settings = QPushButton("⚙️  " + LANG.get("settings"))
        self.btn_settings.setStyleSheet("""
            QPushButton {
                background: #8e44ad;
                color: white;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #9b59b6;
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
        """)
        self.btn_settings.clicked.connect(self.open_settings)
        
        self.btn_exit = QPushButton("🚪  " + LANG.get("exit"))
        self.btn_exit.setStyleSheet("""
            QPushButton {
                background: #c0392b;
                color: white;
                font-size: 18px;
            }
            QPushButton:hover {
                background: #e74c3c;
                border: 2px solid rgba(255, 255, 255, 0.5);
            }
        """)
        self.btn_exit.clicked.connect(self.reject)
        
        for btn in [self.btn_new, self.btn_open, self.btn_settings, self.btn_exit]:
            btn.setFixedHeight(65)
            layout.addWidget(btn, alignment=Qt.AlignmentFlag.AlignCenter)
            layout.addSpacing(15)
        
        layout.addStretch()
        
        # Selector de idioma
        lang_layout = QHBoxLayout()
        lang_layout.addStretch()
        
        lang_label = QLabel("🌍  Idioma:")
        lang_label.setStyleSheet("color: white; font-size: 14px;")
        lang_layout.addWidget(lang_label)
        
        self.combo_lang = QComboBox()
        languages = LANG.get_languages()
        for code, name in languages.items():
            self.combo_lang.addItem(name, code)
        
        # Seleccionar idioma actual
        current_index = self.combo_lang.findData(LANG.current_lang)
        if current_index >= 0:
            self.combo_lang.setCurrentIndex(current_index)
        
        self.combo_lang.currentIndexChanged.connect(self.change_language)
        lang_layout.addWidget(self.combo_lang)
        
        lang_layout.addStretch()
        layout.addLayout(lang_layout)
        
        # Información de versión
        version_label = QLabel("Version 12.0 | © 2024 Match Clip Analyzer")
        version_label.setStyleSheet("""
            color: #bdc3c7;
            font-size: 12px;
            padding: 10px;
        """)
        version_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(version_label)
    
    def accept_with_action(self, action):
        """Acepta el diálogo con una acción específica"""
        self.action = action
        self.accept()
    
    def change_language(self):
        """Cambia el idioma de la aplicación"""
        lang_code = self.combo_lang.currentData()
        if lang_code:
            LANG.set_language(lang_code)
            self.update_texts()
    
    def update_texts(self):
        """Actualiza todos los textos de la interfaz"""
        self.title_label.setText("MATCH CLIP ANALYZER")
        self.subtitle_label.setText("Professional Video Analysis Tool")
        self.btn_new.setText("🆕  " + LANG.get("new_project"))
        self.btn_open.setText("📂  " + LANG.get("open_project"))
        self.btn_settings.setText("⚙️  " + LANG.get("settings"))
        self.btn_exit.setText("🚪  " + LANG.get("exit"))
    
    def open_settings(self):
        """Abre el diálogo de configuración"""
        dialog = SettingsDialog(self)
        dialog.exec()

class SettingsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LANG.get("settings"))
        self.resize(600, 500)
        self.init_ui()
    
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Pestañas
        tabs = QTabWidget()
        
        # Pestaña General
        general_tab = QWidget()
        general_layout = QVBoxLayout(general_tab)
        
        # Idioma
        lang_group = QGroupBox(LANG.get("language"))
        lang_layout = QVBoxLayout()
        
        self.combo_lang = QComboBox()
        languages = LANG.get_languages()
        for code, name in languages.items():
            self.combo_lang.addItem(name, code)
        
        current_index = self.combo_lang.findData(LANG.current_lang)
        if current_index >= 0:
            self.combo_lang.setCurrentIndex(current_index)
        
        lang_layout.addWidget(self.combo_lang)
        lang_group.setLayout(lang_layout)
        general_layout.addWidget(lang_group)
        
        # Rutas
        path_group = QGroupBox("Rutas de Archivos")
        path_layout = QVBoxLayout()
        
        self.btn_change_root = QPushButton("Cambiar Carpeta Principal")
        self.btn_change_root.clicked.connect(self.change_root_folder)
        path_layout.addWidget(self.btn_change_root)
        
        self.label_root = QLabel(f"Carpeta actual: {CARPETA_RAIZ}")
        path_layout.addWidget(self.label_root)
        
        path_group.setLayout(path_layout)
        general_layout.addWidget(path_group)
        
        general_layout.addStretch()
        tabs.addTab(general_tab, "General")
        
        # Pestaña Equipos
        teams_tab = QWidget()
        teams_layout = QVBoxLayout(teams_tab)
        
        # Gestión de equipos
        teams_group = QGroupBox("Gestión de Equipos")
        teams_form = QVBoxLayout()
        
        # Equipo local
        local_layout = QHBoxLayout()
        local_layout.addWidget(QLabel(LANG.get("team_local") + ":"))
        self.local_name = QLineEdit()
        local_layout.addWidget(self.local_name)
        
        self.btn_local_logo = QPushButton("📷 Logo")
        self.btn_local_logo.clicked.connect(self.select_local_logo)
        local_layout.addWidget(self.btn_local_logo)
        
        teams_form.addLayout(local_layout)
        
        # Equipo visitante
        away_layout = QHBoxLayout()
        away_layout.addWidget(QLabel(LANG.get("team_away") + ":"))
        self.away_name = QLineEdit()
        away_layout.addWidget(self.away_name)
        
        self.btn_away_logo = QPushButton("📷 Logo")
        self.btn_away_logo.clicked.connect(self.select_away_logo)
        away_layout.addWidget(self.btn_away_logo)
        
        teams_form.addLayout(away_layout)
        
        teams_group.setLayout(teams_form)
        teams_layout.addWidget(teams_group)
        
        teams_layout.addStretch()
        tabs.addTab(teams_tab, "Equipos")
        
        # Pestaña Etiquetas
        tags_tab = QWidget()
        tags_layout = QVBoxLayout(tags_tab)
        
        tags_group = QGroupBox("Gestión de Etiquetas")
        tags_form = QVBoxLayout()
        
        # Lista de etiquetas
        self.tags_list = QListWidget()
        for tag in TAG_MANAGER.get_tags():
            item = QListWidgetItem(tag["name"])
            item.setData(Qt.ItemDataRole.UserRole, tag)
            item.setForeground(QColor(tag["color"]))
            self.tags_list.addItem(item)
        
        tags_form.addWidget(self.tags_list)
        
        # Botones para etiquetas
        tags_buttons = QHBoxLayout()
        self.btn_add_tag = QPushButton("➕ Agregar")
        self.btn_edit_tag = QPushButton("✏️ Editar")
        self.btn_delete_tag = QPushButton("🗑️ Eliminar")
        
        self.btn_add_tag.clicked.connect(self.add_tag)
        self.btn_edit_tag.clicked.connect(self.edit_tag)
        self.btn_delete_tag.clicked.connect(self.delete_tag)
        
        tags_buttons.addWidget(self.btn_add_tag)
        tags_buttons.addWidget(self.btn_edit_tag)
        tags_buttons.addWidget(self.btn_delete_tag)
        
        tags_form.addLayout(tags_buttons)
        tags_group.setLayout(tags_form)
        tags_layout.addWidget(tags_group)
        
        tags_layout.addStretch()
        tabs.addTab(tags_tab, "Etiquetas")
        
        layout.addWidget(tabs)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        self.btn_save = QPushButton("💾 Guardar")
        self.btn_cancel = QPushButton("❌ Cancelar")
        
        self.btn_save.clicked.connect(self.save_settings)
        self.btn_cancel.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.btn_save)
        btn_layout.addWidget(self.btn_cancel)
        layout.addLayout(btn_layout)
        
        # Cargar configuración actual
        self.load_current_settings()
    
    def load_current_settings(self):
        """Carga la configuración actual"""
        if os.path.exists(ARCHIVO_CONFIG):
            try:
                with open(ARCHIVO_CONFIG, 'r') as f:
                    config = json.load(f)
                    
                    # Cargar nombres de equipos si existen
                    if "teams" in config:
                        teams = config["teams"]
                        self.local_name.setText(teams.get("local", "Equipo Local"))
                        self.away_name.setText(teams.get("away", "Equipo Visitante"))
            except:
                pass
    
    def change_root_folder(self):
        """Cambia la carpeta raíz de la aplicación"""
        folder = QFileDialog.getExistingDirectory(
            self, 
            "Seleccionar Carpeta Principal",
            CARPETA_RAIZ
        )
        if folder:
            # Aquí deberías implementar la lógica para mover/cambiar la carpeta
            QMessageBox.information(
                self,
                "Cambio de Carpeta",
                f"La carpeta principal se cambiará a:\n{folder}\n\n"
                "Nota: Esta función requiere reiniciar la aplicación."
            )
    
    def select_local_logo(self):
        """Selecciona logo para equipo local"""
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Logo",
            "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if file:
            self.local_logo_path = file
    
    def select_away_logo(self):
        """Selecciona logo para equipo visitante"""
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar Logo",
            "", "Imágenes (*.png *.jpg *.jpeg *.bmp)"
        )
        if file:
            self.away_logo_path = file
    
    def add_tag(self):
        """Agrega una nueva etiqueta"""
        name, ok = QInputDialog.getText(
            self, "Nueva Etiqueta",
            "Nombre de la etiqueta:"
        )
        if ok and name:
            color = QColorDialog.getColor(QColor("#3498db"), self)
            if color.isValid():
                tag_id = TAG_MANAGER.add_tag(name, color.name())
                
                # Actualizar lista
                item = QListWidgetItem(name)
                item.setData(Qt.ItemDataRole.UserRole, 
                           {"id": tag_id, "name": name, "color": color.name()})
                item.setForeground(color)
                self.tags_list.addItem(item)
    
    def edit_tag(self):
        """Edita la etiqueta seleccionada"""
        current = self.tags_list.currentItem()
        if not current:
            return
        
        tag = current.data(Qt.ItemDataRole.UserRole)
        new_name, ok = QInputDialog.getText(
            self, "Editar Etiqueta",
            "Nuevo nombre:",
            text=tag["name"]
        )
        if ok and new_name:
            # Actualizar en TAG_MANAGER
            for t in TAG_MANAGER.tags:
                if t["id"] == tag["id"]:
                    t["name"] = new_name
                    break
            TAG_MANAGER.save_tags()
            
            # Actualizar item en la lista
            current.setText(new_name)
            QMessageBox.information(
                self, "Etiqueta editada",
                "Etiqueta actualizada correctamente."
            )
    
    def delete_tag(self):
        """Elimina la etiqueta seleccionada"""
        current = self.tags_list.currentRow()
        if current >= 0:
            reply = QMessageBox.question(
                self, "Confirmar Eliminación",
                "¿Estás seguro de eliminar esta etiqueta?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                item = self.tags_list.currentItem()
                tag = item.data(Qt.ItemDataRole.UserRole)
                
                # Eliminar del TAG_MANAGER
                TAG_MANAGER.tags = [t for t in TAG_MANAGER.tags if t["id"] != tag["id"]]
                TAG_MANAGER.save_tags()
                
                # Eliminar de la lista
                self.tags_list.takeItem(current)
    
    def save_settings(self):
        """Guarda la configuración"""
        try:
            # Guardar configuración general
            config = {
                "language": LANG.current_lang,
                "teams": {
                    "local": self.local_name.text() or "Equipo Local",
                    "away": self.away_name.text() or "Equipo Visitante"
                }
            }
            
            with open(ARCHIVO_CONFIG, 'w') as f:
                json.dump(config, f, indent=2)
            
            QMessageBox.information(
                self, "Configuración Guardada",
                "La configuración se ha guardado exitosamente."
            )
            self.accept()
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error",
                f"No se pudo guardar la configuración:\n{str(e)}"
            )

# ========== CLASES AUXILIARES ==========
class ClickableTimeline(QFrame):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player
        self.marks = []
        self.segmentos = []
        self.duration = 1
        self.position = 0
        self.setFixedHeight(75)

        # **AGREGA ESTO:** No aceptar foco con el tab
        self.setFocusPolicy(Qt.FocusPolicy.NoFocus)

    def paintEvent(self, event):
        painter = QPainter(self)
        w, h = self.width(), self.height()
        
        # Fondo
        painter.fillRect(self.rect(), QColor("#1e272e"))
        if self.duration <= 0: 
            return
        
        px_por_ms = w / self.duration
        espacio_minimo_texto = 60
        
        # Escala de tiempo
        ms_por_marca = 60000 
        if (px_por_ms * 60000) < espacio_minimo_texto: 
            ms_por_marca = 300000
        if (px_por_ms * 300000) < espacio_minimo_texto: 
            ms_por_marca = 600000
        if (px_por_ms * 60000) > 250: 
            ms_por_marca = 10000 

        # Dibujar escala
        painter.setPen(QPen(QColor("#7f8c8d"), 1))
        for i in range(0, self.duration, ms_por_marca):
            x = int(i * px_por_ms)
            painter.drawLine(x, h-25, x, h-10)
            minutos = i // 60000
            segundos = (i % 60000) // 1000
            txt = f"{minutos}m" if segundos == 0 else f"{minutos}:{segundos:02d}"
            painter.drawText(x + 3, h - 30, txt)

        # Dibujar segmentos (cortes completos)
        for inicio, fin, color, nombre in self.segmentos:
            x_ini = int(inicio * px_por_ms)
            x_fin = int(fin * px_por_ms)
            painter.setBrush(QColor(color))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRect(x_ini, 5, x_fin - x_ini, h - 35)
            
            # Nombre del segmento si hay espacio
            if (x_fin - x_ini) > 50:
                painter.setPen(QColor("white"))
                painter.setFont(QFont("Arial", 8))
                painter.drawText(x_ini + 5, 20, nombre[:15])

        # Marcas individuales
        for pos_ms, color in self.marks:
            x = int(pos_ms * px_por_ms)
            painter.setPen(QPen(QColor(color), 4))
            painter.drawLine(x, 5, x, h - 35)

        # Cabezal de reproducción
        x_head = int(self.position * px_por_ms)
        painter.setPen(QPen(QColor("#2ecc71"), 3))
        painter.drawLine(x_head, 0, x_head, h)
        
        # Círculo en el cabezal
        painter.setBrush(QColor("#2ecc71"))
        painter.drawEllipse(x_head - 4, h - 40, 8, 8)

    def mousePressEvent(self, event):
        if self.duration > 0:
            pos = int(event.position().x() / (self.width() / self.duration))
            self.player.setPosition(pos)
            self.player.play()

              # **AGREGA ESTO:** Devolver foco a la ventana principal
            if self.parent():
                main_window = self.parent().parent()  # timeline -> scroll -> main
                if hasattr(main_window, 'setFocus'):
                    main_window.setFocus()

class PlaylistDialog(QDialog):
    def __init__(self, clips, video_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LANG.get("playlist"))
        self.resize(600, 500)
        self.video_path = video_path
        self.clips = clips
        self.layout = QVBoxLayout(self)
        
        self.label = QLabel("Organizar clips para playlist:")
        self.layout.addWidget(self.label)
        
        self.list_w = QListWidget()
        for c in clips:
            it = QListWidgetItem(f"{c['nom']} - {c['tiempo']}")
            it.setData(Qt.ItemDataRole.UserRole, c)
            self.list_w.addItem(it)
        self.layout.addWidget(self.list_w)
        
        # Controles de orden
        btns = QHBoxLayout()
        btn_up = QPushButton("⬆️ Subir")
        btn_down = QPushButton("⬇️ Bajar")
        btn_del = QPushButton("🗑️ Quitar")
        
        btn_up.clicked.connect(self.mover_arriba)
        btn_down.clicked.connect(self.mover_abajo)
        btn_del.clicked.connect(self.quitar_item)
        
        btns.addWidget(btn_up)
        btns.addWidget(btn_down)
        btns.addWidget(btn_del)
        btns.addStretch()
        
        # Filtro por etiquetas
        self.filter_combo = QComboBox()
        self.filter_combo.addItem("Todas las etiquetas", None)
        for tag in TAG_MANAGER.get_tags():
            self.filter_combo.addItem(tag["name"], tag["id"])
        self.filter_combo.currentIndexChanged.connect(self.filtrar_por_tag)
        btns.addWidget(QLabel("Filtrar:"))
        btns.addWidget(self.filter_combo)
        
        # Opción de timestamp
        self.timestamp_checkbox = QCheckBox("Agregar minutero (timestamp)")
        self.timestamp_checkbox.setChecked(True)
        btns.addWidget(self.timestamp_checkbox)
        
        self.layout.addLayout(btns)
        
        # Botón de renderizado
        self.btn_render = QPushButton("🎬 GENERAR PLAYLIST")
        self.btn_render.setStyleSheet("""
            background: #27ae60;
            font-weight: bold;
            height: 40px;
            color: white;
        """)
        self.btn_render.clicked.connect(self.finalizar)
        self.layout.addWidget(self.btn_render)
    
    def mover_arriba(self):
        curr = self.list_w.currentRow()
        if curr > 0:
            it = self.list_w.takeItem(curr)
            self.list_w.insertItem(curr - 1, it)
            self.list_w.setCurrentRow(curr - 1)
    
    def mover_abajo(self):
        curr = self.list_w.currentRow()
        if curr < self.list_w.count() - 1:
            it = self.list_w.takeItem(curr)
            self.list_w.insertItem(curr + 1, it)
            self.list_w.setCurrentRow(curr + 1)
    
    def quitar_item(self):
        curr = self.list_w.currentRow()
        if curr >= 0:
            self.list_w.takeItem(curr)
    
    def filtrar_por_tag(self):
        """Filtra clips por etiqueta seleccionada"""
        tag_id = self.filter_combo.currentData()
        
        # Primero mostrar todos
        for i in range(self.list_w.count()):
            self.list_w.item(i).setHidden(False)
        
        # Si hay tag seleccionado, filtrar
        if tag_id:
            for i in range(self.list_w.count()):
                item = self.list_w.item(i)
                clip_data = item.data(Qt.ItemDataRole.UserRole)
                clip_tags = clip_data.get("tags", [])
                
                # Ocultar si no tiene la etiqueta
                if tag_id not in clip_tags:
                    item.setHidden(True)
    
    def finalizar(self):
        nombre, ok = QInputDialog.getText(
            self, "Guardar Playlist",
            "Nombre del archivo final:",
            text="PLAYLIST_" + time.strftime("%Y%m%d_%H%M")
        )
        
        if ok and nombre:
            clips_finales = []
            for i in range(self.list_w.count()):
                if not self.list_w.item(i).isHidden():
                    clips_finales.append(self.list_w.item(i).data(Qt.ItemDataRole.UserRole))
            
            if not clips_finales:
                QMessageBox.warning(self, "Sin clips", "No hay clips seleccionados.")
                return
            
            # Crear archivo de lista para FFmpeg
            list_file = os.path.join(CARPETA_CORTES, f"lista_{int(time.time())}.txt")
            temp_files = []
            
            # Procesar cada clip
            for idx, c in enumerate(clips_finales):
                clip_duration = (c['fin'] - c['ini']) / 1000  # en segundos
                
                if self.timestamp_checkbox.isChecked():
                    # Crear clip temporal con timestamp
                    temp_clip = os.path.join(CARPETA_CORTES, f"temp_{int(time.time())}_{idx}.mp4")
                    temp_files.append(temp_clip)
                    
                    # Comando para agregar timestamp
                    timestamp_text = f"{c['tiempo']} - {c['nombre']}"
                    ffmpeg_path = get_ffmpeg_path()
                    cmd = [
                        ffmpeg_path, "-i", self.video_path,
                        "-ss", str(c['ini']/1000),
                        "-t", str(clip_duration),
                        "-vf", f"drawtext=text='{timestamp_text}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10",
                        "-c:a", "copy",
                        "-y", temp_clip
                    ]
                    
                    try:
                        result = subprocess.run(cmd, capture_output=True, text=True, timeout=30)
                        if result.returncode != 0:
                            QMessageBox.warning(self, "Advertencia", 
                                              f"No se pudo agregar timestamp al clip {idx+1}. Se continuará sin timestamp.")
                            temp_files[-1] = None
                    except Exception as e:
                        QMessageBox.warning(self, "Advertencia", 
                                          f"Error al procesar clip {idx+1}: {str(e)}")
                        temp_files[-1] = None
                else:
                    # Sin timestamp
                    temp_files.append(None)
            
            # Crear archivo de lista concatenada
            with open(list_file, "w") as f:
                for idx, c in enumerate(clips_finales):
                    if temp_files[idx] and os.path.exists(temp_files[idx]):
                        f.write(f"file '{temp_files[idx]}'\n")
                    else:
                        # Usar el original
                        f.write(f"file '{self.video_path}'\n")
                        f.write(f"inpoint {c['ini']/1000}\n")
                        f.write(f"outpoint {c['fin']/1000}\n")
            
            # Ruta de salida
            out = os.path.join(CARPETA_CORTES, f"{nombre}.mp4")
            
            # Ejecutar FFmpeg para concatenar
            try:
                ffmpeg_path = get_ffmpeg_path()
                result = subprocess.run([
                    ffmpeg_path, "-f", "concat", "-safe", "0",
                    "-i", list_file, "-c", "copy", "-y", out
                ], capture_output=True, text=True)
                
                if result.returncode == 0:
                    QMessageBox.information(
                        self, "Playlist Completada",
                        f"Playlist '{nombre}' generada exitosamente.\n"
                        f"Archivo de salida: {out}"
                    )
                else:
                    QMessageBox.warning(
                        self, "Advertencia",
                        f"Playlist generada con advertencias:\n{result.stderr}"
                    )
                
                # Limpiar archivos temporales
                for temp_file in temp_files:
                    if temp_file and os.path.exists(temp_file):
                        os.remove(temp_file)
                
                if os.path.exists(list_file):
                    os.remove(list_file)
                
                self.accept()
                
            except Exception as e:
                QMessageBox.critical(
                    self, "Error FFmpeg",
                    f"No se pudo generar la playlist:\n{str(e)}"
                )

class ExportWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path, clips, output_path, codec="copy", add_timestamp=False):
        super().__init__()
        self.video_path = video_path
        self.clips = clips
        self.output_path = output_path
        self.codec = codec
        self.add_timestamp = add_timestamp

    def run(self):
        try:
            temp_files = []
            
            # Crear carpeta de exportación si no existe
            export_dir = os.path.dirname(self.output_path)
            if not os.path.exists(export_dir):
                os.makedirs(export_dir, exist_ok=True)
            
            # Procesar cada clip
            for idx, clip in enumerate(self.clips):
                self.progress.emit(int((idx / len(self.clips)) * 50))
                
                clip_duration = (clip['fin'] - clip['ini']) / 1000  # en segundos
                
                if self.add_timestamp:
                    # Crear clip temporal con timestamp
                    temp_clip = os.path.join(CARPETA_CORTES, f"export_temp_{int(time.time())}_{idx}.mp4")
                    temp_files.append(temp_clip)
                    
                    # Texto del timestamp
                    timestamp_text = f"{clip['tiempo']} - {clip.get('nombre', 'Clip')}"
                    
                    # Comando para agregar timestamp
                    ffmpeg_path = get_ffmpeg_path()
                    cmd = [
                        ffmpeg_path, "-i", self.video_path,
                        "-ss", str(clip['ini']/1000),
                        "-t", str(clip_duration),
                        "-vf", f"drawtext=text='{timestamp_text}':fontcolor=white:fontsize=24:box=1:boxcolor=black@0.5:boxborderw=5:x=10:y=10",
                        "-c:a", "copy"
                    ]
                    
                    if self.codec == "copy":
                        cmd.extend(["-c:v", "copy"])
                    else:
                        cmd.extend(["-c:v", "libx264", "-preset", "medium", "-crf", "23"])
                    
                    cmd.extend(["-y", temp_clip])
                    
                    result = subprocess.run(cmd, capture_output=True, text=True)
                    if result.returncode != 0:
                        self.error.emit(f"Error al procesar clip {idx+1}: {result.stderr}")
                        return
                else:
                    # Sin timestamp
                    temp_files.append(None)
            
            self.progress.emit(60)
            
            # Crear archivo de lista para concatenación
            list_file = os.path.join(CARPETA_CORTES, f"export_list_{int(time.time())}.txt")
            with open(list_file, "w") as f:
                for idx, clip in enumerate(self.clips):
                    if temp_files[idx] and os.path.exists(temp_files[idx]):
                        f.write(f"file '{temp_files[idx]}'\n")
                    else:
                        f.write(f"file '{self.video_path}'\n")
                        f.write(f"inpoint {clip['ini']/1000}\n")
                        f.write(f"outpoint {clip['fin']/1000}\n")
            
            self.progress.emit(75)
            
            # Concatenar clips
            ffmpeg_path = get_ffmpeg_path()
            if self.codec == "copy":
                cmd = [ffmpeg_path, "-f", "concat", "-safe", "0", 
                       "-i", list_file, "-c", "copy", "-y", self.output_path]
            else:
                cmd = [ffmpeg_path, "-f", "concat", "-safe", "0", 
                       "-i", list_file, "-c:v", "libx264", "-preset", "medium",
                       "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-y", self.output_path]
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            self.progress.emit(100)
            
            if result.returncode == 0:
                self.finished.emit(self.output_path)
            else:
                self.error.emit(f"Error FFmpeg: {result.stderr}")
            
            # Limpiar archivos temporales
            for temp_file in temp_files:
                if temp_file and os.path.exists(temp_file):
                    try:
                        os.remove(temp_file)
                    except:
                        pass
            
            if os.path.exists(list_file):
                try:
                    os.remove(list_file)
                except:
                    pass
                
        except Exception as e:
            self.error.emit(str(e))

# ========== DIÁLOGO PARA AGREGAR/EDITAR BOTONES ==========
class AddButtonDialog(QDialog):
    """Diálogo para agregar un nuevo botón"""
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Agregar Nuevo Botón")
        self.resize(400, 500)  # Aumentado para incluir duración
        self.button_data = None
        self.setup_ui()
    
    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Nombre del botón
        layout.addWidget(QLabel("Nombre del botón:"))
        self.nombre_input = QLineEdit()
        self.nombre_input.setPlaceholderText("Ej: SALIDA, GOL, FALTA")
        layout.addWidget(self.nombre_input)
        
        # Tecla de acceso
        layout.addWidget(QLabel("Tecla de acceso rápido:"))
        self.tecla_input = QLineEdit()
        self.tecla_input.setMaxLength(1)
        self.tecla_input.setPlaceholderText("Una letra o número")
        layout.addWidget(self.tecla_input)
        
        # Tipo de corte
        layout.addWidget(QLabel("Tipo de corte:"))
        self.tipo_combo = QComboBox()
        self.tipo_combo.addItems(["manual", "auto"])
        self.tipo_combo.currentTextChanged.connect(self.toggle_duracion)
        layout.addWidget(self.tipo_combo)
        
        # Duración para cortes automáticos
        self.duracion_label = QLabel("Duración automática (segundos):")
        self.duracion_spin = QSpinBox()
        self.duracion_spin.setRange(1, 60)
        self.duracion_spin.setValue(10)
        self.duracion_spin.setSuffix(" seg")
        self.duracion_layout = QHBoxLayout()
        self.duracion_layout.addWidget(self.duracion_label)
        self.duracion_layout.addWidget(self.duracion_spin)
        layout.addLayout(self.duracion_layout)
        
        # Equipo
        layout.addWidget(QLabel("Equipo:"))
        self.equipo_combo = QComboBox()
        self.equipo_combo.addItems(["local", "visitante", "ambos"])
        layout.addWidget(self.equipo_combo)
        
        # Carpeta
        layout.addWidget(QLabel("Carpeta para clips:"))
        self.carpeta_input = QLineEdit()
        self.carpeta_input.setPlaceholderText("Se genera automáticamente")
        layout.addWidget(self.carpeta_input)
        
        # Colores
        colors_layout = QGridLayout()
        
        # Color del botón
        colors_layout.addWidget(QLabel("Color del botón:"), 0, 0)
        self.btn_color_btn = QPushButton("Seleccionar")
        self.btn_color_btn.clicked.connect(self.seleccionar_color_boton)
        colors_layout.addWidget(self.btn_color_btn, 0, 1)
        self.btn_color_label = QLabel("#2980b9")
        self.btn_color_label.setStyleSheet("background: #2980b9; color: white; padding: 5px;")
        colors_layout.addWidget(self.btn_color_label, 0, 2)
        
        # Color del texto
        colors_layout.addWidget(QLabel("Color del texto:"), 1, 0)
        self.text_color_btn = QPushButton("Seleccionar")
        self.text_color_btn.clicked.connect(self.seleccionar_color_texto)
        colors_layout.addWidget(self.text_color_btn, 1, 1)
        self.text_color_label = QLabel("#ffffff")
        self.text_color_label.setStyleSheet("background: #ffffff; color: black; padding: 5px;")
        colors_layout.addWidget(self.text_color_label, 1, 2)
        
        layout.addLayout(colors_layout)
        
        # Etiquetas asociadas
        layout.addWidget(QLabel("Etiquetas (opcional):"))
        self.tags_list = QListWidget()
        self.tags_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        
        for tag in TAG_MANAGER.get_tags():
            item = QListWidgetItem(tag["name"])
            item.setData(Qt.ItemDataRole.UserRole, tag["id"])
            item.setForeground(QColor(tag["color"]))
            self.tags_list.addItem(item)
        
        layout.addWidget(self.tags_list)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_aceptar = QPushButton("✅ Agregar")
        btn_cancelar = QPushButton("❌ Cancelar")
        
        btn_aceptar.clicked.connect(self.aceptar)
        btn_cancelar.clicked.connect(self.reject)
        
        btn_layout.addWidget(btn_aceptar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        # Conectar señal para generar carpeta automáticamente
        self.nombre_input.textChanged.connect(self.generar_carpeta)
        
        # Ocultar duración por defecto (solo visible para auto)
        self.toggle_duracion("manual")
    
    def toggle_duracion(self, tipo):
        """Muestra/oculta la duración según el tipo"""
        if tipo == "auto":
            self.duracion_label.setVisible(True)
            self.duracion_spin.setVisible(True)
        else:
            self.duracion_label.setVisible(False)
            self.duracion_spin.setVisible(False)
    
    def generar_carpeta(self, texto):
        """Genera nombre de carpeta automáticamente"""
        if texto and not self.carpeta_input.isModified():
            carpeta = texto.upper().replace(" ", "_")
            self.carpeta_input.setText(carpeta)
    
    def seleccionar_color_boton(self):
        """Selecciona color para el botón"""
        color = QColorDialog.getColor(QColor("#2980b9"), self)
        if color.isValid():
            self.btn_color_label.setText(color.name())
            self.btn_color_label.setStyleSheet(f"background: {color.name()}; color: white; padding: 5px;")
    
    def seleccionar_color_texto(self):
        """Selecciona color para el texto"""
        color = QColorDialog.getColor(QColor("#ffffff"), self)
        if color.isValid():
            self.text_color_label.setText(color.name())
            contrast = "white" if color.lightness() < 128 else "black"
            self.text_color_label.setStyleSheet(f"background: {color.name()}; color: {contrast}; padding: 5px;")
    
    def aceptar(self):
        """Valida y acepta los datos"""
        nombre = self.nombre_input.text().strip().upper()
        tecla = self.tecla_input.text().strip().upper()
        
        if not nombre:
            QMessageBox.warning(self, "Error", "El nombre del botón es obligatorio.")
            return
        
        if not tecla or len(tecla) != 1:
            QMessageBox.warning(self, "Error", "Debe ingresar una tecla de acceso rápido válida.")
            return
        
        # Obtener etiquetas seleccionadas
        etiquetas = []
        for i in range(self.tags_list.count()):
            if self.tags_list.item(i).isSelected():
                etiquetas.append(self.tags_list.item(i).data(Qt.ItemDataRole.UserRole))
        
        # Obtener duración si es automático
        duracion = 0
        if self.tipo_combo.currentText() == "auto":
            duracion = self.duracion_spin.value() * 1000  # Convertir a milisegundos
        
        # Crear datos del botón
        self.button_data = [
            nombre,  # 0: Nombre
            self.btn_color_label.text(),  # 1: Color botón
            self.tipo_combo.currentText(),  # 2: Tipo
            tecla,  # 3: Tecla
            self.carpeta_input.text().strip() or nombre.replace(" ", "_"),  # 4: Carpeta
            self.text_color_label.text(),  # 5: Color texto
            self.equipo_combo.currentText(),  # 6: Equipo
            etiquetas,  # 7: Etiquetas
            duracion  # 8: Duración para auto (ms)
        ]
        
        self.accept()
    
    def get_button_data(self):
        """Devuelve los datos del botón creado"""
        return self.button_data

class EditButtonDialog(AddButtonDialog):
    """Diálogo para editar un botón existente"""
    def __init__(self, button_data, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Editar Botón")
        self.original_data = button_data
        self.cargar_datos()
    
    def cargar_datos(self):
        """Carga los datos del botón a editar"""
        if len(self.original_data) >= 8:
            # Cargar datos básicos
            self.nombre_input.setText(self.original_data[0])
            
            self.btn_color_label.setText(self.original_data[1])
            self.btn_color_label.setStyleSheet(f"background: {self.original_data[1]}; color: white; padding: 5px;")
            
            # Tipo
            index = self.tipo_combo.findText(self.original_data[2])
            if index >= 0:
                self.tipo_combo.setCurrentIndex(index)
            
            self.tecla_input.setText(self.original_data[3])
            self.carpeta_input.setText(self.original_data[4])
            self.carpeta_input.setModified(True)  # Marcar como modificado
            
            self.text_color_label.setText(self.original_data[5])
            contrast = "white" if QColor(self.original_data[5]).lightness() < 128 else "black"
            self.text_color_label.setStyleSheet(f"background: {self.original_data[5]}; color: {contrast}; padding: 5px;")
            
            # Equipo
            if len(self.original_data) > 6:
                index = self.equipo_combo.findText(self.original_data[6])
                if index >= 0:
                    self.equipo_combo.setCurrentIndex(index)
            
            # Etiquetas
            if len(self.original_data) > 7:
                etiquetas = self.original_data[7]
                for i in range(self.tags_list.count()):
                    tag_id = self.tags_list.item(i).data(Qt.ItemDataRole.UserRole)
                    if tag_id in etiquetas:
                        self.tags_list.item(i).setSelected(True)
            
            # Duración
            if len(self.original_data) > 8:
                duracion_ms = self.original_data[8]
                if duracion_ms > 0:
                    self.duracion_spin.setValue(int(duracion_ms / 1000))

# ========== CONFIGURACIÓN DE BOTONERA ==========
class ConfigBotoneraDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Botonera - Agregar/Quitar Botones")
        self.resize(700, 500)
        self.config = config.copy()  # Trabajar con copia
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Información
        info_label = QLabel("Configura los botones de la botonera. Arrastra para reordenar.")
        info_label.setStyleSheet("color: #7f8c8d; padding: 5px;")
        layout.addWidget(info_label)
        
        # Lista de botones
        self.list_widget = QListWidget()
        self.list_widget.setDragDropMode(QAbstractItemView.DragDropMode.InternalMove)
        self.list_widget.setSelectionMode(QAbstractItemView.SelectionMode.SingleSelection)
        
        for i, boton_data in enumerate(self.config):
            # Asegurar que el botón tenga todos los campos
            while len(boton_data) < 9:
                boton_data.append(None if len(boton_data) < 8 else 0)  # Duración por defecto 0
            
            nom, col, tipo, tec, carp, tc, team, etiquetas, duracion = boton_data[:9]
            
            item_text = f"{i+1}. {nom} [{tec}] - Tipo: {tipo} - Equipo: {team}"
            if tipo == "auto" and duracion:
                item_text += f" ({duracion/1000}s)"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, boton_data)
            item.setForeground(QColor(tc))
            item.setBackground(QColor(col))
            self.list_widget.addItem(item)
        
        layout.addWidget(self.list_widget)
        
        # Botones de acción
        btn_layout = QHBoxLayout()
        
        btn_agregar = QPushButton("➕ Agregar Botón")
        btn_agregar.clicked.connect(self.agregar_boton)
        btn_layout.addWidget(btn_agregar)
        
        btn_eliminar = QPushButton("🗑️ Eliminar")
        btn_eliminar.clicked.connect(self.eliminar_boton)
        btn_layout.addWidget(btn_eliminar)
        
        btn_editar = QPushButton("✏️ Editar")
        btn_editar.clicked.connect(self.editar_boton)
        btn_layout.addWidget(btn_editar)
        
        btn_duplicar = QPushButton("⎘ Duplicar")
        btn_duplicar.clicked.connect(self.duplicar_boton)
        btn_layout.addWidget(btn_duplicar)
        
        layout.addLayout(btn_layout)
        
        # Botones de movimiento
        move_layout = QHBoxLayout()
        
        btn_up = QPushButton("⬆️ Subir")
        btn_up.clicked.connect(self.mover_arriba)
        move_layout.addWidget(btn_up)
        
        btn_down = QPushButton("⬇️ Bajar")
        btn_down.clicked.connect(self.mover_abajo)
        move_layout.addWidget(btn_down)
        
        move_layout.addStretch()
        layout.addLayout(move_layout)
        
        # Botones de aceptar/cancelar
        btn_box = QHBoxLayout()
        btn_aceptar = QPushButton("💾 Guardar Cambios")
        btn_aceptar.clicked.connect(self.aceptar)
        btn_cancelar = QPushButton("❌ Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        
        btn_box.addWidget(btn_aceptar)
        btn_box.addWidget(btn_cancelar)
        layout.addLayout(btn_box)

    def agregar_boton(self):
        """Agrega un nuevo botón a la botonera"""
        dialog = AddButtonDialog(self)
        if dialog.exec():
            nuevo_boton = dialog.get_button_data()
            if nuevo_boton:
                self.config.append(nuevo_boton)
                self.actualizar_lista()
                QMessageBox.information(self, "Botón Agregado", 
                                      f"Botón '{nuevo_boton[0]}' agregado exitosamente.")

    def eliminar_boton(self):
        """Elimina el botón seleccionado"""
        current_row = self.list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.config):
            boton = self.config[current_row]
            reply = QMessageBox.question(
                self, "Confirmar Eliminación", 
                f"¿Estás seguro de eliminar el botón '{boton[0]}'?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.config.pop(current_row)
                self.list_widget.takeItem(current_row)
                self.actualizar_numeracion()

    def editar_boton(self):
        """Edita el botón seleccionado"""
        current_row = self.list_widget.currentRow()
        if current_row < 0 or current_row >= len(self.config):
            return
            
        boton_original = self.config[current_row]
        dialog = EditButtonDialog(boton_original, self)
        if dialog.exec():
            boton_editado = dialog.get_button_data()
            if boton_editado:
                self.config[current_row] = boton_editado
                self.actualizar_lista()
                QMessageBox.information(self, "Botón Editado", 
                                      f"Botón '{boton_editado[0]}' editado exitosamente.")

    def duplicar_boton(self):
        """Duplica el botón seleccionado"""
        current_row = self.list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.config):
            boton = self.config[current_row].copy()
            boton[0] = f"{boton[0]} (Copia)"
            boton[3] = self.obtener_tecla_libre()  # Nueva tecla libre
            
            self.config.insert(current_row + 1, boton)
            self.actualizar_lista()
            
            QMessageBox.information(self, "Botón Duplicado", 
                                  f"Botón '{boton[0]}' duplicado exitosamente.")

    def obtener_tecla_libre(self):
        """Busca una tecla disponible para un nuevo botón"""
        teclas_ocupadas = {b[3] for b in self.config if len(b) > 3}
        for tecla in "1234567890QWERTYUIOPASDFGHJKLZXCVBNM":
            if tecla not in teclas_ocupadas:
                return tecla
        return "X"  # Si no hay teclas libres

    def mover_arriba(self):
        """Mueve el botón seleccionado hacia arriba"""
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            # Mover en la lista de configuración
            self.config[current_row], self.config[current_row-1] = \
                self.config[current_row-1], self.config[current_row]
            
            # Mover en la lista visual
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row - 1, item)
            self.list_widget.setCurrentRow(current_row - 1)
            
            self.actualizar_numeracion()

    def mover_abajo(self):
        """Mueve el botón seleccionado hacia abajo"""
        current_row = self.list_widget.currentRow()
        if current_row < len(self.config) - 1:
            # Mover en la lista de configuración
            self.config[current_row], self.config[current_row+1] = \
                self.config[current_row+1], self.config[current_row]
            
            # Mover en la lista visual
            item = self.list_widget.takeItem(current_row)
            self.list_widget.insertItem(current_row + 1, item)
            self.list_widget.setCurrentRow(current_row + 1)
            
            self.actualizar_numeracion()

    def actualizar_lista(self):
        """Actualiza completamente la lista visual"""
        self.list_widget.clear()
        for i, boton_data in enumerate(self.config):
            # Asegurar que el botón tenga todos los campos
            while len(boton_data) < 9:
                boton_data.append(None if len(boton_data) < 8 else 0)
            
            nom, col, tipo, tec, carp, tc, team, etiquetas, duracion = boton_data[:9]
            
            item_text = f"{i+1}. {nom} [{tec}] - Tipo: {tipo} - Equipo: {team}"
            if tipo == "auto" and duracion:
                item_text += f" ({duracion/1000}s)"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, boton_data)
            item.setForeground(QColor(tc))
            item.setBackground(QColor(col))
            self.list_widget.addItem(item)

    def actualizar_numeracion(self):
        """Actualiza solo la numeración de los ítems"""
        for i in range(self.list_widget.count()):
            boton = self.config[i]
            # Asegurar que el botón tenga todos los campos
            while len(boton) < 9:
                boton.append(None if len(boton) < 8 else 0)
            
            nom, col, tipo, tec, carp, tc, team, etiquetas, duracion = boton[:9]
            
            item = self.list_widget.item(i)
            item_text = f"{i+1}. {nom} [{tec}] - Tipo: {tipo} - Equipo: {team}"
            if tipo == "auto" and duracion:
                item_text += f" ({duracion/1000}s)"
            
            item.setText(item_text)

    def aceptar(self):
        """Valida y acepta los cambios"""
        # Verificar teclas duplicadas
        teclas = [boton[3] for boton in self.config if len(boton) > 3]
        if len(teclas) != len(set(teclas)):
            QMessageBox.warning(self, "Advertencia", 
                              "Hay teclas de acceso rápido duplicadas. "
                              "Por favor corrige antes de guardar.")
            return
            
        if len(self.config) == 0:
            QMessageBox.warning(self, "Advertencia", 
                              "La botonera no puede estar vacía.")
            return
            
        self.accept()

# ========== DIAGRAMA TÁCTICO ==========
class CanchaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_diagrama = parent
        self.setFixedSize(400, 600)  # TAMAÑO FIJO
        self.drag_pos = None
        self.jugador_arrastrando = None
        self.tamano_ficha = 24

    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # FONDO VERDE CLARO
        painter.fillRect(self.rect(), QColor("#daf9df"))
        
        w, h = self.width(), self.height()  # Siempre 400x600
        
        # LÍNEAS NEGRAS DE LA CANCHA - SOLO LÍNEAS, NO RELLENO
        painter.setPen(QPen(QColor("#000000"), 2))
        painter.setBrush(Qt.BrushStyle.NoBrush)
        
        # Margen alrededor de la cancha
        margen_x = 30
        margen_y = 30
        ancho_cancha = w - 2 * margen_x  # 340
        alto_cancha = h - 2 * margen_y   # 540
        
        # Dibujar contorno de la cancha (rectángulo vacío)
        painter.drawRect(margen_x, margen_y, ancho_cancha, alto_cancha)
        
        # Línea de mitad de cancha
        painter.drawLine(margen_x, h//2, w - margen_x, h//2)
        
        # Círculo central (solo circunferencia)
        radio_central = 25
        painter.drawEllipse(w//2 - radio_central, h//2 - radio_central, 
                          radio_central*2, radio_central*2)
        
        # Punto central (pequeño círculo negro)
        painter.setBrush(QColor("#000000"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(w//2 - 3, h//2 - 3, 6, 6)
        
        # RESETEAR BRUSH PARA ÁREAS
        painter.setBrush(Qt.BrushStyle.NoBrush)
        painter.setPen(QPen(QColor("#000000"), 2))
        
        # ÁREA CHICA - DIMENSIONES FIJAS
        ancho_area_chica = 80
        alto_area_chica = 45

        # Área chica superior (rectángulo vacío)
        x_area_chica_sup = w//2 - ancho_area_chica//2  # 160
        y_area_chica_sup = margen_y
        painter.drawRect(x_area_chica_sup, y_area_chica_sup, ancho_area_chica, alto_area_chica)

        # Área chica inferior (rectángulo vacío)
        y_area_chica_inf = h - margen_y - alto_area_chica  # 525
        painter.drawRect(x_area_chica_sup, y_area_chica_inf, ancho_area_chica, alto_area_chica)

        # ÁREA GRANDE - DIMENSIONES FIJAS
        ancho_area_grande = 150
        alto_area_grande = 90

        # Área grande superior (rectángulo vacío)
        x_area_grande_sup = w//2 - ancho_area_grande//2  # 125
        y_area_grande_sup = margen_y
        painter.drawRect(x_area_grande_sup, y_area_grande_sup, ancho_area_grande, alto_area_grande)

        # Área grande inferior (rectángulo vacío)
        y_area_grande_inf = h - margen_y - alto_area_grande  # 480
        painter.drawRect(x_area_grande_sup, y_area_grande_inf, ancho_area_grande, alto_area_grande)
        
        # PUNTOS DE PENAL - PEQUEÑOS CÍRCULOS NEGROS
        painter.setBrush(QColor("#000000"))
        painter.setPen(Qt.PenStyle.NoPen)
        
        # Punto penal superior
        x_penal_sup = w//2  # 200
        y_penal_sup = margen_y + alto_area_grande - 20  # 100
        painter.drawEllipse(x_penal_sup - 4, y_penal_sup - 4, 8, 8)
        
        # Punto penal inferior
        y_penal_inf = h - margen_y - alto_area_grande + 20  # 500
        painter.drawEllipse(x_penal_sup - 4, y_penal_inf - 4, 8, 8)
        
        # Dibujar jugadores
        if hasattr(self.parent_diagrama, 'jugadores'):
            for jugador in self.parent_diagrama.jugadores:
                x, y, nombre, numero, es_local, color_ficha, color_numero = jugador
                radio = self.tamano_ficha
                
                # Asegurar que el jugador esté dentro de la cancha
                x = max(margen_x + radio, min(w - margen_x - radio, x))
                y = max(margen_y + radio, min(h - margen_y - radio, y))
                
                # Círculo del jugador con borde blanco
                painter.setBrush(QColor(color_ficha))
                painter.setPen(QPen(QColor("#FFFFFF"), 2))
                painter.drawEllipse(x - radio, y - radio, radio*2, radio*2)
                
                # Número del jugador
                painter.setPen(QColor(color_numero))
                font = QFont("Arial", 10, QFont.Weight.Bold)
                painter.setFont(font)
                texto_ancho = painter.fontMetrics().horizontalAdvance(numero)
                texto_alto = painter.fontMetrics().height()
                painter.drawText(x - texto_ancho//2, y + texto_alto//4, numero)
                
                # Nombre del jugador
                if radio > 15:
                    font_nombre = QFont("Arial", 7, QFont.Weight.Normal)
                    painter.setFont(font_nombre)
                    painter.setPen(QColor("#000000"))
                    
                    nombre_corto = nombre[:10]
                    nombre_width = painter.fontMetrics().horizontalAdvance(nombre_corto)
                    painter.setBrush(QColor(255, 255, 255, 200))
                    painter.setPen(Qt.PenStyle.NoPen)
                    painter.drawRect(x - nombre_width//2 - 3, y + radio + 1, 
                                   nombre_width + 6, 14)
                    
                    painter.setPen(QColor("#000000"))
                    painter.drawText(x - nombre_width//2, y + radio + 12, nombre_corto)
    
    def mousePressEvent(self, event):
        if hasattr(self.parent_diagrama, 'jugadores'):
            for i, (x, y, nombre, numero, es_local, color_ficha, color_numero) in enumerate(self.parent_diagrama.jugadores):
                distancia = ((event.pos().x() - x) ** 2 + (event.pos().y() - y) ** 2) ** 0.5
                if distancia < self.tamano_ficha:
                    self.drag_pos = event.pos()
                    self.jugador_arrastrando = i
                    self.update()
                    break
    
    def mouseMoveEvent(self, event):
        if self.jugador_arrastrando is not None and hasattr(self.parent_diagrama, 'jugadores'):
            jugador = list(self.parent_diagrama.jugadores[self.jugador_arrastrando])
            jugador[0] = event.pos().x()
            jugador[1] = event.pos().y()
            self.parent_diagrama.jugadores[self.jugador_arrastrando] = tuple(jugador)
            self.update()
    
    def mouseReleaseEvent(self, event):
        self.jugador_arrastrando = None
        self.drag_pos = None

class DiagramaTactico(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("⚽ " + LANG.get("diagram"))
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.setFixedSize(500, 850)  # TAMAÑO FIJO
        self.formacion = "4-3-3"
        self.jugadores = []
        self.init_ui()
        
    def init_ui(self):
        layout = QVBoxLayout(self)
        
        # Barra de herramientas superior
        toolbar = QHBoxLayout()
        
        # Selector de formación
        self.combo_formacion = QComboBox()
        self.combo_formacion.addItems(["4-3-3", "4-4-2", "4-2-3-1", "3-5-2", "3-4-3", "5-3-2", "Personalizada"])
        self.combo_formacion.currentTextChanged.connect(self.cambiar_formacion)
        toolbar.addWidget(QLabel("Formación:"))
        toolbar.addWidget(self.combo_formacion)
        
        # Botón para guardar formación
        btn_guardar = QPushButton("💾")
        btn_guardar.setToolTip("Guardar formación actual")
        btn_guardar.clicked.connect(self.guardar_formacion_actual)
        toolbar.addWidget(btn_guardar)
        
        # Botón para exportar a PDF
        btn_exportar = QPushButton("📤 PDF")
        btn_exportar.setToolTip("Exportar formaciones a PDF")
        btn_exportar.clicked.connect(self.exportar_canchas_pdf)
        btn_exportar.setStyleSheet("background: #e74c3c; color: white;")
        toolbar.addWidget(btn_exportar)
        
        toolbar.addStretch()
        layout.addLayout(toolbar)
        
        # Panel de controles de personalización
        panel_controles = QHBoxLayout()
        
        # Control de tamaño de fichas
        panel_controles.addWidget(QLabel("Tamaño fichas:"))
        self.slider_tamano = QSlider(Qt.Orientation.Horizontal)
        self.slider_tamano.setRange(15, 40)
        self.slider_tamano.setValue(24)
        self.slider_tamano.valueChanged.connect(self.cambiar_tamano_fichas)
        panel_controles.addWidget(self.slider_tamano)
        
        # Selector de jugador para personalizar
        panel_controles.addWidget(QLabel("Jugador:"))
        self.combo_jugador = QComboBox()
        self.combo_jugador.currentIndexChanged.connect(self.seleccionar_jugador)
        panel_controles.addWidget(self.combo_jugador)
        
        layout.addLayout(panel_controles)
        
        # Panel de personalización de colores
        panel_colores = QHBoxLayout()
        
        # Color de ficha
        btn_color_ficha = QPushButton("🎨 Color ficha")
        btn_color_ficha.clicked.connect(self.cambiar_color_ficha)
        panel_colores.addWidget(btn_color_ficha)
        
        # Color de número
        btn_color_numero = QPushButton("🔢 Color número")
        btn_color_numero.clicked.connect(self.cambiar_color_numero)
        panel_colores.addWidget(btn_color_numero)
        
        # Campo para cambiar nombre
        self.input_nombre = QLineEdit()
        self.input_nombre.setPlaceholderText("Nombre del jugador")
        self.input_nombre.editingFinished.connect(self.cambiar_nombre_jugador)
        panel_colores.addWidget(self.input_nombre)
        
        # Campo para cambiar número
        self.input_numero = QLineEdit()
        self.input_numero.setPlaceholderText("Número")
        self.input_numero.setMaximumWidth(50)
        self.input_numero.editingFinished.connect(self.cambiar_numero_jugador)
        panel_colores.addWidget(self.input_numero)
        
        panel_colores.addStretch()
        layout.addLayout(panel_colores)
        
        # Contenedor para centrar la cancha
        contenedor_cancha = QWidget()
        contenedor_cancha.setFixedSize(420, 620)
        layout_contenedor = QVBoxLayout(contenedor_cancha)
        layout_contenedor.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.cancha_widget = CanchaWidget(self)
        layout_contenedor.addWidget(self.cancha_widget, alignment=Qt.AlignmentFlag.AlignCenter)
        layout.addWidget(contenedor_cancha, stretch=1)
        
        # Panel inferior con controles
        panel_inferior = QHBoxLayout()
        
        # Botón para equipo local/visitante
        self.btn_cambiar_equipo = QPushButton("Equipo Local")
        self.btn_cambiar_equipo.setCheckable(True)
        self.btn_cambiar_equipo.toggled.connect(self.cambiar_equipo)
        panel_inferior.addWidget(self.btn_cambiar_equipo)
        
        # Botón para resetear
        btn_reset = QPushButton("🔄 Resetear")
        btn_reset.setToolTip("Resetear a formación")
        btn_reset.clicked.connect(self.resetear_posiciones)
        panel_inferior.addWidget(btn_reset)
        
        # Botón para cerrar
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(self.close)
        panel_inferior.addWidget(btn_cerrar)
        
        panel_inferior.addStretch()
        layout.addLayout(panel_inferior)
        
        # Inicializar con formación 4-3-3
        self.cambiar_formacion("4-3-3")
        self.actualizar_combo_jugadores()

    def actualizar_combo_jugadores(self):
        self.combo_jugador.clear()
        for i, jugador in enumerate(self.jugadores):
            x, y, nombre, numero, es_local, color_ficha, color_numero = jugador
            self.combo_jugador.addItem(f"{numero} - {nombre}", i)

    def seleccionar_jugador(self, index):
        if index >= 0:
            jugador_idx = self.combo_jugador.itemData(index)
            if jugador_idx is not None and jugador_idx < len(self.jugadores):
                jugador = self.jugadores[jugador_idx]
                self.input_nombre.setText(jugador[2])
                self.input_numero.setText(jugador[3])

    def cambiar_tamano_fichas(self, valor):
        self.cancha_widget.tamano_ficha = valor
        self.cancha_widget.update()

    def cambiar_color_ficha(self):
        index = self.combo_jugador.currentIndex()
        if index >= 0:
            jugador_idx = self.combo_jugador.itemData(index)
            if jugador_idx is not None:
                color = QColorDialog.getColor()
                if color.isValid():
                    jugador = list(self.jugadores[jugador_idx])
                    jugador[5] = color.name()
                    self.jugadores[jugador_idx] = tuple(jugador)
                    self.cancha_widget.update()

    def cambiar_color_numero(self):
        index = self.combo_jugador.currentIndex()
        if index >= 0:
            jugador_idx = self.combo_jugador.itemData(index)
            if jugador_idx is not None:
                color = QColorDialog.getColor()
                if color.isValid():
                    jugador = list(self.jugadores[jugador_idx])
                    jugador[6] = color.name()
                    self.jugadores[jugador_idx] = tuple(jugador)
                    self.cancha_widget.update()

    def cambiar_nombre_jugador(self):
        index = self.combo_jugador.currentIndex()
        nuevo_nombre = self.input_nombre.text()
        if index >= 0 and nuevo_nombre:
            jugador_idx = self.combo_jugador.itemData(index)
            if jugador_idx is not None:
                jugador = list(self.jugadores[jugador_idx])
                jugador[2] = nuevo_nombre
                self.jugadores[jugador_idx] = tuple(jugador)
                self.cancha_widget.update()
                self.actualizar_combo_jugadores()

    def cambiar_numero_jugador(self):
        index = self.combo_jugador.currentIndex()
        nuevo_numero = self.input_numero.text()
        if index >= 0 and nuevo_numero:
            jugador_idx = self.combo_jugador.itemData(index)
            if jugador_idx is not None:
                jugador = list(self.jugadores[jugador_idx])
                jugador[3] = nuevo_numero
                self.jugadores[jugador_idx] = tuple(jugador)
                self.cancha_widget.update()
                self.actualizar_combo_jugadores()

    def cambiar_equipo(self, checked):
        if checked:
            self.btn_cambiar_equipo.setText("Equipo Visitante")
            for i in range(len(self.jugadores)):
                jugador = list(self.jugadores[i])
                jugador[4] = False
                jugador[5] = "#c0392b"  # Rojo para visitante
                jugador[6] = "#ffffff"  # Número blanco
                self.jugadores[i] = tuple(jugador)
        else:
            self.btn_cambiar_equipo.setText("Equipo Local")
            for i in range(len(self.jugadores)):
                jugador = list(self.jugadores[i])
                jugador[4] = True
                jugador[5] = "#2980b9"  # Azul para local
                jugador[6] = "#ffffff"  # Número blanco
                self.jugadores[i] = tuple(jugador)
        self.cancha_widget.update()

    def cambiar_formacion(self, formacion):
        self.formacion = formacion
        
        color_local_ficha = "#2980b9"
        color_local_numero = "#ffffff"
        
        # POSICIONES PARA CANCHA DE 400x600 (TAMAÑO FIJO)
        formaciones_predefinidas = {
            "4-3-3": [
                # Portero
                (200, 520, "POR", "1", True, color_local_ficha, color_local_numero),
                # Defensa (4)
                (120, 470, "LD", "2", True, color_local_ficha, color_local_numero),
                (180, 470, "DFC", "4", True, color_local_ficha, color_local_numero),
                (220, 470, "DFC", "5", True, color_local_ficha, color_local_numero),
                (280, 470, "LI", "3", True, color_local_ficha, color_local_numero),
                # Medio (3)
                (120, 380, "MCD", "6", True, color_local_ficha, color_local_numero),
                (200, 380, "MC", "8", True, color_local_ficha, color_local_numero),
                (280, 380, "MCD", "7", True, color_local_ficha, color_local_numero),
                # Delantera (3)
                (120, 250, "ED", "11", True, color_local_ficha, color_local_numero),
                (200, 250, "DC", "9", True, color_local_ficha, color_local_numero),
                (280, 250, "EI", "10", True, color_local_ficha, color_local_numero)
            ],
            "4-4-2": [
                (200, 520, "POR", "1", True, color_local_ficha, color_local_numero),
                (120, 470, "LD", "2", True, color_local_ficha, color_local_numero),
                (180, 470, "DFC", "4", True, color_local_ficha, color_local_numero),
                (220, 470, "DFC", "5", True, color_local_ficha, color_local_numero),
                (280, 470, "LI", "3", True, color_local_ficha, color_local_numero),
                (120, 350, "MD", "7", True, color_local_ficha, color_local_numero),
                (180, 350, "MCD", "6", True, color_local_ficha, color_local_numero),
                (220, 350, "MCD", "8", True, color_local_ficha, color_local_numero),
                (280, 350, "MI", "11", True, color_local_ficha, color_local_numero),
                (180, 220, "DC", "9", True, color_local_ficha, color_local_numero),
                (220, 220, "DC", "10", True, color_local_ficha, color_local_numero)
            ],
            "4-2-3-1": [
                (200, 520, "POR", "1", True, color_local_ficha, color_local_numero),
                (120, 470, "LD", "2", True, color_local_ficha, color_local_numero),
                (180, 470, "DFC", "4", True, color_local_ficha, color_local_numero),
                (220, 470, "DFC", "5", True, color_local_ficha, color_local_numero),
                (280, 470, "LI", "3", True, color_local_ficha, color_local_numero),
                (180, 400, "MCD", "6", True, color_local_ficha, color_local_numero),
                (220, 400, "MCD", "8", True, color_local_ficha, color_local_numero),
                (120, 280, "MP", "7", True, color_local_ficha, color_local_numero),
                (200, 280, "MP", "10", True, color_local_ficha, color_local_numero),
                (280, 280, "MP", "11", True, color_local_ficha, color_local_numero),
                (200, 200, "DC", "9", True, color_local_ficha, color_local_numero)
            ],
            "3-5-2": [
                (200, 520, "POR", "1", True, color_local_ficha, color_local_numero),
                (150, 470, "DFC", "3", True, color_local_ficha, color_local_numero),
                (200, 470, "DFC", "4", True, color_local_ficha, color_local_numero),
                (250, 470, "DFC", "5", True, color_local_ficha, color_local_numero),
                (120, 350, "LD", "2", True, color_local_ficha, color_local_numero),
                (160, 350, "MCD", "6", True, color_local_ficha, color_local_numero),
                (200, 350, "MC", "8", True, color_local_ficha, color_local_numero),
                (240, 350, "MCD", "7", True, color_local_ficha, color_local_numero),
                (280, 350, "LI", "11", True, color_local_ficha, color_local_numero),
                (180, 220, "DC", "9", True, color_local_ficha, color_local_numero),
                (220, 220, "DC", "10", True, color_local_ficha, color_local_numero)
            ],
            "3-4-3": [
                (200, 520, "POR", "1", True, color_local_ficha, color_local_numero),
                (150, 470, "DFC", "3", True, color_local_ficha, color_local_numero),
                (200, 470, "DFC", "4", True, color_local_ficha, color_local_numero),
                (250, 470, "DFC", "5", True, color_local_ficha, color_local_numero),
                (120, 350, "LD", "2", True, color_local_ficha, color_local_numero),
                (180, 350, "MCD", "6", True, color_local_ficha, color_local_numero),
                (220, 350, "MCD", "8", True, color_local_ficha, color_local_numero),
                (280, 350, "LI", "7", True, color_local_ficha, color_local_numero),
                (120, 220, "ED", "11", True, color_local_ficha, color_local_numero),
                (200, 220, "DC", "9", True, color_local_ficha, color_local_numero),
                (280, 220, "EI", "10", True, color_local_ficha, color_local_numero)
            ],
            "5-3-2": [
                (200, 520, "POR", "1", True, color_local_ficha, color_local_numero),
                (100, 470, "LD", "2", True, color_local_ficha, color_local_numero),
                (150, 470, "DFC", "3", True, color_local_ficha, color_local_numero),
                (200, 470, "DFC", "4", True, color_local_ficha, color_local_numero),
                (250, 470, "DFC", "5", True, color_local_ficha, color_local_numero),
                (300, 470, "LI", "6", True, color_local_ficha, color_local_numero),
                (150, 350, "MCD", "7", True, color_local_ficha, color_local_numero),
                (200, 350, "MC", "8", True, color_local_ficha, color_local_numero),
                (250, 350, "MCD", "9", True, color_local_ficha, color_local_numero),
                (180, 220, "DC", "10", True, color_local_ficha, color_local_numero),
                (220, 220, "DC", "11", True, color_local_ficha, color_local_numero)
            ]
        }
        
        if formacion in formaciones_predefinidas:
            self.jugadores = formaciones_predefinidas[formacion].copy()
            self.cancha_widget.update()
            self.actualizar_combo_jugadores()

    def crear_imagen_cancha(self, formacion_data):
        """Crea una imagen PNG de la cancha para PDF"""
        try:
            import tempfile
            import uuid
            
            # Crear archivo temporal
            temp_filename = f"cancha_{uuid.uuid4().hex}.png"
            temp_path = os.path.join(tempfile.gettempdir(), temp_filename)
            
            # Crear pixmap del tamaño fijo
            pixmap = QPixmap(400, 600)
            
            # Dibujar la cancha
            painter = QPainter(pixmap)
            painter.setRenderHint(QPainter.RenderHint.Antialiasing)
            
            # Fondo verde claro
            painter.fillRect(pixmap.rect(), QColor("#daf9df"))
            
            w, h = 400, 600
            
            # Líneas de la cancha
            painter.setPen(QPen(QColor("#000000"), 2))
            painter.setBrush(Qt.BrushStyle.NoBrush)
            
            # Contorno
            margen_x, margen_y = 30, 30
            ancho_cancha = w - 2 * margen_x
            alto_cancha = h - 2 * margen_y
            
            painter.drawRect(margen_x, margen_y, ancho_cancha, alto_cancha)
            
            # Línea de mitad
            painter.drawLine(margen_x, h//2, w - margen_x, h//2)
            
            # Círculo central
            radio_central = 25
            painter.drawEllipse(w//2 - radio_central, h//2 - radio_central, 
                              radio_central*2, radio_central*2)
            
            # Punto central
            painter.setBrush(QColor("#000000"))
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawEllipse(w//2 - 3, h//2 - 3, 6, 6)
            
            # Resetear brush para áreas
            painter.setBrush(Qt.BrushStyle.NoBrush)
            painter.setPen(QPen(QColor("#000000"), 2))
            
            # Áreas chicas
            ancho_area_chica = 80
            alto_area_chica = 45
            x_area_chica_sup = w//2 - ancho_area_chica//2
            y_area_chica_sup = margen_y
            painter.drawRect(x_area_chica_sup, y_area_chica_sup, ancho_area_chica, alto_area_chica)
            y_area_chica_inf = h - margen_y - alto_area_chica
            painter.drawRect(x_area_chica_sup, y_area_chica_inf, ancho_area_chica, alto_area_chica)
            
            # Áreas grandes
            ancho_area_grande = 150
            alto_area_grande = 90
            x_area_grande_sup = w//2 - ancho_area_grande//2
            y_area_grande_sup = margen_y
            painter.drawRect(x_area_grande_sup, y_area_grande_sup, ancho_area_grande, alto_area_grande)
            y_area_grande_inf = h - margen_y - alto_area_grande
            painter.drawRect(x_area_grande_sup, y_area_grande_inf, ancho_area_grande, alto_area_grande)
            
            # Puntos de penal
            painter.setBrush(QColor("#000000"))
            painter.setPen(Qt.PenStyle.NoPen)
            x_penal_sup = w//2
            y_penal_sup = margen_y + alto_area_grande - 20
            painter.drawEllipse(x_penal_sup - 4, y_penal_sup - 4, 8, 8)
            y_penal_inf = h - margen_y - alto_area_grande + 20
            painter.drawEllipse(x_penal_sup - 4, y_penal_inf - 4, 8, 8)
            
            # Dibujar jugadores
            tamano_ficha = 24
            for jugador in formacion_data['jugadores']:
                x, y, nombre, numero, es_local, color_ficha, color_numero = jugador
                
                # Ajustar coordenadas
                x = min(max(margen_x + tamano_ficha, x), w - margen_x - tamano_ficha)
                y = min(max(margen_y + tamano_ficha, y), h - margen_y - tamano_ficha)
                
                # Círculo del jugador
                painter.setBrush(QColor(color_ficha))
                painter.setPen(QPen(QColor("#FFFFFF"), 2))
                painter.drawEllipse(x - tamano_ficha, y - tamano_ficha, 
                                  tamano_ficha*2, tamano_ficha*2)
                
                # Número
                painter.setPen(QColor(color_numero))
                font = QFont("Arial", 10, QFont.Weight.Bold)
                painter.setFont(font)
                texto_ancho = painter.fontMetrics().horizontalAdvance(numero)
                texto_alto = painter.fontMetrics().height()
                painter.drawText(x - texto_ancho//2, y + texto_alto//4, numero)
            
            painter.end()
            
            # Guardar imagen
            if not pixmap.save(temp_path, "PNG"):
                return None
            
            return temp_path
            
        except Exception as e:
            print(f"Error creando imagen: {e}")
            return None

    def exportar_canchas_pdf(self):
        """Exporta las canchas a PDF - 3 por página"""

        # Obtener formaciones guardadas del gestor principal
        formaciones = []
        if hasattr(self.parent(), 'gestor_formaciones'):
            formaciones = self.parent().gestor_formaciones.formaciones_guardadas
        
        # Incluir formación actual
        formacion_actual = {
            "minuto": self.parent().player.position() // 1000 if hasattr(self.parent(), 'player') else 0,
            "formacion": self.formacion,
            "jugadores": self.jugadores.copy(),
            "notas": "Formación actual",
            "es_local": self.jugadores[0][4] if self.jugadores else True
        }
        
        todas_formaciones = [formacion_actual] + formaciones
        
        if len(todas_formaciones) == 0:
            QMessageBox.warning(self, "Sin formaciones", "No hay formaciones para exportar.")
            return
        
        # Pedir nombre del archivo
        nombre, ok = QInputDialog.getText(
            self, "Exportar PDF", 
            "Nombre del archivo PDF:",
            text=f"formaciones_{time.strftime('%Y%m%d_%H%M')}"
        )
        
        if not ok or not nombre:
            return
        
        # Asegurar carpeta de exportación
        if not os.path.exists(CARPETA_EXPORT):
            os.makedirs(CARPETA_EXPORT, exist_ok=True)
        
        ruta_salida = os.path.join(CARPETA_EXPORT, f"{nombre}.pdf")
        
        try:
            # Crear documento horizontal
            doc = SimpleDocTemplate(ruta_salida, pagesize=landscape(A4))
            elements = []
            styles = getSampleStyleSheet()
            
            # Título
            titulo = Paragraph("<b>⚽ REPORTE DE FORMACIONES TÁCTICAS</b>", styles['Title'])
            elements.append(titulo)
            elements.append(Spacer(1, 10))
            
            # Información
            info = Paragraph(
                f"<b>Fecha:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}<br/>"
                f"<b>Total de formaciones:</b> {len(todas_formaciones)}<br/>"
                f"<b>Sistema:</b> {SYS_CONFIG['system']}",
                styles['Normal']
            )
            elements.append(info)
            elements.append(Spacer(1, 20))
            
            archivos_temp = []
            
            # Procesar formaciones en grupos de 3
            for i in range(0, len(todas_formaciones), 3):
                # Si no es la primera página, agregar salto
                if i > 0:
                    elements.append(PageBreak())
                    elements.append(Spacer(1, 10))
                
                # Tomar 3 formaciones
                grupo = todas_formaciones[i:i+3]
                datos_tabla = []
                
                for j, formacion_data in enumerate(grupo):
                    equipo = "LOCAL" if formacion_data.get('es_local', True) else "VISITANTE"
                    color_equipo = "#2980b9" if equipo == "LOCAL" else "#c0392b"
                    
                    minuto = formacion_data['minuto']
                    tiempo = f"{minuto//60}:{minuto%60:02d}" if isinstance(minuto, int) else "0:00"
                    
                    # Crear imagen
                    img_path = self.crear_imagen_cancha(formacion_data)
                    if img_path and os.path.exists(img_path):
                        archivos_temp.append(img_path)
                        img = Image(img_path, width=3.5*inch, height=5.25*inch)
                    else:
                        img = Paragraph("<i>Sin imagen</i>", styles['Normal'])
                    
                    # Información
                    info_formacion = Paragraph(
                        f"<b><font color='{color_equipo}'>{formacion_data['formacion']}</font></b><br/>"
                        f"<i>Minuto: {tiempo}<br/>"
                        f"Equipo: {equipo}</i><br/>"
                        f"{formacion_data.get('notas', '')[:30]}...",
                        styles['Normal']
                    )
                    
                    datos_tabla.append([img, info_formacion])
                
                # Completar con celdas vacías si hay menos de 3
                while len(datos_tabla) < 3:
                    datos_tabla.append([Spacer(1, 1), Spacer(1, 1)])
                
                # Crear tabla
                tabla = Table(datos_tabla, colWidths=[3.5*inch, 3.5*inch, 3.5*inch])
                tabla.setStyle(TableStyle([
                    ('ALIGN', (0, 0), (-1, -1), 'CENTER'),
                    ('VALIGN', (0, 0), (-1, -1), 'TOP'),
                    ('GRID', (0, 0), (-1, -1), 0.5, colors.grey),
                    ('PADDING', (0, 0), (-1, -1), 10),
                ]))
                
                elements.append(tabla)
                elements.append(Spacer(1, 20))
            
            # Generar PDF
            doc.build(elements)
            
            # Limpiar archivos temporales
            for archivo in archivos_temp:
                try:
                    if os.path.exists(archivo):
                        os.unlink(archivo)
                except:
                    pass
            
            # Mensaje de éxito
            QMessageBox.information(
                self, "PDF Generado",
                f"Reporte exportado exitosamente a:\n{ruta_salida}\n\n"
                f"Formaciones incluidas: {len(todas_formaciones)}\n"
                f"Ubicación: {CARPETA_EXPORT}"
            )
            
            # Abrir PDF
            try:
                if sys.platform == "darwin":
                    subprocess.run(["open", ruta_salida])
                elif sys.platform == "win32":
                    os.startfile(ruta_salida)
                elif sys.platform == "linux":
                    subprocess.run(["xdg-open", ruta_salida])
            except:
                pass
                
        except Exception as e:
            QMessageBox.critical(
                self, "Error al generar PDF",
                f"No se pudo generar el PDF:\n\n{str(e)[:200]}"
            )
            traceback.print_exc()

    def guardar_formacion_actual(self):
        """Guarda la formación actual en el gestor"""
        minuto_actual = 0
        if hasattr(self.parent(), 'player'):
            minuto_actual = self.parent().player.position() // 1000  # Convertir a segundos
        
        es_local = True
        if len(self.jugadores) > 0:
            es_local = self.jugadores[0][4]
        
        datos_formacion = {
            "minuto": minuto_actual,
            "formacion": self.formacion,
            "jugadores": self.jugadores.copy(),
            "timestamp": time.time(),
            "tamano_fichas": self.cancha_widget.tamano_ficha,
            "es_local": es_local
        }
        
        notas, ok = QInputDialog.getMultiLineText(
            self, "Notas de la formación",
            "Agrega notas para esta formación:",
            f"Formación {self.formacion}"
        )
        
        if ok:
            datos_formacion["notas"] = notas
        
        if hasattr(self.parent(), 'gestor_formaciones'):
            self.parent().gestor_formaciones.agregar_formacion(minuto_actual, datos_formacion)
            equipo = "Local" if es_local else "Visitante"
            QMessageBox.information(
                self, "Formación guardada",
                f"Formación {self.formacion} ({equipo}) guardada en minuto {minuto_actual//60}:{minuto_actual%60:02d}"
            )

    def resetear_posiciones(self):
        self.cambiar_formacion(self.formacion)

    def closeEvent(self, event):
        if hasattr(self.parent(), 'diagrama_tactico'):
            self.parent().diagrama_tactico = None
        event.accept()

# ========== DIÁLOGO DE EXPORTACIÓN ==========
class ExportDialog(QDialog):
    def __init__(self, video_path, clips, parent=None):
        super().__init__(parent)
        self.setWindowTitle(LANG.get("export"))
        self.resize(500, 450)
        self.video_path = video_path
        self.clips = clips
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        # Información del proyecto
        info_group = QGroupBox("Información del Proyecto")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"Clips a exportar: {len(self.clips)}"))
        info_layout.addWidget(QLabel(f"Video fuente: {os.path.basename(self.video_path)}"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Configuración de exportación
        config_group = QGroupBox("Configuración de Exportación")
        config_layout = QVBoxLayout()
        
        # Nombre del archivo
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit("Exportacion_" + time.strftime("%Y%m%d_%H%M"))
        name_layout.addWidget(self.name_input)
        config_layout.addLayout(name_layout)
        
        # Formato
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "AVI", "MOV", "MKV"])
        format_layout.addWidget(self.format_combo)
        config_layout.addLayout(format_layout)
        
        # Codec
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Codec:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems([
            "Copia directa (rápido)",
            "H.264 (compatible)",
            "HEVC (alta calidad)",
            "VP9 (web optimizado)"
        ])
        codec_layout.addWidget(self.codec_combo)
        config_layout.addLayout(codec_layout)
        
        # Calidad
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Calidad:"))
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 5)
        self.quality_slider.setValue(3)
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(QLabel("Media"))
        config_layout.addLayout(quality_layout)
        
        # Opciones adicionales
        self.include_timestamp = QCheckBox("Incluir marca de tiempo en video")
        self.include_timestamp.setChecked(True)
        config_layout.addWidget(self.include_timestamp)
        
        self.include_logo = QCheckBox("Incluir logo del equipo")
        config_layout.addWidget(self.include_logo)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        # Barra de progreso
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        # Etiqueta de estado
        self.status_label = QLabel("Listo para exportar")
        layout.addWidget(self.status_label)
        
        # Botones
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("🚀 Exportar")
        self.export_btn.clicked.connect(self.iniciar_exportacion)
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def iniciar_exportacion(self):
        """Inicia el proceso de exportación"""
        nombre = self.name_input.text().strip()
        if not nombre:
            QMessageBox.warning(self, "Error", "Por favor ingresa un nombre para la exportación.")
            return
        
        # Mapear codec
        codec_map = {
            "Copia directa (rápido)": "copy",
            "H.264 (compatible)": "libx264",
            "HEVC (alta calidad)": "libx265",
            "VP9 (web optimizado)": "libvpx-vp9"
        }
        
        codec = codec_map.get(self.codec_combo.currentText(), "copy")
        formato = self.format_combo.currentText().lower()
        
        # Crear carpeta si no existe
        if not os.path.exists(CARPETA_EXPORT):
            os.makedirs(CARPETA_EXPORT, exist_ok=True)
        
        output_path = os.path.join(CARPETA_EXPORT, f"{nombre}.{formato}")
        
        # Verificar si el archivo ya existe
        if os.path.exists(output_path):
            reply = QMessageBox.question(
                self, "Archivo Existente",
                f"El archivo '{nombre}.{formato}' ya existe.\n¿Deseas reemplazarlo?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            if reply == QMessageBox.StandardButton.No:
                return
        
        # Crear y ejecutar worker con timestamp
        self.worker = ExportWorker(self.video_path, self.clips, output_path, codec, self.include_timestamp.isChecked())
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.exportacion_completada)
        self.worker.error.connect(self.exportacion_error)
        
        self.export_btn.setEnabled(False)
        self.cancel_btn.setText("Cancelar Exportación")
        self.status_label.setText("Exportando...")
        self.worker.start()

    def exportacion_completada(self, output_path):
        """Maneja la exportación completada"""
        QMessageBox.information(
            self, "Exportación Completada", 
            f"Proyecto exportado exitosamente a:\n{output_path}"
        )
        self.accept()

    def exportacion_error(self, error_msg):
        """Maneja errores durante la exportación"""
        QMessageBox.critical(
            self, "Error de Exportación", 
            f"Error durante la exportación:\n{error_msg}"
        )
        self.export_btn.setEnabled(True)
        self.cancel_btn.setText("Cancelar")
        self.status_label.setText("Error - Listo para reintentar")

# ========== GESTIÓN DE PROYECTOS ==========
class ProyectoManager:
    @staticmethod
    def guardar_proyecto(nombre_proyecto, video_path, cortes, config, metadata=None):
        """Guarda un proyecto en disco"""
        proyecto_data = {
            "nombre": nombre_proyecto,
            "fecha_creacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "video_path": video_path,
            "cortes": cortes,
            "botonera_config": config,
            "metadata": metadata or {}
        }
        
        # Crear carpeta del proyecto
        proyecto_folder = os.path.join(CARPETA_PROYECTOS, nombre_proyecto)
        if not os.path.exists(proyecto_folder):
            os.makedirs(proyecto_folder)
        
        # Crear subcarpetas
        capturas_folder = os.path.join(proyecto_folder, "Capturas")
        clips_folder = os.path.join(proyecto_folder, "Clips")
        
        for folder in [capturas_folder, clips_folder]:
            if not os.path.exists(folder):
                os.makedirs(folder)
        
        # Guardar archivo del proyecto
        proyecto_file = os.path.join(proyecto_folder, f"{nombre_proyecto}.mca")
        with open(proyecto_file, 'w') as f:
            json.dump(proyecto_data, f, indent=2, ensure_ascii=False)
        
        return proyecto_file

    @staticmethod
    def cargar_proyecto(archivo_proyecto):
        """Carga un proyecto desde disco"""
        try:
            with open(archivo_proyecto, 'r', encoding='utf-8') as f:
                proyecto_data = json.load(f)
            
            # Verificar que el video aún existe
            video_path = proyecto_data.get("video_path", "")
            if not os.path.exists(video_path):
                # Buscar en carpetas alternativas
                video_name = os.path.basename(video_path)
                proyecto_folder = os.path.dirname(archivo_proyecto)
                possible_paths = [
                    os.path.join(proyecto_folder, video_name),
                    os.path.join(CARPETA_PROYECTOS, video_name),
                    video_path  # Intentar de nuevo
                ]
                
                for path in possible_paths:
                    if os.path.exists(path):
                        proyecto_data["video_path"] = path
                        break
                else:
                    # Si no se encuentra, marcar como no disponible
                    proyecto_data["video_missing"] = True
            
            return proyecto_data
            
        except Exception as e:
            raise Exception(f"Error al cargar proyecto: {str(e)}")

    @staticmethod
    def listar_proyectos():
        """Lista todos los proyectos disponibles"""
        proyectos = []
        if not os.path.exists(CARPETA_PROYECTOS):
            return proyectos
        
        for item in os.listdir(CARPETA_PROYECTOS):
            proyecto_folder = os.path.join(CARPETA_PROYECTOS, item)
            if os.path.isdir(proyecto_folder):
                # Buscar archivo .mca
                for file in os.listdir(proyecto_folder):
                    if file.endswith('.mca'):
                        proyecto_file = os.path.join(proyecto_folder, file)
                        try:
                            with open(proyecto_file, 'r', encoding='utf-8') as f:
                                proyecto_data = json.load(f)
                            
                            # Obtener información básica
                            video_path = proyecto_data.get("video_path", "")
                            video_exists = os.path.exists(video_path)
                            
                            # Contar clips
                            total_clips = len(proyecto_data.get("cortes", []))
                            
                            proyectos.append({
                                "nombre": proyecto_data.get("nombre", item),
                                "archivo": proyecto_file,
                                "fecha": proyecto_data.get("fecha_creacion", ""),
                                "video": video_path,
                                "video_exists": video_exists,
                                "total_clips": total_clips,
                                "carpeta": proyecto_folder
                            })
                        except:
                            pass
        return proyectos

    @staticmethod
    def eliminar_proyecto(nombre_proyecto):
        """Elimina un proyecto"""
        proyecto_folder = os.path.join(CARPETA_PROYECTOS, nombre_proyecto)
        if os.path.exists(proyecto_folder):
            import shutil
            try:
                shutil.rmtree(proyecto_folder)
                return True
            except:
                return False
        return False

# ========== GESTOR DE FORMACIONES ==========
class GestorFormaciones:
    def __init__(self):
        self.formaciones_guardadas = []
        
    def agregar_formacion(self, minuto, diagrama_data):
        """Agrega una formación al gestor"""
        self.formaciones_guardadas.append({
            "minuto": minuto,
            "formacion": diagrama_data["formacion"],
            "jugadores": diagrama_data["jugadores"].copy(),
            "timestamp": time.time(),
            "notas": diagrama_data.get("notas", ""),
            "es_local": diagrama_data.get("es_local", True),
            "tamano_fichas": diagrama_data.get("tamano_fichas", 24)
        })
        
        # Ordenar por minuto
        self.formaciones_guardadas.sort(key=lambda x: x['minuto'])
    
    def obtener_formaciones_por_equipo(self, equipo_local=True):
        """Filtra formaciones por equipo"""
        return [f for f in self.formaciones_guardadas if f.get('es_local', True) == equipo_local]
    
    def limpiar_formaciones(self):
        """Limpia todas las formaciones guardadas"""
        self.formaciones_guardadas = []
    
    def exportar_a_json(self, archivo_salida):
        """Exporta las formaciones a un archivo JSON"""
        try:
            with open(archivo_salida, 'w') as f:
                json.dump(self.formaciones_guardadas, f, indent=2)
            return True
        except:
            return False

# ========== CLASE PRINCIPAL ==========
class MatchClipAnalyzer(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"Match Clip Analyzer - V12.0 ({SYS_CONFIG['system']})")
        self.resize(1400, 950)
        
        # **AGREGA ESTO para asegurar que la ventana siempre pueda recibir foco**
        self.setFocusPolicy(Qt.FocusPolicy.StrongFocus)
        
        # Variables de estado
        self.video_path = ""
        self.cortes_activos = {}
        self.botones_widgets = {}
        self.velocidades = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0]
        self.vel_idx = 3
        self.proyecto_actual = None
        self.proyecto_modificado = False
        self.nombre_proyecto_actual = ""
        
        # Cargar configuración
        self.config = self.cargar_config_botones()
        self.equipos = self.cargar_config_equipos()
        
        # Inicializar multimedia
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Inicializar gestores
        self.diagrama_tactico = None
        self.gestor_formaciones = GestorFormaciones()
        
        # Inicializar variables para listas
        self.listas_widgets = {}
        self.labels_contadores = {}
        
        # Inicializar interfaz
        self.init_ui()
        
        # ====== CONEXIONES MOVIDAS AQUÍ ======
        self.setup_connections()  # <-- ¡IMPORTANTE! Esto va DESPUÉS de init_ui()
        # =====================================
        
        # Temporizadores
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.actualizar_parpadeo)
        self.blink_timer.start(500)
        
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.autoguardar_proyecto)
        self.autosave_timer.start(300000)  # 5 minutos
        
        # Mostrar estado inicial
        self.actualizar_estado_proyecto()
        
        # AL FINAL DE ESTE __init__ AGREGAR:
        self.setFocus()  # <--- ESTA LÍNEA       
    def setup_connections(self):
        """Conectar señales DESPUÉS de que los widgets existen"""
        # Ahora SÍ podemos usar self.video_widget porque ya fue creado
        self.player.setVideoOutput(self.video_widget)
        self.player.positionChanged.connect(self.actualizar_pos)
        self.player.durationChanged.connect(self.actualizar_dur)
        
        # Y también los botones ya existen
        self.btn_back_5.clicked.connect(lambda: self.saltar_tiempo(-5000))
        self.btn_forward_5.clicked.connect(lambda: self.saltar_tiempo(5000))
        self.btn_play_pause.clicked.connect(self.toggle_play_pause)
        self.btn_frame_back.clicked.connect(self.frame_atras)
        self.btn_frame_forward.clicked.connect(self.frame_adelante)
        self.speed_combo.currentTextChanged.connect(self.cambiar_velocidad_combo)
        self.btn_mark_in.clicked.connect(self.marcar_inicio)
        self.btn_mark_out.clicked.connect(self.marcar_fin)

    def cargar_config_botones(self):
        """Carga la configuración de botones por defecto"""
        default = [
            ["SALIDA", "#2980b9", "manual", "1", "Salida_Propia", "#3498db", "local", [], 0],
            ["DESARROLLO", "#2980b9", "manual", "2", "Desarrollo_Propio", "#3498db", "local", [], 0],
            ["TRANSICIÓN", "#2980b9", "auto", "3", "Transicion_Propia", "#3498db", "local", [], 10000],
            ["FINALIZACIÓN", "#2980b9", "auto", "4", "Finalizacion_Propia", "#3498db", "local", [], 10000],
            ["SALIDA RIVAL", "#c0392b", "manual", "5", "Salida_Rival", "#e74c3c", "visitante", [], 0],
            ["DESARROLLO RIVAL", "#c0392b", "manual", "6", "Desarrollo_Rival", "#e74c3c", "visitante", [], 0],
            ["TRANSICIÓN RIVAL", "#c0392b", "auto", "7", "Transicion_Rival", "#e74c3c", "visitante", [], 10000],
            ["FINALIZACIÓN RIVAL", "#c0392b", "auto", "8", "Finalizacion_Rival", "#e74c3c", "visitante", [], 10000]
        ]
        
        config_file = os.path.join(CARPETA_RAIZ, "button_config.json")
        if os.path.exists(config_file):
            try:
                with open(config_file, 'r') as f:
                    return json.load(f)
            except:
                return default
        return default

    def cargar_config_equipos(self):
        """Carga la configuración de equipos"""
        default = {
            "local": {"nombre": "Equipo Local", "logo": None, "color": "#2980b9"},
            "visitante": {"nombre": "Equipo Visitante", "logo": None, "color": "#c0392b"}
        }
        
        if os.path.exists(ARCHIVO_CONFIG):
            try:
                with open(ARCHIVO_CONFIG, 'r') as f:
                    config = json.load(f)
                    if "teams" in config:
                        default.update(config["teams"])
            except:
                pass
        
        return default

    def init_ui(self):
        """Inicializa la interfaz de usuario"""
        self.setStyleSheet("""
            QMainWindow { 
                background-color: #0c0c0c; 
            }
            QLabel { 
                color: white; 
                font-family: Arial, sans-serif;
            }
            QPushButton {
                font-family: Arial, sans-serif;
                font-weight: bold;
                padding: 5px;
                border-radius: 3px;
            }
            QListWidget {
                background-color: #151515;
                color: white;
                border: 1px solid #333;
                border-radius: 3px;
            }
            QGroupBox {
                color: white;
                border: 2px solid #3498db;
                border-radius: 5px;
                margin-top: 10px;
                font-weight: bold;
            }
            QGroupBox::title {
                subcontrol-origin: margin;
                left: 10px;
                padding: 0 5px 0 5px;
            }
        """)
        
        central = QWidget()
        self.setCentralWidget(central)
        layout_principal = QVBoxLayout(central)
        
        # Crear barra de menú
        self.crear_barra_menu()
        
        # Área superior con video y panel
        superior = QHBoxLayout()
        
        # Contenedor del video
        self.video_cont = QWidget()
        v_layout = QHBoxLayout(self.video_cont)
        v_layout.setContentsMargins(0, 0, 0, 0)
        
        self.video_widget = QVideoWidget()
        v_layout.addWidget(self.video_widget)
        
        # Botón para mostrar/ocultar panel
        self.btn_toggle = QPushButton(">")
        self.btn_toggle.setFixedWidth(20)
        self.btn_toggle.clicked.connect(self.toggle_panel)
        v_layout.addWidget(self.btn_toggle)
        
        superior.addWidget(self.video_cont, stretch=4)
        
        # Panel derecho - CREAR CORRECTAMENTE
        self.panel_derecho = QWidget()
        self.panel_derecho.setFixedWidth(350)
        self.panel_derecho.setObjectName("panel_derecho")
        
        # Separar botones por equipo
        equipo_a_botones = []
        rival_botones = []
        
        for boton in self.config:
            if len(boton) > 6 and boton[6] == "visitante":
                rival_botones.append(boton)
            else:
                equipo_a_botones.append(boton)
        
        # Crear layout para el panel
        layout_listas = QHBoxLayout(self.panel_derecho)
        
        # Columna Equipo Local
        col_izq = QVBoxLayout()
        if equipo_a_botones:
            header_a = QLabel(self.equipos["local"]["nombre"])
            header_a.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0, 
                                          stop:0 #2980b9, stop:1 #3498db);
                font-weight: bold; 
                padding: 8px;
                border-radius: 5px;
            """)
            header_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_izq.addWidget(header_a)
            
            for boton in equipo_a_botones:
                self.crear_categoria_widget(boton, col_izq, "#2980b9")
        
        # Columna Equipo Visitante
        col_der = QVBoxLayout()
        if rival_botones:
            header_r = QLabel(self.equipos["visitante"]["nombre"])
            header_r.setStyleSheet("""
                background: qlineargradient(x1:0, y1:0, x2:1, y2:0,
                                          stop:0 #c0392b, stop:1 #e74c3c);
                font-weight: bold;
                padding: 8px;
                border-radius: 5px;
            """)
            header_r.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_der.addWidget(header_r)
            
            for boton in rival_botones:
                self.crear_categoria_widget(boton, col_der, "#c0392b")
        
        layout_listas.addLayout(col_izq)
        layout_listas.addLayout(col_der)
        superior.addWidget(self.panel_derecho)
        layout_principal.addLayout(superior, stretch=5)
        
        # Fila de tiempo y controles
        fila_tiempo = QHBoxLayout()
        
        self.btn_timer = QPushButton("00:00 / 00:00")
        self.btn_timer.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        self.btn_timer.setStyleSheet("""
            QPushButton {
                background: #2c3e50;
                color: white;
                padding: 8px;
                font-family: 'Courier New', monospace;
                font-weight: bold;
            }
        """)
        self.btn_timer.clicked.connect(self.ir_a_tiempo_manual)
        # ==== AGREGAR ESTO INMEDIATAMENTE DESPUÉS ====        
        # ================= CONTROLES DE VIDEO =================
        self.btn_back_5 = QPushButton("⏪ 5s")
        self.btn_back_5.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_play_pause = QPushButton("⏯")
        self.btn_play_pause.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_forward_5 = QPushButton("5s ⏩")
        self.btn_forward_5.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.btn_frame_back = QPushButton("◀︎ frame")
        self.btn_frame_back.setFocusPolicy(Qt.FocusPolicy.NoFocus)

        self.btn_frame_forward = QPushButton("frame ▶︎")
        self.btn_frame_forward.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        
        self.speed_combo = QComboBox()
        self.speed_combo.addItems(["0.5x", "1x", "1.5x", "2x"])
        self.speed_combo.setCurrentText("1x")
        
        self.time_label = QLabel("00:00.000")
        self.time_label.setMinimumWidth(80)
        self.time_label.setAlignment(Qt.AlignmentFlag.AlignCenter)
        
        self.btn_mark_in = QPushButton("IN")
        self.btn_mark_in.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- FALTA ESTO

        self.btn_mark_out = QPushButton("OUT")
        self.btn_mark_out.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- FALTA ESTO

        
        # Añadir controles a la fila
        fila_tiempo.addWidget(self.btn_timer)
        fila_tiempo.addWidget(self.btn_back_5)
        fila_tiempo.addWidget(self.btn_play_pause)
        fila_tiempo.addWidget(self.btn_forward_5)
        fila_tiempo.addWidget(self.btn_frame_back)
        fila_tiempo.addWidget(self.btn_frame_forward)
        fila_tiempo.addWidget(self.speed_combo)
        fila_tiempo.addWidget(self.time_label)
        fila_tiempo.addWidget(self.btn_mark_in)
        fila_tiempo.addWidget(self.btn_mark_out)
        
        # Botón capturar pantalla
        btn_cap = QPushButton("📷 CAPTURAR PANTALLA")
        btn_cap.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_cap.setStyleSheet("background: #8e44ad; color: white;")
        btn_cap.clicked.connect(self.capturar_pantalla)
        fila_tiempo.addWidget(btn_cap)
        
        # Botón playlist
        btn_playlist = QPushButton("🎬 GENERAR PLAYLIST")
        btn_playlist.setFocusPolicy(Qt.FocusPolicy.NoFocus)
        btn_playlist.setStyleSheet("background: #27ae60; color: white;")
        btn_playlist.clicked.connect(self.preparar_playlist)
        fila_tiempo.addWidget(btn_playlist)
        
        fila_tiempo.addStretch()
        
        # Zoom slider
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 2000)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self.cambiar_zoom)
        

        # **AGREGA ESTO al slider:**
        self.zoom_slider.setFocusPolicy(Qt.FocusPolicy.ClickFocus)  # Solo foco con clic

        
        fila_tiempo.addWidget(QLabel("🔍 ZOOM:"))
        fila_tiempo.addWidget(self.zoom_slider)
        
        # Label proyecto
        self.lbl_proyecto = QLabel("Sin proyecto")
        self.lbl_proyecto.setStyleSheet("color: #f39c12; font-weight: bold;")
        fila_tiempo.addWidget(self.lbl_proyecto)
        
        layout_principal.addLayout(fila_tiempo)
        
        # Timeline
        self.scroll_timeline = QScrollArea()
        self.scroll_timeline.setFixedHeight(90)
        self.scroll_timeline.setStyleSheet("background: #1e272e;")
        self.timeline = ClickableTimeline(self.player)
        self.scroll_timeline.setWidget(self.timeline)
        layout_principal.addWidget(self.scroll_timeline)
        
        # Botonera
        self.grid_btns = QGridLayout()
        self.dibujar_botones()
        layout_principal.addLayout(self.grid_btns)
        
        # Footer
        footer = QHBoxLayout()
        
        btn_cargar = QPushButton("📂 CARGAR VIDEO")
        btn_cargar.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- AGREGAR
        btn_cargar.setStyleSheet("background: #34495e; color: white;")
        btn_cargar.clicked.connect(self.abrir_archivo)
        
        btn_config = QPushButton("⚙️ CONFIG BOTONERA")
        btn_config.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- AGREGAR
        btn_config.setStyleSheet("background: #7f8c8d; color: white;")
        btn_config.clicked.connect(self.configurar_botonera_avanzada)
        
        velocidad_group = QHBoxLayout()
        velocidad_group.addWidget(QLabel("VELOCIDAD:"))
        btn_vel_down = QPushButton("⏪")
        btn_vel_down.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- AGREGAR
        btn_vel_down.clicked.connect(self.disminuir_velocidad)
        btn_vel_up = QPushButton("⏩")
        btn_vel_up.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- AGREGAR
        btn_vel_up.clicked.connect(self.aumentar_velocidad)
        self.lbl_vel = QLabel("x1.0")
        self.lbl_vel.setStyleSheet("color: #2ecc71; font-weight: bold;")
        
        velocidad_group.addWidget(btn_vel_down)
        velocidad_group.addWidget(self.lbl_vel)
        velocidad_group.addWidget(btn_vel_up)
        
        self.btn_mostrar_diagrama = QPushButton("⚽ Diagrama Táctico")
        self.btn_mostrar_diagrama.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- AGREGAR
        self.btn_mostrar_diagrama.clicked.connect(self.mostrar_diagrama_tactico)
        self.btn_mostrar_diagrama.setStyleSheet("background: #16a085; color: white;")
        
        footer.addWidget(btn_cargar)
        footer.addWidget(btn_config)
        footer.addStretch()
        footer.addLayout(velocidad_group)
        footer.addStretch()
        footer.addWidget(self.btn_mostrar_diagrama)
        
        btn_exportar = QPushButton("📤 EXPORTAR")
        btn_exportar.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- AGREGAR
        btn_exportar.setStyleSheet("background: #e67e22; color: white;")
        btn_exportar.clicked.connect(self.exportar_proyecto)
        footer.addWidget(btn_exportar)
        
        layout_principal.addLayout(footer)

    def crear_barra_menu(self):
        """Crea la barra de menú"""
        menubar = self.menuBar()
        
        # Menú Archivo
        file_menu = menubar.addMenu("📁 Archivo")
        
        nuevo_action = file_menu.addAction("🆕 Nuevo Proyecto")
        nuevo_action.triggered.connect(self.nuevo_proyecto)
        nuevo_action.setShortcut("Ctrl+N")
        
        abrir_action = file_menu.addAction("📂 Abrir Proyecto")
        abrir_action.triggered.connect(self.abrir_proyecto)
        abrir_action.setShortcut("Ctrl+O")
        
        guardar_action = file_menu.addAction("💾 Guardar Proyecto")
        guardar_action.triggered.connect(self.guardar_proyecto)
        guardar_action.setShortcut("Ctrl+S")
        
        guardar_como_action = file_menu.addAction("💾 Guardar Como...")
        guardar_como_action.triggered.connect(self.guardar_proyecto_como)
        
        file_menu.addSeparator()
        
        importar_action = file_menu.addAction("📥 Importar Clips")
        importar_action.triggered.connect(self.importar_clips)
        
        exportar_action = file_menu.addAction("📤 Exportar Todo")
        exportar_action.triggered.connect(self.exportar_proyecto)
        
        file_menu.addSeparator()
        
        salir_action = file_menu.addAction("🚪 Salir")
        salir_action.triggered.connect(self.close)
        
        # Menú Edición
        edit_menu = menubar.addMenu("✏️ Edición")
        
        undo_action = edit_menu.addAction("↶ Deshacer")
        undo_action.setShortcut("Ctrl+Z")
        
        redo_action = edit_menu.addAction("↷ Rehacer")
        redo_action.setShortcut("Ctrl+Y")
        
        edit_menu.addSeparator()
        
        clear_clips_action = edit_menu.addAction("🗑️ Limpiar Todos los Clips")
        clear_clips_action.triggered.connect(self.limpiar_todos_clips)
        
        # Menú Herramientas
        tools_menu = menubar.addMenu("🔧 Herramientas")
        
        diagrama_action = tools_menu.addAction("⚽ Diagrama Táctico")
        diagrama_action.triggered.connect(self.mostrar_diagrama_tactico)
        diagrama_action.setShortcut("Ctrl+T")
        
        guardar_formacion_action = tools_menu.addAction("💾 Guardar Formación Actual")
        guardar_formacion_action.triggered.connect(self.guardar_formacion_actual)
        guardar_formacion_action.setShortcut("Ctrl+G")
        
        tools_menu.addSeparator()
        
        config_action = tools_menu.addAction("⚙️ Configurar Botonera")
        config_action.triggered.connect(self.configurar_botonera_avanzada)
        
        stats_action = tools_menu.addAction("📊 Estadísticas")
        stats_action.triggered.connect(self.mostrar_estadisticas)
        
        exportar_pdf_action = tools_menu.addAction("📤 Exportar Canchas a PDF")
        exportar_pdf_action.triggered.connect(self.exportar_canchas_pdf)
        
        # Menú Ayuda
        help_menu = menubar.addMenu("❓ Ayuda")
        
        about_action = help_menu.addAction("ℹ️ Acerca de")
        about_action.triggered.connect(self.mostrar_acerca_de)
        
        docs_action = help_menu.addAction("📖 Documentación")
        docs_action.triggered.connect(self.mostrar_documentacion)

    def crear_categoria_widget(self, boton, layout, color_base):
        """Crea un widget de categoría para el panel derecho"""
        if len(boton) < 1:
            return
            
        nom_base = boton[0]
        
        # Layout de información
        info = QHBoxLayout()
        
        # Contador de clips
        if nom_base not in self.labels_contadores:
            self.labels_contadores[nom_base] = QLabel("0")
            self.labels_contadores[nom_base].setStyleSheet(f"""
                background: {color_base};
                border-radius: 10px;
                padding: 2px 8px;
                font-weight: bold;
                color: white;
                min-width: 25px;
                text-align: center;
            """)
        
        # Nombre de la categoría
        lbl_nombre = QLabel(nom_base.replace(" RIVAL", ""))
        lbl_nombre.setStyleSheet("font-weight: bold; color: #ecf0f1;")
        
        info.addWidget(lbl_nombre)
        info.addStretch()
        info.addWidget(self.labels_contadores[nom_base])
        layout.addLayout(info)
        
        # Lista de clips
        if nom_base not in self.listas_widgets:
            lw = QListWidget()
            lw.setStyleSheet("""
                QListWidget {
                    background: #151515;
                    color: white;
                    border: 1px solid #2c3e50;
                    border-radius: 3px;
                    font-family: 'Arial', sans-serif;
                }
                QListWidget::item {
                    padding: 5px;
                    border-bottom: 1px solid #2c3e50;
                }
                QListWidget::item:selected {
                    background: #3498db;
                    color: white;
                }
                QListWidget::item:hover {
                    background: #2c3e50;
                }
            """)
            lw.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
            lw.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
            lw.customContextMenuRequested.connect(lambda pos, w=lw, n=nom_base: self.menu_contextual(pos, w, n))
            lw.itemDoubleClicked.connect(self.saltar_a_evento)
            
            layout.addWidget(lw)
            self.listas_widgets[nom_base] = lw
        else:
            # Si ya existe, solo agregar al layout
            layout.addWidget(self.listas_widgets[nom_base])

    def dibujar_botones(self):
        """Dibuja los botones en la botonera"""
        # Limpiar botones existentes
        for i in reversed(range(self.grid_btns.count())):
            widget = self.grid_btns.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        # Configurar grid (4 columnas)
        num_columnas = 4
        num_botones = len(self.config)
        
        # Crear botones
        for i, boton_data in enumerate(self.config):
            # Asegurar que el botón tenga todos los campos
            while len(boton_data) < 9:
                boton_data.append(None if len(boton_data) < 8 else 0)  # Duración por defecto 0
            
            nom, col, tipo, tec, carp, tc, equipo, tags, duracion = boton_data[:9]
            
            btn = QPushButton(f"{nom}\n[{tec}]")
            btn.setFixedHeight(55)
            
            btn.setFocusPolicy(Qt.FocusPolicy.NoFocus)  # <-- NO ROBA FOCO

            
            # Estilo dinámico
            estilo = f"""
                QPushButton {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 {col}, stop:1 {self.oscurecer_color(col)});
                    color: {tc};
                    font-weight: bold;
                    border-radius: 5px;
                    border: 2px solid {self.oscurecer_color(col, 50)};
                    font-size: 11px;
                    padding: 5px;
                }}
                QPushButton:hover {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 {self.aclarar_color(col)}, stop:1 {col});
                    border: 2px solid {tc};
                }}
                QPushButton:pressed {{
                    background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                              stop:0 {self.oscurecer_color(col, 100)}, 
                                              stop:1 {self.oscurecer_color(col, 50)});
                }}
            """
            btn.setStyleSheet(estilo)
            
            # Conectar señal
            btn.clicked.connect(lambda checked, idx=i: self.manejar_evento_idx(idx))
            
            # Tooltip informativo
            tooltip_text = f"{nom}\nTipo: {tipo}\nTecla: {tec}\nEquipo: {equipo}"
            if duracion and tipo == "auto":
                tooltip_text += f"\nDuración automática: {duracion/1000} segundos"
            if tags:
                tag_names = [TAG_MANAGER.get_tag_by_id(tag_id)["name"] for tag_id in tags if TAG_MANAGER.get_tag_by_id(tag_id)]
                if tag_names:
                    tooltip_text += f"\nEtiquetas: {', '.join(tag_names)}"
            btn.setToolTip(tooltip_text)
            
            # Agregar al grid
            self.grid_btns.addWidget(btn, i // num_columnas, i % num_columnas)
            self.botones_widgets[nom] = (btn, col)

    def oscurecer_color(self, hex_color, amount=30):
        """Oscurece un color hexadecimal"""
        color = QColor(hex_color)
        return color.darker(100 + amount).name()

    def aclarar_color(self, hex_color, amount=30):
        """Aclara un color hexadecimal"""
        color = QColor(hex_color)
        return color.lighter(100 + amount).name()

    def preparar_playlist(self):
        """Prepara una playlist con los clips seleccionados"""
        seleccionados = []
        for nom, lw in self.listas_widgets.items():
            for i in range(lw.count()):
                if lw.item(i).isSelected():
                    seleccionados.append(lw.item(i).data(Qt.ItemDataRole.UserRole))
        
        if not seleccionados:
            QMessageBox.warning(self, "Sin selección", 
                              "No hay clips seleccionados para la playlist.")
            return
        
        dialog = PlaylistDialog(seleccionados, self.video_path, self)
        dialog.exec()

    def manejar_evento(self, nom, tipo, carp, col_t, etiquetas, duracion=0):
        """Maneja un evento de botón (corte o marca)"""
        if not self.video_path: 
            QMessageBox.warning(self, "Sin video", "Primero carga un video.")
            return
            
        pos = self.player.position()
        
        if tipo == "auto":
            # Corte automático con duración personalizada
            ini = max(0, pos - duracion) if duracion > 0 else max(0, pos - 10000)
            self.registrar(ini, pos, nom, col_t, etiquetas)
        else:
            # Corte manual (inicio/fin)
            if nom not in self.cortes_activos: 
                # Primer click: marca inicio
                self.cortes_activos[nom] = pos
                self.proyecto_modificado = True
                
                # Cambiar apariencia del botón
                if nom in self.botones_widgets:
                    btn, col_orig = self.botones_widgets[nom]
                    idx = [c[0] for c in self.config].index(nom)
                    color_texto = self.config[idx][5]
                    btn.setStyleSheet(f"""
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 {col_orig}, stop:1 {self.oscurecer_color(col_orig)});
                        color: {color_texto};
                        font-weight: bold;
                        border-radius: 5px;
                        border: 3px solid #f1c40f;
                    """)
            else:
                # Segundo click: marca fin y registra
                ini = self.cortes_activos.pop(nom)
                self.registrar(ini, pos, nom, col_t, etiquetas)
                
                # Restaurar apariencia del botón
                if nom in self.botones_widgets:
                    btn, col_orig = self.botones_widgets[nom]
                    idx = [c[0] for c in self.config].index(nom)
                    color_texto = self.config[idx][5]
                    btn.setStyleSheet(f"""
                        background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                  stop:0 {col_orig}, stop:1 {self.oscurecer_color(col_orig)});
                        color: {color_texto};
                        font-weight: bold;
                        border-radius: 5px;
                        border: 2px solid {self.oscurecer_color(col_orig, 50)};
                    """)

    def registrar(self, ini, fin, nom, col, etiquetas):
        """Registra un nuevo clip"""
        if nom not in self.listas_widgets:
            return
            
        l = self.listas_widgets[nom]
        
        # Verificar que el corte tenga duración válida
        if fin <= ini:
            QMessageBox.warning(self, "Corte inválido", 
                              "El tiempo de fin debe ser mayor que el de inicio.")
            return
        
        # Calcular número de clip
        num_clip = l.count() + 1
        nombre_base = nom.replace(" RIVAL", "").replace("_", " ")
        nombre_auto = f"{nombre_base} {num_clip}"
        tiempo_formateado = self.format_time(ini)
        
        # Crear item de lista
        it = QListWidgetItem(f"[{tiempo_formateado}] {nombre_auto}")
        
        # Datos del clip
        data = {
            "ini": ini, 
            "fin": fin, 
            "nom": nom, 
            "tiempo": tiempo_formateado,
            "nombre": nombre_auto,
            "color": col,
            "categoria": nom,
            "numero": num_clip,
            "tags": etiquetas.copy() if etiquetas else [],
            "notas": ""
        }
        
        it.setData(Qt.ItemDataRole.UserRole, data)
        it.setForeground(QColor(col))
        
        # Tooltip con información
        tooltip_text = f"{nombre_auto}\n"
        tooltip_text += f"Tiempo: {tiempo_formateado}\n"
        tooltip_text += f"Duración: {(fin-ini)/1000:.1f}s"
        
        if etiquetas:
            tag_names = [TAG_MANAGER.get_tag_by_id(tag_id)["name"] 
                       for tag_id in etiquetas 
                       if TAG_MANAGER.get_tag_by_id(tag_id)]
            if tag_names:
                tooltip_text += f"\nEtiquetas: {', '.join(tag_names)}"
        
        it.setToolTip(tooltip_text)
        
        # Agregar a la lista
        l.addItem(it)
        
        # Actualizar contador
        self.labels_contadores[nom].setText(str(num_clip))
        
        # Actualizar timeline
        self.timeline.marks.append((ini, col))
        self.timeline.segmentos.append((ini, fin, col, nombre_auto))
        self.timeline.update()
        
        # Marcar proyecto como modificado
        self.proyecto_modificado = True
        self.actualizar_estado_proyecto()
        
        # RENDERIZAR EL CLIP INDIVIDUALMENTE
        self.renderizar_clip_individual(data)

    def renderizar_clip_individual(self, clip_data):
            """Renderiza un clip individual usando FFmpeg"""
            try:
                # ===== VERIFICAR FFMPEG PRIMERO =====
                try:
                    ffmpeg_path = get_ffmpeg_path()
                except FileNotFoundError as e:
                    QMessageBox.warning(
                        self, 
                        "FFmpeg no encontrado",
                        f"No se puede renderizar clip:\n{str(e)}"
                    )
                    return
                # ====================================
                
                # Crear carpeta si no existe
                categoria = clip_data['categoria']
                for boton in self.config:
                    if boton[0] == categoria and len(boton) > 4:
                        carpeta_nombre = boton[4]
                        break
                else:
                    carpeta_nombre = categoria
                
                path = os.path.join(CARPETA_CORTES, carpeta_nombre)
                if not os.path.exists(path): 
                    os.makedirs(path, exist_ok=True)
                
                # Nombre del archivo de salida
                nombre_seguro = clip_data['nombre'].replace(' ', '_').replace('/', '_')
                out = os.path.join(path, f"{nombre_seguro}_{int(clip_data['ini'])}.mp4")
                
                # Convertir tiempos a segundos
                inicio_seg = clip_data['ini'] / 1000.0
                duracion_seg = (clip_data['fin'] - clip_data['ini']) / 1000.0
                
                # Comando FFmpeg
                cmd = [
                    ffmpeg_path, "-ss", str(inicio_seg), 
                    "-i", self.video_path, 
                    "-t", str(duracion_seg), 
                    "-c:v", "copy", 
                    "-c:a", "copy", 
                    "-y", out
                ]
                
                # Ejecutar en segundo plano
                if SYS_CONFIG["system"] == "Windows":
                    subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
                else:
                    subprocess.Popen(cmd)
                    
                QMessageBox.information(
                    self, "Clip Renderizado", 
                    f"Clip '{clip_data['nombre']}' renderizado exitosamente.\n"
                    f"Archivo: {out}"
                )
                
            except Exception as e:
                QMessageBox.warning(
                    self, "Advertencia", 
                    f"No se pudo renderizar el clip automáticamente:\n{str(e)}\n"
                    "Puedes intentarlo manualmente desde el menú contextual."
                )           

    def actualizar_timeline_segmentos(self):
        """Actualiza los segmentos en el timeline"""
        self.timeline.segmentos = []
        for nom, lw in self.listas_widgets.items():
            for i in range(lw.count()):
                data = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if data:
                    self.timeline.segmentos.append(
                        (data['ini'], data['fin'], data.get('color', '#3498db'), 
                         data.get('nombre', 'Clip'))
                    )
        self.timeline.update()

    def limpiar_listas_huérfanas(self):
        """Elimina listas de categorías que ya no existen en la configuración"""
        categorias_actuales = [boton[0] for boton in self.config]
        
        for categoria in list(self.listas_widgets.keys()):
            if categoria not in categorias_actuales:
                # Ocultar la lista en lugar de eliminarla
                self.listas_widgets[categoria].setVisible(False)
                # También ocultar su contador
                if categoria in self.labels_contadores:
                    self.labels_contadores[categoria].setVisible(False)        

    def ejecutar_ffmpeg(self, s, d, c, n):
        """Ejecuta FFmpeg para renderizar un clip (método alternativo)"""
        # Crear carpeta si no existe
        path = os.path.join(CARPETA_CORTES, c)
        if not os.path.exists(path): 
            os.makedirs(path, exist_ok=True)
        
        # Nombre del archivo de salida
        out = os.path.join(path, f"{n}_{int(s)}.mp4")
        
        # Convertir tiempos a segundos
        inicio_seg = s / 1000.0
        duracion_seg = d / 1000.0
        
        # Comando FFmpeg
        ffmpeg_path = get_ffmpeg_path()
        cmd = [
            ffmpeg_path, "-ss", str(inicio_seg), 
            "-i", self.video_path, 
            "-t", str(duracion_seg), 
            "-c:v", "copy", 
            "-c:a", "copy", 
            "-y", out
        ]
        
        try:
            if SYS_CONFIG["system"] == "Windows":
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(cmd)
                
            QMessageBox.information(
                self, "Clip Renderizado", 
                f"Clip '{n}' renderizado exitosamente.\n"
                f"Archivo: {out}"
            )
        except Exception as e:
            QMessageBox.critical(
                self, "Error FFmpeg", 
                f"No se pudo ejecutar FFmpeg:\n{str(e)}"
            )

    def abrir_archivo(self):
        """Abre un archivo de video"""
        if self.proyecto_modificado:
            reply = QMessageBox.question(
                self, "Proyecto modificado",
                "¿Deseas guardar los cambios antes de abrir otro video?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.guardar_proyecto()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Diálogo para seleccionar video
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar video", 
            "", 
            "Video files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv *.m4v *.mpg *.mpeg)"
        )
        
        if file: 
            self.video_path = file
            self.player.setSource(QUrl.fromLocalFile(file))
            self.player.play()
            
            # ===== AGREGAR ESTO =====
            self.setFocus()  # Asegurar que la ventana tenga el foco
            # ========================
            
            # Si no hay proyecto activo, crear uno temporal
            if not self.proyecto_actual:
                self.proyecto_modificado = True
                nombre_base = os.path.splitext(os.path.basename(file))[0]
                self.nombre_proyecto_actual = f"Proyecto_{nombre_base}"
                self.actualizar_estado_proyecto()

    def manejar_evento_idx(self, idx):
        """Maneja evento por índice de botón"""
        if idx < len(self.config):
            c = self.config[idx]
            # Asegurar que el botón tenga todos los campos
            while len(c) < 9:
                c.append(None if len(c) < 8 else 0)
            
            nom, col, tipo, tec, carp, tc, equipo, etiquetas, duracion = c[:9]
            self.manejar_evento(nom, tipo, carp, tc, etiquetas, duracion)
            
            # **AGREGA ESTA LÍNEA** - Devuelve el foco a la ventana principal
            self.setFocus()

    def actualizar_parpadeo(self):
        """Actualiza parpadeo de botones activos"""
        for nom in self.cortes_activos:
            if nom in self.botones_widgets:
                btn, col = self.botones_widgets[nom]
                idx = [c[0] for c in self.config].index(nom)
                color_texto = self.config[idx][5]
                bg = "white" if (int(time.time()*2) % 2) else col
                btn.setStyleSheet(f"""
                    background: {bg};
                    color: black;
                    font-weight: bold;
                    border-radius: 5px;
                    border: 2px solid {color_texto};
                """)

    def actualizar_pos(self, p):
        """Actualiza posición del reproductor"""
        self.timeline.position = p
        self.timeline.update()
        self.btn_timer.setText(f"{self.format_time(p)} / {self.format_time(self.player.duration())}")
        # Actualizar label de tiempo
        self.time_label.setText(f"{p//60000:02d}:{(p%60000)//1000:02d}.{p%1000:03d}")

    def actualizar_dur(self, d):
        """Actualiza duración del video"""
        self.timeline.duration = d
        self.cambiar_zoom(self.zoom_slider.value())

    def cambiar_zoom(self, val):
        """Cambia el zoom del timeline"""
        self.timeline.setFixedWidth(int(self.scroll_timeline.width() * (val / 10.0)))

        # **AGREGA ESTO:** Devolver foco después de cambiar zoom
        self.setFocus()

    def saltar_a_evento(self, item):
        """Salta a la posición de un evento"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.player.setPosition(data['ini'])
            self.player.play()

    def format_time(self, ms):
        """Formatea milisegundos a HH:MM:SS o MM:SS"""
        s = int(ms // 1000)
        horas = s // 3600
        minutos = (s % 3600) // 60
        segundos = s % 60
        
        if horas > 0:
            return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        return f"{minutos:02d}:{segundos:02d}"

    def toggle_panel(self):
        """Muestra/oculta el panel derecho"""
        v = self.panel_derecho.isVisible()
        self.panel_derecho.setVisible(not v)
        self.btn_toggle.setText("<" if v else ">")

    def mostrar_diagrama_tactico(self):
        """Muestra el diagrama táctico"""
        if self.diagrama_tactico is None or not self.diagrama_tactico.isVisible():
            self.diagrama_tactico = DiagramaTactico(self)
            main_window_geometry = self.geometry()
            diagrama_x = main_window_geometry.x() + main_window_geometry.width() - 400
            diagrama_y = main_window_geometry.y() + 100
            self.diagrama_tactico.move(diagrama_x, diagrama_y)
        
        self.diagrama_tactico.show()
        self.diagrama_tactico.raise_()

    def capturar_pantalla(self):
        """Captura usando FFmpeg"""
        if not self.video_path: 
            QMessageBox.warning(self, "Sin video", "Primero carga un video.")
            return
        
        try:
            # ===== VERIFICAR FFMPEG =====
            try:
                ffmpeg_path = get_ffmpeg_path()
            except FileNotFoundError as e:
                QMessageBox.warning(
                    self,
                    "FFmpeg no encontrado",
                    f"No se puede capturar pantalla:\n{str(e)}"
                )
                return
            # ============================
            # Tiempo actual en segundos
            tiempo_segundos = self.player.position() / 1000.0
            
            # Crear carpeta si no existe
            os.makedirs(CARPETA_CAPTURAS, exist_ok=True)
            
            # Nombre del archivo
            timestamp = int(time.time())
            tiempo_ms = self.player.position()
            minutos = tiempo_ms // 60000
            segundos = (tiempo_ms % 60000) // 1000
            
            nombre = os.path.join(
                CARPETA_CAPTURAS, 
                f"frame_{minutos:02d}_{segundos:02d}_{timestamp}.jpg"
            )
            
            # Comando FFmpeg para extraer frame exacto

            cmd = [
                ffmpeg_path,
                "-ss", str(tiempo_segundos),      # Ir al tiempo exacto
                "-i", self.video_path,           # Archivo de entrada
                "-vframes", "1",                 # Solo 1 frame
                "-q:v", "2",                     # Calidad (2 = alta calidad)
                "-y",                            # Sobrescribir si existe
                nombre                           # Archivo de salida
            ]
            
            # DEBUG: Mostrar comando
            print("Ejecutando FFmpeg:", " ".join(cmd))
            
            # Ejecutar FFmpeg
            result = subprocess.run(
                cmd, 
                capture_output=True, 
                text=True,
                timeout=10
            )
            
            if result.returncode == 0 and os.path.exists(nombre):
                QMessageBox.information(
                    self, "✅ Captura exitosa", 
                    f"📸 Frame extraído con FFmpeg:\n{nombre}\n"
                    f"⏱️ Tiempo: {minutos:02d}:{segundos:02d}"
                )
            else:
                error_msg = result.stderr[:300] if result.stderr else "Error desconocido"
                QMessageBox.warning(
                    self, "Error FFmpeg", 
                    f"No se pudo extraer frame:\n{error_msg}"
                )
                
        except subprocess.TimeoutExpired:
            QMessageBox.warning(self, "Timeout", "FFmpeg tardó demasiado")
        except Exception as e:
            QMessageBox.warning(self, "Error", f"Error: {str(e)}")

    def ir_a_tiempo_manual(self):
        """Salta a un tiempo específico"""
        txt, ok = QInputDialog.getText(self, "Saltar a tiempo", 
                                      "Formato: HH:MM:SS o MM:SS")
        if ok and txt:
            try:
                partes = txt.split(":")
                if len(partes) == 3:
                    h, m, s = map(int, partes)
                    segundos = h * 3600 + m * 60 + s
                elif len(partes) == 2:
                    m, s = map(int, partes)
                    segundos = m * 60 + s
                else:
                    segundos = int(partes[0])
                
                self.player.setPosition(segundos * 1000)
                self.player.play()
            except:
                QMessageBox.warning(self, "Formato incorrecto", 
                                  "Usa HH:MM:SS o MM:SS")

    def configurar_botonera_avanzada(self):
        dialog = ConfigBotoneraDialog(self.config, self)
        if dialog.exec():
            self.config = dialog.config
            # Guardar en archivo...
            
            # Esto:
            self.dibujar_botones()
            self.limpiar_listas_huérfanas()  # <-- AGREGAR ESTA LÍNEA
            
            QMessageBox.information(self, "Configuración Guardada", 
                                "Botones actualizados.")

    def reconstruir_interfaz(self):
        """Versión SEGURA - Solo actualiza lo necesario"""
        # 1. Redibujar botones principales (ESTO SÍ FUNCIONA)
        self.dibujar_botones()
        
        # 2. Actualizar headers del panel si existen
        # (Pero mantener las listas de clips intactas)
        
        # 3. Si se eliminó una categoría, sus clips quedarán huérfanos
        # pero es mejor que crashear

    def nuevo_proyecto(self):
        """Crea un nuevo proyecto"""
        if self.proyecto_modificado:
            reply = QMessageBox.question(
                self, "Proyecto modificado",
                "¿Deseas guardar el proyecto actual?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.guardar_proyecto()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Pedir nombre del proyecto
        nombre, ok = QInputDialog.getText(
            self, "Nuevo Proyecto", 
            "Nombre del proyecto:", 
            text=f"Proyecto_{time.strftime('%Y%m%d_%H%M')}"
        )
        
        if ok and nombre:
            # Resetear estado
            self.nombre_proyecto_actual = nombre
            self.proyecto_actual = None
            self.proyecto_modificado = True
            
            # Limpiar clips
            for lw in self.listas_widgets.values():
                lw.clear()
            
            for lbl in self.labels_contadores.values():
                lbl.setText("0")
            
            # Limpiar timeline
            self.timeline.marks = []
            self.timeline.segmentos = []
            self.timeline.update()
            
            # Limpiar formaciones
            self.gestor_formaciones.formaciones_guardadas = []
            
            # Actualizar estado
            self.actualizar_estado_proyecto()
            
            # Preguntar por video
            reply = QMessageBox.question(
                self, "Cargar Video",
                "¿Deseas cargar un video ahora?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.abrir_archivo()

    def guardar_proyecto(self):
        """Guarda el proyecto actual"""
        if not self.nombre_proyecto_actual:
            self.guardar_proyecto_como()
            return
        
        # Recolectar todos los clips
        cortes = []
        for nom, lw in self.listas_widgets.items():
            for i in range(lw.count()):
                data = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if data:
                    cortes.append(data)
        
        # Metadata del proyecto
        metadata = {
            "total_clips": len(cortes),
            "video_duracion": self.player.duration(),
            "fecha_modificacion": time.strftime("%Y-%m-d %H:%M:%S"),
            "formaciones_guardadas": self.gestor_formaciones.formaciones_guardadas,
            "equipos": self.equipos,
            "config_botones": self.config
        }
        
        # Guardar proyecto
        try:
            proyecto_file = ProyectoManager.guardar_proyecto(
                self.nombre_proyecto_actual,
                self.video_path,
                cortes,
                self.config,
                metadata
            )
            
            self.proyecto_actual = proyecto_file
            self.proyecto_modificado = False
            self.actualizar_estado_proyecto()
            
            QMessageBox.information(self, "Proyecto Guardado", 
                                  f"Proyecto '{self.nombre_proyecto_actual}' guardado exitosamente.")
            
        except Exception as e:
            QMessageBox.critical(self, "Error al guardar", 
                               f"No se pudo guardar el proyecto:\n{str(e)}")

    def guardar_proyecto_como(self):
        """Guarda el proyecto con un nuevo nombre"""
        nombre, ok = QInputDialog.getText(
            self, "Guardar Proyecto Como", 
            "Nombre del proyecto:", 
            text=self.nombre_proyecto_actual or f"Proyecto_{time.strftime('%Y%m%d_%H%M')}"
        )
        
        if ok and nombre:
            self.nombre_proyecto_actual = nombre
            self.lbl_proyecto.setText(f"📁 {nombre}")
            self.guardar_proyecto()

    def abrir_proyecto(self):
        """Abre un proyecto existente"""
        if self.proyecto_modificado:
            reply = QMessageBox.question(
                self, "Proyecto modificado",
                "¿Deseas guardar los cambios antes de abrir otro proyecto?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.guardar_proyecto()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        # Listar proyectos disponibles
        proyectos = ProyectoManager.listar_proyectos()
        
        if not proyectos:
            QMessageBox.information(self, "No hay proyectos", 
                                  "No hay proyectos guardados.")
            return
        
        # Diálogo para seleccionar proyecto
        dialog = QDialog(self)
        dialog.setWindowTitle("Abrir Proyecto")
        dialog.resize(700, 400)
        
        layout = QVBoxLayout(dialog)
        
        # Lista de proyectos
        list_widget = QListWidget()
        for proyecto in proyectos:
            # Icono según estado del video
            icono = "✅" if proyecto["video_exists"] else "⚠️"
            item_text = f"{icono} {proyecto['nombre']}\n"
            item_text += f"   📅 {proyecto['fecha']}\n"
            item_text += f"   🎬 {os.path.basename(proyecto['video'])[:30]}"
            
            if not proyecto["video_exists"]:
                item_text += " (NO ENCONTRADO)"
            
            item_text += f"\n   📊 {proyecto['total_clips']} clips"
            
            item = QListWidgetItem(item_text)
            item.setData(Qt.ItemDataRole.UserRole, proyecto)
            
            # Color según disponibilidad del video
            if not proyecto["video_exists"]:
                item.setForeground(QColor("#e74c3c"))
            
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_abrir = QPushButton("Abrir")
        btn_eliminar = QPushButton("Eliminar")
        btn_cancelar = QPushButton("Cancelar")
        
        def cargar_proyecto():
            current_item = list_widget.currentItem()
            if not current_item:
                QMessageBox.warning(dialog, "Selección requerida", 
                                  "Por favor selecciona un proyecto.")
                return
            
            proyecto_data = current_item.data(Qt.ItemDataRole.UserRole)
            
            try:
                # Cargar proyecto
                proyecto = ProyectoManager.cargar_proyecto(proyecto_data['archivo'])
                
                # Actualizar estado de la aplicación
                self.nombre_proyecto_actual = proyecto['nombre']
                self.video_path = proyecto['video_path']
                self.config = proyecto['botonera_config']
                
                # Cargar equipos si existen
                if 'metadata' in proyecto and 'equipos' in proyecto['metadata']:
                    self.equipos = proyecto['metadata']['equipos']
                
                # Cargar video si existe
                if os.path.exists(self.video_path):
                    self.player.setSource(QUrl.fromLocalFile(self.video_path))
                else:
                    QMessageBox.warning(self, "Video no encontrado",
                                      f"El video original no se encuentra en:\n{self.video_path}")
                
                # Reconstruir interfaz
                self.reconstruir_interfaz()
                
                # Cargar clips
                for corte in proyecto.get('cortes', []):
                    nom = corte['nom']
                    if nom in self.listas_widgets:
                        lw = self.listas_widgets[nom]
                        
                        # Crear item
                        it = QListWidgetItem(f"[{corte['tiempo']}] {corte.get('nombre', 'Clip')}")
                        it.setData(Qt.ItemDataRole.UserRole, corte)
                        it.setForeground(QColor(corte.get('color', '#3498db')))
                        
                        # Tooltip
                        tooltip_text = f"{corte.get('nombre', 'Clip')}\n"
                        tooltip_text += f"Tiempo: {corte['tiempo']}\n"
                        tooltip_text += f"Duración: {(corte['fin']-corte['ini'])/1000:.1f}s"
                        
                        if 'tags' in corte and corte['tags']:
                            tag_names = [TAG_MANAGER.get_tag_by_id(tag_id)["name"] 
                                       for tag_id in corte['tags'] 
                                       if TAG_MANAGER.get_tag_by_id(tag_id)]
                            if tag_names:
                                tooltip_text += f"\nEtiquetas: {', '.join(tag_names)}"
                        
                        it.setToolTip(tooltip_text)
                        
                        lw.addItem(it)
                        
                        # Actualizar contador
                        self.labels_contadores[nom].setText(str(lw.count()))
                        
                        # Agregar a timeline
                        self.timeline.segmentos.append((
                            corte['ini'], corte['fin'], 
                            corte.get('color', '#3498db'), 
                            corte.get('nombre', 'Clip')
                        ))
                
                # Cargar formaciones
                if 'metadata' in proyecto and 'formaciones_guardadas' in proyecto['metadata']:
                    self.gestor_formaciones.formaciones_guardadas = proyecto['metadata']['formaciones_guardadas']
                
                # Actualizar interfaz
                self.lbl_proyecto.setText(f"📁 {self.nombre_proyecto_actual}")
                self.proyecto_modificado = False
                self.actualizar_estado_proyecto()
                self.timeline.update()
                
                dialog.accept()
                
                QMessageBox.information(self, "Proyecto Cargado", 
                                      f"Proyecto '{self.nombre_proyecto_actual}' cargado exitosamente.")
                
            except Exception as e:
                QMessageBox.critical(dialog, "Error", 
                                   f"No se pudo cargar el proyecto:\n{str(e)}")
        
        def eliminar_proyecto():
            current_item = list_widget.currentItem()
            if not current_item:
                return
            
            proyecto_data = current_item.data(Qt.ItemDataRole.UserRole)
            
            reply = QMessageBox.question(
                dialog, "Confirmar Eliminación",
                f"¿Estás seguro de eliminar el proyecto '{proyecto_data['nombre']}'?\n"
                "Esta acción no se puede deshacer.",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                if ProyectoManager.eliminar_proyecto(proyecto_data['nombre']):
                    list_widget.takeItem(list_widget.currentRow())
                    QMessageBox.information(dialog, "Proyecto Eliminado",
                                          f"Proyecto '{proyecto_data['nombre']}' eliminado.")
                else:
                    QMessageBox.critical(dialog, "Error",
                                       f"No se pudo eliminar el proyecto.")
        
        btn_abrir.clicked.connect(cargar_proyecto)
        btn_eliminar.clicked.connect(eliminar_proyecto)
        btn_cancelar.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(btn_abrir)
        btn_layout.addWidget(btn_eliminar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def exportar_proyecto(self):
        """Exporta el proyecto completo"""
        if not self.video_path:
            QMessageBox.warning(self, "Sin video", "Primero carga un video para exportar.")
            return
        
        # Recolectar todos los clips
        todos_clips = []
        for lw in self.listas_widgets.values():
            for i in range(lw.count()):
                data = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if data:
                    todos_clips.append(data)
        
        if not todos_clips:
            QMessageBox.warning(self, "Sin clips", "No hay clips para exportar.")
            return
        
        # Mostrar diálogo de exportación
        dialog = ExportDialog(self.video_path, todos_clips, self)
        dialog.exec()

    def guardar_formacion_actual(self):
        """Guarda la formación actual del diagrama táctico"""
        if not self.diagrama_tactico:
            QMessageBox.warning(self, "Diagrama no abierto", 
                              "Abre el diagrama táctico primero.")
            return
            
        self.diagrama_tactico.guardar_formacion_actual()

    def exportar_canchas_pdf(self):
        """Exporta las canchas a PDF"""
        if not self.diagrama_tactico:
            QMessageBox.warning(self, "Diagrama no abierto", 
                              "Abre el diagrama táctico primero.")
            return
            
        self.diagrama_tactico.exportar_canchas_pdf()

    def mostrar_estadisticas(self):
        """Muestra estadísticas del proyecto"""
        total_clips = 0
        for lw in self.listas_widgets.values():
            total_clips += lw.count()
        
        # Calcular tiempo total de clips
        tiempo_total = 0
        for nom, lw in self.listas_widgets.items():
            for i in range(lw.count()):
                data = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if data:
                    tiempo_total += (data['fin'] - data['ini'])
        
        tiempo_total_seg = tiempo_total / 1000
        
        stats = f"""
        📊 ESTADÍSTICAS DEL PROYECTO
        
        Proyecto: {self.nombre_proyecto_actual or 'Sin nombre'}
        Video: {os.path.basename(self.video_path) if self.video_path else 'No cargado'}
        
        Total de clips: {total_clips}
        Tiempo total de clips: {tiempo_total_seg:.1f} segundos
        Formaciones guardadas: {len(self.gestor_formaciones.formaciones_guardadas)}
        
        Distribución por categoría:
        """
        
        for nom, lw in self.listas_widgets.items():
            stats += f"\n{nom}: {lw.count()} clips"
        
        QMessageBox.information(self, "Estadísticas", stats)

    def aumentar_velocidad(self):
        """Aumenta la velocidad de reproducción"""
        if self.vel_idx < len(self.velocidades) - 1:
            self.vel_idx += 1
            self.player.setPlaybackRate(self.velocidades[self.vel_idx])
            self.lbl_vel.setText(f"x{self.velocidades[self.vel_idx]}")

    def disminuir_velocidad(self):
        """Disminuye la velocidad de reproducción"""
        if self.vel_idx > 0:
            self.vel_idx -= 1
            self.player.setPlaybackRate(self.velocidades[self.vel_idx])
            self.lbl_vel.setText(f"x{self.velocidades[self.vel_idx]}")

    def autoguardar_proyecto(self):
        """Auto-guarda el proyecto cada cierto tiempo"""
        if self.proyecto_modificado and self.nombre_proyecto_actual:
            # Auto-guardar solo si hay cambios significativos
            if hasattr(self, 'last_autosave_hash'):
                current_hash = hash(str(self.config) + str(self.video_path))
                if current_hash == self.last_autosave_hash:
                    return
            
            self.guardar_proyecto()
            self.last_autosave_hash = hash(str(self.config) + str(self.video_path))

    def actualizar_estado_proyecto(self):
        """Actualiza el estado del proyecto en la interfaz"""
        estado = f"📁 {self.nombre_proyecto_actual or 'Sin proyecto'}"
        if self.proyecto_modificado:
            estado += " ●"
        
        self.lbl_proyecto.setText(estado)

    def importar_clips(self):
        """Importa clips desde un archivo externo"""
        QMessageBox.information(self, "Importar Clips",
                              "Esta función está en desarrollo.\n"
                              "Próximamente podrás importar clips desde otros proyectos.")

    def limpiar_todos_clips(self):
        """Limpia todos los clips del proyecto"""
        if not any(lw.count() > 0 for lw in self.listas_widgets.values()):
            return
        
        reply = QMessageBox.question(
            self, "Confirmar Limpieza",
            "¿Estás seguro de eliminar TODOS los clips del proyecto?\n"
            "Esta acción no se puede deshacer.",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            for lw in self.listas_widgets.values():
                lw.clear()
            
            for lbl in self.labels_contadores.values():
                lbl.setText("0")
            
            self.timeline.marks = []
            self.timeline.segmentos = []
            self.timeline.update()
            
            self.proyecto_modificado = True
            self.actualizar_estado_proyecto()
            
            QMessageBox.information(self, "Clips Limpiados",
                                  "Todos los clips han sido eliminados.")

    def mostrar_acerca_de(self):
        """Muestra información acerca del programa"""
        about_text = f"""
        <h1>Match Clip Analyzer</h1>
        <h3>Versión 12.0</h3>
        
        <p>Herramienta profesional para análisis de video deportivo.</p>
        
        <p><b>Características principales:</b></p>
        <ul>
        <li>Marcado y corte de clips con botonera personalizable</li>
        <li>Sistema de etiquetas para organización avanzada</li>
        <li>Diagrama táctico interactivo con exportación a PDF</li>
        <li>Generación de playlists automáticas</li>
        <li>Gestor de proyectos integrado</li>
        <li>Soporte multi-idioma</li>
        </ul>
        
        <p><b>Desarrollado por:</b> Pedro Servín</p>
        <p><b>Contacto:</b> pedroservin97@gmail.com</p>
        
        <p>© 2026 Match Clip Analyzer - Todos los derechos reservados</p>
        """
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Acerca de Match Clip Analyzer")
        dialog.resize(500, 400)
        
        layout = QVBoxLayout(dialog)
        
        text_browser = QTextBrowser()
        text_browser.setHtml(about_text)
        text_browser.setOpenExternalLinks(True)
        
        layout.addWidget(text_browser)
        
        btn_cerrar = QPushButton("Cerrar")
        btn_cerrar.clicked.connect(dialog.accept)
        layout.addWidget(btn_cerrar, alignment=Qt.AlignmentFlag.AlignCenter)
        
        dialog.exec()

    def mostrar_documentacion(self):
        """Muestra la documentación del programa"""
        QMessageBox.information(self, "Documentación",
                              "La documentación completa está disponible en:\n"
                              "https://github.com/tuusuario/match-clip-analyzer\n\n"
                              "Próximamente: Manual de usuario integrado.")

    def keyPressEvent(self, event):
        """Maneja eventos de teclado"""
        # Primero manejar los atajos de teclado principales
        key = event.key()
        
        # BARRA ESPACIADORA - Play/Pause
        if key == Qt.Key.Key_Space:
            self.toggle_play_pause()
            event.accept()
            return
        
        # FLECHA IZQUIERDA - Retroceder 5 segundos
        elif key == Qt.Key.Key_Left:
            self.saltar_tiempo(-5000)
            event.accept()
            return
        
        # FLECHA DERECHA - Avanzar 5 segundos
        elif key == Qt.Key.Key_Right:
            self.saltar_tiempo(5000)
            event.accept()
            return
        
        # FLECHA ARRIBA - Aumentar velocidad
        elif key == Qt.Key.Key_Up:
            self.aumentar_velocidad()
            event.accept()
            return
        
        # FLECHA ABAJO - Disminuir velocidad
        elif key == Qt.Key.Key_Down:
            self.disminuir_velocidad()
            event.accept()
            return

            # ================ AQUÍ VA EL NUEVO CÓDIGO ================
    # Solo después manejar otras teclas
    # Si el foco está en un widget que necesita sus propias teclas
        focused = self.focusWidget()
        if focused and isinstance(focused, (QLineEdit, QTextEdit, QComboBox)):
            # Permitir navegación en campos de texto
            if key in [Qt.Key.Key_Left, Qt.Key.Key_Right, Qt.Key.Key_Home, 
                    Qt.Key.Key_End, Qt.Key.Key_Backspace, Qt.Key.Key_Delete]:
                super().keyPressEvent(event)
                return
    # ================ FIN DEL NUEVO CÓDIGO ================
        
        # Tecla V - Cambiar velocidad cíclica
        elif key == Qt.Key.Key_V:
            self.vel_idx = (self.vel_idx + 1) % len(self.velocidades)
            self.player.setPlaybackRate(self.velocidades[self.vel_idx])
            self.lbl_vel.setText(f"x{self.velocidades[self.vel_idx]}")
            event.accept()
            return
        
        # Mapear teclas a botones (números y letras)
        key_text = event.text().upper()
        if key_text:
            # Buscar botón con esta tecla de acceso
            for idx, boton_data in enumerate(self.config):
                if len(boton_data) > 3 and boton_data[3] == key_text:
                    self.manejar_evento_idx(idx)
                    event.accept()
                    return
        
        # Ctrl+S - Guardar proyecto
        elif key == Qt.Key.Key_S and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.guardar_proyecto()
            event.accept()
            return
        
        # Ctrl+T - Diagrama táctico
        elif key == Qt.Key.Key_T and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.mostrar_diagrama_tactico()
            event.accept()
            return
        
        # Ctrl+G - Guardar formación
        elif key == Qt.Key.Key_G and event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            self.guardar_formacion_actual()
            event.accept()
            return
        
        # ESC - Pausar video
        elif key == Qt.Key.Key_Escape:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            event.accept()
            return
        
        # F - Ir a frame siguiente
        elif key == Qt.Key.Key_F:
            self.frame_adelante()
            event.accept()
            return
        
        # B - Ir a frame anterior
        elif key == Qt.Key.Key_B:
            self.frame_atras()
            event.accept()
            return
        
        # I - Marcar inicio
        elif key == Qt.Key.Key_I:
            self.marcar_inicio()
            event.accept()
            return
        
        # O - Marcar fin
        elif key == Qt.Key.Key_O:
            self.marcar_fin()
            event.accept()
            return
        
        super().keyPressEvent(event)

    def toggle_play_pause(self):
        """Alterna entre play y pause"""
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
            self.player.pause()
            self.btn_play_pause.setText("▶️")
        else:
            self.player.play()
            self.btn_play_pause.setText("⏸")

    def saltar_tiempo(self, ms):
        """Salta un tiempo específico en milisegundos"""
        if not self.video_path:
            return
            
        new_pos = self.player.position() + ms
        new_pos = max(0, min(new_pos, self.player.duration()))
        self.player.setPosition(new_pos)
        
        # Si estaba pausado, reproducir brevemente para actualizar frame
        if self.player.playbackState() == QMediaPlayer.PlaybackState.PausedState:
            self.player.play()
            QTimer.singleShot(100, lambda: self.player.pause() if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState else None)

    def frame_atras(self):
        """Retrocede un frame"""
        if not self.video_path:
            return
            
        # Obtener FPS del video si es posible (estimado)
        fps = 30  # FPS por defecto
        frame_time = 1000 / fps  # ms por frame
        
        new_pos = self.player.position() - frame_time
        new_pos = max(0, min(new_pos, self.player.duration()))
        self.player.setPosition(int(new_pos))

    def frame_adelante(self):
        """Avanza un frame"""
        if not self.video_path:
            return
            
        # Obtener FPS del video si es posible (estimado)
        fps = 30  # FPS por defecto
        frame_time = 1000 / fps  # ms por frame
        
        new_pos = self.player.position() + frame_time
        new_pos = max(0, min(new_pos, self.player.duration()))
        self.player.setPosition(int(new_pos))

    def cambiar_velocidad_combo(self, texto):
        """Cambia la velocidad desde el combo box"""
        if texto == "0.5x":
            self.player.setPlaybackRate(0.5)
            self.lbl_vel.setText("x0.5")
        elif texto == "1x":
            self.player.setPlaybackRate(1.0)
            self.lbl_vel.setText("x1.0")
        elif texto == "1.5x":
            self.player.setPlaybackRate(1.5)
            self.lbl_vel.setText("x1.5")
        elif texto == "2x":
            self.player.setPlaybackRate(2.0)
            self.lbl_vel.setText("x2.0")

    def marcar_inicio(self):
        """Marca el punto de inicio para corte manual"""
        if not self.video_path:
            QMessageBox.warning(self, "Sin video", "Primero carga un video.")
            return
            
        pos = self.player.position()
        
        # Buscar botón manual activo para marcar inicio
        for idx, boton_data in enumerate(self.config):
            if len(boton_data) > 2 and boton_data[2] == "manual":
                nom = boton_data[0]
                if nom not in self.cortes_activos:
                    # Este es un botón manual que no tiene inicio marcado
                    self.cortes_activos[nom] = pos
                    self.proyecto_modificado = True
                    
                    # Cambiar apariencia del botón
                    if nom in self.botones_widgets:
                        btn, col_orig = self.botones_widgets[nom]
                        color_texto = boton_data[5] if len(boton_data) > 5 else "#ffffff"
                        btn.setStyleSheet(f"""
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                      stop:0 {col_orig}, stop:1 {self.oscurecer_color(col_orig)});
                            color: {color_texto};
                            font-weight: bold;
                            border-radius: 5px;
                            border: 3px solid #f1c40f;
                        """)
                    
                    QMessageBox.information(self, "Inicio marcado", 
                                          f"Inicio marcado en {self.format_time(pos)}\nAhora marca el fin con el mismo botón.")
                    return
        
        QMessageBox.information(self, "Sin botones manuales", 
                              "No hay botones manuales disponibles para marcar inicio.")

    def marcar_fin(self):
        """Marca el punto de fin para corte manual"""
        if not self.video_path:
            QMessageBox.warning(self, "Sin video", "Primero carga un video.")
            return
            
        pos = self.player.position()
        
        # Buscar botón manual que ya tenga inicio marcado
        for idx, boton_data in enumerate(self.config):
            if len(boton_data) > 2 and boton_data[2] == "manual":
                nom = boton_data[0]
                if nom in self.cortes_activos:
                    # Este botón tiene inicio marcado, marcar fin
                    ini = self.cortes_activos.pop(nom)
                    
                    # Obtener etiquetas del botón
                    etiquetas = boton_data[7] if len(boton_data) > 7 else []
                    
                    # Registrar el corte
                    self.registrar(ini, pos, nom, boton_data[5], etiquetas)
                    
                    # Restaurar apariencia del botón
                    if nom in self.botones_widgets:
                        btn, col_orig = self.botones_widgets[nom]
                        color_texto = boton_data[5] if len(boton_data) > 5 else "#ffffff"
                        btn.setStyleSheet(f"""
                            background: qlineargradient(x1:0, y1:0, x2:1, y2:1,
                                                      stop:0 {col_orig}, stop:1 {self.oscurecer_color(col_orig)});
                            color: {color_texto};
                            font-weight: bold;
                            border-radius: 5px;
                            border: 2px solid {self.oscurecer_color(col_orig, 50)};
                        """)
                    
                    QMessageBox.information(self, "Fin marcado", 
                                          f"Corte completado: {self.format_time(ini)} - {self.format_time(pos)}")
                    return
        
        QMessageBox.information(self, "Sin inicio marcado", 
                              "Primero marca un inicio con I o un botón manual.")

    def menu_contextual(self, pos, list_widget, categoria):
        """Muestra menú contextual para clips"""
        item = list_widget.itemAt(pos)
        if not item:
            return
        
        menu = QMenu(self)
        
        # Acciones del menú
        action_saltar = menu.addAction("Saltar a este clip")
        action_editar = menu.addAction("Editar clip...")
        action_eliminar = menu.addAction("Eliminar clip")
        action_renderizar = menu.addAction("🎬 Renderizar clip")
        menu.addSeparator()
        action_propiedades = menu.addAction("Propiedades...")
        
        # Ejecutar menú
        action = menu.exec(list_widget.mapToGlobal(pos))
        
        if action == action_saltar:
            self.saltar_a_evento(item)
        elif action == action_editar:
            self.editar_clip(item, categoria)
        elif action == action_eliminar:
            self.eliminar_clip(item, categoria)
        elif action == action_renderizar:
            self.renderizar_clip_desde_menu(item)
        elif action == action_propiedades:
            self.mostrar_propiedades_clip(item)

    def renderizar_clip_desde_menu(self, item):
        """Renderiza un clip desde el menú contextual"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        try:
            # Crear carpeta si no existe
            categoria = data['categoria']
            for boton in self.config:
                if boton[0] == categoria and len(boton) > 4:
                    carpeta_nombre = boton[4]
                    break
            else:
                carpeta_nombre = categoria
            
            path = os.path.join(CARPETA_CORTES, carpeta_nombre)
            if not os.path.exists(path): 
                os.makedirs(path, exist_ok=True)
            
            # Nombre del archivo de salida
            nombre_seguro = data['nombre'].replace(' ', '_').replace('/', '_')
            out = os.path.join(path, f"{nombre_seguro}_{int(data['ini'])}.mp4")
            
            # Convertir tiempos a segundos
            inicio_seg = data['ini'] / 1000.0
            duracion_seg = (data['fin'] - data['ini']) / 1000.0
            
            # Comando FFmpeg
            ffmpeg_path = get_ffmpeg_path()
            cmd = [
                ffmpeg_path, "-ss", str(inicio_seg), 
                "-i", self.video_path, 
                "-t", str(duracion_seg), 
                "-c:v", "copy", 
                "-c:a", "copy", 
                "-y", out
            ]
            
            # Ejecutar en segundo plano
            if SYS_CONFIG["system"] == "Windows":
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(cmd)
                
            QMessageBox.information(
                self, "Clip Renderizado", 
                f"Clip '{data['nombre']}' renderizado exitosamente.\n"
                f"Archivo: {out}"
            )
            
        except Exception as e:
            QMessageBox.critical(
                self, "Error al renderizar", 
                f"No se pudo renderizar el clip:\n{str(e)}"
            )

    def editar_clip(self, item, categoria):
        """Edita un clip existente"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Editar Clip")
        dialog.resize(400, 300)
        
        layout = QVBoxLayout(dialog)
        
        # Información del clip
        info_group = QGroupBox("Información del Clip")
        info_layout = QVBoxLayout()
        
        # Nombre
        info_layout.addWidget(QLabel("Nombre:"))
        nombre_input = QLineEdit(data.get('nombre', 'Clip'))
        info_layout.addWidget(nombre_input)
        
        # Tiempos
        tiempo_layout = QHBoxLayout()
        tiempo_layout.addWidget(QLabel("Inicio:"))
        inicio_input = QLineEdit(self.format_time(data['ini']))
        inicio_input.setReadOnly(True)
        tiempo_layout.addWidget(inicio_input)
        
        tiempo_layout.addWidget(QLabel("Fin:"))
        fin_input = QLineEdit(self.format_time(data['fin']))
        fin_input.setReadOnly(True)
        tiempo_layout.addWidget(fin_input)
        
        info_layout.addLayout(tiempo_layout)
        
        # Duración
        duracion = (data['fin'] - data['ini']) / 1000
        info_layout.addWidget(QLabel(f"Duración: {duracion:.2f} segundos"))
        
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        # Etiquetas
        tags_group = QGroupBox("Etiquetas")
        tags_layout = QVBoxLayout()
        
        tags_list = QListWidget()
        tags_list.setSelectionMode(QAbstractItemView.SelectionMode.MultiSelection)
        
        for tag in TAG_MANAGER.get_tags():
            item_tag = QListWidgetItem(tag["name"])
            item_tag.setData(Qt.ItemDataRole.UserRole, tag["id"])
            item_tag.setForeground(QColor(tag["color"]))
            
            # Marcar si está seleccionada
            if 'tags' in data and tag["id"] in data['tags']:
                item_tag.setSelected(True)
            
            tags_list.addItem(item_tag)
        
        tags_layout.addWidget(tags_list)
        tags_group.setLayout(tags_layout)
        layout.addWidget(tags_group)
        
        # Notas
        notas_group = QGroupBox("Notas")
        notas_layout = QVBoxLayout()
        
        notas_input = QTextEdit()
        notas_input.setPlainText(data.get('notas', ''))
        notas_input.setMaximumHeight(80)
        notas_layout.addWidget(notas_input)
        
        notas_group.setLayout(notas_layout)
        layout.addWidget(notas_group)
        
        # Botones
        btn_layout = QHBoxLayout()
        btn_guardar = QPushButton("💾 Guardar")
        btn_cancelar = QPushButton("❌ Cancelar")
        
        def guardar_cambios():
            # Actualizar datos del clip
            data['nombre'] = nombre_input.text().strip() or data.get('nombre', 'Clip')
            
            # Actualizar etiquetas
            etiquetas = []
            for i in range(tags_list.count()):
                if tags_list.item(i).isSelected():
                    etiquetas.append(tags_list.item(i).data(Qt.ItemDataRole.UserRole))
            data['tags'] = etiquetas
            
            # Actualizar notas
            data['notas'] = notas_input.toPlainText()
            
            # Actualizar item en la lista
            item.setText(f"[{data['tiempo']}] {data['nombre']}")
            item.setData(Qt.ItemDataRole.UserRole, data)
            
            # Actualizar tooltip
            tooltip_text = f"{data['nombre']}\n"
            tooltip_text += f"Tiempo: {data['tiempo']}\n"
            tooltip_text += f"Duración: {duracion:.2f}s"
            
            if etiquetas:
                tag_names = [TAG_MANAGER.get_tag_by_id(tag_id)["name"] 
                           for tag_id in etiquetas 
                           if TAG_MANAGER.get_tag_by_id(tag_id)]
                if tag_names:
                    tooltip_text += f"\nEtiquetas: {', '.join(tag_names)}"
            
            if data['notas']:
                tooltip_text += f"\nNotas: {data['notas'][:50]}..."
            
            item.setToolTip(tooltip_text)
            
            self.proyecto_modificado = True
            self.actualizar_estado_proyecto()
            
            dialog.accept()
        
        btn_guardar.clicked.connect(guardar_cambios)
        btn_cancelar.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(btn_guardar)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        dialog.exec()

    def eliminar_clip(self, item, categoria):
        """Elimina un clip"""
        row = self.listas_widgets[categoria].row(item)
        if row < 0:
            return
        
        reply = QMessageBox.question(
            self, "Confirmar Eliminación",
            f"¿Estás seguro de eliminar este clip?\n{item.text()}",
            QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No
        )
        
        if reply == QMessageBox.StandardButton.Yes:
            # Eliminar de la lista
            self.listas_widgets[categoria].takeItem(row)
            
            # Actualizar contador
            self.labels_contadores[categoria].setText(str(self.listas_widgets[categoria].count()))
            
            # Actualizar timeline (necesitaríamos más información para esto)
            # Por ahora, simplemente recargamos toda la timeline
            self.actualizar_timeline_segmentos()
            
            self.proyecto_modificado = True
            self.actualizar_estado_proyecto()
            
            QMessageBox.information(self, "Clip Eliminado", "Clip eliminado exitosamente.")

    def mostrar_propiedades_clip(self, item):
        """Muestra propiedades detalladas del clip"""
        data = item.data(Qt.ItemDataRole.UserRole)
        if not data:
            return
        
        duracion = (data['fin'] - data['ini']) / 1000
        etiquetas_texto = "Ninguna"
        
        if 'tags' in data and data['tags']:
            tag_names = [TAG_MANAGER.get_tag_by_id(tag_id)["name"] 
                       for tag_id in data['tags'] 
                       if TAG_MANAGER.get_tag_by_id(tag_id)]
            if tag_names:
                etiquetas_texto = ", ".join(tag_names)
        
        propiedades = f"""
        <h3>Propiedades del Clip</h3>
        
        <b>Nombre:</b> {data.get('nombre', 'Clip')}<br/>
        <b>Categoría:</b> {data.get('categoria', 'Sin categoría')}<br/>
        <b>Número:</b> {data.get('numero', 1)}<br/>
        
        <b>Tiempo de inicio:</b> {self.format_time(data['ini'])}<br/>
        <b>Tiempo de fin:</b> {self.format_time(data['fin'])}<br/>
        <b>Duración:</b> {duracion:.2f} segundos<br/>
        
        <b>Etiquetas:</b> {etiquetas_texto}<br/>
        
        <b>Color:</b> <font color='{data.get('color', '#3498db')}'>■</font> {data.get('color', '#3498db')}<br/>
        
        <b>Notas:</b><br/>
        {data.get('notas', 'Sin notas')}
        """
        
        QMessageBox.information(self, "Propiedades del Clip", propiedades)

    def closeEvent(self, event):
        """Maneja el cierre de la aplicación"""
        if self.proyecto_modificado:
            reply = QMessageBox.question(
                self, "Proyecto modificado",
                "¿Deseas guardar los cambios antes de salir?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            
            if reply == QMessageBox.StandardButton.Yes:
                self.guardar_proyecto()
                event.accept()
            elif reply == QMessageBox.StandardButton.No:
                event.accept()
            else:
                event.ignore()
                return
        
        # Detener temporizadores
        self.blink_timer.stop()
        self.autosave_timer.stop()
        
        # Detener reproductor
        self.player.stop()
        
        # Guardar configuración de idioma
        LANG.save_settings()
        
        event.accept()

# ========== PUNTO DE ENTRADA ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    app.setStyle("Fusion")
    
    # Establecer estilo global
    app.setStyleSheet("""
        QMessageBox {
            background-color: #2c3e50;
            color: white;
        }
        QMessageBox QLabel {
            color: white;
        }
        QMessageBox QPushButton {
            background-color: #3498db;
            color: white;
            padding: 8px 16px;
            border-radius: 4px;
        }
        QMessageBox QPushButton:hover {
            background-color: #2980b9;
        }
    """)
    
    # Mostrar pantalla de inicio
    startup = StartupScreen()
    result = startup.exec()
    
    if result == QDialog.DialogCode.Accepted:
        action = getattr(startup, 'action', 'new')
        
        # Crear ventana principal
        window = MatchClipAnalyzer()
        window.show()
        
        # Configurar acciones según selección
        if action == "new":
            window.nuevo_proyecto()
        elif action == "open":
            window.abrir_proyecto()
        
        sys.exit(app.exec())
    else:
        sys.exit(0)