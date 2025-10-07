import sys
from PySide6.QtWidgets import (
    QApplication, QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout,
    QFileDialog, QFrame, QStackedWidget, QScrollArea, QGraphicsOpacityEffect,
    QGraphicsDropShadowEffect
)
from PySide6.QtGui import QPixmap, QIcon, QColor, QFont
from PySide6.QtCore import Qt, QPropertyAnimation, QEasingCurve
from service import Processor
from history_utils import save_history_entry, load_history

IMAGE_PROCESSOR = Processor()

# --- Стили ---
STYLES = {
    "font_family": "Segoe UI",
    "background": "#1e1e2f",
    "content_bg": "#27293d",
    "primary": "#7f5af0",
    "primary_hover": "#9d7bf5",
    "text": "#e0e0e0",
    "accent": "#2cb67d",
    "danger": "#e53e3e",
    "danger_hover": "#f56565",
    "card_bg": "#2d2d4d",
    "border": "#44475a",
    "shadow": "#101018",
}

# --- Вспомогательная функция для теней ---
def apply_shadow(widget, blur_radius=20, x_offset=0, y_offset=5, color=STYLES["shadow"]):
    shadow = QGraphicsDropShadowEffect()
    shadow.setBlurRadius(blur_radius)
    shadow.setXOffset(x_offset)
    shadow.setYOffset(y_offset)
    shadow.setColor(QColor(color))
    widget.setGraphicsEffect(shadow)


# ✅ Словарь для русских названий пунктов
COMPARISON_LABELS = {
    "energy_value": "Энергетическая ценность",
    "sodium": "Натрий",
    "total_sugar": "Общий сахар",
    "free_sugar": "Свободный сахар",
    "total_protein": "Белки",
    "total_fat": "Жиры",
    "fruit_content": "Содержание фруктов",
    "age_marking": "Возрастная маркировка",
    "high_sugar_front_packaging": "Высокий сахар на упаковке",
    "labeling": "Маркировка"
}


# ---------- Виджет для превью изображений ----------
class ImagePreview(QFrame):
    def __init__(self, file_path, remove_callback):
        super().__init__()
        self.file_path = file_path
        self.remove_callback = remove_callback

        self.setFixedSize(160, 170)
        self.setStyleSheet(f"""
            QFrame {{
                background-color: {STYLES['card_bg']};
                border-radius: 12px;
            }}
        """)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(8, 8, 8, 8)
        layout.setSpacing(8)

        self.image_label = QLabel()
        self.image_label.setFixedSize(144, 120)
        pixmap = QPixmap(file_path).scaled(self.image_label.size(), Qt.KeepAspectRatioByExpanding, Qt.SmoothTransformation)
        self.image_label.setPixmap(pixmap)
        self.image_label.setStyleSheet("border-radius: 8px;")
        layout.addWidget(self.image_label, alignment=Qt.AlignCenter)

        remove_btn = QPushButton("✖ Удалить")
        remove_btn.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLES['danger']};
                color: white;
                border: none;
                border-radius: 8px;
                padding: 6px;
                font-size: 13px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {STYLES['danger_hover']};
            }}
        """)
        remove_btn.setCursor(Qt.PointingHandCursor)
        remove_btn.clicked.connect(self.remove_image)
        layout.addWidget(remove_btn)
        
        apply_shadow(self, blur_radius=15, y_offset=4)

    def remove_image(self):
        self.remove_callback(self.file_path)


# ---------- Виджет загрузки изображений ----------
class ImageUploadWidget(QFrame):
    def __init__(self):
        super().__init__()
        self.setAcceptDrops(True)
        self.images = []

        self.setStyleSheet(f"""
            QFrame {{
                border: 2px dashed {STYLES['border']};
                border-radius: 15px;
                background-color: {STYLES['content_bg']};
            }}
        """)
        self.layout = QHBoxLayout(self)
        self.layout.setSpacing(15)
        self.layout.setContentsMargins(15, 15, 15, 15)

        self.placeholder = QLabel("📷 Перетащите сюда до 3-х изображений")
        self.placeholder.setAlignment(Qt.AlignCenter)
        self.placeholder.setStyleSheet(f"color: {STYLES['text']}; font-size: 16px; border: none;")
        self.layout.addWidget(self.placeholder)
    
    def clear_images(self):
        for img_path, preview_widget in self.images:
            preview_widget.deleteLater()
        self.images.clear()
        self.layout.addWidget(self.placeholder)
        self.placeholder.show()

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.acceptProposedAction()

    def dropEvent(self, event):
        for url in event.mimeData().urls():
            if len(self.images) < 3:
                file_path = url.toLocalFile()
                if file_path.lower().endswith(('.png', '.jpg', '.jpeg')):
                    self.add_image(file_path)

    def add_image(self, file_path):
        if len(self.images) >= 3:
            return
        if self.placeholder in [self.layout.itemAt(i).widget() for i in range(self.layout.count())]:
            self.layout.removeWidget(self.placeholder)
            self.placeholder.hide()

        preview = ImagePreview(file_path, self.remove_image)
        self.layout.addWidget(preview)
        self.images.append((file_path, preview))

    def remove_image(self, file_path):
        for img in self.images:
            if img[0] == file_path:
                widget = img[1]
                self.layout.removeWidget(widget)
                widget.deleteLater()
                self.images.remove(img)
                break
        if not self.images:
            self.layout.addWidget(self.placeholder)
            self.placeholder.show()


# ---------- Основное окно ----------
class MainWindow(QWidget):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Честный Знак")
        self.setGeometry(100, 100, 1200, 700)
        self.setStyleSheet(f"""
            background-color: {STYLES['background']};
            color: {STYLES['text']};
            font-family: '{STYLES['font_family']}';
            font-size: 14px;
        """)
        self.setWindowIcon(QIcon("./data/favicon.ico"))

        self.stack = QStackedWidget()
        main_screen = self.create_main_screen()
        self.history_screen = self.create_history_screen()

        self.stack.addWidget(main_screen)
        self.stack.addWidget(self.history_screen)

        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.addWidget(self.stack)
        self.setLayout(layout)

    def create_main_screen(self):
        main_widget = QWidget()
        main_layout = QVBoxLayout(main_widget)
        main_layout.setContentsMargins(20, 15, 20, 20)
        main_layout.setSpacing(20)
        
        header_layout = QHBoxLayout()
        content_layout = QHBoxLayout()
        content_layout.setSpacing(20)

        header_title = QLabel("Честный Знак")
        header_title.setStyleSheet("font-size: 28px; font-weight: bold;")
        header_layout.addWidget(header_title)
        header_layout.addStretch()

        history_button = QPushButton("📜 История")
        history_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLES['content_bg']};
                border: 1px solid {STYLES['border']};
                padding: 10px 20px;
                border-radius: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {STYLES['border']};
            }}
        """)
        history_button.setCursor(Qt.PointingHandCursor)
        history_button.clicked.connect(self.show_history)
        header_layout.addWidget(history_button)

        # --- Левая панель ---
        left_frame = QFrame()
        left_frame.setStyleSheet(f"background-color: {STYLES['content_bg']}; border-radius: 15px;")
        upload_container = QVBoxLayout(left_frame)
        upload_container.setContentsMargins(20, 20, 20, 20)
        upload_container.setSpacing(15)

        self.upload_widget = ImageUploadWidget()
        upload_container.addWidget(self.upload_widget)

        self.upload_button = QPushButton("📂 Выбрать файлы")
        self.upload_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLES['card_bg']};
                border: 1px solid {STYLES['border']};
                border-radius: 12px;
                padding: 12px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {STYLES['border']};
            }}
        """)
        self.upload_button.setCursor(Qt.PointingHandCursor)
        self.upload_button.clicked.connect(self.open_file_dialog)
        upload_container.addWidget(self.upload_button)

        self.analyze_button = QPushButton("🚀 Проанализировать")
        self.analyze_button.setStyleSheet(f"""
            QPushButton {{
                background-color: {STYLES['primary']};
                color: white;
                border-radius: 12px;
                padding: 14px;
                font-size: 16px;
                font-weight: bold;
            }}
            QPushButton:hover {{
                background-color: {STYLES['primary_hover']};
            }}
        """)
        self.analyze_button.setCursor(Qt.PointingHandCursor)
        self.analyze_button.clicked.connect(self.analyze_images)
        upload_container.addWidget(self.analyze_button)
        apply_shadow(self.analyze_button, blur_radius=25, color=STYLES['primary'])

        # --- Правая панель ---
        right_frame = QFrame()
        right_frame.setStyleSheet(f"background-color: {STYLES['content_bg']}; border-radius: 15px;")
        right_layout = QVBoxLayout(right_frame)
        right_layout.setContentsMargins(5, 5, 5, 5)

        self.analysis_scroll = QScrollArea()
        self.analysis_scroll.setWidgetResizable(True)
        self.analysis_scroll.setStyleSheet("border: none; background-color: transparent;")

        self.analysis_container = QWidget()
        self.analysis_container.setStyleSheet("background-color: transparent;")
        self.analysis_layout = QVBoxLayout(self.analysis_container)
        self.analysis_layout.setAlignment(Qt.AlignTop)
        self.analysis_layout.setContentsMargins(15, 15, 15, 15)
        self.analysis_layout.setSpacing(15)

        self.analysis_title = QLabel("Информация о продукте")
        self.analysis_title.setStyleSheet(f"font-size: 22px; font-weight: bold; color: {STYLES['accent']};")
        self.analysis_title.setAlignment(Qt.AlignCenter)
        self.analysis_layout.addWidget(self.analysis_title)

        self.placeholder_frame = self.create_analysis_placeholder()
        self.analysis_layout.addWidget(self.placeholder_frame)

        self.analysis_scroll.setWidget(self.analysis_container)
        right_layout.addWidget(self.analysis_scroll)

        content_layout.addWidget(left_frame, 1)
        content_layout.addWidget(right_frame, 2) # Правая панель шире

        main_layout.addLayout(header_layout)
        main_layout.addLayout(content_layout)
        return main_widget

    def create_analysis_placeholder(self):
        placeholder_frame = QFrame()
        placeholder_layout = QVBoxLayout(placeholder_frame)
        placeholder_layout.setAlignment(Qt.AlignCenter)
        placeholder_layout.setSpacing(15)

        placeholder_image = QLabel("🤖")
        placeholder_image.setFont(QFont(STYLES['font_family'], 60))
        placeholder_image.setAlignment(Qt.AlignCenter)

        placeholder_text = QLabel("Здесь появится информация о продукте\nпосле анализа изображений")
        placeholder_text.setStyleSheet(f"color: {STYLES['text']}; font-size: 16px;")
        placeholder_text.setAlignment(Qt.AlignCenter)
        placeholder_text.setWordWrap(True)

        placeholder_layout.addWidget(placeholder_image)
        placeholder_layout.addWidget(placeholder_text)
        return placeholder_frame


    def analyze_images(self):
        image_paths = [img[0] for img in self.upload_widget.images]
        if not image_paths:
            return
        
        self.upload_widget.clear_images()
        
        for i in reversed(range(self.analysis_layout.count())):
            widget = self.analysis_layout.itemAt(i).widget()
            if widget:
                # Скрываем, а затем удаляем, чтобы избежать мерцания
                widget.hide()
                widget.deleteLater()
        
        # Восстанавливаем заголовок
        self.analysis_layout.addWidget(self.analysis_title)
        self.analysis_title.show()

        IMAGE_PROCESSOR.initialize_images(image_paths)
        analysis_data = IMAGE_PROCESSOR.turn_to_llm()

        # save to persistent history
        try:
            saved = save_history_entry(analysis_data, image_paths)
            print('Saved history entry', saved.get('id'))
        except Exception as e:
            print('Failed to save history:', e)

        self.render_analysis(analysis_data)
    
    def render_analysis(self, data):
        # 1. Основная информация
        main_card = self.create_card("Основная информация", [
            f"Название: {data['name'] if data['name'] != 'N/A' else 'Информация не найдена'}",
            f"Категория: {data['category'] if data['category'] != 'N/A' else 'Информация не найдена'}",
        ])
        self.analysis_layout.addWidget(main_card)

        # ✅ 2. Новый блок: Сравнение с требованиями ВОЗ
        comparison_data = data.get("comparison", {})
        if comparison_data:
            comp_frame = QFrame()
            comp_frame.setStyleSheet(f"background-color: {STYLES['card_bg']}; border-radius: 12px; padding: 10px;")
            comp_layout = QVBoxLayout(comp_frame)
            comp_title = QLabel("Сравнение с требованиями ВОЗ")
            comp_title.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {STYLES['accent']}; margin-bottom: 8px;")
            comp_layout.addWidget(comp_title)

            for key, value in comparison_data.items():
                title = COMPARISON_LABELS.get(key, key)
                comp_layout.addWidget(self.create_comparison_block(title, value))
            
            self.analysis_layout.addWidget(comp_frame)
            apply_shadow(comp_frame)

        # 3. Характеристики
        characteristics = data.get("characteristics", {})
        char_items = [
            f"Энергетическая ценность: {self.check_value(characteristics.get('energy_value'))}",
            f"Натрий: {self.check_value(characteristics.get('sodium'))}",
            f"Общий сахар: {self.check_value(characteristics.get('total_sugar'))}",
            f"Свободный сахар: {self.check_value(characteristics.get('free_sugar'))}",
            f"Белки: {self.check_value(characteristics.get('total_protein'))}",
            f"Жиры: {self.check_value(characteristics.get('total_fat'))}",
            f"Содержание фруктов: {self.check_value(characteristics.get('fruit_content'))}",
            f"Возрастная маркировка: {self.check_value(characteristics.get('age_marking'))}",
            f"Высокий сахар на упаковке: {self.check_value(characteristics.get('high_sugar_front_packaging'))}",
            f"Маркировка: {self.check_value(characteristics.get('labeling'))}",
        ]
        self.analysis_layout.addWidget(self.create_card("Характеристики", char_items))

        # 4. Дополнительно
        additional = data.get("additional_info", {})
        add_items = [
            f"Состав: {self.check_value(additional.get('containings'))}",
            f"Описание: {self.check_value(additional.get('description'))}",
            f"Адрес производителя: {self.check_value(additional.get('manufactuer_address'))}",
            f"Условия хранения: {self.check_value(additional.get('storing_conditions'))}",
        ]
        self.analysis_layout.addWidget(self.create_card("Дополнительно", add_items))

    def create_comparison_block(self, title, value):
        if value == "true" or value is True:
            color = STYLES['accent']
            icon = "✅"
        elif value == "false" or value is False:
            color = STYLES['danger']
            icon = "❌"
        else:
            color = STYLES['border']
            icon = "⚪"

        block = QFrame()
        block.setStyleSheet(f"""
            QFrame {{
                background-color: {color};
                border-radius: 10px;
                padding: 10px;
                margin-bottom: 6px;
            }}
            QLabel {{
                color: white;
                font-size: 14px;
                font-weight: bold;
                background-color: transparent;
            }}
        """)
        layout = QHBoxLayout(block)
        lbl = QLabel(f"{icon}  {title}")
        layout.addWidget(lbl)
        layout.setContentsMargins(10, 6, 10, 6)
        return block

    def check_value(self, value):
        return value if value != "N/A" else "Информация не найдена"
    
    def create_card(self, title, items):
        card = QFrame()
        card.setStyleSheet(f"""
            QFrame {{
                background-color: {STYLES['card_bg']};
                border-radius: 12px;
                padding: 15px;
            }}
            QLabel {{
                color: {STYLES['text']};
                font-size: 14px;
                padding: 3px;
                background-color: transparent;
            }}
        """)
        layout = QVBoxLayout(card)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(5)

        title_label = QLabel(title)
        title_label.setWordWrap(True)
        title_label.setStyleSheet(f"font-size: 18px; font-weight: bold; color: {STYLES['accent']};")
        layout.addWidget(title_label)

        for item in items:
            lbl = QLabel(item)
            lbl.setWordWrap(True)
            layout.addWidget(lbl)

        apply_shadow(card)
        return card

    def create_history_screen(self):
        widget = QWidget()
        layout = QVBoxLayout(widget)
        layout.setContentsMargins(20, 15, 20, 20)
        layout.setSpacing(15)

        back_btn = QPushButton("← Назад")
        back_btn.clicked.connect(self.show_main)
        back_btn.setStyleSheet(f"""
             QPushButton {{
                background-color: {STYLES['content_bg']};
                border: 1px solid {STYLES['border']};
                padding: 10px 20px;
                border-radius: 12px;
                font-weight: bold;
                max-width: 120px;
            }}
            QPushButton:hover {{
                background-color: {STYLES['border']};
            }}
        """)
        back_btn.setCursor(Qt.PointingHandCursor)
        layout.addWidget(back_btn, alignment=Qt.AlignLeft)

        title = QLabel("История анализов")
        title.setStyleSheet(f"font-size: 24px; font-weight: bold; color: {STYLES['text']};")
        layout.addWidget(title, alignment=Qt.AlignCenter)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setStyleSheet("border: none; background-color: transparent;")
        
        scroll_content = QWidget()
        scroll_layout = QVBoxLayout(scroll_content)
        scroll_layout.setSpacing(15)
        scroll_layout.setAlignment(Qt.AlignTop)

        # Load real history
        entries = load_history()
        if not entries:
            empty = QLabel("Тут пока нет сохранённых анализов")
            empty.setStyleSheet(f"color: {STYLES['text']}; font-size: 16px;")
            scroll_layout.addWidget(empty)
        else:
            for entry in entries:
                card = QFrame()
                card.setStyleSheet(f"background-color: {STYLES['card_bg']}; border-radius: 15px; padding: 12px;")
                hdr = QLabel(f"{entry.get('name','N/A')} — {entry.get('category','N/A')}")
                hdr.setStyleSheet(f"font-size: 16px; color: {STYLES['text']}; font-weight: bold;")

                ts = QLabel(f"{entry.get('timestamp')}")
                ts.setStyleSheet(f"font-size: 12px; color: {STYLES['text']}; opacity: 0.8;")

                images_layout = QHBoxLayout()
                for img_rel in entry.get('images', []):
                    img_path = img_rel
                    thumb = QLabel()
                    try:
                        pix = QPixmap(img_path).scaled(100, 80, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                        thumb.setPixmap(pix)
                    except Exception:
                        thumb.setText('📷')
                    images_layout.addWidget(thumb)

                # delete button
                del_btn = QPushButton('Удалить')
                del_btn.setStyleSheet(f"background-color: {STYLES['danger']}; color: white; border-radius: 8px; padding: 6px;")
                del_btn.setCursor(Qt.PointingHandCursor)
                # closure capture
                def make_handler(eid):
                    def handler():
                        from history_utils import delete_history_entry
                        from PySide6.QtWidgets import QMessageBox
                        mb = QMessageBox()
                        mb.setIcon(QMessageBox.Warning)
                        mb.setWindowTitle('Подтвердите')
                        mb.setText('Удалить запись истории?')
                        mb.setStandardButtons(QMessageBox.Yes | QMessageBox.No)
                        res = mb.exec()
                        if res == QMessageBox.Yes:
                            ok = delete_history_entry(eid)
                            if ok:
                                # refresh history screen
                                try:
                                    new_history = self.create_history_screen()
                                    idx = self.stack.indexOf(self.history_screen)
                                    if idx != -1:
                                        self.stack.removeWidget(self.history_screen)
                                    self.history_screen = new_history
                                    self.stack.addWidget(self.history_screen)
                                    self.animate_transition(self.history_screen)
                                except Exception as ex:
                                    print('Failed to refresh history after delete:', ex)
                    return handler

                del_btn.clicked.connect(make_handler(entry.get('id')))

                card_layout = QVBoxLayout(card)
                top_row = QHBoxLayout()
                top_row.addWidget(hdr)
                top_row.addStretch()
                top_row.addWidget(del_btn)

                card_layout.addLayout(top_row)
                card_layout.addWidget(ts)
                card_layout.addLayout(images_layout)
                apply_shadow(card)
                scroll_layout.addWidget(card)

        scroll.setWidget(scroll_content)
        layout.addWidget(scroll)
        return widget

    def open_file_dialog(self):
        files, _ = QFileDialog.getOpenFileNames(self, "Выберите изображения", "", "Images (*.png *.jpg *.jpeg)")
        for file in files:
            self.upload_widget.add_image(file)

    def show_history(self):
        # Recreate history screen to reflect latest saved entries
        try:
            new_history = self.create_history_screen()
            # replace widget in stack
            idx = self.stack.indexOf(self.history_screen)
            if idx != -1:
                self.stack.removeWidget(self.history_screen)
            self.history_screen = new_history
            self.stack.addWidget(self.history_screen)
            self.animate_transition(self.history_screen)
        except Exception as e:
            print('Failed to open history:', e)

    def show_main(self):
        self.animate_transition(self.stack.widget(0))

    def animate_transition(self, widget):
        self.stack.setCurrentWidget(widget)
        # use QGraphicsOpacityEffect (QGraphicsEffect is abstract and cannot be instantiated)
        opacity_effect = QGraphicsOpacityEffect()
        opacity_effect.setOpacity(0.0)
        widget.setGraphicsEffect(opacity_effect)

        anim = QPropertyAnimation(opacity_effect, b"opacity")
        anim.setDuration(300)
        anim.setStartValue(0.0)
        anim.setEndValue(1.0)
        anim.setEasingCurve(QEasingCurve.InOutCubic)
        # keep reference to animation so it isn't GC'd
        widget._opacity_anim = anim
        anim.start()


if __name__ == '__main__':
    app = QApplication([])
    app.setFont(QFont(STYLES["font_family"], 9))
    window = MainWindow()
    window.show()
    sys.exit(app.exec())
