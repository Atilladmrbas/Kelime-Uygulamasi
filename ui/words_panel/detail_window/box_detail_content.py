# ui/words_panel/detail_window/box_detail_content.py
import os
import sys

# ÖNCE import path'ini düzelt
current_dir = os.path.dirname(os.path.abspath(__file__))
if current_dir not in sys.path:
    sys.path.insert(0, current_dir)

from PyQt6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QFrame, QLabel, QSizePolicy, QPushButton, QDialog
from PyQt6.QtCore import Qt, QTimer, pyqtSignal, QPoint
from PyQt6.QtGui import QPainter, QColor
from PyQt6.QtWidgets import QApplication

try:
    from .box_detail_controller import get_controller
    CONTROLLER_AVAILABLE = True
except ImportError:
    CONTROLLER_AVAILABLE = False

try:
    from ui.words_panel.button_and_cards.card_teleporter import CardTeleporter
    CARDTELEPORTER_AVAILABLE = True
except ImportError:
    CARDTELEPORTER_AVAILABLE = False
    CardTeleporter = None

try:
    from .card_scroll_layout import CardScrollLayout
    print("✅ CardScrollLayout import başarılı")
except ImportError as e:
    print(f"❌ CardScrollLayout import hatası: {e}")
    CardScrollLayout = None

# Filtre widget'larını import et
try:
    from .filter_widgets import ContainerFilterWidgets
except ImportError:
    ContainerFilterWidgets = None

try:
    from .duplicate_checker import get_duplicate_checker
    DUPLICATE_CHECKER_AVAILABLE = True
except ImportError:
    DUPLICATE_CHECKER_AVAILABLE = False
    get_duplicate_checker = None

try:
    from .flash_card_dialog import GlobalPairDuplicateDialog, CopyCardWarningDialog
    GLOBAL_DUPLICATE_DIALOG_AVAILABLE = True
except ImportError:
    GLOBAL_DUPLICATE_DIALOG_AVAILABLE = False
    GlobalPairDuplicateDialog = None
    CopyCardWarningDialog = None


class DirectionalArrowButton(QPushButton):
    def __init__(self, direction="right", parent=None):
        super().__init__(parent)
        self.direction = direction
        self.is_selected = False
        self.base_color = QColor("#94a3b8")
        self.selected_color = QColor("#10b981") if direction == "right" else QColor("#3b82f6")
        self.hover_color = QColor("#64748b")
        
        self.setFixedSize(38, 38)
        self.setCursor(Qt.CursorShape.PointingHandCursor)
        self.setStyleSheet("""
            DirectionalArrowButton {
                background-color: transparent;
                border: none;
                border-radius: 19px;
            }
            DirectionalArrowButton:hover {
                background-color: #f1f5f9;
            }
        """)
    
    def set_selected(self, selected: bool):
        self.is_selected = selected
        self.update()
    
    def paintEvent(self, event):
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        center = self.rect().center()
        radius = 15
        color = self.selected_color if self.is_selected else self.base_color
        
        painter.setBrush(color)
        painter.setPen(Qt.PenStyle.NoPen)
        painter.drawEllipse(center, radius, radius)
        
        painter.setBrush(QColor("white"))
        painter.setPen(Qt.PenStyle.NoPen)
        
        size = 6
        if self.direction == "right":
            x, y = center.x(), center.y()
            points = [(x + size, y), (x - size/2, y - size), (x - size/2, y + size)]
        else:
            x, y = center.x(), center.y()
            points = [(x - size, y), (x + size/2, y - size), (x + size/2, y + size)]
        
        polygon_points = [QPoint(int(x), int(y)) for x, y in points]
        painter.drawPolygon(*polygon_points)
        painter.end()
    
    def enterEvent(self, event):
        if not self.is_selected:
            self.base_color = self.hover_color
        self.update()
        super().enterEvent(event)
    
    def leaveEvent(self, event):
        if not self.is_selected:
            self.base_color = QColor("#94a3b8")
        self.update()
        super().leaveEvent(event)


class BoxDetailContent(QWidget):
    card_deleted = pyqtSignal(object)
    card_teleported = pyqtSignal(int)
    
    def __init__(self, parent=None):
        super().__init__(parent)
        self.db = None
        self.box_id = None
        self.box_state = None
        self.state_loader = None
        
        self.controller = None
        if CONTROLLER_AVAILABLE:
            self.controller = get_controller()
        
        # ✅ YENİ: Global Duplicate Checker
        self.duplicate_checker = None
        if DUPLICATE_CHECKER_AVAILABLE:
            self.duplicate_checker = get_duplicate_checker()
        
        # Filtre widget'ları
        self.unknown_filter_widgets = None
        self.learned_filter_widgets = None
        
        # UI ayarları
        self.title_padding = (27, 30, 20, 25)
        self.title_divider_spacing = 12
        self.divider_margin = (10, 10)
        self.divider_style = (2, "#e2e8f0")
        
        # Kart verileri
        self.cards_data = {"unknown": [], "learned": []}
        self.card_widgets = {"unknown": [], "learned": []}
        
        # CardScrollLayout'lar
        self.unknown_scroll_layout = None
        self.learned_scroll_layout = None
        
        # CardTeleporter
        self.card_teleporter = None
        self._create_card_teleporter()
        self._connect_card_teleporter_signals()
        
        # Timer'lar
        self.card_teleporter_timer = QTimer(self)
        self.card_teleporter_timer.timeout.connect(self._try_connect_card_teleporter)
        self.card_teleporter_timer.setSingleShot(True)
        self.card_teleporter_timer.start(100)
        
        self.setup_ui()
        
        # ✅ YENİ: Duplicate checker'a kayıt ol
        self._register_with_duplicate_checker()

    def _register_with_duplicate_checker(self):
        """Kendini global duplicate checker'a kaydet"""
        if self.duplicate_checker and hasattr(self.duplicate_checker, 'register_content'):
            content_id = id(self)
            self.duplicate_checker.register_content(content_id, self)
    
    def _unregister_from_duplicate_checker(self):
        """Global duplicate checker'dan kaldır"""
        if self.duplicate_checker and hasattr(self.duplicate_checker, 'unregister_content'):
            content_id = id(self)
            self.duplicate_checker.unregister_content(content_id)

    def _connect_card_teleporter_signals(self):
        if self.card_teleporter and hasattr(self.card_teleporter, 'card_moved'):
            try:
                self.card_teleporter.card_moved.disconnect()
            except:
                pass
            self.card_teleporter.card_moved.connect(self._on_card_teleported)

    def _on_card_learned(self, card):
        """Kart öğrenildi container'ına taşındığında"""
        print(f"🎓 Kart öğrenildi container'ına taşındı: {card.card_id}")
        
        # Kartın overlay'ini hemen kaldır
        if hasattr(card, 'on_card_learned'):
            card.on_card_learned()
    
    def _create_card_teleporter(self):
        if not CARDTELEPORTER_AVAILABLE:
            return False
        
        try:
            self.card_teleporter = CardTeleporter(parent_widget=self)
            if hasattr(self.card_teleporter, 'selection_changed'):
                try:
                    self.card_teleporter.selection_changed.disconnect()
                except:
                    pass
                self.card_teleporter.selection_changed.connect(
                    lambda: self.selection_changed_externally()
                )
            return True
        except Exception:
            return False
    
    def setup_ui(self):
        main_layout = QHBoxLayout(self)
        main_layout.setContentsMargins(10, 10, 10, 10)
        main_layout.setSpacing(20)
        
        # Container'ları oluştur
        self.unknown_container = self._create_container("Bilmediklerim", "unknown")
        self.learned_container = self._create_container("Öğrendiklerim", "learned")
        
        main_layout.addWidget(self.unknown_container, 1)
        main_layout.addWidget(self.learned_container, 1)
        
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
    
    def _create_container(self, title, container_type):
        """Container oluştur - artık CardScrollLayout kullanıyor"""
        container = QFrame()
        container.setStyleSheet("""
            QFrame {
                background-color: #f8f9fa;
                border: none;
                border-radius: 8px;
            }
        """)
        container.setMinimumWidth(300)
        
        layout = QVBoxLayout(container)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(0)
        
        # Başlık widget'ı
        title_widget = QWidget()
        title_widget.setStyleSheet("background-color: transparent;")
        title_layout = QHBoxLayout(title_widget)
        title_layout.setContentsMargins(25, 20, 25, 15)
        title_layout.setSpacing(10)
        
        # Başlık etiketi
        title_label = QLabel(title)
        title_label.setStyleSheet("""
            QLabel {
                font-size: 20px;
                font-weight: 700;
                color: #2d3748;
                padding: 0px;
                margin: 0px;
            }
        """)
        title_label.setAlignment(Qt.AlignmentFlag.AlignLeft | Qt.AlignmentFlag.AlignVCenter)
        title_layout.addWidget(title_label)
        
        # Filtre widget'ları
        if ContainerFilterWidgets:
            filter_widgets = ContainerFilterWidgets(container_type)
            filter_widgets.filter_changed.connect(
                lambda st, ci, is_filt: self._on_filter_changed(container_type, st, ci, is_filt)
            )
            title_layout.addWidget(filter_widgets)
            
            if container_type == "unknown":
                self.unknown_filter_widgets = filter_widgets
            else:
                self.learned_filter_widgets = filter_widgets
        
        # Transfer butonları
        if container_type == "unknown":
            self.transfer_to_learned_btn = DirectionalArrowButton("right")
            self.transfer_to_learned_btn.clicked.connect(
                lambda: self._on_transfer_button_clicked("unknown", "learned")
            )
            title_layout.addWidget(self.transfer_to_learned_btn)
        else:
            self.transfer_to_unknown_btn = DirectionalArrowButton("left")
            self.transfer_to_unknown_btn.clicked.connect(
                lambda: self._on_transfer_button_clicked("learned", "unknown")
            )
            title_layout.addWidget(self.transfer_to_unknown_btn)
        
        layout.addWidget(title_widget)
        
        # Bölücü
        h, color = self.divider_style
        l_margin, r_margin = self.divider_margin
        divider = QFrame()
        divider.setFrameShape(QFrame.Shape.HLine)
        divider.setStyleSheet(f"""
            QFrame {{
                border: none;
                border-top: {h}px solid {color};
                margin-left: {l_margin}px;
                margin-right: {r_margin}px;
            }}
        """)
        divider.setFixedHeight(h)
        layout.addWidget(divider)
        
        # CardScrollLayout oluştur
        if CardScrollLayout:
            scroll_layout = CardScrollLayout(container_type, parent=container)
            layout.addWidget(scroll_layout, 1)
            
            # Kaydet
            if container_type == "unknown":
                self.unknown_scroll_layout = scroll_layout
            else:
                self.learned_scroll_layout = scroll_layout
            
            # Container özelliklerini kaydet
            container.scroll_layout = scroll_layout
            container.container_type = container_type
        
        container.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        
        return container
    
    def _show_global_duplicate_warning(self, duplicate_info):
        """Global duplicate uyarısı göster"""
        try:
            if GLOBAL_DUPLICATE_DIALOG_AVAILABLE and GlobalPairDuplicateDialog:
                dialog = GlobalPairDuplicateDialog(duplicate_info, self)
                return dialog.exec() == QDialog.DialogCode.Accepted
            else:
                # Fallback: Basit bir mesaj göster
                print(f"⚠️ DUPLICATE BULUNDU: {duplicate_info}")
                return True
        except Exception as e:
            print(f"❌ Global duplicate uyarısı gösterilirken hata: {e}")
        return True  # Hata durumunda devam et
    
    def _show_copy_card_warning(self, copy_cards_in_boxes):
        try:
            if CopyCardWarningDialog:
                dialog = CopyCardWarningDialog(copy_cards_in_boxes, self)
                return dialog.exec() == QDialog.DialogCode.Accepted
        except Exception as e:
            print(f"❌ Kopya kart uyarısı gösterilirken hata: {e}")
            return True
        return True
    
    def _on_filter_changed(self, container_type, search_text, color_id, is_filtering):
        """Filtre değişikliği için tek handler"""
        self._apply_filter_to_container(container_type, search_text, color_id, is_filtering)

    def _apply_filter_to_container(self, container_type, search_text, color_id, is_filtering):
        """Filtreyi container'a uygula - BAŞ HARFE GÖRE!"""
        scroll_layout = self.unknown_scroll_layout if container_type == "unknown" else self.learned_scroll_layout
        
        if not scroll_layout:
            return
        
        if not is_filtering:
            # Tüm kartları göster
            scroll_layout.filter_cards(lambda card: True)
            return
        
        # Filtre fonksiyonu - BAŞ HARFE GÖRE!
        def filter_func(card_widget):
            card_data = self._get_card_data_for_widget(card_widget, container_type)
            if not card_data:
                return False
            
            # ContainerFilterWidgets.card_matches_filter kullan
            from .filter_widgets import ContainerFilterWidgets
            
            return ContainerFilterWidgets.card_matches_filter(
                card_data=card_data,
                search_text=search_text,
                color_id=color_id if container_type == "unknown" else 0,
                db=self.db
            )
        
        # Filtreyi uygula
        scroll_layout.filter_cards(filter_func)
        print(f"🔍 [BoxDetailContent] {container_type} filtresi uygulandı: '{search_text}'")
    
    def _get_card_data_for_widget(self, card_widget, container_type):
        """Kart widget'ı için veri bul"""
        card_id = getattr(card_widget, 'card_id', None)
        if not card_id:
            return None
        
        for data in self.cards_data[container_type]:
            if data.get('id') == card_id:
                return data
        
        return None
        
    def add_card_to_container(self, container_type, card_data=None, show_duplicate_warning=False):
        print("=" * 80)
        print(f"🎴 add_card_to_container ÇAĞRILDI:")
        print(f"   - Container: {container_type}")
        print(f"   - show_duplicate_warning: {show_duplicate_warning}")
        print(f"   - card_data: {card_data}")
        
        scroll_layout = self.unknown_scroll_layout if container_type == "unknown" else self.learned_scroll_layout
        
        if not scroll_layout:
            print("❌ Scroll layout yok!")
            return None
        
        try:
            from ui.words_panel.button_and_cards.flashcard_view import FlashCardView
            print("✅ FlashCardView import edildi")
            
            simple_data = {}
            if card_data:
                if isinstance(card_data, dict):
                    simple_data = card_data.copy()
                    print(f"   - card_data DICT: {simple_data}")
                else:
                    simple_data = {
                        'id': getattr(card_data, 'id', None),
                        'english': getattr(card_data, 'english', ''),
                        'turkish': getattr(card_data, 'turkish', ''),
                        'detail': getattr(card_data, 'detail', '{}'),
                        'box_id': getattr(card_data, 'box_id', self.box_id),
                        'bucket': getattr(card_data, 'bucket', 0)
                    }
                    print(f"   - card_data OBJE: {simple_data}")
            
            simple_data.setdefault('english', '')
            simple_data.setdefault('turkish', '')
            simple_data.setdefault('detail', '{}')
            
            print(f"📊 Simple data: {simple_data}")
            
            # Kart ID kontrolü
            card_id = simple_data.get('id')
            if card_id:
                print(f"🔍 Mevcut kart kontrolü: ID={card_id}")
                for i, existing_card in enumerate(self.card_widgets[container_type]):
                    if hasattr(existing_card, 'card_id') and existing_card.card_id == card_id:
                        print(f"✅ Kart zaten mevcut: index={i}")
                        return existing_card
            
            # ✅ YENİ: GLOBAL ÇİFT DUPLICATE KONTROLÜ - TÜM SİSTEMDE!
            if show_duplicate_warning and self.duplicate_checker:
                front_text = simple_data.get('english', '').strip()
                back_text = simple_data.get('turkish', '').strip()
                
                print(f"🔍 DUPLICATE KONTROLÜ BAŞLIYOR:")
                print(f"   - front_text: '{front_text}'")
                print(f"   - back_text: '{back_text}'")
                print(f"   - duplicate_checker mevcut: {self.duplicate_checker is not None}")
                print(f"   - 🔥 TÜM SİSTEMDE aranacak (check_only_same_box=False)")
                
                if front_text and back_text:
                    print(f"🔍 YENİ KART DUPLICATE KONTROLÜ: '{front_text}' → '{back_text}'")
                    
                    # Global duplicate kontrolü yap - TÜM SİSTEMDE!
                    duplicate_info = self.duplicate_checker.check_global_pair_duplicate(
                        front_text=front_text,
                        back_text=back_text,
                        exclude_card_id=simple_data.get('id'),
                        current_box_id=self.box_id,
                        check_only_same_box=False  # ✅ BÜTÜN SİSTEMDE ARA!
                    )
                    
                    print(f"🔍 Duplicate kontrol SONUCU:")
                    print(f"   - has_duplicate: {duplicate_info.get('has_duplicate', False)}")
                    print(f"   - total_count: {duplicate_info.get('total_count', 0)}")
                    print(f"   - locations: {len(duplicate_info.get('found_locations', []))} adet")
                    print(f"   - check_only_same_box: {duplicate_info.get('check_only_same_box', False)}")
                    
                    # DEBUG: Bulunan duplicate'ları göster
                    if duplicate_info.get('found_locations'):
                        print(f"📋 BULUNAN DUPLICATE'LAR:")
                        for i, loc in enumerate(duplicate_info['found_locations'], 1):
                            same_box_mark = "✅ AYNI BOX" if loc.get('same_box') else "🌍 FARKLI BOX"
                            print(f"   {i}. {same_box_mark} - Box {loc['box_id']} - {loc['container']} - ID: {loc['card_id']}")
                    
                    if duplicate_info.get('has_duplicate', False):
                        print("⚠️ DUPLICATE BULUNDU! Dialog gösteriliyor...")
                        # Kullanıcıya uyarı göster
                        should_continue = self._show_global_duplicate_warning(duplicate_info)
                        print(f"   - Kullanıcı seçimi: {'DEVAM' if should_continue else 'İPTAL'}")
                        if not should_continue:
                            print("❌ Kullanıcı iptal etti, kart eklenmiyor")
                            return None
                        else:
                            print("✅ Kullanıcı devam etmeyi seçti, kart ekleniyor")
                    else:
                        print("✅ Duplicate BULUNAMADI, kart ekleniyor")
            else:
                print(f"⚠️ Duplicate kontrol YAPILMIYOR:")
                print(f"   - show_duplicate_warning: {show_duplicate_warning}")
                print(f"   - duplicate_checker mevcut: {self.duplicate_checker is not None}")
                if not show_duplicate_warning:
                    print(f"   - ❌ show_duplicate_warning=False olduğu için kontrol yapılmıyor!")
            
            # Kart widget'ını oluştur
            print(f"🛠️ FlashCardView oluşturuluyor...")
            card = FlashCardView(data=simple_data)
            print(f"✅ FlashCardView oluşturuldu: {card}")
            
            if simple_data and 'id' in simple_data:
                card.card_id = simple_data['id']
                card.box_id = simple_data.get('box_id', self.box_id)
                card.bucket_id = simple_data.get('bucket', 0)
                print(f"📝 Kart özellikleri ayarlandı: ID={card.card_id}, Box={card.box_id}, Bucket={card.bucket_id}")
            
            card.db = self.db
            print(f"✅ Database atandı")
            
            # ✅ DEBUG: Sinyal bağlantısını DETAYLI kontrol et
            print(f"🔗 SİNYAL BAĞLANTILARI KONTROLÜ:")
            print(f"   - card objesi: {card}")
            print(f"   - card.updated var mı?: {hasattr(card, 'updated')}")
            print(f"   - card.card_clicked var mı?: {hasattr(card, 'card_clicked')}")
            print(f"   - card.delete_requested var mı?: {hasattr(card, 'delete_requested')}")
            
            # updated sinyali var mı kontrol et
            if hasattr(card, 'updated'):
                print(f"   - ✅ card.updated SINYALI MEVCUT")
                
                # 1. ÖNCE tüm eski bağlantıları temizle
                try:
                    card.updated.disconnect()
                    print(f"   - Eski bağlantılar temizlendi")
                except Exception as e:
                    print(f"   - Eski bağlantı yok veya temizlenemedi: {e}")
                
                # 2. DEBUG sinyali ekle
                def debug_signal():
                    print(f"🚨🚨🚨 SİNYAL GELDİ! Kart {getattr(card, 'card_id', 'N/A')} güncellendi")
                    print(f"   - Kart objesi: {card}")
                    print(f"   - İngilizce: {getattr(card, 'english_edit', getattr(card, 'english_label', 'N/A'))}")
                    print(f"   - Türkçe: {getattr(card, 'turkish_edit', getattr(card, 'turkish_label', 'N/A'))}")
                
                card.updated.connect(debug_signal)
                print(f"   - Debug sinyali bağlandı")
                
                # 3. ASIL handler'ı bağla
                card.updated.connect(
                    lambda: self._on_card_updated(card)
                )
                print(f"   - Ana handler bağlandı: self._on_card_updated")
            else:
                print(f"❌❌❌ CRITICAL: card.updated SINYALI YOK!")
                print(f"   - FlashCardView sınıfında updated sinyali tanımlı değil")
                print(f"   - Sınıf özellikleri: {dir(card)}")
            
            # Diğer sinyalleri bağla
            if hasattr(card, 'card_clicked'):
                print(f"   - card_clicked bağlanıyor...")
                card.card_clicked.connect(
                    lambda c=card, ct=container_type: self._on_card_clicked(c, ct)
                )
            
            if hasattr(card, 'delete_requested'):
                print(f"   - delete_requested bağlanıyor...")
                card.delete_requested.connect(
                    lambda c=card, ct=container_type: self._on_card_deleted(c, ct)
                )
            
            # Kartı ekle
            print(f"📥 Kart listelere ekleniyor...")
            self.cards_data[container_type].append(simple_data)
            self.card_widgets[container_type].append(card)
            print(f"✅ Listelere eklendi:")
            print(f"   - cards_data[{container_type}]: {len(self.cards_data[container_type])} kart")
            print(f"   - card_widgets[{container_type}]: {len(self.card_widgets[container_type])} widget")
            
            # CardScrollLayout'a ekle
            print(f"📜 CardScrollLayout'a ekleniyor...")
            success = scroll_layout.add_card(card)
            print(f"✅ CardScrollLayout sonucu: {'Başarılı' if success else 'Başarısız'}")
            
            if not success:
                return None
            
            # State'i güncelle
            if self.box_state and hasattr(card, 'card_id') and card.card_id:
                bucket = 0 if container_type == "unknown" else 1
                self._update_state_for_card(card.card_id, bucket)
            
            # Overlay'ı başlat
            self._initialize_card_overlay(card)
            
            # Filtreleri kontrol et
            if container_type == "unknown" and self.unknown_filter_widgets:
                filter_state = self.unknown_filter_widgets.get_filter_state()
                if filter_state.get('is_filtering', False):
                    self._apply_filter_to_container(
                        container_type,
                        filter_state.get('search_text', ''),
                        filter_state.get('color_id', 0),
                        True
                    )
            elif container_type == "learned" and self.learned_filter_widgets:
                filter_state = self.learned_filter_widgets.get_filter_state()
                if filter_state.get('is_filtering', False):
                    self._apply_filter_to_container(
                        container_type,
                        filter_state.get('search_text', ''),
                        0,
                        True
                    )
            
            # ✅ YENİ: Duplicate checker cache'ini güncelle
            if self.duplicate_checker:
                QTimer.singleShot(100, lambda: self.duplicate_checker._update_cache_for_content(self))
                print(f"✅ Duplicate checker cache güncellenecek")
            
            print(f"✅✅✅ Kart başarıyla eklendi: ID={getattr(card, 'card_id', 'N/A')}")
            print("=" * 80)
            
            return card
                    
        except Exception as e:
            print(f"❌❌❌ Kart eklenirken CRITICAL HATA: {e}")
            import traceback
            traceback.print_exc()
            print("=" * 80)
            return None
    
    def _initialize_card_overlay(self, card_widget):
        if not card_widget or not self.db:
            return
        
        if not hasattr(card_widget, 'card_id') or not card_widget.card_id:
            return
        
        try:
            cursor = self.db.conn.cursor()
            cursor.execute("SELECT is_copy FROM words WHERE id=?", (card_widget.card_id,))
            row = cursor.fetchone()
            
            if row and row[0] == 1:
                return
        except Exception:
            return
        
        if hasattr(card_widget, 'bucket_id') and card_widget.bucket_id == 1:
            return
        
        try:
            from ui.words_panel.button_and_cards.color_overlay import ColorOverlayWidget
            from PyQt6.QtCore import QTimer
            
            card_widget.color_overlay = ColorOverlayWidget(parent_card=card_widget)
            card_widget.color_overlay.db = self.db
            
            card_widget.color_overlay.overlay_updated.connect(
                lambda: card_widget.update() if card_widget else None
            )
            
            QTimer.singleShot(300, lambda: card_widget.color_overlay.update_overlay()
                            if hasattr(card_widget, 'color_overlay') and card_widget.color_overlay else None)
        except Exception:
            card_widget.color_overlay = None
    
    def _on_card_clicked(self, card_widget, container_type: str):
        if not self.card_teleporter:
            self._create_card_teleporter()
        
        if not self.card_teleporter:
            return
        
        card_widget.teleporter = self.card_teleporter
        app = QApplication.instance()
        ctrl_pressed = app and (app.keyboardModifiers() & Qt.KeyboardModifier.ControlModifier)
        
        if ctrl_pressed:
            self.card_teleporter.toggle_card_selection(card_widget)
            self._update_transfer_buttons(self.card_teleporter)
            self._notify_all_containers_selection_changed()
    
    def _on_transfer_button_clicked(self, from_type: str, to_type: str):
        if not self.db:
            return
        
        if not self.card_teleporter:
            self.card_teleporter = self._find_card_teleporter()
        
        if not self.card_teleporter or not self.card_teleporter.has_selection():
            return
        
        cards_to_transfer = []
        for card_id in list(self.card_teleporter.selected_cards):
            if self._is_card_in_container(card_id, from_type):
                cards_to_transfer.append(card_id)
        
        if not cards_to_transfer:
            return
        
        new_bucket = 1 if to_type == "learned" else 0
        successful_transfers = []
        
        for card_id in cards_to_transfer:
            success = self._transfer_single_card(card_id, new_bucket, from_type, to_type)
            
            if success:
                if self.controller and new_bucket == 1:
                    if self.controller._is_original_card(card_id):
                        self.controller.handle_card_learned(card_id, self.box_id)
                
                successful_transfers.append(card_id)
                self.card_teleporter.remove_card_selection(card_id)
        
        if successful_transfers:
            if self.card_teleporter:
                self._update_transfer_buttons(self.card_teleporter)
            
            self._refresh_box_counter()
            
            # Filtreleri yeniden uygula
            if from_type == "unknown" and self.unknown_filter_widgets:
                filter_state = self.unknown_filter_widgets.get_filter_state()
                if filter_state.get('is_filtering', False):
                    self._apply_filter_to_container(
                        "unknown",
                        filter_state.get('search_text', ''),
                        filter_state.get('color_id', 0),
                        True
                    )
            
            if to_type == "unknown" and self.unknown_filter_widgets:
                filter_state = self.unknown_filter_widgets.get_filter_state()
                if filter_state.get('is_filtering', False):
                    self._apply_filter_to_container(
                        "unknown",
                        filter_state.get('search_text', ''),
                        filter_state.get('color_id', 0),
                        True
                    )
            
            if from_type == "learned" and self.learned_filter_widgets:
                filter_state = self.learned_filter_widgets.get_filter_state()
                if filter_state.get('is_filtering', False):
                    self._apply_filter_to_container(
                        "learned",
                        filter_state.get('search_text', ''),
                        0,
                        True
                    )
            
            if to_type == "learned" and self.learned_filter_widgets:
                filter_state = self.learned_filter_widgets.get_filter_state()
                if filter_state.get('is_filtering', False):
                    self._apply_filter_to_container(
                        "learned",
                        filter_state.get('search_text', ''),
                        0,
                        True
                    )
            
            # ✅ YENİ: Duplicate checker cache'ini güncelle
            if self.duplicate_checker:
                QTimer.singleShot(100, lambda: self.duplicate_checker._update_cache_for_content(self))
            
            self.update()
            QApplication.processEvents()
    
    def _transfer_single_card(self, card_id: int, new_bucket: int, from_type: str, to_type: str) -> bool:
        try:
            # Kopya kart kontrolü
            has_copy_cards = False
            copy_cards_in_boxes = {}
            
            if self.db and card_id and new_bucket == 1:
                try:
                    cursor = self.db.conn.cursor()
                    cursor.execute("""
                        SELECT id, box FROM words 
                        WHERE original_card_id = ? AND is_copy = 1
                    """, (card_id,))
                    copy_rows = cursor.fetchall()
                    
                    if copy_rows:
                        has_copy_cards = True
                        for copy_id, box_id in copy_rows:
                            if box_id not in copy_cards_in_boxes:
                                copy_cards_in_boxes[box_id] = []
                            copy_cards_in_boxes[box_id].append(copy_id)
                except Exception:
                    has_copy_cards = False
            
            # Kopya kart uyarısı
            if has_copy_cards and new_bucket == 1:
                response = self._show_copy_card_warning(copy_cards_in_boxes)
                if not response:
                    return False
                
                self._delete_copy_cards_from_memory_boxes(copy_cards_in_boxes)
            
            # Widget'ı bul
            widget = None
            widget_index = -1
            
            for i, w in enumerate(self.card_widgets[from_type]):
                if getattr(w, 'card_id', None) == card_id:
                    widget = w
                    widget_index = i
                    break
            
            if not widget:
                return False
            
            # ============= YENİ: Kart öğrenildi container'ına taşındı =============
            if new_bucket == 1:
                # Kartın overlay'ini hemen kaldır
                if hasattr(widget, 'on_card_learned'):
                    widget.on_card_learned()
                    print(f"🎓 [TRANSFER] Kart öğrenildi, overlay kaldırıldı: {card_id}")
            # ======================================================================
            
            # Veriyi bul
            card_data = None
            data_index = -1
            
            for i, data in enumerate(self.cards_data[from_type]):
                if data.get('id') == card_id:
                    card_data = data.copy()
                    data_index = i
                    break
            
            if not card_data:
                return False
            
            # Veritabanını güncelle
            success = False
            if self.db:
                word_data = self.db.get_word_by_id(card_id)
                if word_data:
                    success = self.db.update_word(
                        word_id=card_id,
                        english=word_data.get('english', ''),
                        turkish=word_data.get('turkish', ''),
                        detail=word_data.get('detail', '{}'),
                        box_id=word_data.get('box_id', self.box_id),
                        bucket=new_bucket
                    )
            
            # Overlay observer
            if new_bucket == 1:
                try:
                    from ui.boxes_panel.overlay_observer import get_overlay_observer
                    observer = get_overlay_observer()
                    observer.notify_card_learned(card_id)
                except Exception:
                    pass
            
            # State'i güncelle
            if self.box_state:
                self._update_state_for_card(card_id, new_bucket)
            
            card_data['bucket'] = new_bucket
            
            # Listelerden çıkar
            if widget_index >= 0:
                self.card_widgets[from_type].pop(widget_index)
            elif widget in self.card_widgets[from_type]:
                self.card_widgets[from_type].remove(widget)
            
            if data_index >= 0:
                self.cards_data[from_type].pop(data_index)
            
            # Yeni listeye ekle
            self.card_widgets[to_type].append(widget)
            self.cards_data[to_type].append(card_data)
            
            # Bucket ID'sini güncelle
            if hasattr(widget, 'bucket_id'):
                widget.bucket_id = new_bucket
            
            # CardScrollLayout'lardan taşı
            from_layout = self.unknown_scroll_layout if from_type == "unknown" else self.learned_scroll_layout
            to_layout = self.unknown_scroll_layout if to_type == "unknown" else self.learned_scroll_layout
            
            if from_layout and to_layout:
                # Eski layout'tan çıkar
                from_layout.remove_card(widget)
                # Yeni layout'a ekle
                to_layout.add_card(widget)
            
            # Selection efektini kaldır
            if hasattr(widget, '_remove_selection_effect'):
                widget._remove_selection_effect()
            
            # ✅ YENİ: Duplicate checker cache'ini güncelle
            if self.duplicate_checker:
                QTimer.singleShot(100, lambda: self.duplicate_checker._update_cache_for_content(self))
            
            return True
            
        except Exception as e:
            print(f"❌ Kart transfer edilirken hata: {e}")
            return False

    def _delete_copy_cards_from_memory_boxes(self, copy_cards_in_boxes):
        try:
            if not self.db:
                return
            
            total_deleted = 0
            
            for box_id, card_ids in copy_cards_in_boxes.items():
                for card_id in card_ids:
                    try:
                        self.db.delete_word(card_id)
                        total_deleted += 1
                        self._remove_copy_card_from_ui(card_id)
                    except Exception:
                        continue
            
            # Memory box sayaçlarını güncelle
            for box_id in copy_cards_in_boxes.keys():
                self._update_memory_box_counter(box_id)
            
        except Exception as e:
            print(f"❌ Kopya kartları silerken hata: {e}")

    def _remove_copy_card_from_ui(self, card_id):
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            
            app = QApplication.instance()
            if not app:
                return
            
            # Bekleme alanlarında ara
            for widget in app.allWidgets():
                if hasattr(widget, '__class__') and 'WaitingAreaWidget' in widget.__class__.__name__:
                    if hasattr(widget, 'cards') and card_id in widget.cards:
                        if hasattr(widget, '_remove_card_by_id'):
                            widget._remove_card_by_id(card_id)
                        elif hasattr(widget, 'remove_card'):
                            widget.remove_card(card_id)
                        break
            
            # Aktif pencerelerdeki kopya kartları kaldır
            for window in app.topLevelWidgets():
                if hasattr(window, '__class__') and 'BoxesWindow' in window.__class__.__name__:
                    if hasattr(window, 'design'):
                        if hasattr(window.design, 'drawn_cards'):
                            for drawn_card in list(window.design.drawn_cards.keys()):
                                if hasattr(drawn_card, 'card_id') and drawn_card.card_id == card_id:
                                    window.design.remove_drawn_card(card_id)
                                    break
            
        except Exception as e:
            print(f"❌ UI'dan kopya kart kaldırılırken hata: {e}")

    def _update_memory_box_counter(self, box_id):
        try:
            from PyQt6.QtWidgets import QApplication
            from PyQt6.QtCore import QTimer
            
            app = QApplication.instance()
            if not app:
                return
            
            for widget in app.allWidgets():
                if hasattr(widget, '__class__') and 'MemoryBox' in widget.__class__.__name__:
                    if hasattr(widget, 'box_id') and widget.box_id == box_id:
                        if hasattr(widget, 'update_card_count'):
                            QTimer.singleShot(100, widget.update_card_count)
                        break
            
        except Exception as e:
            print(f"❌ Memory box sayacı güncellenirken hata: {e}")
    
    def _is_card_in_container(self, card_id: int, container_type: str) -> bool:
        for card_data in self.cards_data[container_type]:
            if card_data.get('id') == card_id:
                return True
        
        for widget in self.card_widgets[container_type]:
            if getattr(widget, 'card_id', None) == card_id:
                return True
        
        return False
    
    def _update_transfer_buttons(self, card_teleporter):
        if not card_teleporter:
            return
        
        unknown_selected = 0
        learned_selected = 0
        
        for card_id in list(card_teleporter.selected_cards):
            if self._is_card_in_container(card_id, "unknown"):
                unknown_selected += 1
            elif self._is_card_in_container(card_id, "learned"):
                learned_selected += 1
        
        if hasattr(self, 'transfer_to_learned_btn'):
            should_select = unknown_selected > 0
            self.transfer_to_learned_btn.set_selected(should_select)
            self.transfer_to_learned_btn.setEnabled(unknown_selected > 0)
        
        if hasattr(self, 'transfer_to_unknown_btn'):
            should_select = learned_selected > 0
            self.transfer_to_unknown_btn.set_selected(should_select)
            self.transfer_to_unknown_btn.setEnabled(learned_selected > 0)
    
    def _notify_all_containers_selection_changed(self):
        window = self.window()
        if not window:
            return
        
        for widget in window.findChildren(BoxDetailContent):
            if widget != self and hasattr(widget, '_update_transfer_buttons'):
                widget._update_transfer_buttons(self.card_teleporter)
    
    def selection_changed_externally(self):
        if not self.card_teleporter:
            self.card_teleporter = self._find_card_teleporter()
        
        if self.card_teleporter:
            self._update_transfer_buttons(self.card_teleporter)
    
    def _update_state_for_card(self, card_id, bucket):
        if not card_id or not self.box_state:
            return
        
        card_found = False
        for card in self.box_state.cards:
            if card.get("id") == card_id:
                card["bucket"] = bucket
                card_found = True
                break
        
        if not card_found:
            self.box_state.cards.append({
                "id": card_id,
                "bucket": bucket,
                "rect": None
            })
        
        self.box_state.mark_dirty()
        self.box_state.save()
    
    def _on_card_updated(self, card_widget):
        """Kart güncellendiğinde çağrılır - GÜNCELLENMİŞ VERSİYON"""
        print("=" * 80)
        print("🔄🔄🔄 _on_card_updated ÇAĞRILDI! 🔄🔄🔄")
        print(f"   - Gelen widget: {card_widget}")
        print(f"   - Widget type: {type(card_widget)}")
        print(f"   - Widget ID: {getattr(card_widget, 'card_id', 'N/A')}")
        
        if not self.db:
            print("❌ Database yok, işlem iptal")
            print("=" * 80)
            return
        
        # Kart ID'sini al
        card_id = getattr(card_widget, 'card_id', None)
        if not card_id:
            print("❌ Kart ID yok, işlem iptal")
            print("=" * 80)
            return
        
        print(f"📊 Kart ID bulundu: {card_id}")
        
        # Container'ı bul
        current_container_type = None
        for container_type in ["unknown", "learned"]:
            for i, card in enumerate(self.card_widgets[container_type]):
                if card == card_widget:
                    current_container_type = container_type
                    print(f"✅ Container bulundu: {container_type} (index: {i})")
                    break
            if current_container_type:
                break
        
        if not current_container_type:
            print("⚠️ Container bulunamadı, ID ile aranıyor...")
            for container_type in ["unknown", "learned"]:
                for i, card in enumerate(self.card_widgets[container_type]):
                    if hasattr(card, 'card_id') and card.card_id == card_id:
                        current_container_type = container_type
                        print(f"✅ Container ID ile bulundu: {container_type} (index: {i})")
                        break
                if current_container_type:
                    break
        
        if not current_container_type:
            print("❌❌❌ Container BULUNAMADI! İşlem iptal")
            print("=" * 80)
            return
        
        # Kart verilerini al - MÜMKÜN OLAN TÜM YOLLARLA
        english_text = ""
        turkish_text = ""
        detail_text = "{}"
        box_id = self.box_id
        
        print(f"🔍 Kart verileri alınıyor...")
        
        try:
            # 1. YOL: get_card_data() metodu
            if hasattr(card_widget, 'get_card_data'):
                print(f"   - get_card_data() metodu var, çağrılıyor...")
                card_data = card_widget.get_card_data()
                english_text = card_data.get('english', '')
                turkish_text = card_data.get('turkish', '')
                detail_text = card_data.get('detail', '{}')
                box_id = card_data.get('box_id', self.box_id)
                print(f"   - get_card_data() sonucu: EN='{english_text}', TR='{turkish_text}'")
        except Exception as e:
            print(f"   - get_card_data() hatası: {e}")
        
        # 2. YOL: Doğrudan widget özelliklerinden
        if not english_text and hasattr(card_widget, 'english_edit'):
            try:
                english_text = card_widget.english_edit.text().strip()
                print(f"   - english_edit.text(): '{english_text}'")
            except:
                pass
        
        if not english_text and hasattr(card_widget, 'english_label'):
            try:
                english_text = card_widget.english_label.text().strip()
                print(f"   - english_label.text(): '{english_text}'")
            except:
                pass
        
        if not turkish_text and hasattr(card_widget, 'turkish_edit'):
            try:
                turkish_text = card_widget.turkish_edit.text().strip()
                print(f"   - turkish_edit.text(): '{turkish_text}'")
            except:
                pass
        
        if not turkish_text and hasattr(card_widget, 'turkish_label'):
            try:
                turkish_text = card_widget.turkish_label.text().strip()
                print(f"   - turkish_label.text(): '{turkish_text}'")
            except:
                pass
        
        # 3. YOL: Cache'den al
        if (not english_text or not turkish_text):
            print(f"   - Widget'tan alınamadı, cache aranıyor...")
            for container in ["unknown", "learned"]:
                for card_data in self.cards_data[container]:
                    if card_data.get('id') == card_id:
                        if not english_text:
                            english_text = card_data.get('english', english_text)
                        if not turkish_text:
                            turkish_text = card_data.get('turkish', turkish_text)
                        if not detail_text or detail_text == "{}":
                            detail_text = card_data.get('detail', detail_text)
                        box_id = card_data.get('box_id', box_id)
                        print(f"   - Cache bulundu: EN='{english_text}', TR='{turkish_text}'")
                        break
        
        print(f"📊 SONUÇ KELİMELER: EN='{english_text}', TR='{turkish_text}'")
        
        # ✅ GLOBAL DUPLICATE KONTROLÜ - TÜM SİSTEMDE!
        if english_text.strip() and turkish_text.strip():
            print(f"🔍 DUPLICATE KONTROLÜ BAŞLIYOR:")
            print(f"   - Kontrol edilecek: '{english_text}' → '{turkish_text}'")
            print(f"   - Kart ID (exclude): {card_id}")
            print(f"   - Box ID: {box_id}")
            print(f"   - Duplicate checker mevcut: {self.duplicate_checker is not None}")
            print(f"   - 🔥 TÜM SİSTEMDE aranacak (check_only_same_box=False)")
            
            if self.duplicate_checker:
                duplicate_info = self.duplicate_checker.check_global_pair_duplicate(
                    front_text=english_text,
                    back_text=turkish_text,
                    exclude_card_id=card_id,  # ✅ KENDİ KARTINI HARİÇ TUT
                    current_box_id=box_id,
                    check_only_same_box=False  # ✅ BÜTÜN SİSTEMDE ARA!
                )
                
                print(f"🔍 DUPLICATE KONTROL SONUCU:")
                print(f"   - has_duplicate: {duplicate_info.get('has_duplicate', False)}")
                print(f"   - total_count: {duplicate_info.get('total_count', 0)}")
                print(f"   - locations: {len(duplicate_info.get('found_locations', []))} adet")
                print(f"   - check_only_same_box: {duplicate_info.get('check_only_same_box', False)}")
                
                # DEBUG: Bulunan duplicate'ları göster
                if duplicate_info.get('found_locations'):
                    print(f"📋 BULUNAN DUPLICATE'LAR:")
                    for i, loc in enumerate(duplicate_info['found_locations'], 1):
                        same_box_mark = "✅ AYNI BOX" if loc.get('same_box') else "🌍 FARKLI BOX"
                        print(f"   {i}. {same_box_mark} - Box {loc['box_id']} - {loc['container']} - ID: {loc['card_id']}")
                
                if duplicate_info.get('has_duplicate', False):
                    print(f"⚠️⚠️⚠️ DUPLICATE BULUNDU! Dialog gösteriliyor...")
                    should_continue = self._show_global_duplicate_warning(duplicate_info)
                    print(f"   - Kullanıcı seçimi: {'DEVAM' if should_continue else 'İPTAL'}")
                    if not should_continue:
                        print("❌ Kullanıcı iptal etti, kart GERİ ALINIYOR")
                        self._revert_card_to_previous_state(card_widget)
                        print("=" * 80)
                        return
                    else:
                        print("✅ Kullanıcı devam etmeyi seçti")
                else:
                    print("✅ Duplicate BULUNAMADI, devam ediliyor")
            else:
                print("❌ Duplicate checker mevcut değil, kontrol yapılamıyor")
        else:
            print("⚠️ Boş kelime, duplicate kontrol YAPILMIYOR")
        
        # Bucket'ı belirle
        bucket = 0 if current_container_type == "unknown" else 1
        print(f"📦 Bucket: {bucket} ({'Bilmediklerim' if bucket == 0 else 'Öğrendiklerim'})")
        
        # Veritabanını güncelle
        print(f"💾 Veritabanı güncelleniyor...")
        try:
            success = self.db.update_word(
                word_id=card_id,
                english=english_text,
                turkish=turkish_text,
                detail=detail_text,
                box_id=box_id,
                bucket=bucket
            )
            print(f"✅ Veritabanı güncelleme: {'BAŞARILI' if success else 'BAŞARISIZ'}")
            
            if not success:
                print("❌ Veritabanı güncelleme BAŞARISIZ, eski veriler kontrol ediliyor...")
                # Eski verileri al
                old_data = self.db.get_word_by_id(card_id)
                if old_data:
                    print(f"   - Eski veriler: EN='{old_data.get('english')}', TR='{old_data.get('turkish')}'")
        except Exception as e:
            print(f"❌❌❌ Veritabanı güncelleme HATASI: {e}")
            import traceback
            traceback.print_exc()
            success = False
        
        # Cache'i güncelle
        self._update_card_cache(card_id, english_text, turkish_text, detail_text, bucket, current_container_type)
        print(f"✅ Cache güncellendi")
        
        # State'i güncelle
        if self.box_state:
            self._update_state_for_card(card_id, bucket)
            print(f"✅ State güncellendi")
        
        # Box counter'ı güncelle
        self._refresh_box_counter()
        print(f"✅ Box counter güncellendi")
        
        # Duplicate checker cache'ini güncelle
        if self.duplicate_checker:
            QTimer.singleShot(100, lambda: self.duplicate_checker._update_cache_for_content(self))
            print(f"✅ Duplicate checker cache güncellenecek")
        
        # Filtreleri yeniden uygula
        if current_container_type == "unknown" and self.unknown_filter_widgets:
            filter_state = self.unknown_filter_widgets.get_filter_state()
            if filter_state.get('is_filtering', False):
                self._apply_filter_to_container(
                    "unknown",
                    filter_state.get('search_text', ''),
                    filter_state.get('color_id', 0),
                    True
                )
        elif current_container_type == "learned" and self.learned_filter_widgets:
            filter_state = self.learned_filter_widgets.get_filter_state()
            if filter_state.get('is_filtering', False):
                self._apply_filter_to_container(
                    "learned",
                    filter_state.get('search_text', ''),
                    0,
                    True
                )
        
        print(f"✅✅✅ Kart güncelleme TAMAMLANDI")
        print("=" * 80)

    def _revert_card_to_previous_state(self, card_widget):
        """Kartı önceki durumuna döndür (duplicate uyarısından sonra)"""
        try:
            if hasattr(card_widget, 'revert_to_previous_state'):
                card_widget.revert_to_previous_state()
            elif hasattr(card_widget, 'refresh_display'):
                card_widget.refresh_display()
        except Exception as e:
            print(f"❌ Kart geri alınırken hata: {e}")

    def _update_card_cache(self, card_id, english, turkish, detail, bucket, new_container_type):
        # Kart ID'si ile arama yap
        for container in ["unknown", "learned"]:
            for i, card_data in enumerate(self.cards_data[container]):
                if card_data.get('id') == card_id:
                    # Eğer container değiştiyse
                    if container != new_container_type:
                        self.cards_data[container].pop(i)
                        # Yeni container'a ekle
                        self.cards_data[new_container_type].append({
                            'id': card_id,
                            'english': english,
                            'turkish': turkish,
                            'detail': detail,
                            'box_id': self.box_id,
                            'bucket': bucket
                        })
                    else:
                        # Aynı container'da güncelle
                        card_data['english'] = english
                        card_data['turkish'] = turkish
                        card_data['detail'] = detail
                        card_data['bucket'] = bucket
                    return
        
        # Eğer cache'te bulunamadıysa yeni ekle
        self.cards_data[new_container_type].append({
            'id': card_id,
            'english': english,
            'turkish': turkish,
            'detail': detail,
            'box_id': self.box_id,
            'bucket': bucket
        })
    
    def add_new_card(self):
        if not self.db:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'db') and parent.db:
                    self.db = parent.db
                    break
                parent = parent.parent()
        
        if not self.box_id:
            parent = self.parent()
            while parent:
                if hasattr(parent, 'box_id') and parent.box_id:
                    self.box_id = parent.box_id
                    break
                parent = parent.parent()
        
        if not self.box_id:
            window = self.window()
            if window and hasattr(window, 'box_id'):
                self.box_id = window.box_id
        
        if not self.db:
            window = self.window()
            if window and hasattr(window, 'db'):
                self.db = window.db
        
        if not self.db or not self.box_id:
            return
        
        try:
            card_id = self.db.add_word(
                english="",
                turkish="",
                detail="{}",
                box_id=self.box_id,
                bucket=0
            )
            
            if not card_id:
                return
            
            card_data = {
                'id': card_id,
                'english': '',
                'turkish': '',
                'detail': '{}',
                'box_id': self.box_id,
                'bucket': 0
            }
            
            card = self.add_card_to_container("unknown", card_data, show_duplicate_warning=True)
            
            if card:
                card.card_id = card_id
                card.box_id = self.box_id
                card.is_newlyd_create = True
                self._refresh_box_counter()
                
        except Exception as e:
            print(f"❌ Yeni kart eklenirken hata: {e}")
    
    def _refresh_box_counter(self):
        if not self.db or not self.box_id:
            return
        
        window = self.window()
        if not window:
            return
        
        from PyQt6.QtCore import QTimer
        QTimer.singleShot(100, lambda: self._find_and_update_box_view(window))
    
    def _find_and_update_box_view(self, top_window):
        try:
            from ui.words_panel.box_widgets.box_view import BoxView
            
            box_views = []
            
            def find_box_views(widget):
                if isinstance(widget, BoxView) and not widget._deleted:
                    box_views.append(widget)
                
                for child in widget.children():
                    if isinstance(child, QWidget):
                        find_box_views(child)
            
            find_box_views(top_window)
            
            for box_view in box_views:
                if box_view.db_id == self.box_id:
                    QTimer.singleShot(0, box_view.refresh_card_counts)
                    break
        
        except Exception as e:
            print(f"❌ Box view bulunurken hata: {e}")
    
    def _on_card_teleported(self, card_id: int, new_box_id: int):
        if not card_id:
            return
        
        current_box_id = getattr(self, 'box_id', None)
        window_box_id = getattr(self.window(), 'box_id', None) if self.window() else None
        box_id = current_box_id or window_box_id
        
        if box_id and new_box_id != box_id:
            card_found = False
            
            for container_type in ["unknown", "learned"]:
                # Widget'larda ara
                for widget in self.card_widgets[container_type]:
                    if hasattr(widget, 'card_id') and widget.card_id == card_id:
                        card_found = True
                        break
                
                if card_found:
                    break
                
                # Cache'de ara
                for data in self.cards_data[container_type]:
                    if data.get('id') == card_id:
                        card_found = True
                        break
                
                if card_found:
                    break
            
            if card_found:
                self._remove_card_immediately(card_id)

    def _remove_card_immediately(self, card_id: int):
        if not card_id:
            return
        
        for container_type in ["unknown", "learned"]:
            # Widget'lardan kaldır
            widgets_to_remove = []
            for i, widget in enumerate(self.card_widgets[container_type]):
                if hasattr(widget, 'card_id') and widget.card_id == card_id:
                    widgets_to_remove.append(widget)
            
            for widget in widgets_to_remove:
                try:
                    if hasattr(widget, '_remove_selection_effect'):
                        widget._remove_selection_effect()
                    
                    # CardScrollLayout'tan kaldır
                    scroll_layout = self.unknown_scroll_layout if container_type == "unknown" else self.learned_scroll_layout
                    if scroll_layout:
                        scroll_layout.remove_card(widget)
                    
                    widget.hide()
                    widget.setParent(None)
                    
                    if widget in self.card_widgets[container_type]:
                        self.card_widgets[container_type].remove(widget)
                    
                    QTimer.singleShot(100, widget.deleteLater)
                except Exception as e:
                    print(f"❌ Widget kaldırılırken hata: {e}")
            
            # Cache'den kaldır
            self.cards_data[container_type] = [
                data for data in self.cards_data[container_type]
                if data.get('id') != card_id
            ]
        
        # State'den kaldır
        if self.box_state:
            self.box_state.remove_card(card_id)
            self.box_state.mark_dirty()
            self.box_state.save()
        
        # ✅ YENİ: Duplicate checker cache'ini güncelle
        if self.duplicate_checker:
            QTimer.singleShot(100, lambda: self.duplicate_checker._update_cache_for_content(self))
        
        # UI güncellemelerini zorla
        self.update()
        QApplication.processEvents()
    
    def _on_card_deleted(self, card_widget, container_type):
        card_id = getattr(card_widget, 'card_id', None)
        
        if card_widget not in self.card_widgets[container_type]:
            return
        
        if card_id:
            if self.db:
                try:
                    self.db.delete_word(int(card_id))
                except Exception:
                    pass
            
            if self.box_state:
                removed = self.box_state.remove_card(card_id)
                if removed:
                    self.box_state.mark_dirty()
                    self.box_state.save()
        
        try:
            self.card_widgets[container_type].remove(card_widget)
            
            self.cards_data[container_type] = [
                card for card in self.cards_data[container_type]
                if card and card.get('id') != card_id
            ]
            
            # CardScrollLayout'tan kaldır
            scroll_layout = self.unknown_scroll_layout if container_type == "unknown" else self.learned_scroll_layout
            if scroll_layout:
                scroll_layout.remove_card(card_widget)
            
            card_widget.hide()
            card_widget.setParent(None)
            card_widget.deleteLater()
            
        except Exception:
            pass
        
        self._refresh_box_counter()
        self.card_deleted.emit(card_widget)
        
        # ✅ YENİ: Duplicate checker cache'ini güncelle
        if self.duplicate_checker:
            QTimer.singleShot(100, lambda: self.duplicate_checker._update_cache_for_content(self))
        
        # Filtreleri yeniden uygula
        if container_type == "unknown" and self.unknown_filter_widgets:
            filter_state = self.unknown_filter_widgets.get_filter_state()
            if filter_state.get('is_filtering', False):
                self._apply_filter_to_container(
                    "unknown",
                    filter_state.get('search_text', ''),
                    filter_state.get('color_id', 0),
                    True
                )
        elif container_type == "learned" and self.learned_filter_widgets:
            filter_state = self.learned_filter_widgets.get_filter_state()
            if filter_state.get('is_filtering', False):
                self._apply_filter_to_container(
                    "learned",
                    filter_state.get('search_text', ''),
                    0,
                    True
                )
    
    def delete_card_from_detail(self, card_widget):
        for container_type in ["unknown", "learned"]:
            if card_widget in self.card_widgets[container_type]:
                self._on_card_deleted(card_widget, container_type)
                return
    
    def load_cards(self, db, box_id):
        self.db = db
        self.box_id = box_id
        
        # ✅ YENİ: Duplicate checker'a database'i set et
        if self.duplicate_checker and not self.duplicate_checker.db:
            self.duplicate_checker.set_database(db)
        
        if not self.db or not self.box_id:
            return
        
        try:
            try:
                from .internal.states.state_loader import BoxDetailStateLoader
                from .internal.states.box_state import BoxDetailState
                
                self.state_loader = BoxDetailStateLoader(db)
                
                box_info = db.get_box_info(box_id)
                if not box_info:
                    return
                
                box_title = box_info.get("title", f"Kutu {box_id}")
                ui_index = 1
                all_boxes = db.get_boxes()
                for idx, (b_id, title) in enumerate(all_boxes, 1):
                    if b_id == box_id:
                        ui_index = idx
                        break
                
                self.box_state = BoxDetailState(box_id, box_title, ui_index, db)
                
                loaded = self.state_loader._load_state(self.box_state)
                if not loaded:
                    self._populate_state_from_db()
                    self.box_state.mark_dirty()
                    self.box_state.save()
                
            except Exception:
                self.box_state = None
            
            # Eski kartları temizle
            for container_type in ["unknown", "learned"]:
                # CardScrollLayout'tan temizle
                scroll_layout = self.unknown_scroll_layout if container_type == "unknown" else self.learned_scroll_layout
                if scroll_layout:
                    scroll_layout.clear_all_cards()
                
                # Listeleri temizle
                for widget in self.card_widgets[container_type][:]:
                    try:
                        widget.hide()
                        widget.setParent(None)
                        widget.deleteLater()
                    except Exception:
                        pass
                
                self.card_widgets[container_type] = []
                self.cards_data[container_type] = []
            
            # State'den kartları yükle
            if self.box_state and self.box_state.cards:
                for card_data in self.box_state.cards:
                    card_id = card_data.get("id")
                    bucket = card_data.get("bucket", 0)
                    
                    if not card_id:
                        continue
                    
                    word_data = self.db.get_word_by_id(card_id)
                    if not word_data:
                        if self.box_state:
                            self.box_state.remove_card(card_id)
                        continue
                    
                    container_type = "unknown" if bucket == 0 else "learned"
                    
                    card_full_data = {
                        'id': card_id,
                        'english': word_data.get('english', ''),
                        'turkish': word_data.get('turkish', ''),
                        'detail': word_data.get('detail', '{}'),
                        'box_id': self.box_id,
                        'bucket': bucket
                    }
                    
                    card = self.add_card_to_container(container_type, card_full_data)
                    
                    if card:
                        card.card_id = card_id
                        card.box_id = self.box_id
                        card.bucket_id = bucket
            
            # Veritabanından kartları yükle
            rows = self.db.get_cards_by_box(self.box_id)
            
            for row in rows:
                card_id = row.get('id')
                bucket = row.get('bucket', 0)
                
                if not card_id:
                    continue
                
                # Zaten yüklü mü kontrol et
                card_already_loaded = False
                for container_type in ["unknown", "learned"]:
                    for card_widget in self.card_widgets[container_type]:
                        if hasattr(card_widget, 'card_id') and card_widget.card_id == card_id:
                            card_already_loaded = True
                            break
                    if card_already_loaded:
                        break
                
                if card_already_loaded:
                    continue
                
                # State'e ekle
                if self.box_state:
                    card_in_state = False
                    for card in self.box_state.cards:
                        if card.get("id") == card_id:
                            card_in_state = True
                            break
                    
                    if not card_in_state:
                        self.box_state.add_card(card_id, bucket)
                
                container_type = "unknown" if bucket == 0 else "learned"
                
                card_full_data = {
                    'id': card_id,
                    'english': row.get('english', ''),
                    'turkish': row.get('turkish', ''),
                    'detail': row.get('detail', '{}'),
                    'box_id': self.box_id,
                    'bucket': bucket
                }
                
                card = self.add_card_to_container(container_type, card_full_data)
                if card:
                    card.card_id = card_id
                    card.box_id = self.box_id
                    card.bucket_id = bucket
            
            # State'i kaydet
            if self.box_state:
                self.box_state.mark_dirty()
                self.box_state.save()
            
            # ✅ YENİ: Duplicate checker cache'ini güncelle
            if self.duplicate_checker:
                QTimer.singleShot(200, lambda: self.duplicate_checker._update_cache_for_content(self))
            
            # Timer'ları başlat
            QTimer.singleShot(250, self._connect_card_teleporter_signals)
            QTimer.singleShot(150, lambda: self._connect_to_card_teleporter())
                
        except Exception as e:
            print(f"❌ Kartlar yüklenirken hata: {e}")
    
    def _connect_to_card_teleporter(self):
        if not self.card_teleporter:
            self.card_teleporter = self._find_card_teleporter()
        
        if self.card_teleporter:
            try:
                if hasattr(self.card_teleporter, 'selection_changed'):
                    self.card_teleporter.selection_changed.connect(
                        lambda: self.selection_changed_externally()
                    )
            except Exception:
                pass
    
    def _populate_state_from_db(self):
        if not self.box_state or not self.db:
            return
        
        try:
            rows = self.db.get_cards_by_box(self.box_id)
            
            for row in rows:
                card_id = row.get('id')
                bucket = row.get('bucket', 0)
                
                if card_id:
                    self.box_state.add_card(card_id, bucket)
                    
        except Exception:
            pass
    
    def _try_connect_card_teleporter(self):
        if not self.card_teleporter:
            self._create_card_teleporter()
        
        if self.card_teleporter:
            self._connect_card_teleporter_signals()
    
    def _find_card_teleporter(self):
        if not self.card_teleporter:
            self._create_card_teleporter()
        return self.card_teleporter
    
    def _connect_card_teleporter_to_cards(self):
        if not self.card_teleporter:
            self._create_card_teleporter()
        
        if self.card_teleporter:
            for container_type in ["unknown", "learned"]:
                for card in self.card_widgets[container_type]:
                    if hasattr(card, 'teleporter'):
                        card.teleporter = self.card_teleporter
    
    def clear_filters(self):
        if self.unknown_filter_widgets:
            self.unknown_filter_widgets.clear_filters()
        if self.learned_filter_widgets:
            self.learned_filter_widgets.clear_filters()
    
    def closeEvent(self, event):
        self._unregister_from_duplicate_checker()
        super().closeEvent(event)