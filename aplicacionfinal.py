import sys, os, subprocess, time, json, platform, traceback, io
from PyQt6.QtWidgets import (QApplication, QMainWindow, QWidget, QVBoxLayout, 
                             QHBoxLayout, QPushButton, QListWidget, QGridLayout, 
                             QLabel, QFileDialog, QFrame, QScrollArea, 
                             QSlider, QInputDialog, QMenu, QColorDialog, 
                             QAbstractItemView, QDialog, QListWidgetItem,
                             QMessageBox, QTabWidget, QLineEdit, QTextEdit,
                             QComboBox, QCheckBox, QGroupBox, QProgressBar)
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput
from PyQt6.QtMultimediaWidgets import QVideoWidget
from PyQt6.QtCore import QUrl, Qt, QTimer, QThread, pyqtSignal, QBuffer
from PyQt6.QtGui import QPainter, QColor, QPen, QFont, QIcon, QPixmap, QImage

# ========== CONFIGURACIÓN MULTIPLATAFORMA ==========
def get_system_paths():
    """Obtiene rutas según el sistema operativo"""
    system = platform.system()
    
    if system == "Darwin":  # macOS
        base_dir = os.path.expanduser("~/Desktop/Analisis_video")
    elif system == "Windows":
        base_dir = os.path.expanduser("~/Documents/Analisis_video")
    else:  # Linux
        base_dir = os.path.expanduser("~/Analisis_video")
    
    return {
        "system": system,
        "base_dir": base_dir
    }

# Obtener configuración del sistema
SYS_CONFIG = get_system_paths()

# Configurar carpetas
CARPETA_RAIZ = SYS_CONFIG["base_dir"]
CARPETA_PROYECTOS = os.path.join(CARPETA_RAIZ, "Proyectos")
CARPETA_CAPTURAS = os.path.join(CARPETA_RAIZ, "Capturas")
CARPETA_CORTES = os.path.join(CARPETA_RAIZ, "Cortes")
CARPETA_EXPORT = os.path.join(CARPETA_RAIZ, "Exportaciones")
ARCHIVO_CONFIG = os.path.join(CARPETA_RAIZ, "botonera_config.json")

# Crear carpetas si no existen
for p in [CARPETA_PROYECTOS, CARPETA_CAPTURAS, CARPETA_CORTES, CARPETA_EXPORT]:
    if not os.path.exists(p): 
        os.makedirs(p)

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

class PlaylistDialog(QDialog):
    def __init__(self, clips, video_path, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Organizar Playlist")
        self.resize(400, 500)
        self.video_path = video_path
        self.clips = clips
        self.layout = QVBoxLayout(self)
        self.label = QLabel("Orden de los clips (Arrastra o usa botones):")
        self.layout.addWidget(self.label)
        self.list_w = QListWidget()
        for c in clips:
            it = QListWidgetItem(f"{c['nom']} - {c['tiempo']}")
            it.setData(Qt.ItemDataRole.UserRole, c)
            self.list_w.addItem(it)
        self.layout.addWidget(self.list_w)
        btns = QHBoxLayout()
        btn_up = QPushButton("⬆️ Subir"); btn_up.clicked.connect(self.mover_arriba)
        btn_down = QPushButton("⬇️ Bajar"); btn_down.clicked.connect(self.mover_abajo)
        btn_del = QPushButton("🗑️ Quitar"); btn_del.clicked.connect(self.quitar_item)
        btns.addWidget(btn_up); btns.addWidget(btn_down); btns.addWidget(btn_del)
        self.layout.addLayout(btns)
        self.btn_render = QPushButton("🎬 RENDERIZAR PLAYLIST")
        self.btn_render.setStyleSheet("background: #27ae60; font-weight: bold; height: 40px;")
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
        self.list_w.takeItem(self.list_w.currentRow())

    def finalizar(self):
        nombre, ok = QInputDialog.getText(self, "Guardar", "Nombre del archivo final:", text="PLAYLIST_FINAL")
        if ok and nombre:
            clips_finales = []
            for i in range(self.list_w.count()):
                clips_finales.append(self.list_w.item(i).data(Qt.ItemDataRole.UserRole))
            with open("lista.txt", "w") as f:
                for c in clips_finales:
                    f.write(f"file '{self.video_path}'\ninpoint {c['ini']/1000}\noutpoint {c['fin']/1000}\n")
            out = os.path.join(CARPETA_CORTES, f"{nombre}.mp4")
            subprocess.Popen(["ffmpeg", "-f", "concat", "-safe", "0", "-i", "lista.txt", "-c", "copy", "-y", out])
            self.accept()

class ExportWorker(QThread):
    progress = pyqtSignal(int)
    finished = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(self, video_path, clips, output_path, codec="copy"):
        super().__init__()
        self.video_path = video_path
        self.clips = clips
        self.output_path = output_path
        self.codec = codec

    def run(self):
        try:
            list_file = "temp_clips.txt"
            with open(list_file, "w") as f:
                for clip in self.clips:
                    f.write(f"file '{self.video_path}'\n")
                    f.write(f"inpoint {clip['ini']/1000}\n")
                    f.write(f"outpoint {clip['fin']/1000}\n")
            
            if self.codec == "copy":
                cmd = ["ffmpeg", "-f", "concat", "-safe", "0", 
                       "-i", list_file, "-c", "copy", "-y", self.output_path]
            else:
                cmd = ["ffmpeg", "-f", "concat", "-safe", "0", 
                       "-i", list_file, "-c:v", "libx264", "-preset", "medium",
                       "-crf", "23", "-c:a", "aac", "-b:a", "128k", "-y", self.output_path]
            
            total_clips = len(self.clips)
            for i in range(total_clips + 1):
                self.progress.emit(int((i / total_clips) * 100))
                time.sleep(0.5)
            
            result = subprocess.run(cmd, capture_output=True, text=True)
            
            if result.returncode == 0:
                self.finished.emit(self.output_path)
            else:
                self.error.emit(f"Error FFmpeg: {result.stderr}")
            
            if os.path.exists(list_file):
                os.remove(list_file)
                
        except Exception as e:
            self.error.emit(str(e))

class ConfigBotoneraDialog(QDialog):
    def __init__(self, config, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Configurar Botonera - Agregar/Quitar Botones")
        self.resize(600, 400)
        self.config = config
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        self.list_widget = QListWidget()
        for i, (nom, col, tipo, tec, carp, tc) in enumerate(self.config):
            self.list_widget.addItem(f"{i+1}. {nom} [{tec}] - Tipo: {tipo}")
        layout.addWidget(self.list_widget)
        
        btn_layout = QHBoxLayout()
        
        btn_agregar = QPushButton("➕ Agregar Botón")
        btn_agregar.clicked.connect(self.agregar_boton)
        btn_layout.addWidget(btn_agregar)
        
        btn_eliminar = QPushButton("🗑️ Eliminar Seleccionado")
        btn_eliminar.clicked.connect(self.eliminar_boton)
        btn_layout.addWidget(btn_eliminar)
        
        btn_editar = QPushButton("✏️ Editar Seleccionado")
        btn_editar.clicked.connect(self.editar_boton)
        btn_layout.addWidget(btn_editar)
        
        btn_mover_arriba = QPushButton("⬆️")
        btn_mover_arriba.clicked.connect(self.mover_arriba)
        btn_layout.addWidget(btn_mover_arriba)
        
        btn_mover_abajo = QPushButton("⬇️")
        btn_mover_abajo.clicked.connect(self.mover_abajo)
        btn_layout.addWidget(btn_mover_abajo)
        
        layout.addLayout(btn_layout)
        
        btn_box = QHBoxLayout()
        btn_aceptar = QPushButton("💾 Guardar Cambios")
        btn_aceptar.clicked.connect(self.aceptar)
        btn_cancelar = QPushButton("❌ Cancelar")
        btn_cancelar.clicked.connect(self.reject)
        btn_box.addWidget(btn_aceptar)
        btn_box.addWidget(btn_cancelar)
        layout.addLayout(btn_box)

    def agregar_boton(self):
        nom, ok1 = QInputDialog.getText(self, "Nuevo Botón", "Nombre del botón:")
        if not ok1 or not nom:
            return
            
        tec, ok2 = QInputDialog.getText(self, "Nuevo Botón", "Tecla de acceso rápido (una letra/número):")
        if not ok2 or not tec:
            return
            
        tipos = ["manual", "auto"]
        tipo, ok3 = QInputDialog.getItem(self, "Nuevo Botón", "Tipo de corte:", tipos, 0, False)
        if not ok3:
            return
            
        color = QColorDialog.getColor(QColor("#2980b9"), self, "Color del botón")
        if not color.isValid():
            return
            
        color_texto = QColorDialog.getColor(QColor("#3498db"), self, "Color del texto")
        if not color_texto.isValid():
            return
            
        carpeta = nom.replace(" ", "_").upper()
        nuevo_boton = [nom.upper(), color.name(), tipo, tec.upper(), carpeta, color_texto.name()]
        self.config.append(nuevo_boton)
        self.list_widget.addItem(f"{len(self.config)}. {nom} [{tec}] - Tipo: {tipo}")
        QMessageBox.information(self, "Botón Agregado", f"Botón '{nom}' agregado exitosamente.")

    def eliminar_boton(self):
        current_row = self.list_widget.currentRow()
        if current_row >= 0 and current_row < len(self.config):
            boton = self.config[current_row]
            reply = QMessageBox.question(self, "Confirmar Eliminación", 
                                         f"¿Estás seguro de eliminar el botón '{boton[0]}'?",
                                         QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No)
            if reply == QMessageBox.StandardButton.Yes:
                self.config.pop(current_row)
                self.list_widget.takeItem(current_row)
                for i in range(current_row, self.list_widget.count()):
                    self.list_widget.item(i).setText(f"{i+1}. {self.config[i][0]} [{self.config[i][3]}] - Tipo: {self.config[i][2]}")

    def editar_boton(self):
        current_row = self.list_widget.currentRow()
        if current_row < 0 or current_row >= len(self.config):
            return
            
        boton = self.config[current_row]
        
        nom, ok1 = QInputDialog.getText(self, "Editar Botón", "Nombre del botón:", text=boton[0])
        if not ok1:
            return
            
        tec, ok2 = QInputDialog.getText(self, "Editar Botón", "Tecla de acceso rápido:", text=boton[3])
        if not ok2:
            return
            
        tipos = ["manual", "auto"]
        tipo, ok3 = QInputDialog.getItem(self, "Editar Botón", "Tipo de corte:", tipos, tipos.index(boton[2]), False)
        if not ok3:
            return
            
        color = QColorDialog.getColor(QColor(boton[1]), self, "Color del botón")
        if not color.isValid():
            return
            
        color_texto = QColorDialog.getColor(QColor(boton[5]), self, "Color del texto")
        if not color_texto.isValid():
            return
            
        carpeta = nom.replace(" ", "_").upper()
        self.config[current_row] = [nom.upper(), color.name(), tipo, tec.upper(), carpeta, color_texto.name()]
        self.list_widget.item(current_row).setText(f"{current_row+1}. {nom} [{tec}] - Tipo: {tipo}")

    def mover_arriba(self):
        current_row = self.list_widget.currentRow()
        if current_row > 0:
            self.config[current_row], self.config[current_row-1] = self.config[current_row-1], self.config[current_row]
            self.list_widget.insertItem(current_row-1, self.list_widget.takeItem(current_row))
            self.list_widget.setCurrentRow(current_row-1)
            self.actualizar_numeracion()

    def mover_abajo(self):
        current_row = self.list_widget.currentRow()
        if current_row < len(self.config) - 1:
            self.config[current_row], self.config[current_row+1] = self.config[current_row+1], self.config[current_row]
            self.list_widget.insertItem(current_row+1, self.list_widget.takeItem(current_row))
            self.list_widget.setCurrentRow(current_row+1)
            self.actualizar_numeracion()

    def actualizar_numeracion(self):
        for i in range(self.list_widget.count()):
            boton = self.config[i]
            self.list_widget.item(i).setText(f"{i+1}. {boton[0]} [{boton[3]}] - Tipo: {boton[2]}")

    def aceptar(self):
        teclas = [boton[3] for boton in self.config]
        if len(teclas) != len(set(teclas)):
            QMessageBox.warning(self, "Advertencia", "Hay teclas de acceso rápido duplicadas. Por favor corrige antes de guardar.")
            return
            
        if len(self.config) == 0:
            QMessageBox.warning(self, "Advertencia", "La botonera no puede estar vacía.")
            return
            
        self.accept()

# ========== DIAGRAMA TÁCTICO CON CANCHA SIMPLE Y CORRECTA ==========
class CanchaWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent_diagrama = parent
        self.setMinimumSize(400, 600)  # Relación 2:3
        self.setMaximumWidth(500)
        self.drag_pos = None
        self.jugador_arrastrando = None
        self.tamano_ficha = 24
        
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # FONDO VERDE CLARO QUE PEDISTE (#daf9df)
        painter.fillRect(self.rect(), QColor("#daf9df"))
        
        w, h = self.width(), self.height()
        
        # LÍNEAS NEGRAS DE LA CANCHA - SOLO LÍNEAS, NO RELLENO
        painter.setPen(QPen(QColor("#000000"), 2))
        
        # Margen alrededor de la cancha
        margen_x = 20
        margen_y = 20
        ancho_cancha = w - 2 * margen_x
        alto_cancha = h - 2 * margen_y
        
        # Dibujar contorno de la cancha (rectángulo vacío)
        painter.drawRect(margen_x, margen_y, ancho_cancha, alto_cancha)
        
        # Línea de mitad de cancha
        painter.drawLine(margen_x, h//2, w - margen_x, h//2)
        
        # Círculo central (solo circunferencia)
        radio_central = min(ancho_cancha, alto_cancha) * 0.1
        painter.drawEllipse(w//2 - radio_central, h//2 - radio_central, 
                          radio_central*2, radio_central*2)
        
        # Punto central (pequeño círculo negro)
        painter.setBrush(QColor("#000000"))
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(w//2 - 3, h//2 - 3, 6, 6)
        
        # ÁREA CHICA - SOLO LÍNEAS, SIN RELLENO
        painter.setPen(QPen(QColor("#000000"), 2))
        ancho_area_chica = ancho_cancha * 0.25
        alto_area_chica = alto_cancha * 0.15
        
        # Área chica superior (rectángulo vacío)
        x_area_chica_sup = w//2 - ancho_area_chica//2
        y_area_chica_sup = margen_y
        painter.drawRect(x_area_chica_sup, y_area_chica_sup, ancho_area_chica, alto_area_chica)
        
        # Área chica inferior (rectángulo vacío)
        y_area_chica_inf = h - margen_y - alto_area_chica
        painter.drawRect(x_area_chica_sup, y_area_chica_inf, ancho_area_chica, alto_area_chica)
        
        # ÁREA GRANDE - SOLO LÍNEAS, SIN RELLENO
        ancho_area_grande = ancho_cancha * 0.4
        alto_area_grande = alto_cancha * 0.3
        
        # Área grande superior (rectángulo vacío)
        x_area_grande_sup = w//2 - ancho_area_grande//2
        y_area_grande_sup = margen_y
        painter.drawRect(x_area_grande_sup, y_area_grande_sup, ancho_area_grande, alto_area_grande)
        
        # Área grande inferior (rectángulo vacío)
        y_area_grande_inf = h - margen_y - alto_area_grande
        painter.drawRect(x_area_grande_sup, y_area_grande_inf, ancho_area_grande, alto_area_grande)
        
        # PUNTOS DE PENAL - PEQUEÑOS CÍRCULOS NEGROS
        painter.setBrush(QColor("#000000"))
        
        # Punto penal superior
        x_penal_sup = w//2
        y_penal_sup = margen_y + alto_area_grande * 0.7
        painter.drawEllipse(x_penal_sup - 4, y_penal_sup - 4, 8, 8)
        
        # Punto penal inferior
        y_penal_inf = h - margen_y - alto_area_grande * 0.3
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
        self.setWindowTitle("⚽ Diagrama Táctico - Personalizable")
        self.setWindowFlags(Qt.WindowType.Window | Qt.WindowType.WindowStaysOnTopHint)
        self.resize(450, 700)
        self.formacion = "4-3-3"
        self.jugadores = []
        self.posiciones_guardadas = []
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
        
        # Área de dibujo
        self.cancha_widget = CanchaWidget(self)
        layout.addWidget(self.cancha_widget, stretch=1)
        
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
        
        # POSICIONES PARA CANCHA DE 400x600
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

    def exportar_canchas_pdf(self):
        """Exporta las canchas a PDF - FUNCIONA"""
        try:
            from reportlab.lib.pagesizes import A4, landscape
            from reportlab.platypus import SimpleDocTemplate, Paragraph, Spacer, Image
            from reportlab.lib.styles import getSampleStyleSheet
            from reportlab.lib.units import inch
            import tempfile
        except ImportError:
            QMessageBox.warning(self, "Dependencia faltante",
                              "Necesitas instalar reportlab:\n"
                              "pip3 install reportlab")
            return
        
        # Obtener formaciones guardadas
        formaciones = []
        if hasattr(self.parent(), 'gestor_formaciones'):
            formaciones = self.parent().gestor_formaciones.formaciones_guardadas
        
        if not formaciones and not self.jugadores:
            QMessageBox.warning(self, "Sin formaciones", "No hay formaciones guardadas para exportar.")
            return
        
        nombre, ok = QInputDialog.getText(
            self, "Exportar PDF de Canchas",
            "Nombre del archivo PDF:",
            text=f"canchas_{time.strftime('%Y%m%d_%H%M')}"
        )
        
        if ok and nombre:
            ruta_salida = os.path.join(CARPETA_EXPORT, f"{nombre}.pdf")
            
            try:
                # Crear documento en horizontal
                doc = SimpleDocTemplate(ruta_salida, pagesize=landscape(A4))
                elements = []
                styles = getSampleStyleSheet()
                
                # Título
                titulo = Paragraph(f"<b>⚽ FORMULACIONES TÁCTICAS</b>", styles['Title'])
                elements.append(titulo)
                
                info_text = f"""
                <b>Fecha:</b> {time.strftime('%Y-%m-%d %H:%M:%S')}<br/>
                <b>Total de formaciones:</b> {len(formaciones) + 1}<br/>
                """
                info = Paragraph(info_text, styles['Normal'])
                elements.append(info)
                elements.append(Spacer(1, 20))
                
                # Si hay formaciones guardadas, usarlas; sino, usar la actual
                todas_formaciones = []
                
                # Agregar la formación actual primero
                minuto_actual = 0
                if hasattr(self.parent(), 'player'):
                    minuto_actual = self.parent().player.position() // 1000 // 60  # Convertir a minutos
                
                todas_formaciones.append({
                    "minuto": minuto_actual,
                    "formacion": self.formacion,
                    "jugadores": self.jugadores.copy(),
                    "notas": "Formación actual"
                })
                
                # Agregar las guardadas
                todas_formaciones.extend(formaciones)
                
                # Ordenar por minuto
                todas_formaciones.sort(key=lambda x: x['minuto'])
                
                # Procesar 3 formaciones por página
                for pagina in range(0, len(todas_formaciones), 3):
                    if pagina > 0:
                        elements.append(Spacer(1, 50))
                    
                    # Tomar hasta 3 formaciones para esta página
                    formaciones_pagina = todas_formaciones[pagina:pagina+3]
                    
                    # Para cada formación, crear su imagen
                    for idx, formacion_data in enumerate(formaciones_pagina):
                        # Crear imagen de la cancha
                        img_path = self.crear_imagen_cancha(formacion_data)
                        if img_path and os.path.exists(img_path):
                            try:
                                # Tamaño para 3 por fila
                                img = Image(img_path, width=3.5*inch, height=5.0*inch)
                                elements.append(img)
                                
                                # Si no es el último de la fila, agregar espacio horizontal
                                if idx < len(formaciones_pagina) - 1 and idx < 2:
                                    elements.append(Spacer(20, 0))
                            finally:
                                # Limpiar archivo temporal
                                if os.path.exists(img_path):
                                    os.unlink(img_path)
                    
                    # Salto de línea después de cada fila
                    elements.append(Spacer(1, 30))
                
                doc.build(elements)
                
                QMessageBox.information(
                    self, "PDF generado",
                    f"Canchas exportadas exitosamente a:\n{ruta_salida}\n"
                    f"Total: {len(todas_formaciones)} formaciones"
                )
                
                # Abrir PDF automáticamente
                if sys.platform == "darwin":
                    subprocess.run(["open", ruta_salida])
                elif sys.platform == "win32":
                    os.startfile(ruta_salida)
                    
            except Exception as e:
                QMessageBox.critical(
                    self, "Error al exportar",
                    f"No se pudo generar el PDF:\n{str(e)}\n\n"
                    f"Traceback: {traceback.format_exc()}"
                )

    def crear_imagen_cancha(self, formacion_data):
        """Crea una imagen PNG de la cancha - FUNCIONA BIEN"""
        try:
            # Crear un widget temporal para renderizar
            temp_widget = CanchaWidget(self)
            temp_widget.tamano_ficha = self.cancha_widget.tamano_ficha
            
            # Crear una clase temporal para pasar los jugadores
            class DiagramaTemp:
                def __init__(self, jugadores):
                    self.jugadores = jugadores
            
            temp_diagrama = DiagramaTemp(formacion_data['jugadores'].copy())
            temp_widget.parent_diagrama = temp_diagrama
            
            # Establecer tamaño fijo
            temp_widget.resize(400, 600)
            
            # Forzar que se dibuje
            temp_widget.update()
            
            # Crear pixmap (captura de pantalla del widget)
            pixmap = temp_widget.grab()
            
            # Guardar en archivo temporal
            temp_file = tempfile.NamedTemporaryFile(suffix='.png', delete=False)
            pixmap.save(temp_file.name, "PNG")
            temp_file.close()
            
            return temp_file.name
            
        except Exception as e:
            print(f"Error creando imagen: {e}")
            traceback.print_exc()
            return None

    def guardar_formacion_actual(self):
        """Guarda la formación actual"""
        minuto_actual = 0
        if hasattr(self.parent(), 'player'):
            minuto_actual = self.parent().player.position() // 1000
        
        datos_formacion = {
            "minuto": minuto_actual,
            "formacion": self.formacion,
            "jugadores": self.jugadores.copy(),
            "timestamp": time.time(),
            "tamano_fichas": self.cancha_widget.tamano_ficha
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
            QMessageBox.information(
                self, "Formación guardada",
                f"Formación {self.formacion} guardada en minuto {minuto_actual//60}:{minuto_actual%60:02d}"
            )

    def resetear_posiciones(self):
        self.cambiar_formacion(self.formacion)

    def closeEvent(self, event):
        if hasattr(self.parent(), 'diagrama_tactico'):
            self.parent().diagrama_tactico = None
        event.accept()

class ExportDialog(QDialog):
    def __init__(self, video_path, clips, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Exportar Proyecto")
        self.resize(500, 400)
        self.video_path = video_path
        self.clips = clips
        self.worker = None
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        
        info_group = QGroupBox("Información del Proyecto")
        info_layout = QVBoxLayout()
        info_layout.addWidget(QLabel(f"Clips a exportar: {len(self.clips)}"))
        info_layout.addWidget(QLabel(f"Video fuente: {os.path.basename(self.video_path)}"))
        info_group.setLayout(info_layout)
        layout.addWidget(info_group)
        
        config_group = QGroupBox("Configuración de Exportación")
        config_layout = QVBoxLayout()
        
        name_layout = QHBoxLayout()
        name_layout.addWidget(QLabel("Nombre:"))
        self.name_input = QLineEdit("Exportacion_" + time.strftime("%Y%m%d_%H%M"))
        name_layout.addWidget(self.name_input)
        config_layout.addLayout(name_layout)
        
        format_layout = QHBoxLayout()
        format_layout.addWidget(QLabel("Formato:"))
        self.format_combo = QComboBox()
        self.format_combo.addItems(["MP4", "AVI", "MOV"])
        format_layout.addWidget(self.format_combo)
        config_layout.addLayout(format_layout)
        
        codec_layout = QHBoxLayout()
        codec_layout.addWidget(QLabel("Codec:"))
        self.codec_combo = QComboBox()
        self.codec_combo.addItems(["Copia directa (rápido)", "H.264 (compatible)", "HEVC (alta calidad)"])
        format_layout.addWidget(self.codec_combo)
        config_layout.addLayout(codec_layout)
        
        quality_layout = QHBoxLayout()
        quality_layout.addWidget(QLabel("Calidad:"))
        self.quality_slider = QSlider(Qt.Orientation.Horizontal)
        self.quality_slider.setRange(1, 5)
        self.quality_slider.setValue(3)
        quality_layout.addWidget(self.quality_slider)
        quality_layout.addWidget(QLabel("Media"))
        config_layout.addLayout(quality_layout)
        
        self.include_overlay = QCheckBox("Incluir marca de tiempo en video")
        config_layout.addWidget(self.include_overlay)
        
        config_group.setLayout(config_layout)
        layout.addWidget(config_group)
        
        self.progress_bar = QProgressBar()
        layout.addWidget(self.progress_bar)
        
        self.status_label = QLabel("Listo para exportar")
        layout.addWidget(self.status_label)
        
        btn_layout = QHBoxLayout()
        self.export_btn = QPushButton("🚀 Exportar")
        self.export_btn.clicked.connect(self.iniciar_exportacion)
        self.cancel_btn = QPushButton("Cancelar")
        self.cancel_btn.clicked.connect(self.reject)
        btn_layout.addWidget(self.export_btn)
        btn_layout.addWidget(self.cancel_btn)
        layout.addLayout(btn_layout)

    def iniciar_exportacion(self):
        nombre = self.name_input.text()
        if not nombre:
            QMessageBox.warning(self, "Error", "Por favor ingresa un nombre para la exportación.")
            return
        
        codec_map = {
            "Copia directa (rápido)": "copy",
            "H.264 (compatible)": "libx264",
            "HEVC (alta calidad)": "libx265"
        }
        
        codec = codec_map.get(self.codec_combo.currentText(), "copy")
        formato = self.format_combo.currentText().lower()
        
        output_path = os.path.join(CARPETA_EXPORT, f"{nombre}.{formato}")
        
        self.worker = ExportWorker(self.video_path, self.clips, output_path, codec)
        self.worker.progress.connect(self.progress_bar.setValue)
        self.worker.finished.connect(self.exportacion_completada)
        self.worker.error.connect(self.exportacion_error)
        
        self.export_btn.setEnabled(False)
        self.status_label.setText("Exportando...")
        self.worker.start()

    def exportacion_completada(self, output_path):
        QMessageBox.information(self, "Exportación Completada", 
                               f"Proyecto exportado exitosamente a:\n{output_path}")
        self.accept()

    def exportacion_error(self, error_msg):
        QMessageBox.critical(self, "Error de Exportación", 
                           f"Error durante la exportación:\n{error_msg}")
        self.export_btn.setEnabled(True)
        self.status_label.setText("Error - Listo para reintentar")

class ProyectoManager:
    @staticmethod
    def guardar_proyecto(nombre_proyecto, video_path, cortes, config, metadata=None):
        proyecto_data = {
            "nombre": nombre_proyecto,
            "fecha_creacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "video_path": video_path,
            "cortes": cortes,
            "botonera_config": config,
            "metadata": metadata or {}
        }
        
        proyecto_folder = os.path.join(CARPETA_PROYECTOS, nombre_proyecto)
        if not os.path.exists(proyecto_folder):
            os.makedirs(proyecto_folder)
        
        proyecto_file = os.path.join(proyecto_folder, f"{nombre_proyecto}.json")
        with open(proyecto_file, 'w') as f:
            json.dump(proyecto_data, f, indent=2)
        
        capturas_folder = os.path.join(proyecto_folder, "Capturas")
        if not os.path.exists(capturas_folder):
            os.makedirs(capturas_folder)
        
        return proyecto_file

    @staticmethod
    def cargar_proyecto(archivo_proyecto):
        with open(archivo_proyecto, 'r') as f:
            proyecto_data = json.load(f)
        return proyecto_data

    @staticmethod
    def listar_proyectos():
        proyectos = []
        if os.path.exists(CARPETA_PROYECTOS):
            for item in os.listdir(CARPETA_PROYECTOS):
                proyecto_folder = os.path.join(CARPETA_PROYECTOS, item)
                if os.path.isdir(proyecto_folder):
                    for file in os.listdir(proyecto_folder):
                        if file.endswith('.json'):
                            proyecto_file = os.path.join(proyecto_folder, file)
                            try:
                                with open(proyecto_file, 'r') as f:
                                    proyecto_data = json.load(f)
                                    proyectos.append({
                                        "nombre": proyecto_data.get("nombre", item),
                                        "archivo": proyecto_file,
                                        "fecha": proyecto_data.get("fecha_creacion", ""),
                                        "video": proyecto_data.get("video_path", "")
                                    })
                            except:
                                pass
        return proyectos

class GestorFormaciones:
    def __init__(self):
        self.formaciones_guardadas = []
        
    def agregar_formacion(self, minuto, diagrama_data):
        self.formaciones_guardadas.append({
            "minuto": minuto,
            "formacion": diagrama_data["formacion"],
            "jugadores": diagrama_data["jugadores"].copy(),
            "timestamp": time.time(),
            "notas": diagrama_data.get("notas", "")
        })

# ========== CLASE PRINCIPAL ==========
class VideoSuite(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle(f"FOOTBALL ANALYZER PRO - V11.0 ({SYS_CONFIG['system']})")
        self.resize(1400, 950)
        self.video_path = ""
        self.cortes_activos = {}
        self.botones_widgets = {}
        self.velocidades = [0.25, 0.5, 0.75, 1.0, 1.5, 2.0, 3.0, 4.0, 8.0]
        self.vel_idx = 3
        self.config = self.cargar_config_botones()
        self.proyecto_actual = None
        self.proyecto_modificado = False
        
        # Inicializar multimedia
        self.player = QMediaPlayer()
        self.audio_output = QAudioOutput()
        self.player.setAudioOutput(self.audio_output)
        
        # Inicializar diagrama táctico
        self.diagrama_tactico = None
        self.gestor_formaciones = GestorFormaciones()
        
        self.init_ui()
        self.player.setVideoOutput(self.video_widget)
        self.player.positionChanged.connect(self.actualizar_pos)
        self.player.durationChanged.connect(self.actualizar_dur)
        
        self.blink_timer = QTimer()
        self.blink_timer.timeout.connect(self.actualizar_parpadeo)
        self.blink_timer.start(500)
        
        self.autosave_timer = QTimer()
        self.autosave_timer.timeout.connect(self.autoguardar_proyecto)
        self.autosave_timer.start(300000)

    def cargar_config_botones(self):
        default = [
            ["SALIDA", "#2980b9", "manual", "1", "Salida_Propia", "#3498db"],
            ["DESARROLLO", "#2980b9", "manual", "2", "Desarrollo_Propio", "#3498db"],
            ["TRANSICIÓN", "#2980b9", "auto", "3", "Transicion_Propia", "#3498db"],
            ["FINALIZACIÓN", "#2980b9", "auto", "4", "Finalizacion_Propia", "#3498db"],
            ["SALIDA RIVAL", "#c0392b", "manual", "5", "Salida_Rival", "#e74c3c"],
            ["DESARROLLO RIVAL", "#c0392b", "manual", "6", "Desarrollo_Rival", "#e74c3c"],
            ["TRANSICIÓN RIVAL", "#c0392b", "auto", "7", "Transicion_Rival", "#e74c3c"],
            ["FINALIZACIÓN RIVAL", "#c0392b", "auto", "8", "Finalizacion_Rival", "#e74c3c"]
        ]
        if os.path.exists(ARCHIVO_CONFIG):
            try:
                with open(ARCHIVO_CONFIG, 'r') as f:
                    return json.load(f)
            except:
                return default
        return default

    def init_ui(self):
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
        
        # Panel derecho
        self.panel_derecho = QWidget()
        self.panel_derecho.setFixedWidth(350)
        layout_listas = QHBoxLayout(self.panel_derecho)
        
        self.listas_widgets = {}
        self.labels_contadores = {}
        
        equipo_a_botones = []
        rival_botones = []
        
        for boton in self.config:
            if "RIVAL" in boton[0]:
                rival_botones.append(boton)
            else:
                equipo_a_botones.append(boton)
        
        # Columna Equipo A
        col_izq = QVBoxLayout()
        if equipo_a_botones:
            header_a = QLabel("EQUIPO A")
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
        
        # Columna Rival
        col_der = QVBoxLayout()
        if rival_botones:
            header_r = QLabel("RIVAL")
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
        
        btn_cap = QPushButton("📷 CAPTURAR PANTALLA")
        btn_cap.setStyleSheet("background: #8e44ad; color: white;")
        btn_cap.clicked.connect(self.capturar_pantalla_mac)
        
        btn_playlist = QPushButton("🎬 GENERAR PLAYLIST")
        btn_playlist.setStyleSheet("background: #27ae60; color: white;")
        btn_playlist.clicked.connect(self.preparar_playlist)
        
        fila_tiempo.addWidget(self.btn_timer)
        fila_tiempo.addWidget(btn_cap)
        fila_tiempo.addWidget(btn_playlist)
        fila_tiempo.addStretch()
        
        self.zoom_slider = QSlider(Qt.Orientation.Horizontal)
        self.zoom_slider.setRange(10, 2000)
        self.zoom_slider.setValue(10)
        self.zoom_slider.setFixedWidth(150)
        self.zoom_slider.valueChanged.connect(self.cambiar_zoom)
        
        fila_tiempo.addWidget(QLabel("🔍 ZOOM:"))
        fila_tiempo.addWidget(self.zoom_slider)
        
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
        btn_cargar.setStyleSheet("background: #34495e; color: white;")
        btn_cargar.clicked.connect(self.abrir_archivo)
        
        btn_config = QPushButton("⚙️ CONFIG BOTONERA")
        btn_config.setStyleSheet("background: #7f8c8d; color: white;")
        btn_config.clicked.connect(self.configurar_botonera_avanzada)
        
        velocidad_group = QHBoxLayout()
        velocidad_group.addWidget(QLabel("VELOCIDAD:"))
        btn_vel_down = QPushButton("⏪")
        btn_vel_down.clicked.connect(self.disminuir_velocidad)
        btn_vel_up = QPushButton("⏩")
        btn_vel_up.clicked.connect(self.aumentar_velocidad)
        self.lbl_vel = QLabel("x1.0")
        self.lbl_vel.setStyleSheet("color: #2ecc71; font-weight: bold;")
        
        velocidad_group.addWidget(btn_vel_down)
        velocidad_group.addWidget(self.lbl_vel)
        velocidad_group.addWidget(btn_vel_up)
        
        self.btn_mostrar_diagrama = QPushButton("⚽ Diagrama Táctico")
        self.btn_mostrar_diagrama.clicked.connect(self.mostrar_diagrama_tactico)
        self.btn_mostrar_diagrama.setStyleSheet("background: #16a085; color: white;")
        
        footer.addWidget(btn_cargar)
        footer.addWidget(btn_config)
        footer.addStretch()
        footer.addLayout(velocidad_group)
        footer.addStretch()
        footer.addWidget(self.btn_mostrar_diagrama)
        
        btn_exportar = QPushButton("📤 EXPORTAR")
        btn_exportar.setStyleSheet("background: #e67e22; color: white;")
        btn_exportar.clicked.connect(self.exportar_proyecto)
        footer.addWidget(btn_exportar)
        
        layout_principal.addLayout(footer)

    def crear_barra_menu(self):
        menubar = self.menuBar()
        
        file_menu = menubar.addMenu("📁 Archivo")
        
        nuevo_action = file_menu.addAction("🆕 Nuevo Proyecto")
        nuevo_action.triggered.connect(self.nuevo_proyecto)
        
        abrir_action = file_menu.addAction("📂 Abrir Proyecto")
        abrir_action.triggered.connect(self.abrir_proyecto)
        
        guardar_action = file_menu.addAction("💾 Guardar Proyecto")
        guardar_action.triggered.connect(self.guardar_proyecto)
        guardar_action.setShortcut("Ctrl+S")
        
        guardar_como_action = file_menu.addAction("💾 Guardar Como...")
        guardar_como_action.triggered.connect(self.guardar_proyecto_como)
        
        file_menu.addSeparator()
        
        exportar_action = file_menu.addAction("📤 Exportar Todo")
        exportar_action.triggered.connect(self.exportar_proyecto)
        
        file_menu.addSeparator()
        
        salir_action = file_menu.addAction("🚪 Salir")
        salir_action.triggered.connect(self.close)
        
        tools_menu = menubar.addMenu("🔧 Herramientas")
        
        diagrama_action = tools_menu.addAction("⚽ Diagrama Táctico")
        diagrama_action.triggered.connect(self.mostrar_diagrama_tactico)
        diagrama_action.setShortcut("Ctrl+T")
        
        guardar_formacion_action = tools_menu.addAction("💾 Guardar Formación Actual")
        guardar_formacion_action.triggered.connect(self.guardar_formacion_actual)
        guardar_formacion_action.setShortcut("Ctrl+G")
        
        config_action = tools_menu.addAction("⚙️ Configurar Botonera")
        config_action.triggered.connect(self.configurar_botonera_avanzada)
        
        stats_action = tools_menu.addAction("📊 Estadísticas")
        stats_action.triggered.connect(self.mostrar_estadisticas)
        
        exportar_pdf_action = tools_menu.addAction("📤 Exportar Canchas a PDF")
        exportar_pdf_action.triggered.connect(self.exportar_canchas_pdf)

    def crear_categoria_widget(self, boton, layout, color_base):
        nom_base = boton[0]
        
        info = QHBoxLayout()
        
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
        
        lbl_nombre = QLabel(nom_base.replace(" RIVAL", ""))
        lbl_nombre.setStyleSheet("font-weight: bold; color: #ecf0f1;")
        
        info.addWidget(lbl_nombre)
        info.addStretch()
        info.addWidget(self.labels_contadores[nom_base])
        layout.addLayout(info)
        
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

    def menu_contextual(self, pos, list_w, nom_cat):
        it = list_w.itemAt(pos)
        if not it: 
            return
            
        menu = QMenu()
        
        data = it.data(Qt.ItemDataRole.UserRole)
        
        act_render = menu.addAction("🎥 Renderizar este clip")
        act_renombrar = menu.addAction("✏️ Renombrar clip")
        act_notas = menu.addAction("📝 Agregar notas")
        menu.addSeparator()
        act_eliminar = menu.addAction("🗑️ Eliminar")
        
        res = menu.exec(list_w.mapToGlobal(pos))
        
        if res == act_render:
            self.ejecutar_ffmpeg(data['ini']/1000, (data['fin']-data['ini'])/1000, 
                               nom_cat, data['nombre'])
        
        elif res == act_renombrar:
            nuevo_nombre, ok = QInputDialog.getText(
                self, "Renombrar Clip", 
                "Nuevo nombre para el clip:", 
                text=data.get('nombre', f"{nom_cat} {data.get('numero', '1')}")
            )
            if ok and nuevo_nombre:
                data['nombre'] = nuevo_nombre
                it.setData(Qt.ItemDataRole.UserRole, data)
                
                tiempo_actual = it.text().split(']')[0] + ']'
                it.setText(f"{tiempo_actual} {nuevo_nombre}")
                
                for i, (inicio, fin, color, nombre) in enumerate(self.timeline.segmentos):
                    if inicio == data['ini'] and fin == data['fin']:
                        self.timeline.segmentos[i] = (inicio, fin, color, nuevo_nombre)
                        self.timeline.update()
                        break
                
                self.proyecto_modificado = True
        
        elif res == act_notas:
            notas, ok = QInputDialog.getMultiLineText(
                self, "Agregar Notas", 
                "Notas para este clip:",
                text=data.get('notas', '')
            )
            if ok:
                data['notas'] = notas
                it.setData(Qt.ItemDataRole.UserRole, data)
                self.proyecto_modificado = True
        
        elif res == act_eliminar:
            list_w.takeItem(list_w.row(it))
            self.labels_contadores[nom_cat].setText(str(list_w.count()))
            self.proyecto_modificado = True
            self.actualizar_timeline_segmentos()

    def dibujar_botones(self):
        for i in reversed(range(self.grid_btns.count())):
            widget = self.grid_btns.itemAt(i).widget()
            if widget:
                widget.setParent(None)
        
        num_columnas = 4
        num_botones = len(self.config)
        
        for i, (nom, col, tipo, tec, carp, tc) in enumerate(self.config):
            btn = QPushButton(f"{nom}\n[{tec}]")
            btn.setFixedHeight(55)
            
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
            btn.clicked.connect(lambda ch, idx=i: self.manejar_evento_idx(idx))
            
            btn.setToolTip(f"{nom}\nTipo: {tipo}\nTecla: {tec}")
            
            self.grid_btns.addWidget(btn, i // num_columnas, i % num_columnas)
            self.botones_widgets[nom] = (btn, col)

    def oscurecer_color(self, hex_color, amount=30):
        color = QColor(hex_color)
        return color.darker(100 + amount).name()

    def aclarar_color(self, hex_color, amount=30):
        color = QColor(hex_color)
        return color.lighter(100 + amount).name()

    def preparar_playlist(self):
        seleccionados = []
        for nom, lw in self.listas_widgets.items():
            for i in range(lw.count()):
                if lw.item(i).isSelected():
                    seleccionados.append(lw.item(i).data(Qt.ItemDataRole.UserRole))
        if seleccionados:
            dialog = PlaylistDialog(seleccionados, self.video_path, self)
            dialog.exec()

    def manejar_evento(self, nom, tipo, carp, col_t):
        if not self.video_path: 
            return
            
        pos = self.player.position()
        if tipo == "auto":
            ini = max(0, pos - 10000)
            self.registrar(ini, pos, nom, col_t)
        else:
            if nom not in self.cortes_activos: 
                self.cortes_activos[nom] = pos
                self.proyecto_modificado = True
            else:
                ini = self.cortes_activos.pop(nom)
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
                self.registrar(ini, pos, nom, col_t)

    def registrar(self, ini, fin, nom, col):
        if nom not in self.listas_widgets:
            return
            
        l = self.listas_widgets[nom]
        
        num_clip = l.count() + 1
        nombre_base = nom.replace(" RIVAL", "").replace("_", " ")
        nombre_auto = f"{nombre_base} {num_clip}"
        tiempo_formateado = self.format_time(ini)
        
        it = QListWidgetItem(f"[{tiempo_formateado}] {nombre_auto}")
        
        data = {
            "ini": ini, 
            "fin": fin, 
            "nom": nom, 
            "tiempo": tiempo_formateado,
            "nombre": nombre_auto,
            "color": col,
            "categoria": nom,
            "numero": num_clip
        }
        
        it.setData(Qt.ItemDataRole.UserRole, data)
        it.setForeground(QColor(col))
        l.addItem(it)
        
        self.labels_contadores[nom].setText(str(num_clip))
        self.timeline.marks.append((ini, col))
        self.timeline.segmentos.append((ini, fin, col, nombre_auto))
        self.timeline.update()
        
        self.proyecto_modificado = True
        self.actualizar_estado_proyecto()

    def actualizar_timeline_segmentos(self):
        self.timeline.segmentos = []
        for nom, lw in self.listas_widgets.items():
            for i in range(lw.count()):
                data = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if data:
                    self.timeline.segmentos.append(
                        (data['ini'], data['fin'], data.get('color', '#3498db'), data.get('nombre', 'Clip'))
                    )
        self.timeline.update()

    def ejecutar_ffmpeg(self, s, d, c, n):
        path = os.path.join(CARPETA_CORTES, c)
        if not os.path.exists(path): 
            os.makedirs(path)
        out = os.path.join(path, f"{n}_{int(s)}.mp4")
        
        cmd = ["ffmpeg", "-ss", str(s), "-i", self.video_path, 
               "-t", str(d), "-c", "copy", "-y", out]
        
        try:
            if SYS_CONFIG["system"] == "Windows":
                subprocess.Popen(cmd, creationflags=subprocess.CREATE_NO_WINDOW)
            else:
                subprocess.Popen(cmd)
                
            QMessageBox.information(self, "Renderizando", 
                                  f"Clip '{n}' se está renderizando...")
        except Exception as e:
            QMessageBox.critical(self, "Error FFmpeg", 
                               f"No se pudo ejecutar FFmpeg:\n{str(e)}")

    def abrir_archivo(self):
        if self.proyecto_modificado:
            reply = QMessageBox.question(
                self, "Proyecto modificado",
                "¿Deseas guardar los cambios antes de cargar un nuevo video?",
                QMessageBox.StandardButton.Yes | QMessageBox.StandardButton.No | QMessageBox.StandardButton.Cancel
            )
            if reply == QMessageBox.StandardButton.Yes:
                self.guardar_proyecto()
            elif reply == QMessageBox.StandardButton.Cancel:
                return
        
        file, _ = QFileDialog.getOpenFileName(
            self, "Seleccionar video", 
            "", 
            "Video files (*.mp4 *.avi *.mov *.mkv *.flv *.wmv)"
        )
        if file: 
            self.video_path = file
            self.player.setSource(QUrl.fromLocalFile(file))
            self.player.play()
            self.setFocus()
            self.proyecto_modificado = True
            self.actualizar_estado_proyecto()

    def manejar_evento_idx(self, idx):
        if idx < len(self.config):
            c = self.config[idx]
            self.manejar_evento(c[0], c[2], c[4], c[5])

    def actualizar_parpadeo(self):
        for nom in self.cortes_activos:
            if nom in self.botones_widgets:
                btn, col = self.botones_widgets[nom]
                idx = [c[0] for c in self.config].index(nom)  # CORRECCIÓN AQUÍ
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
        self.timeline.position = p
        self.timeline.update()
        self.btn_timer.setText(f"{self.format_time(p)} / {self.format_time(self.player.duration())}")

    def actualizar_dur(self, d):
        self.timeline.duration = d
        self.cambiar_zoom(self.zoom_slider.value())

    def cambiar_zoom(self, val):
        self.timeline.setFixedWidth(int(self.scroll_timeline.width() * (val / 10.0)))

    def saltar_a_evento(self, item):
        data = item.data(Qt.ItemDataRole.UserRole)
        if data:
            self.player.setPosition(data['ini'])
            self.player.play()

    def format_time(self, ms):
        s = int(ms//1000)
        horas = s // 3600
        minutos = (s % 3600) // 60
        segundos = s % 60
        if horas > 0:
            return f"{horas:02d}:{minutos:02d}:{segundos:02d}"
        return f"{minutos:02d}:{segundos:02d}"

    def toggle_panel(self):
        v = self.panel_derecho.isVisible()
        self.panel_derecho.setVisible(not v)
        self.btn_toggle.setText("<" if v else ">")

    def mostrar_diagrama_tactico(self):
        if self.diagrama_tactico is None or not self.diagrama_tactico.isVisible():
            self.diagrama_tactico = DiagramaTactico(self)
            main_window_geometry = self.geometry()
            diagrama_x = main_window_geometry.x() + main_window_geometry.width() - 400
            diagrama_y = main_window_geometry.y() + 100
            self.diagrama_tactico.move(diagrama_x, diagrama_y)
        
        self.diagrama_tactico.show()
        self.diagrama_tactico.raise_()

    def capturar_pantalla_mac(self):
        if not self.video_path: 
            return
            
        try:
            pixmap = self.video_widget.grab()
            nombre = os.path.join(CARPETA_CAPTURAS, f"Cap_{self.player.position()}.jpg")
            pixmap.save(nombre, "JPG")
            QMessageBox.information(self, "Captura exitosa", 
                                  "Captura de pantalla guardada.")
        except Exception as e:
            QMessageBox.warning(self, "Error", 
                              f"No se pudo capturar la pantalla: {str(e)}")

    def ir_a_tiempo_manual(self):
        txt, ok = QInputDialog.getText(self, "Saltar a tiempo", "Formato: HH:MM:SS o MM:SS")
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
                QMessageBox.warning(self, "Formato incorrecto", "Usa HH:MM:SS o MM:SS")

    def configurar_botonera_avanzada(self):
        dialog = ConfigBotoneraDialog(self.config, self)
        if dialog.exec():
            self.config = dialog.config
            with open(ARCHIVO_CONFIG, 'w') as f:
                json.dump(self.config, f, indent=2)
            self.reconstruir_interfaz()
            QMessageBox.information(self, "Configuración Guardada", "La botonera ha sido actualizada exitosamente.")

    def reconstruir_interfaz(self):
        self.listas_widgets.clear()
        self.labels_contadores.clear()
        self.botones_widgets.clear()
        self.cortes_activos.clear()
        
        self.panel_derecho.deleteLater()
        self.panel_derecho = QWidget()
        self.panel_derecho.setFixedWidth(350)
        layout_listas = QHBoxLayout(self.panel_derecho)
        
        equipo_a_botones = []
        rival_botones = []
        
        for boton in self.config:
            if "RIVAL" in boton[0]:
                rival_botones.append(boton)
            else:
                equipo_a_botones.append(boton)
        
        col_izq = QVBoxLayout()
        col_der = QVBoxLayout()
        
        if equipo_a_botones:
            header_a = QLabel("EQUIPO A")
            header_a.setStyleSheet("background: #2980b9; font-weight: bold; padding: 8px; border-radius: 5px;")
            header_a.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_izq.addWidget(header_a)
            
            for boton in equipo_a_botones:
                self.crear_categoria_widget(boton, col_izq, "#2980b9")
        
        if rival_botones:
            header_r = QLabel("RIVAL")
            header_r.setStyleSheet("background: #c0392b; font-weight: bold; padding: 8px; border-radius: 5px;")
            header_r.setAlignment(Qt.AlignmentFlag.AlignCenter)
            col_der.addWidget(header_r)
            
            for boton in rival_botones:
                self.crear_categoria_widget(boton, col_der, "#c0392b")
        
        layout_listas.addLayout(col_izq)
        layout_listas.addLayout(col_der)
        
        self.layout().itemAt(0).itemAt(0).layout().replaceWidget(
            self.layout().itemAt(0).itemAt(0).layout().itemAt(1).widget(), 
            self.panel_derecho
        )
        
        self.dibujar_botones()
        self.actualizar_timeline_segmentos()

    def nuevo_proyecto(self):
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
        
        nombre, ok = QInputDialog.getText(
            self, "Nuevo Proyecto", 
            "Nombre del proyecto:", 
            text=f"Proyecto_{time.strftime('%Y%m%d_%H%M')}"
        )
        
        if ok and nombre:
            self.proyecto_actual = nombre
            self.lbl_proyecto.setText(f"📁 {nombre}")
            self.proyecto_modificado = True
            self.actualizar_estado_proyecto()
            
            for lw in self.listas_widgets.values():
                lw.clear()
            for lbl in self.labels_contadores.values():
                lbl.setText("0")
            
            self.timeline.marks = []
            self.timeline.segmentos = []
            self.timeline.update()
            
            self.gestor_formaciones.formaciones_guardadas = []

    def guardar_proyecto(self):
        if not self.proyecto_actual:
            self.guardar_proyecto_como()
            return
        
        cortes = []
        for nom, lw in self.listas_widgets.items():
            for i in range(lw.count()):
                data = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if data:
                    cortes.append(data)
        
        metadata = {
            "total_clips": len(cortes),
            "video_duracion": self.player.duration(),
            "fecha_modificacion": time.strftime("%Y-%m-%d %H:%M:%S"),
            "formaciones_guardadas": self.gestor_formaciones.formaciones_guardadas
        }
        
        proyecto_file = ProyectoManager.guardar_proyecto(
            self.proyecto_actual,
            self.video_path,
            cortes,
            self.config,
            metadata
        )
        
        self.proyecto_modificado = False
        self.actualizar_estado_proyecto()
        QMessageBox.information(self, "Proyecto Guardado", f"Proyecto '{self.proyecto_actual}' guardado exitosamente.")

    def guardar_proyecto_como(self):
        nombre, ok = QInputDialog.getText(
            self, "Guardar Proyecto Como", 
            "Nombre del proyecto:", 
            text=self.proyecto_actual or f"Proyecto_{time.strftime('%Y%m%d_%H%M')}"
        )
        
        if ok and nombre:
            self.proyecto_actual = nombre
            self.lbl_proyecto.setText(f"📁 {nombre}")
            self.guardar_proyecto()

    def abrir_proyecto(self):
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
        
        proyectos = ProyectoManager.listar_proyectos()
        
        if not proyectos:
            QMessageBox.information(self, "No hay proyectos", "No hay proyectos guardados.")
            return
        
        dialog = QDialog(self)
        dialog.setWindowTitle("Abrir Proyecto")
        dialog.resize(600, 400)
        
        layout = QVBoxLayout(dialog)
        
        list_widget = QListWidget()
        for proyecto in proyectos:
            item = QListWidgetItem(f"📁 {proyecto['nombre']}\n📅 {proyecto['fecha']}\n🎬 {os.path.basename(proyecto['video'])}")
            item.setData(Qt.ItemDataRole.UserRole, proyecto)
            list_widget.addItem(item)
        
        layout.addWidget(list_widget)
        
        btn_layout = QHBoxLayout()
        btn_abrir = QPushButton("Abrir")
        btn_cancelar = QPushButton("Cancelar")
        
        btn_abrir.clicked.connect(lambda: self.cargar_proyecto_seleccionado(list_widget, dialog))
        btn_cancelar.clicked.connect(dialog.reject)
        
        btn_layout.addWidget(btn_abrir)
        btn_layout.addWidget(btn_cancelar)
        layout.addLayout(btn_layout)
        
        if dialog.exec():
            pass

    def cargar_proyecto_seleccionado(self, list_widget, dialog):
        current_item = list_widget.currentItem()
        if not current_item:
            QMessageBox.warning(dialog, "Selección requerida", "Por favor selecciona un proyecto.")
            return
        
        proyecto_data = current_item.data(Qt.ItemDataRole.UserRole)
        
        try:
            proyecto = ProyectoManager.cargar_proyecto(proyecto_data['archivo'])
            
            self.proyecto_actual = proyecto['nombre']
            self.video_path = proyecto['video_path']
            self.config = proyecto['botonera_config']
            
            if os.path.exists(self.video_path):
                self.player.setSource(QUrl.fromLocalFile(self.video_path))
            
            self.reconstruir_interfaz()
            
            for corte in proyecto.get('cortes', []):
                nom = corte['nom']
                if nom in self.listas_widgets:
                    lw = self.listas_widgets[nom]
                    it = QListWidgetItem(f"[{corte['tiempo']}] {corte.get('nombre', 'Clip')}")
                    it.setData(Qt.ItemDataRole.UserRole, corte)
                    it.setForeground(QColor(corte.get('color', '#3498db')))
                    lw.addItem(it)
                    
                    self.labels_contadores[nom].setText(str(lw.count()))
                    
                    self.timeline.segmentos.append((
                        corte['ini'], corte['fin'], 
                        corte.get('color', '#3498db'), 
                        corte.get('nombre', 'Clip')
                    ))
            
            if 'metadata' in proyecto and 'formaciones_guardadas' in proyecto['metadata']:
                self.gestor_formaciones.formaciones_guardadas = proyecto['metadata']['formaciones_guardadas']
            
            self.lbl_proyecto.setText(f"📁 {self.proyecto_actual}")
            self.proyecto_modificado = False
            self.actualizar_estado_proyecto()
            self.timeline.update()
            
            dialog.accept()
            QMessageBox.information(self, "Proyecto Cargado", f"Proyecto '{self.proyecto_actual}' cargado exitosamente.")
            
        except Exception as e:
            QMessageBox.critical(dialog, "Error", f"No se pudo cargar el proyecto: {str(e)}")

    def exportar_proyecto(self):
        if not self.video_path:
            QMessageBox.warning(self, "Sin video", "Primero carga un video para exportar.")
            return
        
        todos_clips = []
        for lw in self.listas_widgets.values():
            for i in range(lw.count()):
                data = lw.item(i).data(Qt.ItemDataRole.UserRole)
                if data:
                    todos_clips.append(data)
        
        if not todos_clips:
            QMessageBox.warning(self, "Sin clips", "No hay clips para exportar.")
            return
        
        dialog = ExportDialog(self.video_path, todos_clips, self)
        dialog.exec()

    def guardar_formacion_actual(self):
        if not self.diagrama_tactico:
            QMessageBox.warning(self, "Diagrama no abierto", 
                              "Abre el diagrama táctico primero.")
            return
            
        self.diagrama_tactico.guardar_formacion_actual()

    def exportar_canchas_pdf(self):
        if not self.diagrama_tactico:
            QMessageBox.warning(self, "Diagrama no abierto", 
                              "Abre el diagrama táctico primero.")
            return
            
        self.diagrama_tactico.exportar_canchas_pdf()

    def mostrar_estadisticas(self):
        total_clips = 0
        for lw in self.listas_widgets.values():
            total_clips += lw.count()
        
        stats = f"""
        📊 ESTADÍSTICAS DEL PROYECTO
        
        Proyecto: {self.proyecto_actual or 'Sin nombre'}
        Video: {os.path.basename(self.video_path) if self.video_path else 'No cargado'}
        
        Total de clips: {total_clips}
        Formaciones guardadas: {len(self.gestor_formaciones.formaciones_guardadas)}
        """
        
        for nom, lw in self.listas_widgets.items():
            stats += f"\n{nom}: {lw.count()} clips"
        
        QMessageBox.information(self, "Estadísticas", stats)

    def aumentar_velocidad(self):
        if self.vel_idx < len(self.velocidades) - 1:
            self.vel_idx += 1
            self.player.setPlaybackRate(self.velocidades[self.vel_idx])
            self.lbl_vel.setText(f"x{self.velocidades[self.vel_idx]}")

    def disminuir_velocidad(self):
        if self.vel_idx > 0:
            self.vel_idx -= 1
            self.player.setPlaybackRate(self.velocidades[self.vel_idx])
            self.lbl_vel.setText(f"x{self.velocidades[self.vel_idx]}")

    def autoguardar_proyecto(self):
        if self.proyecto_modificado and self.proyecto_actual:
            self.guardar_proyecto()

    def actualizar_estado_proyecto(self):
        estado = f"📁 {self.proyecto_actual or 'Sin proyecto'}"
        if self.proyecto_modificado:
            estado += " ●"
        
        self.lbl_proyecto.setText(estado)

    def closeEvent(self, event):
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
        else:
            event.accept()

    # ========== CORRECCIÓN DE LAS FLECHAS PARA 5 SEGUNDOS ==========
    def keyPressEvent(self, event):
        teclas_map = {c[3]: i for i, c in enumerate(self.config)}
        t = event.text().upper()
        
        if t in teclas_map:
            self.manejar_evento_idx(teclas_map[t])
        
        elif event.key() == Qt.Key.Key_Space:
            if self.player.playbackState() == QMediaPlayer.PlaybackState.PlayingState:
                self.player.pause()
            else:
                self.player.play()
        
        # FLECHAS PARA SALTOS DE 5 SEGUNDOS - CORREGIDO
        elif event.key() == Qt.Key.Key_Left:
            # Flecha izquierda: -5 segundos
            nueva_pos = max(0, self.player.position() - 5000)
            self.player.setPosition(nueva_pos)
            self.timeline.update()
        
        elif event.key() == Qt.Key.Key_Right:
            # Flecha derecha: +5 segundos
            nueva_pos = min(self.player.duration(), self.player.position() + 5000)
            self.player.setPosition(nueva_pos)
            self.timeline.update()
        
        # Flechas arriba/abajo para velocidad
        elif event.key() == Qt.Key.Key_Up:
            self.aumentar_velocidad()
        
        elif event.key() == Qt.Key.Key_Down:
            self.disminuir_velocidad()
        
        elif event.key() == Qt.Key.Key_V:
            self.vel_idx = (self.vel_idx + 1) % len(self.velocidades)
            self.player.setPlaybackRate(self.velocidades[self.vel_idx])
            self.lbl_vel.setText(f"x{self.velocidades[self.vel_idx]}")
        
        elif event.modifiers() == Qt.KeyboardModifier.ControlModifier:
            if event.key() == Qt.Key.Key_S:
                self.guardar_proyecto()
            elif event.key() == Qt.Key.Key_T:
                self.mostrar_diagrama_tactico()
            elif event.key() == Qt.Key.Key_G:
                self.guardar_formacion_actual()
            elif event.key() == Qt.Key.Key_R:
                if self.diagrama_tactico:
                    self.diagrama_tactico.resetear_posiciones()
            elif event.key() == Qt.Key.Key_P:
                if self.diagrama_tactico:
                    self.diagrama_tactico.exportar_canchas_pdf()

# ========== EJECUCIÓN PRINCIPAL ==========
if __name__ == "__main__":
    app = QApplication(sys.argv)
    
    pixmap = QPixmap(64, 64)
    pixmap.fill(Qt.GlobalColor.transparent)
    
    painter = QPainter(pixmap)
    painter.setRenderHint(QPainter.RenderHint.Antialiasing)
    
    painter.setBrush(QColor(255, 255, 255))
    painter.drawEllipse(2, 2, 60, 60)
    
    painter.setBrush(QColor(0, 0, 0))
    painter.drawEllipse(27, 10, 10, 10)
    painter.drawEllipse(47, 27, 10, 10)
    painter.drawEllipse(27, 44, 10, 10)
    painter.drawEllipse(7, 27, 10, 10)
    painter.drawEllipse(27, 27, 10, 10)
    
    painter.end()
    
    app.setWindowIcon(QIcon(pixmap))
    app.setApplicationName("Football Analyzer Pro")
    app.setApplicationDisplayName("Football Analyzer Pro V11.0")
    
    if SYS_CONFIG["system"] == "Windows":
        app.setStyle("Fusion")
    
    ex = VideoSuite()
    ex.show()
    
    sys.exit(app.exec())