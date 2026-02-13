from qgis.PyQt import QtWidgets, QtGui

def apply_adaptive_palette(widget):
    """ Dostosowuje kolory tekstu w przyciskach. """
    # Pobieranie koloru tekstu bezpośrednio z palety
    bright_color = widget.palette().color(widget.foregroundRole())

    if bright_color.lightness() > 150:
        # Znalezienie wszystkich przycisków
        for btn in (b for b in widget.findChildren(QtWidgets.QPushButton)):
            btn_pal = btn.palette()

            # Stan aktywny i nieaktywny
            btn_pal.setColor(QtGui.QPalette.Active, QtGui.QPalette.ButtonText, bright_color)
            btn_pal.setColor(QtGui.QPalette.Inactive, QtGui.QPalette.ButtonText, bright_color)

            # Stan wyłączony (przyciemniony tekst)
            btn_pal.setColor(QtGui.QPalette.Disabled, QtGui.QPalette.ButtonText, bright_color.darker(180))

            btn.setPalette(btn_pal)