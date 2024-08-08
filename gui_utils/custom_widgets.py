from PyQt6.QtWidgets import QGraphicsScene, QApplication, QPushButton, QLineEdit, QVBoxLayout, QFormLayout, QDialog, QGridLayout, QDialogButtonBox, QTableWidget, QHeaderView, QMenu, QAbstractItemView, QSizePolicy, QStyle, QStyleOptionSlider, QSlider
from PyQt6.QtGui import QIntValidator, QAction, QCursor, QPen, QBrush, QPainter, QPalette
from PyQt6.QtCore import Qt, QRect, QPoint, pyqtSignal

from gui_utils.drawing_utils import *
from gui_utils.image_utils import reset_mask_stack


class CTGraphicsScene(QGraphicsScene):
    def __init__(self, imageType, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.imageType = imageType
        self.drawing = False
        self.adjusting = False
        self.maskShown = True
        self.mask = reset_mask_stack(self.parent.currentMaskStack)
        self.drawingSize = 7
        self.drawingHigh = 4
        self.drawingLow = 3
        self.drawingShape = seven_circle
        self.drawnMaskType = None
        self.currentMaskIndex = 0
        self.adjustX = None
        self.adjustY = None

    def createMask(self, maskType):
        self.mask[maskType] = np.zeros(self.parent.currentDICOMStack.shape)

    def keyPressEvent(self, event):
        if not self.drawing:
            if event.key() == Qt.Key.Key_Q:
                if self.imageType == "axial":
                    self.parent.axialSlider.setValue(self.parent.axialSlider.value() - 1)
                elif self.imageType == "coronal":
                    self.parent.coronalSlider.setValue(self.parent.coronalSlider.value() - 1)
                elif self.imageType == "sagittal":
                    self.parent.sagittalSlider.setValue(self.parent.sagittalSlider.value() - 1)
            elif event.key() == Qt.Key.Key_W:
                if self.imageType == "axial":
                    self.parent.axialSlider.setValue(self.parent.axialSlider.value() + 1)
                elif self.imageType == "coronal":
                    self.parent.coronalSlider.setValue(self.parent.coronalSlider.value() + 1)
                elif self.imageType == "sagittal":
                    self.parent.sagittalSlider.setValue(self.parent.sagittalSlider.value() + 1)
            elif event.key() == Qt.Key.Key_Plus:
                self.zoomIn()
            elif event.key() == Qt.Key.Key_Minus:
                self.zoomOut()
            elif event.key() == Qt.Key.Key_Left:
                if event.isAutoRepeat():
                    return
                if len(self.parent.annotableFolders) != 0 and self.parent.annotableIndex != 0:
                    self.parent.annotableIndex -= 1
                    self.parent.changeAnnotable()
            elif event.key() == Qt.Key.Key_Right:
                if event.isAutoRepeat():
                    return
                if len(self.parent.annotableFolders) != 0 and (self.parent.annotableIndex != len(self.parent.annotableFolders) - 1):
                    self.parent.annotableIndex += 1
                    self.parent.changeAnnotable()

    def mousePressEvent(self, event):
        if self.parent.currentDICOMStack is not None:
            if event.button() == Qt.MouseButton.LeftButton:
                x = int(event.scenePos().x())
                y = int(event.scenePos().y())
                if (self.parent.clickType["Drawing"] or self.parent.clickType["Erasing"]) and self.imageType == "axial" and self.drawnMaskType is not None and self.maskShown and self.parent.currentMaskStack[self.drawnMaskType] is not None and self.parent.showMasks and self.imageType == "axial" and self.mask[self.drawnMaskType] is not None and x >= 0 and y >= 0 and x < self.parent.currentDICOMStack.shape[2] and y < self.parent.currentDICOMStack.shape[1] and not self.adjusting:
                    self.drawing = True
                    self.currentMaskIndex = self.parent.axialDICOMIndex
                    try:
                        self.mask[self.drawnMaskType][self.currentMaskIndex, y - self.drawingLow:y + self.drawingHigh, x - self.drawingLow:x + self.drawingHigh] = self.drawingShape
                    except ValueError:
                        pass
                    self.parent.drawMask()
                elif self.parent.clickType["Selecting"]:
                    if x < 0 or y < 0:
                        x = 0
                        y = 0
                    if self.imageType == "axial":
                        self.parent.coronalDICOMIndex = y
                        self.parent.sagittalDICOMIndex = x
                        self.parent.coronalSlider.setValue(y)
                        self.parent.sagittalSlider.setValue(x)
                        self.parent.updateImages()
                    elif self.imageType == "coronal":
                        self.parent.axialDICOMIndex = y
                        self.parent.sagittalDICOMIndex = x
                        self.parent.axialSlider.setValue(y)
                        self.parent.sagittalSlider.setValue(x)
                        self.parent.updateImages()
                    elif self.imageType == "sagittal":
                        self.parent.axialDICOMIndex = y
                        self.parent.coronalDICOMIndex = x
                        self.parent.axialSlider.setValue(y)
                        self.parent.coronalSlider.setValue(x)
                        self.parent.updateImages()
            elif event.button() == Qt.MouseButton.RightButton and self.imageType == "axial" and not self.drawing:
                self.adjustX = int(event.scenePos().x())
                self.adjustY = int(event.scenePos().y())
                self.adjusting = True

    def wheelEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if not self.drawing and not self.adjusting and bool(modifiers == Qt.KeyboardModifier.ControlModifier):
            if event.delta() > 0:
                self.zoomIn()
            elif event.delta() < 0:
                self.zoomOut()

    def mouseMoveEvent(self, event):
        x = int(event.scenePos().x())
        y = int(event.scenePos().y())
        if self.parent.currentDICOMStack is not None:
            if self.drawing and x >= 0 and y >= 0 and x < self.parent.currentDICOMStack.shape[2] and y < self.parent.currentDICOMStack.shape[1]:
                try:
                    self.mask[self.drawnMaskType][self.currentMaskIndex, y - self.drawingLow:y + self.drawingHigh, x - self.drawingLow:x + self.drawingHigh] = self.drawingShape
                except ValueError:
                    pass
                self.parent.drawMask()
            elif self.adjusting and x >= 0 and y >= 0 and x < self.parent.currentDICOMStack.shape[2] and y < self.parent.currentDICOMStack.shape[1] and self.adjustX is not None and self.adjustY is not None:
                xChange = x - self.adjustX
                yChange = self.adjustY - y
                if -65535 < self.parent.brightness < 65535:
                    self.parent.brightness += xChange * 1
                if self.parent.contrast > 0 or (self.parent.contrast <= 0 < yChange):
                    self.parent.contrast += yChange * 0.0001

    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.drawing = False
            if self.parent.fillContours and self.parent.clickType["Drawing"]:
                self.parent.fillContoursFunc()
            self.parent.updateImages()
        if self.adjusting:
            self.adjusting = False
            self.parent.updateImages()

    def zoomIn(self):
        if self.parent.imageScale == 1.0:
            self.parent.imageScale = 1.5
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[1].setChecked(True)
            self.parent.updateImages()
        elif self.parent.imageScale == 1.5:
            self.parent.imageScale = 2.0
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[2].setChecked(True)
            self.parent.updateImages()
        elif self.parent.imageScale == 2.0:
            self.parent.imageScale = 4.0
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[3].setChecked(True)
            self.parent.updateImages()
        elif self.parent.imageScale == 4.0:
            self.parent.imageScale = 8.0
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[4].setChecked(True)
            self.parent.updateImages()

    def zoomOut(self):
        if self.parent.imageScale == 1.5:
            self.parent.imageScale = 1.0
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[0].setChecked(True)
            self.parent.updateImages()
        elif self.parent.imageScale == 2.0:
            self.parent.imageScale = 1.5
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[1].setChecked(True)
            self.parent.updateImages()
        elif self.parent.imageScale == 4.0:
            self.parent.imageScale = 2.0
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[2].setChecked(True)
            self.parent.updateImages()
        elif self.parent.imageScale == 8.0:
            self.parent.imageScale = 4.0
            self.parent.scaleChanged = True
            self.parent.agZoom.actions()[3].setChecked(True)
            self.parent.updateImages()


class LabelTable(QTableWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        columns = ["Label name", "Label class", "Label color"]
        self.setColumnCount(3)
        self.row = 0
        self.col = 0
        self.setContextMenuPolicy(Qt.ContextMenuPolicy.CustomContextMenu)
        self.customContextMenuRequested.connect(self.contextMenuEvent)
        self.setHorizontalHeaderLabels(columns)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)
        self.horizontalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)
        self.setEditTriggers(QAbstractItemView.EditTrigger.NoEditTriggers)
        self.viewport().installEventFilter(self)

    def contextMenuEvent(self, event):
        self.row = self.rowAt(event.y())
        self.col = self.columnAt(event.x())
        menu = QMenu()
        addLabelAction = QAction("Add new label", self)
        addLabelAction.triggered.connect(self.addLabel)
        setClassesAction = QAction("Set label classes", self)
        setClassesAction.triggered.connect(self.setClasses)
        labelDrawAction = QAction("Set as drawn label", self)
        labelDrawAction.triggered.connect(self.drawnLabel)
        showHideLabelAction = QAction("Show/hide this label", self)
        showHideLabelAction.triggered.connect(self.showHideLabel)
        removeLabelAction = QAction("Remove this label", self)
        removeLabelAction.triggered.connect(self.removeLabel)
        resetColorAction = QAction("Reset this label's color", self)
        resetColorAction.triggered.connect(self.resetColor)
        menu.addAction(addLabelAction)
        if self.row == -1 or self.col == -1:
            pass
        else:
            menu.addAction(labelDrawAction)
            menu.addAction(showHideLabelAction)
            menu.addAction(removeLabelAction)
            menu.addAction(resetColorAction)
            menu.addAction(setClassesAction)
        menu.exec(QCursor.pos())

    def addLabel(self):
        self.parent.addLabel()

    def drawnLabel(self):
        row = self.row
        labelName = self.item(row, 0).text()
        if labelName is not None:
            self.parent.changeDrawnLabel(labelName, row)

    def showHideLabel(self):
        row = self.row
        labelName = self.item(row, 0).text()
        if labelName is not None:
            self.parent.showHideLabel(labelName, row)

    def removeLabel(self):
        row = self.row
        labelName = self.item(row, 0).text()
        if labelName is not None:
            self.parent.removeLabel(labelName, row)

    def setClasses(self):
        self.parent.setClasses()

    def resetColor(self):
        row = self.row
        labelName = self.item(row, 0).text()
        self.parent.resetLabelColor(labelName, row)


class AddLabelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        onlyInt = QIntValidator()
        self.setLabelName = QLineEdit()
        self.setRedValue = QLineEdit()
        self.setRedValue.setValidator(onlyInt)
        self.setGreenValue = QLineEdit()
        self.setGreenValue.setValidator(onlyInt)
        self.setBlueValue = QLineEdit()
        self.setBlueValue.setValidator(onlyInt)
        self.formLayout.addRow("Label name: ", self.setLabelName)
        self.formLayout.addRow("Red: ", self.setRedValue)
        self.formLayout.addRow("Green: ", self.setGreenValue)
        self.formLayout.addRow("Blue: ", self.setBlueValue)
        buttons = QDialogButtonBox()
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        self.gridLayout = QGridLayout()

        self.redButton = QPushButton()
        self.redButton.setStyleSheet("background-color: red")
        self.redButton.clicked.connect(self.buttonColorSet)
        self.greenButton = QPushButton()
        self.greenButton.setStyleSheet("background-color: green")
        self.greenButton.clicked.connect(self.buttonColorSet)
        self.blueButton = QPushButton()
        self.blueButton.setStyleSheet("background-color: blue")
        self.blueButton.clicked.connect(self.buttonColorSet)
        self.maroonButton = QPushButton()
        self.maroonButton.setStyleSheet("background-color: maroon")
        self.maroonButton.clicked.connect(self.buttonColorSet)
        self.limeButton = QPushButton()
        self.limeButton.setStyleSheet("background-color: lime")
        self.limeButton.clicked.connect(self.buttonColorSet)
        self.aquaButton = QPushButton()
        self.aquaButton.setStyleSheet("background-color: aqua")
        self.aquaButton.clicked.connect(self.buttonColorSet)
        self.fuchsiaButton = QPushButton()
        self.fuchsiaButton.setStyleSheet("background-color: fuchsia")
        self.fuchsiaButton.clicked.connect(self.buttonColorSet)
        self.yellowButton = QPushButton()
        self.yellowButton.setStyleSheet("background-color: yellow")
        self.yellowButton.clicked.connect(self.buttonColorSet)
        self.navyButton = QPushButton()
        self.navyButton.setStyleSheet("background-color: navy")
        self.navyButton.clicked.connect(self.buttonColorSet)

        self.gridLayout.addWidget(self.redButton, 0, 0)
        self.gridLayout.addWidget(self.greenButton, 1, 1)
        self.gridLayout.addWidget(self.blueButton, 0, 2)
        self.gridLayout.addWidget(self.maroonButton, 1, 0)
        self.gridLayout.addWidget(self.limeButton, 0, 1)
        self.gridLayout.addWidget(self.navyButton, 1, 2)
        self.gridLayout.addWidget(self.fuchsiaButton, 2, 0)
        self.gridLayout.addWidget(self.yellowButton, 2, 1)
        self.gridLayout.addWidget(self.aquaButton, 2, 2)
        layout.addLayout(self.formLayout)
        layout.addLayout(self.gridLayout)
        layout.addWidget(buttons)
        self.setWindowTitle("Set label name and color (0-255)")
        self.setLayout(layout)
        buttons.accepted.connect(self.accepting)
        buttons.rejected.connect(self.rejecting)

    def buttonColorSet(self):
        button = self.sender()
        red = button.palette().button().color().red()
        green = button.palette().button().color().green()
        blue = button.palette().button().color().blue()
        self.setRedValue.setText(str(red))
        self.setGreenValue.setText(str(green))
        self.setBlueValue.setText(str(blue))

    def rejecting(self):
        self.reject()

    def accepting(self):
        self.accept()


class RemoveLabelDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        for k, v in self.parent.currentMaskStack.items():
            self.labelButton = QPushButton(k, self)
            self.formLayout.addWidget(self.labelButton)
            self.labelButton.clicked.connect(self.returnLabel)
        layout.addLayout(self.formLayout)
        buttons = QDialogButtonBox()
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
        )
        layout.addLayout(self.formLayout)
        layout.addWidget(buttons)
        self.setWindowTitle("Select which label to remove")
        self.setLayout(layout)
        buttons.accepted.connect(self.accepting)
        buttons.rejected.connect(self.rejecting)

    def returnLabel(self):
        button = self.sender()
        label = button.text()
        self.parent.maskColors.pop(label)
        self.parent.currentMaskStack.pop(label)
        self.parent.axialImageScene.mask.pop(label)
        self.parent.modelClasses.pop(label)
        if self.parent.drawnMaskType == label:
            self.parent.drawnMaskType = None
            self.parent.axialImageScene.drawnMaskType = None
        self.accept()

    def rejecting(self):
        self.reject()

    def accepting(self):
        self.accept()


class ResetLabelColorDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        onlyInt = QIntValidator()
        self.setRedValue = QLineEdit()
        self.setRedValue.setValidator(onlyInt)
        self.setGreenValue = QLineEdit()
        self.setGreenValue.setValidator(onlyInt)
        self.setBlueValue = QLineEdit()
        self.setBlueValue.setValidator(onlyInt)
        self.formLayout.addRow("Red: ", self.setRedValue)
        self.formLayout.addRow("Green: ", self.setGreenValue)
        self.formLayout.addRow("Blue: ", self.setBlueValue)
        buttons = QDialogButtonBox()
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        self.gridLayout = QGridLayout()

        self.redButton = QPushButton()
        self.redButton.setStyleSheet("background-color: red")
        self.redButton.clicked.connect(self.buttonColorSet)
        self.greenButton = QPushButton()
        self.greenButton.setStyleSheet("background-color: green")
        self.greenButton.clicked.connect(self.buttonColorSet)
        self.blueButton = QPushButton()
        self.blueButton.setStyleSheet("background-color: blue")
        self.blueButton.clicked.connect(self.buttonColorSet)
        self.maroonButton = QPushButton()
        self.maroonButton.setStyleSheet("background-color: maroon")
        self.maroonButton.clicked.connect(self.buttonColorSet)
        self.limeButton = QPushButton()
        self.limeButton.setStyleSheet("background-color: lime")
        self.limeButton.clicked.connect(self.buttonColorSet)
        self.aquaButton = QPushButton()
        self.aquaButton.setStyleSheet("background-color: aqua")
        self.aquaButton.clicked.connect(self.buttonColorSet)
        self.fuchsiaButton = QPushButton()
        self.fuchsiaButton.setStyleSheet("background-color: fuchsia")
        self.fuchsiaButton.clicked.connect(self.buttonColorSet)
        self.yellowButton = QPushButton()
        self.yellowButton.setStyleSheet("background-color: yellow")
        self.yellowButton.clicked.connect(self.buttonColorSet)
        self.navyButton = QPushButton()
        self.navyButton.setStyleSheet("background-color: navy")
        self.navyButton.clicked.connect(self.buttonColorSet)

        self.gridLayout.addWidget(self.redButton, 0, 0)
        self.gridLayout.addWidget(self.greenButton, 1, 1)
        self.gridLayout.addWidget(self.blueButton, 0, 2)
        self.gridLayout.addWidget(self.maroonButton, 1, 0)
        self.gridLayout.addWidget(self.limeButton, 0, 1)
        self.gridLayout.addWidget(self.navyButton, 1, 2)
        self.gridLayout.addWidget(self.fuchsiaButton, 2, 0)
        self.gridLayout.addWidget(self.yellowButton, 2, 1)
        self.gridLayout.addWidget(self.aquaButton, 2, 2)
        layout.addLayout(self.formLayout)
        layout.addLayout(self.gridLayout)
        layout.addWidget(buttons)
        self.setWindowTitle("Set label color (0-255)")
        self.setLayout(layout)
        buttons.accepted.connect(self.accepting)
        buttons.rejected.connect(self.rejecting)

    def buttonColorSet(self):
        button = self.sender()
        red = button.palette().button().color().red()
        green = button.palette().button().color().green()
        blue = button.palette().button().color().blue()
        self.setRedValue.setText(str(red))
        self.setGreenValue.setText(str(green))
        self.setBlueValue.setText(str(blue))

    def rejecting(self):
        self.reject()

    def accepting(self):
        self.accept()


class CustomWindowDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        onlyInt = QIntValidator()
        self.setCenterValue = QLineEdit()
        self.setCenterValue.setValidator(onlyInt)
        self.setWidthValue = QLineEdit()
        self.setWidthValue.setValidator(onlyInt)
        self.formLayout.addRow("Center: ", self.setCenterValue)
        self.formLayout.addRow("Width: ", self.setWidthValue)
        buttons = QDialogButtonBox()
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        layout.addLayout(self.formLayout)
        layout.addWidget(buttons)
        self.setWindowTitle("Set custom window")
        self.setLayout(layout)
        buttons.accepted.connect(self.accepting)
        buttons.rejected.connect(self.rejecting)

    def rejecting(self):
        self.reject()

    def accepting(self):
        self.accept()


class SetClassesDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        onlyInt = QIntValidator()
        self.segmentationClasses = []
        for maskType in parent.currentMaskStack:
            self.setSegmentationClass = QLineEdit()
            self.setSegmentationClass.setValidator(onlyInt)
            self.formLayout.addRow(maskType, self.setSegmentationClass)
            self.segmentationClasses.append(self.setSegmentationClass)
        buttons = QDialogButtonBox()
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        layout.addLayout(self.formLayout)
        layout.addWidget(buttons)
        self.setWindowTitle("Set segmentation model classes to labels")
        self.setLayout(layout)
        buttons.accepted.connect(self.accepting)
        buttons.rejected.connect(self.rejecting)

    def rejecting(self):
        self.reject()

    def accepting(self):
        self.accept()


class SelectDrawTypeDialog(QDialog):

    def __init__(self, parent=None):
        super().__init__(parent)
        self.parent = parent
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        for k, v in self.parent.currentMaskStack.items():
            self.labelButton = QPushButton(k, self)
            self.formLayout.addWidget(self.labelButton)
            self.labelButton.clicked.connect(self.returnLabel)
        layout.addLayout(self.formLayout)
        self.setWindowTitle("Select drawn mask")
        self.setLayout(layout)

    def returnLabel(self):
        button = self.sender()
        label = button.text()
        self.parent.drawnMaskType = label
        self.parent.axialImageScene.drawnMaskType = label
        self.accept()


class SelectExamDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        onlyInt = QIntValidator()
        self.setIndexValue = QLineEdit()
        self.setIndexValue.setValidator(onlyInt)
        self.formLayout.addRow("Exam number: ", self.setIndexValue)
        buttons = QDialogButtonBox()
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        layout.addLayout(self.formLayout)
        layout.addWidget(buttons)
        self.setWindowTitle("Select exam")
        self.setLayout(layout)
        buttons.accepted.connect(self.accepting)
        buttons.rejected.connect(self.rejecting)

    def rejecting(self):
        self.reject()

    def accepting(self):
        self.accept()


class NameLabelsDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.formLayout = QFormLayout()
        self.setCSVName = QLineEdit()
        self.formLayout.addRow("Csv name: ", self.setCSVName)
        buttons = QDialogButtonBox()
        buttons.setStandardButtons(
            QDialogButtonBox.StandardButton.Cancel
            | QDialogButtonBox.StandardButton.Ok
        )
        layout.addLayout(self.formLayout)
        layout.addWidget(buttons)
        self.setWindowTitle("Set csv file name")
        self.setLayout(layout)
        buttons.accepted.connect(self.accepting)
        buttons.rejected.connect(self.rejecting)

    def rejecting(self):
        self.reject()

    def accepting(self):
        self.accept()


class RangeSlider(QSlider):

    # Originated from
    # https://www.mail-archive.com/pyqt@riverbankcomputing.com/msg22889.html
    # Modification referred from
    # https://gist.github.com/Riateche/27e36977f7d5ea72cf4f
    # PyQt5 version from https://github.com/Qt-Widgets/range_slider_for_Qt5_and_PyQt5

    sliderMoved = pyqtSignal(int, int)

    """ A slider for ranges.

        This class provides a dual-slider for ranges, where there is a defined
        maximum and minimum, as is a normal slider, but instead of having a
        single slider value, there are 2 slider values.

        This class emits the same signals as the QSlider base class, with the 
        exception of valueChanged
    """

    def __init__(self, *args):
        super(RangeSlider, self).__init__(*args)

        self._low = self.minimum()
        self._high = self.maximum()

        self.pressed_control = QStyle.SubControl.SC_None
        self.tick_interval = 0
        self.tick_position = QSlider.TickPosition.NoTicks
        self.hover_control = QStyle.SubControl.SC_None
        self.click_offset = 0

        # 0 for the low, 1 for the high, -1 for both
        self.active_slider = 0

    def low(self):
        return self._low

    def setLow(self, low: int):
        self._low = low
        self.update()

    def high(self):
        return self._high

    def setHigh(self, high):
        self._high = high
        self.update()

    def paintEvent(self, event):
        # based on http://qt.gitorious.org/qt/qt/blobs/master/src/gui/widgets/qslider.cpp

        painter = QPainter(self)
        style = QApplication.style()

        # draw groove
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        opt.siderValue = 0
        opt.sliderPosition = 0
        opt.subControls = QStyle.SubControl.SC_SliderGroove
        if self.tickPosition() != self.TickPosition.NoTicks:
            opt.subControls |= QStyle.SubControl.SC_SliderTickmarks
        style.drawComplexControl(QStyle.ComplexControl.CC_Slider, opt, painter, self)
        groove = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderGroove, self)

        # drawSpan
        # opt = QtWidgets.QStyleOptionSlider()
        self.initStyleOption(opt)
        opt.subControls = QStyle.SubControl.SC_SliderGroove
        # if self.tickPosition() != self.NoTicks:
        #    opt.subControls |= QtWidgets.QStyle.SC_SliderTickmarks
        opt.siderValue = 0
        # print(self._low)
        opt.sliderPosition = self._low
        low_rect = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self)
        opt.sliderPosition = self._high
        high_rect = style.subControlRect(QStyle.ComplexControl.CC_Slider, opt, QStyle.SubControl.SC_SliderHandle, self)

        # print(low_rect, high_rect)
        low_pos = self.__pick(low_rect.center())
        high_pos = self.__pick(high_rect.center())

        min_pos = min(low_pos, high_pos)
        max_pos = max(low_pos, high_pos)

        c = QRect(low_rect.center(), high_rect.center()).center()
        # print(min_pos, max_pos, c)
        if opt.orientation == Qt.Orientation.Horizontal:
            span_rect = QRect(QPoint(min_pos, c.y() - 2), QPoint(max_pos, c.y() + 1))
        else:
            span_rect = QRect(QPoint(c.x() - 2, min_pos), QPoint(c.x() + 1, max_pos))

        # self.initStyleOption(opt)
        # print(groove.x(), groove.y(), groove.width(), groove.height())
        if opt.orientation == Qt.Orientation.Horizontal:
            groove.adjust(0, 0, -1, 0)
        else:
            groove.adjust(0, 0, 0, -1)

        if True:  # self.isEnabled():
            highlight = self.palette().color(QPalette.ColorRole.Highlight)
            painter.setBrush(QBrush(highlight))
            painter.setPen(QPen(highlight, 0))
            # painter.setPen(QtGui.QPen(self.palette().color(QtGui.QPalette.Dark), 0))
            '''
            if opt.orientation == QtCore.Qt.Horizontal:
                self.setupPainter(painter, opt.orientation, groove.center().x(), groove.top(), groove.center().x(), groove.bottom())
            else:
                self.setupPainter(painter, opt.orientation, groove.left(), groove.center().y(), groove.right(), groove.center().y())
            '''
            # spanRect =
            painter.drawRect(span_rect.intersected(groove))
            # painter.drawRect(groove)

        for i, value in enumerate([self._low, self._high]):
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)

            # Only draw the groove for the first slider so it doesn't get drawn
            # on top of the existing ones every time
            if i == 0:
                opt.subControls = QStyle.SubControl.SC_SliderHandle  # | QtWidgets.QStyle.SC_SliderGroove
            else:
                opt.subControls = QStyle.SubControl.SC_SliderHandle

            if self.tickPosition() != self.TickPosition.NoTicks:
                opt.subControls |= QStyle.SubControl.SC_SliderTickmarks

            if self.pressed_control:
                opt.activeSubControls = self.pressed_control
            else:
                opt.activeSubControls = self.hover_control

            opt.sliderPosition = value
            opt.sliderValue = value
            style.drawComplexControl(QStyle.ComplexControl.CC_Slider, opt, painter, self)

    def mousePressEvent(self, event):
        event.accept()

        style = QApplication.style()
        button = event.button()

        # In a normal slider control, when the user clicks on a point in the
        # slider's total range, but not on the slider part of the control the
        # control would jump the slider value to where the user clicked.
        # For this control, clicks which are not direct hits will slide both
        # slider parts

        if button:
            opt = QStyleOptionSlider()
            self.initStyleOption(opt)

            self.active_slider = -1

            for i, value in enumerate([self._low, self._high]):
                opt.sliderPosition = value
                hit = style.hitTestComplexControl(style.ComplexControl.CC_Slider, opt, event.pos(), self)
                if hit == style.SubControl.SC_SliderHandle:
                    self.active_slider = i
                    self.pressed_control = hit

                    self.triggerAction(self.SliderAction.SliderMove)
                    self.setRepeatAction(self.SliderAction.SliderNoAction)
                    self.setSliderDown(True)
                    break

            if self.active_slider < 0:
                self.pressed_control = QStyle.SubControl.SC_SliderHandle
                self.click_offset = self.__pixelPosToRangeValue(self.__pick(event.pos()))
                self.triggerAction(self.SliderAction.SliderMove)
                self.setRepeatAction(self.SliderAction.SliderNoAction)
        else:
            event.ignore()

    def mouseMoveEvent(self, event):
        if self.pressed_control != QStyle.SubControl.SC_SliderHandle:
            event.ignore()
            return

        event.accept()
        new_pos = self.__pixelPosToRangeValue(self.__pick(event.pos()))
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)

        if self.active_slider < 0:
            offset = new_pos - self.click_offset
            self._high += offset
            self._low += offset
            if self._low < self.minimum():
                diff = self.minimum() - self._low
                self._low += diff
                self._high += diff
            if self._high > self.maximum():
                diff = self.maximum() - self._high
                self._low += diff
                self._high += diff
        elif self.active_slider == 0:
            if new_pos >= self._high:
                new_pos = self._high - 1
            self._low = new_pos
        else:
            if new_pos <= self._low:
                new_pos = self._low + 1
            self._high = new_pos

        self.click_offset = new_pos

        self.update()

        # self.emit(QtCore.SIGNAL('sliderMoved(int)'), new_pos)
        self.sliderMoved.emit(self._low, self._high)

    def __pick(self, pt):
        if self.orientation() == Qt.Orientation.Horizontal:
            return pt.x()
        else:
            return pt.y()

    def __pixelPosToRangeValue(self, pos):
        opt = QStyleOptionSlider()
        self.initStyleOption(opt)
        style = QApplication.style()

        gr = style.subControlRect(style.ComplexControl.CC_Slider, opt, style.SubControl.SC_SliderGroove, self)
        sr = style.subControlRect(style.ComplexControl.CC_Slider, opt, style.SubControl.SC_SliderHandle, self)

        if self.orientation() == Qt.Orientation.Horizontal:
            slider_length = sr.width()
            slider_min = gr.x()
            slider_max = gr.right() - slider_length + 1
        else:
            slider_length = sr.height()
            slider_min = gr.y()
            slider_max = gr.bottom() - slider_length + 1

        return style.sliderValueFromPosition(self.minimum(), self.maximum(),
                                             pos - slider_min, slider_max - slider_min,
                                             opt.upsideDown)
    