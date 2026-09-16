from PySide6.QtCore import Qt
from PySide6.QtWidgets import QApplication, QWidget, QVBoxLayout
from PySide6.QtTest import QTest
from tecnomata_iptv.widgets import CategoryComboBox, CHOSEN_ROLE
from tecnomata_iptv.app import Window


def test_category_overlay_is_bounded_scrollable_and_closable():
    app = QApplication.instance() or QApplication([])
    host = QWidget()
    layout = QVBoxLayout(host)
    combo = CategoryComboBox()
    layout.addWidget(combo)
    layout.addStretch()
    for i in range(200):
        combo.addItem(f"Categoría {i} " + "muy larga " * 30, i)
    host.resize(520, 420)
    host.show()
    app.processEvents()
    combo.showPopup()
    app.processEvents()
    assert host.rect().contains(combo.popup.geometry())
    assert combo.popup.width() == combo.width()
    assert combo.popup_list.verticalScrollBar().maximum() > 0
    combo.popup_list.scrollToBottom()
    assert combo.popup_list.verticalScrollBar().value() > 0
    combo.choose(combo.model().index(199, 0))
    assert combo.currentData() == 199
    assert not combo.popup.isVisible()
    combo.showPopup()
    QTest.keyClick(combo.popup_list, Qt.Key.Key_Escape)
    assert not combo.popup.isVisible()
    combo.showPopup()
    QTest.mouseClick(combo.close_button, Qt.MouseButton.LeftButton)
    assert not combo.popup.isVisible()
    combo.showPopup()
    QTest.mouseClick(host, Qt.MouseButton.LeftButton, pos=host.rect().bottomRight())
    assert not combo.popup.isVisible()
    host.close()
    host.deleteLater()


def test_content_identity_survives_search_tabs_and_series_navigation():
    app = QApplication.instance() or QApplication([])
    window = Window(demo=True, restore=False)
    window.choose_content(window.rows[1])
    window.items.setCurrentRow(0)  # Browsing another row does not change chosen content.
    assert window.items.item(1).data(CHOSEN_ROLE)
    assert not window.items.item(0).data(CHOSEN_ROLE)
    window.search.setText("A")
    window.search.clear()
    assert window.items.item(1).data(CHOSEN_ROLE)
    window.section("vod")
    assert not window.items.item(0).data(CHOSEN_ROLE)
    window.section("live")
    assert window.items.item(1).data(CHOSEN_ROLE)
    window.section("series")
    window.activate(window.items.item(0))
    assert window.in_episodes
    window.choose_content(window.rows[0])
    assert window.items.item(0).data(CHOSEN_ROLE)
    window.section("series")
    assert window.items.item(0).data(CHOSEN_ROLE)
    window.activate(window.items.item(0))
    assert window.items.item(0).data(CHOSEN_ROLE)
    window.close()
    window.deleteLater()
