from PyQt6.QtWidgets import QGraphicsScene, QApplication, QPushButton, QLineEdit, QVBoxLayout, QFormLayout, QDialog, QGridLayout, QDialogButtonBox, QTableWidget, QHeaderView, QMenu, QAbstractItemView, QSizePolicy
from PyQt6.QtGui import QIntValidator, QAction, QCursor
from PyQt6.QtCore import Qt

from gui_utils.drawing_utils import *
from gui_utils.image_utils import reset_mask_stack


class CTGraphicsScene(QGraphicsScene):
    def __init__(self, imageType, parent=None):
        super().__init__(parent)
        self.parent = parent
        self.imageType = imageType
        self.drawing = False
        self.maskShown = True
        self.mask = reset_mask_stack(self.parent.currentMaskStack)
        self.drawingSize = 7
        self.drawingHigh = 4
        self.drawingLow = 3
        self.drawingShape = seven_circle
        self.drawnMaskType = None
        self.currentMaskIndex = 0

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
        if event.button() == Qt.MouseButton.LeftButton:
            x = int(event.scenePos().x())
            y = int(event.scenePos().y())
            if (self.parent.clickType["Drawing"] or self.parent.clickType["Erasing"]) and self.imageType == "axial" and self.drawnMaskType is not None and self.maskShown and self.parent.currentMaskStack[self.drawnMaskType] is not None and self.parent.showMasks and self.imageType == "axial" and self.mask[self.drawnMaskType] is not None and x >= 0 and y >= 0 and x < self.parent.currentDICOMStack.shape[2] and y < self.parent.currentDICOMStack.shape[1]:
                self.drawing = True
                self.currentMaskIndex = self.parent.axialDICOMIndex
                self.mask[self.drawnMaskType][self.currentMaskIndex, y - self.drawingLow:y + self.drawingHigh, x - self.drawingLow:x + self.drawingHigh] = self.drawingShape
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

    def wheelEvent(self, event):
        modifiers = QApplication.keyboardModifiers()
        if not self.drawing and bool(modifiers == Qt.KeyboardModifier.ControlModifier):
            if event.delta() > 0:
                self.zoomIn()
            elif event.delta() < 0:
                self.zoomOut()

    def mouseMoveEvent(self, event):
        x = int(event.scenePos().x())
        y = int(event.scenePos().y())
        if self.drawing and x >= 0 and y >= 0 and x < self.parent.currentDICOMStack.shape[2] and y < self.parent.currentDICOMStack.shape[1]:
            try:
                self.mask[self.drawnMaskType][self.currentMaskIndex, y - self.drawingLow:y + self.drawingHigh, x - self.drawingLow:x + self.drawingHigh] = self.drawingShape
            except ValueError:
                pass
            self.parent.drawMask()

    def mouseReleaseEvent(self, event):
        if self.drawing:
            self.drawing = False
            if self.parent.fillContours and self.parent.clickType["Drawing"]:
                self.parent.fillContoursFunc()
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
        removeLabelAction = QAction("Remove this label", self)
        removeLabelAction.triggered.connect(self.removeLabel)
        resetColorAction = QAction("Reset this label's color", self)
        resetColorAction.triggered.connect(self.resetColor)
        menu.addAction(addLabelAction)
        if self.row == -1 or self.col == -1:
            pass
        else:
            menu.addAction(labelDrawAction)
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
