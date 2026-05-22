from qgis.PyQt import QtWidgets, QtGui

def apply_adaptive_palette(widget):
    """ Dostosowuje kolory tekstu w przyciskach. """
    # Pobieranie koloru tekstu bezpośrednio z palety
    bright_color = widget.palette().color(widget.foregroundRole())

    if bright_color.lightness() > 150:
        # Znalezienie wszystkich przycisków
        for btn in widget.findChildren(QtWidgets.QAbstractButton):
            btn_pal = btn.palette()

            # Stan aktywny i nieaktywny
            btn_pal.setColor(QtGui.QPalette.ColorGroup.Active, QtGui.QPalette.ColorRole.ButtonText, bright_color)
            btn_pal.setColor(QtGui.QPalette.ColorGroup.Inactive, QtGui.QPalette.ColorRole.ButtonText, bright_color)

            # Stan wyłączony (przyciemniony tekst)
            btn_pal.setColor(QtGui.QPalette.ColorGroup.Disabled, QtGui.QPalette.ColorRole.ButtonText, bright_color.darker(180))

            btn.setPalette(btn_pal)

            if btn.property("icon_path"):
                btn.setIcon(QtGui.QIcon(btn.property("icon_path").replace(".svg", "_white.svg")))