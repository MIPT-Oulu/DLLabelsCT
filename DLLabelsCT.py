import sys
import os
import csv
import cv2
import pydicom.errors
from pydicom import dcmread
from pathlib import Path
from skimage.morphology import reconstruction

from PyQt6.QtWidgets import QWidget, QTableWidgetItem, QSlider, QLabel, QGridLayout, QHBoxLayout, QFileDialog, QMainWindow, QGraphicsView, QProgressBar, QMessageBox
from PyQt6.QtGui import QImage, QPixmap, QPainter, QActionGroup, QKeySequence, QColor

from gui_utils.custom_widgets import *
from gui_utils.segmentation_utils import segmentation
from gui_utils.image_utils import *
from gui_utils.drawing_utils import *


class DLLabelsCT(QMainWindow):

    def __init__(self):

        super().__init__()
        self.DICOMFolderPath = ""
        self.dicoms = []

        self.axialDICOMIndex = 0
        self.coronalDICOMIndex = 0
        self.sagittalDICOMIndex = 0
        self.dicomWindowCenter = 50
        self.dicomWindowWidth = 400
        self.currentDICOMStack = None
        self.currentMaskStack = {}
        self.maskColors = {}
        self.modelClasses = {}

        self.currentStudyID = None
        self.currentPatientID = None
        self.defaultDirectory = os.path.realpath(__file__)
        self.annotableDirectory = None
        self.annotableFolders = []
        self.annotableIndex = 0
        self.saveDirectory = None
        self.segmentationModelFolderPath = None
        self.segmentationModelPath = None
        self.indexesToSegment = []

        self.showMasks = True
        self.saveImages = True
        self.saveFlipped = True
        self.removeOutliers = False
        self.fillContours = False
        self.device = "cuda"
        self.flip = {"Axial": False, "Coronal": False, "Sagittal": False}
        self.axialImageQt = None

        self.clickType = {"Selecting": True, "Dragging": False, "Drawing": False, "Erasing": False}
        self.erasingOrDrawing = 1

        self.scaleChanged = False
        self.imageScale = 1.0
        self.drawnMaskType = None

        self.segmentationModelType = None

        self.maskOpacity = 128

        centralWidget = QWidget(self)
        self.setCentralWidget(centralWidget)
        centralLayout = QHBoxLayout(centralWidget)

        self.gridLayout = QGridLayout()
        self.gridLayout.setRowStretch(0, 1)
        self.gridLayout.setColumnStretch(0, 2)
        self.vLayout = QVBoxLayout()
        centralLayout.addLayout(self.gridLayout)
        centralLayout.addLayout(self.vLayout)

        self.initUI()

    def initUI(self):

        self._createMenu()
        self._createLabels()
        self._createStatusBar()
        self._createButtons()
        self._createSliders()
        self._createProgressBar()
        self.setGeometry(100, 100, 500, 300)
        self.setWindowTitle("DLLabelsCT")

    def _createMenu(self):

        menubar = self.menuBar()

        fileMenu = menubar.addMenu('File')
        selectDICOMFolderAct = QAction('Select DICOM folder...', self)
        selectDICOMFolderAct.triggered.connect(self.getDICOMFolder)
        selectSegmentationModelFolderAct = QAction('Select segmentation model folder...', self)
        selectSegmentationModelFolderAct.triggered.connect(self.getSegmentationModelFolder)
        selectSaveDirectoryAct = QAction('Select save folder...', self)
        selectSaveDirectoryAct.triggered.connect(self.getSaveFolder)
        selectAnnotableFolderAct = QAction('Select folder to annotate...', self)
        selectAnnotableFolderAct.triggered.connect(self.getAnnotableFolder)
        saveMasksAct = QAction('Save masks', self)
        saveMasksAct.triggered.connect(self.saveMasks)
        loadMasksAct = QAction('Load masks...', self)
        loadMasksAct.triggered.connect(self.loadMasks)
        saveAnnotationsAct = QAction('Save annotations', self)
        saveAnnotationsAct.triggered.connect(self.saveAnnotations)
        saveLabelsAct = QAction('Save labels...', self)
        saveLabelsAct.triggered.connect(self.saveLabels)
        loadLabelsAct = QAction('Load labels...', self)
        loadLabelsAct.triggered.connect(self.loadLabels)
        fileMenu.addAction(selectDICOMFolderAct)
        fileMenu.addAction(selectSegmentationModelFolderAct)
        fileMenu.addAction(selectAnnotableFolderAct)
        fileMenu.addAction(selectSaveDirectoryAct)
        fileMenu.addSeparator()
        fileMenu.addAction(saveMasksAct)
        fileMenu.addAction(loadMasksAct)
        fileMenu.addSeparator()
        fileMenu.addAction(saveAnnotationsAct)
        fileMenu.addSeparator()
        fileMenu.addAction(saveLabelsAct)
        fileMenu.addAction(loadLabelsAct)

        self.showMenu = menubar.addMenu('Show')
        showAxialAct = QAction('Axial', self, checkable=True)
        showAxialAct.setShortcut(QKeySequence("Z"))
        showCoronalAct = QAction('Coronal', self, checkable=True)
        showCoronalAct.setShortcut(QKeySequence("X"))
        showSagittalAct = QAction('Sagittal', self, checkable=True)
        showSagittalAct.setShortcut(QKeySequence("C"))
        showMasksAct = QAction('Masks', self, checkable=True)
        showMasksAct.setShortcut(QKeySequence("V"))
        self.showMenu.triggered.connect(self.showOrHide)
        showAxialAct.setChecked(True)
        showCoronalAct.setChecked(True)
        showSagittalAct.setChecked(True)
        showMasksAct.setChecked(True)
        self.showMenu.addAction(showAxialAct)
        self.showMenu.addAction(showCoronalAct)
        self.showMenu.addAction(showSagittalAct)
        self.showMenu.addAction(showMasksAct)
        self.showMenu.hide()

        windowingMenu = menubar.addMenu('Windowing')
        selectDefaultAct = QAction('Tissue 1', self, checkable=True)
        selectTissue2Act = QAction('Tissue 2', self, checkable=True)
        selectTissue3Act = QAction('Tissue 3', self, checkable=True)
        selectLungsAct = QAction('Lungs', self, checkable=True)
        selectBoneAct = QAction('Bone', self, checkable=True)
        selectCustomWindowAct = QAction("Custom...", self, checkable=True)
        self.agWindowing = QActionGroup(self)
        d = self.agWindowing.addAction(selectDefaultAct)
        t2 = self.agWindowing.addAction(selectTissue2Act)
        t3 = self.agWindowing.addAction(selectTissue3Act)
        l = self.agWindowing.addAction(selectLungsAct)
        b = self.agWindowing.addAction(selectBoneAct)
        cw = self.agWindowing.addAction(selectCustomWindowAct)
        self.agWindowing.setExclusive(True)
        d.setChecked(True)
        windowingMenu.addAction(d)
        windowingMenu.addAction(t2)
        windowingMenu.addAction(t3)
        windowingMenu.addAction(l)
        windowingMenu.addAction(b)
        windowingMenu.addAction(cw)
        self.agWindowing.triggered.connect(self.changeWindowing)

        deviceMenu = menubar.addMenu('Device')
        selectGPUAct = QAction('GPU', self, checkable=True)
        selectCPUAct = QAction('CPU', self, checkable=True)
        agDevice = QActionGroup(self)
        gpu = agDevice.addAction(selectGPUAct)
        cpu = agDevice.addAction(selectCPUAct)
        agDevice.setExclusive(True)
        gpu.setChecked(True)
        deviceMenu.addAction(gpu)
        deviceMenu.addAction(cpu)
        agDevice.triggered.connect(self.changeDevice)

        optionsMenu = menubar.addMenu('Options')
        selectPatientIDShowingAct = QAction('Show patient ID', self, checkable=True)
        selectRemovingAct = QAction('Remove outliers after segmentation/when saving', self, checkable=True)
        selectFillingAct = QAction('Automatically fill holes in masks', self, checkable=True)
        selectImageSavingAct = QAction('Save images when annotating', self, checkable=True)
        selectImageFlippingAct = QAction('Save flipped images when annotating', self, checkable=True)
        self.agOptions = QActionGroup(self)
        showing = self.agOptions.addAction(selectPatientIDShowingAct)
        removing = self.agOptions.addAction(selectRemovingAct)
        filling = self.agOptions.addAction(selectFillingAct)
        savingImages = self.agOptions.addAction(selectImageSavingAct)
        savingFlipped = self.agOptions.addAction(selectImageFlippingAct)
        self.agOptions.setExclusive(False)
        savingImages.setChecked(True)
        savingFlipped.setChecked(True)
        optionsMenu.addAction(showing)
        optionsMenu.addAction(removing)
        optionsMenu.addAction(filling)
        optionsMenu.addAction(savingImages)
        optionsMenu.addAction(savingFlipped)
        self.agOptions.triggered.connect(self.changeOptions)

        drawingMenu = menubar.addMenu('Drawing options')
        selectSelectingAct = QAction('Selecting', self, checkable=True)
        selectSelectingAct.setShortcut(QKeySequence("S"))
        selectDrawingAct = QAction('Drawing', self, checkable=True)
        selectDrawingAct.setShortcut(QKeySequence("D"))
        selectErasingAct = QAction('Erasing', self, checkable=True)
        selectErasingAct.setShortcut(QKeySequence("E"))
        selectDraggingAct = QAction('Dragging', self, checkable=True)
        selectDraggingAct.setShortcut(QKeySequence("F"))
        agDrawErase = QActionGroup(self)
        selecting = agDrawErase.addAction(selectSelectingAct)
        drawing = agDrawErase.addAction(selectDrawingAct)
        erasing = agDrawErase.addAction(selectErasingAct)
        dragging = agDrawErase.addAction(selectDraggingAct)
        agDrawErase.setExclusive(True)
        selecting.setChecked(True)
        drawingMenu.addAction(selecting)
        drawingMenu.addAction(drawing)
        drawingMenu.addAction(erasing)
        drawingMenu.addAction(dragging)
        drawingMenu.addSeparator()
        agDrawErase.triggered.connect(self.changeDrawingErasing)
        select1x1Act = QAction('1x1', self, checkable=True)
        select1x1Act.setShortcut(QKeySequence("1"))
        select3x3Act = QAction('3x3', self, checkable=True)
        select3x3Act.setShortcut(QKeySequence("2"))
        select5x5Act = QAction('5x5', self, checkable=True)
        select5x5Act.setShortcut(QKeySequence("3"))
        select7x7Act = QAction('7x7', self, checkable=True)
        select7x7Act.setShortcut(QKeySequence("4"))
        agDrawSize = QActionGroup(self)
        onexone = agDrawSize.addAction(select1x1Act)
        threexthree = agDrawSize.addAction(select3x3Act)
        fivexfive = agDrawSize.addAction(select5x5Act)
        sevenxseven = agDrawSize.addAction(select7x7Act)
        agDrawSize.setExclusive(True)
        sevenxseven.setChecked(True)
        drawingMenu.addAction(onexone)
        drawingMenu.addAction(threexthree)
        drawingMenu.addAction(fivexfive)
        drawingMenu.addAction(sevenxseven)
        drawingMenu.addSeparator()
        agDrawSize.triggered.connect(self.changeDrawingSize)
        selectCircleAct = QAction('Circle', self, checkable=True)
        selectSquareAct = QAction('Square', self, checkable=True)
        self.agDrawShape = QActionGroup(self)
        circle = self.agDrawShape.addAction(selectCircleAct)
        square = self.agDrawShape.addAction(selectSquareAct)
        self.agDrawShape.setExclusive(True)
        circle.setChecked(True)
        drawingMenu.addAction(circle)
        drawingMenu.addAction(square)
        self.agDrawShape.triggered.connect(self.changeDrawingShape)

        zoomMenu = menubar.addMenu('Zoom')
        select1Act = QAction('1.0', self, checkable=True)
        select15Act = QAction('1.5', self, checkable=True)
        select2Act = QAction('2.0', self, checkable=True)
        select4Act = QAction('4.0', self, checkable=True)
        select8Act = QAction('8.0', self, checkable=True)
        self.agZoom = QActionGroup(self)
        one = self.agZoom.addAction(select1Act)
        onefive = self.agZoom.addAction(select15Act)
        two = self.agZoom.addAction(select2Act)
        four = self.agZoom.addAction(select4Act)
        eight = self.agZoom.addAction(select8Act)
        self.agZoom.setExclusive(True)
        one.setChecked(True)
        zoomMenu.addAction(one)
        zoomMenu.addAction(onefive)
        zoomMenu.addAction(two)
        zoomMenu.addAction(four)
        zoomMenu.addAction(eight)
        self.agZoom.triggered.connect(self.changeZoom)

        flipMenu = menubar.addMenu('Flip')
        selectAxis0Act = QAction('Axial', self, checkable=True)
        selectAxis1Act = QAction('Coronal', self, checkable=True)
        selectAxis2Act = QAction('Sagittal', self, checkable=True)
        self.agFlip = QActionGroup(self)
        axis0 = self.agFlip.addAction(selectAxis0Act)
        axis1 = self.agFlip.addAction(selectAxis1Act)
        axis2 = self.agFlip.addAction(selectAxis2Act)
        self.agFlip.setExclusive(False)
        flipMenu.addAction(axis0)
        flipMenu.addAction(axis1)
        flipMenu.addAction(axis2)
        self.agFlip.triggered.connect(self.changeFlip)

        self.selectExamAct = menubar.addAction('Change exam...')
        self.selectExamAct.setVisible(False)
        self.selectExamAct.triggered.connect(self.selectExam)

    def _createLabels(self):

        self.currentDICOMPathLabel = QLabel("DICOM folder: None", self)
        self.gridLayout.addWidget(self.currentDICOMPathLabel, 3, 0, alignment=Qt.AlignmentFlag.AlignCenter)

        self.currentSegmentationModelPathLabel = QLabel("Segmentation model folder: None", self)
        self.gridLayout.addWidget(self.currentSegmentationModelPathLabel, 4, 0, alignment=Qt.AlignmentFlag.AlignCenter)

        self.currentSavePathLabel = QLabel("Save folder: None", self)
        self.gridLayout.addWidget(self.currentSavePathLabel, 5, 0, alignment=Qt.AlignmentFlag.AlignCenter)

        self.currentPatientIDLabel = QLabel("Patient ID: None", self)
        self.gridLayout.addWidget(self.currentPatientIDLabel, 6, 0, alignment=Qt.AlignmentFlag.AlignCenter)
        self.currentPatientIDLabel.hide()

        self.axialImageScene = CTGraphicsScene("axial", self)
        self.axialImageLabel = QGraphicsView(self)
        self.axialImageLabel.setScene(self.axialImageScene)
        self.axialImageLabel.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.axialImageLabel.fitInView(self.axialImageScene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.gridLayout.addWidget(self.axialImageLabel, 0, 0)

        self.coronalImageScene = CTGraphicsScene("coronal", self)
        self.coronalImageLabel = QGraphicsView(self)
        self.coronalImageLabel.setScene(self.coronalImageScene)
        self.coronalImageLabel.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.coronalImageLabel.fitInView(self.coronalImageScene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.gridLayout.addWidget(self.coronalImageLabel, 0, 1)

        self.sagittalImageScene = CTGraphicsScene("sagittal", self)
        self.sagittalImageLabel = QGraphicsView(self)
        self.sagittalImageLabel.setScene(self.sagittalImageScene)
        self.sagittalImageLabel.setCursor(QCursor(Qt.CursorShape.CrossCursor))
        self.sagittalImageLabel.fitInView(self.sagittalImageScene.sceneRect(), Qt.AspectRatioMode.KeepAspectRatio)
        self.gridLayout.addWidget(self.sagittalImageLabel, 0, 2)

        self.labelTable = LabelTable(self)
        self.labelTable.setFixedWidth(280)
        self.vLayout.addWidget(self.labelTable, alignment=Qt.AlignmentFlag.AlignTrailing)

        self.axialIndexLabel = QLabel(self)
        self.gridLayout.addWidget(self.axialIndexLabel, 1, 0, alignment=Qt.AlignmentFlag.AlignCenter)

        self.coronalIndexLabel = QLabel(self)
        self.gridLayout.addWidget(self.coronalIndexLabel, 1, 1, alignment=Qt.AlignmentFlag.AlignCenter)

        self.sagittalIndexLabel = QLabel(self)
        self.gridLayout.addWidget(self.sagittalIndexLabel, 1, 2, alignment=Qt.AlignmentFlag.AlignCenter)

        self.segmentationIndexLabel = QLabel(self)
        self.gridLayout.addWidget(self.segmentationIndexLabel, 6, 1, alignment=Qt.AlignmentFlag.AlignCenter)
        self.segmentationIndexLabel.hide()

    def _createButtons(self):

        self.removeOutliersButton = QPushButton("Remove outliers from drawn mask")
        self.gridLayout.addWidget(self.removeOutliersButton, 3, 1)
        self.removeOutliersButton.clicked.connect(self.removeOutliersFunc)
        self.removeOutliersButton.hide()

        self.fillContoursButton = QPushButton("Fill masks")
        self.fillContoursButton.clicked.connect(self.fillContoursFunc)
        self.gridLayout.addWidget(self.fillContoursButton, 4, 1)
        self.fillContoursButton.hide()

        self.doSegmentationButton = QPushButton("Do segmentation")
        self.gridLayout.addWidget(self.doSegmentationButton, 5, 1)
        self.doSegmentationButton.clicked.connect(self.doSegmentation)
        self.doSegmentationButton.hide()

    def _createSliders(self):

        self.axialSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.axialSlider.setRange(0, 100)
        self.axialSlider.valueChanged[int].connect(self.changeAxialImageIndex)
        self.gridLayout.addWidget(self.axialSlider, 2, 0)
        self.axialSlider.hide()

        self.coronalSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.coronalSlider.setRange(0, 511)
        self.coronalSlider.valueChanged[int].connect(self.changeCoronalImageIndex)
        self.gridLayout.addWidget(self.coronalSlider, 2, 1)
        self.coronalSlider.hide()

        self.sagittalSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.sagittalSlider.setRange(0, 511)
        self.sagittalSlider.valueChanged[int].connect(self.changeSagittalImageIndex)
        self.gridLayout.addWidget(self.sagittalSlider, 2, 2)
        self.sagittalSlider.hide()

        self.setOpacitySlider = QSlider(Qt.Orientation.Horizontal, self)
        self.setOpacitySlider.setRange(0, 255)
        self.setOpacitySlider.setValue(self.maskOpacity)
        self.setOpacitySlider.valueChanged[int].connect(self.changeOpacity)
        self.gridLayout.addWidget(self.setOpacitySlider, 3, 2)
        self.setOpacitySlider.hide()

        self.setMinSegmentationSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.setMinSegmentationSlider.setRange(0, 100)
        self.setMinSegmentationSlider.setValue(0)
        self.setMinSegmentationSlider.valueChanged[int].connect(self.changeSegmentationIndexMin)
        self.gridLayout.addWidget(self.setMinSegmentationSlider, 4, 2)
        self.setMinSegmentationSlider.hide()

        self.setMaxSegmentationSlider = QSlider(Qt.Orientation.Horizontal, self)
        self.setMaxSegmentationSlider.setRange(0, 100)
        self.setMaxSegmentationSlider.setValue(100)
        self.setMaxSegmentationSlider.valueChanged[int].connect(self.changeSegmentationIndexMax)
        self.gridLayout.addWidget(self.setMaxSegmentationSlider, 5, 2)
        self.setMaxSegmentationSlider.hide()

    def _createStatusBar(self):

        self.statusbar = self.statusBar()

    def _createProgressBar(self):

        self.progressBar = QProgressBar(self)
        self.progressBar.setRange(0, 100)
        self.gridLayout.addWidget(self.progressBar, 8, 0, 1, 3)
        self.progressBar.hide()

    def changeAxialImageIndex(self, sliderValue):

        self.axialDICOMIndex = sliderValue
        self.updateSingleImage(imageType="axial")

    def changeCoronalImageIndex(self, sliderValue):

        self.coronalDICOMIndex = sliderValue
        self.updateSingleImage(imageType="coronal")

    def changeSagittalImageIndex(self, sliderValue):

        self.sagittalDICOMIndex = sliderValue
        self.updateSingleImage(imageType="sagittal")

    def changeOpacity(self, sliderValue):

        self.maskOpacity = sliderValue
        self.updateImages()

    def changeSegmentationIndexMax(self, sliderValue):

        if sliderValue <= self.setMinSegmentationSlider.value():
            self.setMaxSegmentationSlider.setValue(self.setMinSegmentationSlider.value() + 1)

        self.indexesToSegment = list(range(self.setMinSegmentationSlider.value(), self.setMaxSegmentationSlider.value() + 1))

        self.segmentationIndexLabel.setText(f"Slices to segment: {self.setMinSegmentationSlider.value()} - {self.setMaxSegmentationSlider.value()}")

    def changeSegmentationIndexMin(self, sliderValue):

        if sliderValue >= self.setMaxSegmentationSlider.value():
            self.setMinSegmentationSlider.setValue(self.setMaxSegmentationSlider.value() - 1)

        self.indexesToSegment = list(range(self.setMinSegmentationSlider.value(), self.setMaxSegmentationSlider.value() + 1))

        self.segmentationIndexLabel.setText(f"Slices to segment:  {self.setMinSegmentationSlider.value()} - {self.setMaxSegmentationSlider.value()}")

    def changeWindowing(self, act):

        if self.currentDICOMStack is not None:
            if act.text() == "Tissue 1":
                self.dicomWindowCenter = 50
                self.dicomWindowWidth = 400
            elif act.text() == "Tissue 2":
                self.dicomWindowCenter = 50
                self.dicomWindowWidth = 250
            elif act.text() == "Tissue 3":
                self.dicomWindowCenter = 30
                self.dicomWindowWidth = 150
            elif act.text() == "Lungs":
                self.dicomWindowCenter = -600
                self.dicomWindowWidth = 1500
            elif act.text() == "Bone":
                self.dicomWindowCenter = 400
                self.dicomWindowWidth = 1800
            elif act.text() == "Custom...":
                customWindowDialog = CustomWindowDialog(parent=self)
                if customWindowDialog.exec():
                    try:
                        widthValue = int(customWindowDialog.setWidthValue.text())
                        centerValue = int(customWindowDialog.setCenterValue.text())
                        if widthValue > 0:
                            self.dicomWindowCenter = centerValue
                            self.dicomWindowWidth = widthValue
                        else:
                            self.statusbar.showMessage("Invalid values!")
                            self.agWindowing.actions()[0].setChecked(True)
                            self.dicomWindowCenter = 50
                            self.dicomWindowWidth = 400
                    except ValueError:
                        self.statusbar.showMessage("Invalid values!")
                        self.agWindowing.actions()[0].setChecked(True)
                        self.dicomWindowCenter = 50
                        self.dicomWindowWidth = 400
            self.currentDICOMStack = None
            self.showImages(imagesChanged=False)
            if self.showMasks:
                self.updateImages()
        else:
            self.agWindowing.actions()[0].setChecked(True)
            self.dicomWindowCenter = 50
            self.dicomWindowWidth = 400
            self.statusbar.showMessage("Windowing cannot be changed without DICOMs! (Window changed back to default)")

    def changeDevice(self, act):

        if act.text() == "GPU":
            self.device = "cuda"
        elif act.text() == "CPU":
            self.device = "cpu"

    def changeOptions(self):

        if self.agOptions.actions()[0].isChecked():
            self.currentPatientIDLabel.show()
        else:
            self.currentPatientIDLabel.hide()
        if self.agOptions.actions()[1].isChecked():
            self.removeOutliers = True
        else:
            self.removeOutliers = False
        if self.agOptions.actions()[2].isChecked():
            self.fillContours = True
        else:
            self.fillContours = False
        if self.agOptions.actions()[3].isChecked():
            self.saveImages = True
        else:
            self.saveImages = False
        if self.agOptions.actions()[4].isChecked():
            self.saveFlipped = True
        else:
            self.saveFlipped = False

    def changeDrawingErasing(self, act):

        self.clickType = dict.fromkeys(self.clickType, False)
        self.clickType[act.text()] = True

        if self.clickType["Dragging"]:
            self.axialImageLabel.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.sagittalImageLabel.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
            self.coronalImageLabel.setDragMode(QGraphicsView.DragMode.ScrollHandDrag)
        else:
            self.axialImageLabel.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.sagittalImageLabel.setDragMode(QGraphicsView.DragMode.NoDrag)
            self.coronalImageLabel.setDragMode(QGraphicsView.DragMode.NoDrag)

        if self.clickType["Erasing"]:
            self.erasingOrDrawing = -1
        elif self.clickType["Drawing"]:
            self.erasingOrDrawing = 1

    def changeDrawingSize(self, act):

        if act.text() == "1x1":
            self.axialImageScene.drawingSize = 1
            self.axialImageScene.drawingHigh = 1
            self.axialImageScene.drawingLow = 0
        elif act.text() == "3x3":
            self.axialImageScene.drawingSize = 3
            self.axialImageScene.drawingHigh = 2
            self.axialImageScene.drawingLow = 1
        elif act.text() == "5x5":
            self.axialImageScene.drawingSize = 5
            self.axialImageScene.drawingHigh = 3
            self.axialImageScene.drawingLow = 2
        elif act.text() == "7x7":
            self.axialImageScene.drawingSize = 7
            self.axialImageScene.drawingHigh = 4
            self.axialImageScene.drawingLow = 3
        if self.agDrawShape.actions()[0].isChecked():
            self.axialImageScene.drawingShape = circles[str(self.axialImageScene.drawingSize)]
        else:
            self.axialImageScene.drawingShape = squares[str(self.axialImageScene.drawingSize)]

    def changeDrawingShape(self, act):

        if act.text().lower() == "circle":
            self.axialImageScene.drawingShape = circles[str(self.axialImageScene.drawingSize)]
        else:
            self.axialImageScene.drawingShape = squares[str(self.axialImageScene.drawingSize)]

    def changeDrawnLabel(self, labelName, row):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        labelAmount = len(self.currentMaskStack)
        if labelAmount == 0:
            self.statusbar.showMessage("No labels!")
        else:
            for oldRow in range(self.labelTable.rowCount()):
                if self.labelTable.item(oldRow, 0).text() == self.drawnMaskType:
                    self.labelTable.item(oldRow, 0).setBackground(QColor(255, 255, 255))
            self.drawnMaskType = labelName
            self.axialImageScene.drawnMaskType = labelName
            self.labelTable.item(row, 0).setBackground((QColor(0, 0, 255, 80)))
        QApplication.restoreOverrideCursor()

    def changeZoom(self, act):

        self.imageScale = float(act.text())
        self.scaleChanged = True
        self.updateImages()
        self.scaleChanged = False

    def changeFlip(self, act):

        if self.currentDICOMStack is None:
            pass
        else:
            self.flip[act.text()] = True
        self.updateImages()
        self.flip = {"Axial": False, "Coronal": False, "Sagittal": False}

    def addLabel(self):

        addLabelDialog = AddLabelDialog(parent=self)
        if addLabelDialog.exec():
            try:
                label = addLabelDialog.setLabelName.text().lower()
                red = int(addLabelDialog.setRedValue.text())
                green = int(addLabelDialog.setGreenValue.text())
                blue = int(addLabelDialog.setBlueValue.text())
                if label == "":
                    raise ValueError
                elif label in self.currentMaskStack.keys():
                    raise NameError
                if red > 255:
                    red = 255
                if green > 255:
                    green = 255
                if blue > 255:
                    blue = 255
            except ValueError:
                self.statusbar.showMessage("Invalid value!")
            except NameError:
                self.statusbar.showMessage("Label name already taken!")
            else:
                self.maskColors[label] = [red, green, blue]
                if self.currentDICOMStack is None:
                    self.currentMaskStack[label] = None
                    self.axialImageScene.mask[label] = None
                else:
                    self.currentMaskStack[label] = np.zeros(self.currentDICOMStack.shape)
                    self.axialImageScene.createMask(label)
                rowPosition = self.labelTable.rowCount()
                self.modelClasses[label] = rowPosition
                self.labelTable.insertRow(rowPosition)
                self.labelTable.setItem(rowPosition, 0, QTableWidgetItem(label))
                self.labelTable.setItem(rowPosition, 1, QTableWidgetItem(str(rowPosition)))
                self.labelTable.setItem(rowPosition, 2, QTableWidgetItem(""))
                self.labelTable.item(rowPosition, 2).setBackground(QColor(red, green, blue))

    def removeLabel(self, labelName, row):

        mb = QMessageBox()
        text = "Are you sure you want to remove label \"" + labelName + "\"?"
        yesNo = mb.question(self, '', text, QMessageBox.StandardButton.Yes, QMessageBox.StandardButton.No)
        if yesNo is QMessageBox.StandardButton.Yes:
            self.labelTable.removeRow(row)
            for i in range(self.labelTable.rowCount()):
                self.labelTable.item(i, 1).setText("")
            self.maskColors.pop(labelName)
            self.currentMaskStack.pop(labelName)
            self.axialImageScene.mask.pop(labelName)
            self.modelClasses.pop(labelName)
            if self.drawnMaskType == labelName:
                self.drawnMaskType = None
                self.axialImageScene.drawnMaskType = None
            self.updateImages()
            self.labelTable.resizeRowsToContents()
            self.labelTable.verticalHeader().setSectionResizeMode(QHeaderView.ResizeMode.Stretch)

    def resetLabelColor(self, labelName, rowPosition):

        resetLabelColor = ResetLabelColorDialog(parent=self)
        if resetLabelColor.exec():
            red = int(resetLabelColor.setRedValue.text())
            green = int(resetLabelColor.setGreenValue.text())
            blue = int(resetLabelColor.setBlueValue.text())
            if red > 255:
                red = 255
            if green > 255:
                green = 255
            if blue > 255:
                blue = 255
            self.maskColors[labelName] = [red, green, blue]
            self.labelTable.item(rowPosition, 2).setBackground(QColor(red, green, blue))
            self.updateImages()

    def selectExam(self):

        annotableAmount = len(self.annotableFolders)
        if annotableAmount == 0:
            self.statusbar.showMessage("Invalid amount of exams!")
        else:
            selectExamDialog = SelectExamDialog(parent=self)
            if selectExamDialog.exec():
                try:
                    index = int(selectExamDialog.setIndexValue.text())
                    if index >= annotableAmount or index < 0:
                        self.statusbar.showMessage("Invalid number!")
                    else:
                        self.annotableIndex = index
                        self.changeAnnotable(True)
                except ValueError:
                    self.statusbar.showMessage("Invalid number!")

    def setClasses(self):

        labelAmount = len(self.currentMaskStack)
        if labelAmount == 0:
            self.statusbar.showMessage("No labels!")
        else:
            setClassesDialog = SetClassesDialog(parent=self)
            if setClassesDialog.exec():
                segmentationClasses = setClassesDialog.segmentationClasses
                num = list(range(len(segmentationClasses)))
                classList = []
                try:
                    for i in segmentationClasses:
                        classList.append(int(i.text()))
                    if set(classList) != set(num):
                        self.statusbar.showMessage("Invalid classes!")
                    else:
                        for k, v in self.currentMaskStack.items():
                            self.modelClasses[k] = None
                        for j, maskType in enumerate(self.modelClasses):
                            self.modelClasses[maskType] = int(segmentationClasses[j].text())
                            if maskType == self.labelTable.item(j, 0).text():
                                self.labelTable.item(j, 1).setText(segmentationClasses[j].text())
                except ValueError:
                    self.statusbar.showMessage("Empty value in classes!")

    def getDICOMFolder(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.DICOMFolderPath = QFileDialog.getExistingDirectory(self, 'Choose DICOM folder', directory=self.defaultDirectory)
        except ValueError:
            pass
        else:
            if not self.DICOMFolderPath or self.DICOMFolderPath is None:
                pass
            else:
                self.currentPatientID = Path(self.DICOMFolderPath).name
                self.dicoms = sorted(list(Path(self.DICOMFolderPath).rglob("*.dcm")))
                if len(self.dicoms) > 1500 or len(self.dicoms) == 0:
                    self.dicoms = sorted(list(Path(self.DICOMFolderPath).rglob("*")))
                    if len(self.dicoms) > 1500 or len(self.dicoms) == 0:
                        self.statusbar.showMessage("Invalid folder (too many DICOMs (> 1500) or no DICOMs found)")
                    else:
                        labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                        self.currentDICOMPathLabel.setText(labelText)
                        self.axialSlider.setRange(0, len(self.dicoms) - 1)
                        self.currentDICOMStack = None
                        self.currentMaskStack = reset_mask_stack(self.currentMaskStack)
                        self.currentStudyID = None
                        validFolder = self.showImages()
                        if validFolder == 0:
                            self.DICOMFolderPath = "None"
                            labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                            self.currentDICOMPathLabel.setText(labelText)
                        self.annotableFolders = []
                        self.annotableDirectory = None
                        self.annotableIndex = 0
                        self.selectExamAct.setVisible(False)
                else:
                    labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                    self.currentDICOMPathLabel.setText(labelText)
                    self.axialSlider.setRange(0, len(self.dicoms) - 1)
                    self.currentDICOMStack = None
                    self.currentMaskStack = reset_mask_stack(self.currentMaskStack)
                    self.currentStudyID = None
                    validFolder = self.showImages()
                    if validFolder == 0:
                        self.DICOMFolderPath = "None"
                        labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                        self.currentDICOMPathLabel.setText(labelText)
                    self.annotableFolders = []
                    self.annotableDirectory = None
                    self.annotableIndex = 0
                    self.selectExamAct.setVisible(False)
        QApplication.restoreOverrideCursor()

    def getSegmentationModelFolder(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.segmentationModelFolderPath = QFileDialog.getExistingDirectory(self, 'Choose segmentation model folder', directory=self.defaultDirectory)
        except ValueError:
            pass
        else:
            if not self.segmentationModelFolderPath or self.segmentationModelFolderPath is None:
                pass
            else:
                self.segmentationModelPath = list(Path(self.segmentationModelFolderPath).glob("*.p"))
                if len(self.segmentationModelPath) == 0:
                    self.segmentationModelPath = list(Path(self.segmentationModelFolderPath).glob("*.pth"))
                if len(self.segmentationModelPath) == 0:
                    self.statusbar.showMessage("No model(s) found")
                    self.segmentationModelPath = None
                try:
                    if len(self.segmentationModelPath) > 0:
                        labelText = f"Segmentation model folder: {str(Path(self.segmentationModelFolderPath).name)}"
                        self.currentSegmentationModelPathLabel.setText(labelText)
                        self.segmentationModelType = str(Path(self.segmentationModelFolderPath).parents[0].name).lower()
                        self.doSegmentationButton.show()
                        self.setMinSegmentationSlider.show()
                        self.setMaxSegmentationSlider.show()
                        self.segmentationIndexLabel.setText(f"Slices to segment: {self.setMinSegmentationSlider.value()} - {self.setMaxSegmentationSlider.value()}")
                        self.segmentationIndexLabel.show()
                except TypeError:
                    self.statusbar.showMessage("No model(s) found")
        QApplication.restoreOverrideCursor()

    def getSaveFolder(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            self.saveDirectory = QFileDialog.getExistingDirectory(self, 'Choose save folder', directory=self.defaultDirectory)
        except ValueError:
            self.saveDirectory = None
        else:
            labelText = f"Save folder: {str(self.saveDirectory)}"
            self.currentSavePathLabel.setText(labelText)
        QApplication.restoreOverrideCursor()

    def getAnnotableFolder(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            if self.saveDirectory is None:
                self.statusbar.showMessage("Select save folder before annotating!")
            else:
                self.annotableDirectory = QFileDialog.getExistingDirectory(self, 'Choose folder to annotate', directory=self.defaultDirectory)
        except ValueError:
            pass
        else:
            if not self.annotableDirectory or self.annotableDirectory is None:
                pass
            else:
                self.annotableFolders = sorted(os.listdir(self.annotableDirectory))
                if len(self.annotableFolders) == 0:
                    self.statusbar.showMessage("Folder is empty!")
                    self.annotableFolders = []
                else:
                    self.annotableIndex = 0
                    self.DICOMFolderPath = Path(self.annotableDirectory) / self.annotableFolders[self.annotableIndex]
                    self.currentPatientID = Path(self.DICOMFolderPath).name
                    self.dicoms = sorted(list(Path(self.DICOMFolderPath).rglob("*.dcm")))
                    if len(self.dicoms) > 1500 or len(self.dicoms) == 0:
                        self.dicoms = sorted(list(Path(self.DICOMFolderPath).rglob("*")))
                        if len(self.dicoms) > 1500 or len(self.dicoms) == 0:
                            self.statusbar.showMessage("Invalid folder (too many DICOMs (> 1500) or no DICOMs found)")
                        else:
                            labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                            self.currentDICOMPathLabel.setText(labelText)
                            self.axialSlider.setRange(0, len(self.dicoms) - 1)
                            self.currentDICOMStack = None
                            self.currentMaskStack = reset_mask_stack(self.currentMaskStack)
                            self.currentStudyID = None
                            validFolder = self.showImages()
                            if validFolder == 0:
                                self.DICOMFolderPath = "None"
                                self.annotableDirectory = None
                                self.annotableFolders = []
                                labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                                self.currentDICOMPathLabel.setText(labelText)
                            elif self.saveDirectory is not None:
                                self.loadAnnotations()
                                self.selectExamAct.setVisible(True)
                            else:
                                self.selectExamAct.setVisible(True)
                    else:
                        labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                        self.currentDICOMPathLabel.setText(labelText)
                        self.axialSlider.setRange(0, len(self.dicoms) - 1)
                        self.currentDICOMStack = None
                        self.currentMaskStack = reset_mask_stack(self.currentMaskStack)
                        self.currentStudyID = None
                        validFolder = self.showImages()
                        if validFolder == 0:
                            self.DICOMFolderPath = "None"
                            self.annotableDirectory = None
                            self.annotableFolders = []
                            labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                            self.currentDICOMPathLabel.setText(labelText)
                        elif self.saveDirectory is not None:
                            self.loadAnnotations()
                            self.selectExamAct.setVisible(True)
                        else:
                            self.selectExamAct.setVisible(True)
        QApplication.restoreOverrideCursor()

    def changeAnnotable(self, save=True):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        if save:
            self.saveAnnotations()
        self.DICOMFolderPath = Path(self.annotableDirectory) / self.annotableFolders[self.annotableIndex]
        self.currentPatientID = Path(self.DICOMFolderPath).name
        self.dicoms = sorted(list(Path(self.DICOMFolderPath).rglob("*.dcm")))
        if len(self.dicoms) > 1500 or len(self.dicoms) == 0:
            self.dicoms = sorted(list(Path(self.DICOMFolderPath).rglob("*")))
            if len(self.dicoms) > 1500 or len(self.dicoms) == 0:
                self.statusbar.showMessage("Invalid folder (too many DICOMs (> 1500) or no DICOMs found)")
            else:
                self.axialSlider.setRange(0, len(self.dicoms) - 1)
                self.currentDICOMStack = None
                self.currentMaskStack = reset_mask_stack(self.currentMaskStack)
                self.currentStudyID = None
                validFolder = self.showImages()
                if validFolder == 0:
                    self.annotableIndex += 1
                    if self.annotableIndex >= len(self.annotableFolders):
                        self.annotableIndex = 0
                        self.statusbar.showMessage("Last annotable folder was invalid, switching to first folder")
                    else:
                        self.statusbar.showMessage("Invalid folder in annotables, switching to next folder")
                    self.changeAnnotable(save=False)
                else:
                    self.loadAnnotations()
                    labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                    self.currentDICOMPathLabel.setText(labelText)
        else:
            self.axialSlider.setRange(0, len(self.dicoms) - 1)
            self.currentDICOMStack = None
            self.currentMaskStack = reset_mask_stack(self.currentMaskStack)
            self.currentStudyID = None
            validFolder = self.showImages()
            if validFolder == 0:
                self.annotableIndex += 1
                if self.annotableIndex >= len(self.annotableFolders):
                    self.annotableIndex = 0
                    self.statusbar.showMessage("Last annotable folder was invalid, switching to first folder")
                else:
                    self.statusbar.showMessage("Invalid folder in annotables, switching to next folder")
                self.changeAnnotable(save=False)
            else:
                self.loadAnnotations()
                labelText = f"DICOM folder: {str(Path(self.DICOMFolderPath))}"
                self.currentDICOMPathLabel.setText(labelText)
        QApplication.restoreOverrideCursor()

    def saveMasks(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        for maskType, mask in self.currentMaskStack.items():
            if self.currentMaskStack[maskType] is not None and self.currentStudyID is not None and self.saveDirectory is not None:
                self.progressBar.show()
                study_id = Path(self.DICOMFolderPath).name
                save_dir = Path(self.saveDirectory)
                os.makedirs(save_dir / study_id / maskType, exist_ok=True)
                if self.segmentationModelPath is not None:
                    model_name = self.segmentationModelPath[0].parent.name
                    os.makedirs(save_dir / study_id / maskType / model_name, exist_ok=True)
                mask_stack = self.currentMaskStack[maskType].copy()
                if self.removeOutliers:
                    mask_stack = remove_outliers(mask_stack)
                elif mask_stack.max() == 1:
                    mask_stack = mask_stack.astype("uint8")
                    mask_stack = mask_stack * 255
                for slice_num, slice in enumerate(mask_stack):
                    mask_filename = study_id + "_" + str(slice_num) + ".png"
                    if self.segmentationModelPath is not None:
                        mask_save_path = save_dir / study_id / maskType / model_name / mask_filename
                    else:
                        mask_save_path = save_dir / study_id / maskType / mask_filename
                    cv2.imwrite(str(mask_save_path), slice)
                    self.progressBar.setValue(int(slice_num * (100 / len(mask_stack))))
                self.statusbar.showMessage("Saving complete")
            elif self.currentStudyID is None:
                self.statusbar.showMessage("Select DICOMs before saving!")
            elif self.currentMaskStack[maskType] is None:
                self.statusbar.showMessage("No masks of this type!")
            elif self.saveDirectory is None:
                self.statusbar.showMessage("Select save folder before saving!")
            else:
                pass
        self.progressBar.hide()
        QApplication.restoreOverrideCursor()

    def loadMasks(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        if self.currentStudyID is not None:
            if len(self.currentMaskStack) != 0:
                try:
                    loadDirectory = QFileDialog.getExistingDirectory(self, 'Choose load folder', directory=self.defaultDirectory)
                except ValueError:
                    pass
                else:
                    for maskType in self.currentMaskStack:
                        maskDirectory = Path(loadDirectory) / maskType
                        if os.path.isdir(maskDirectory):
                            maskList = list(maskDirectory.glob("*.png"))
                            masks = sorted(maskList, key=lambda i: int(os.path.splitext(os.path.basename(i).split("_")[-1])[0]))
                            if len(masks) != len(self.dicoms):
                                self.statusbar.showMessage("Invalid number of masks in directory!")
                            else:
                                self.progressBar.show()
                                maskStack = np.zeros(self.currentDICOMStack.shape)
                                for i, mask_path in enumerate(masks):
                                    mask = cv2.imread(str(mask_path), 0)
                                    maskStack[i, :, :] = mask
                                    self.progressBar.setValue(int(i * (100 / len(maskStack))))
                                self.progressBar.setValue(100)
                                if self.removeOutliers:
                                    maskStack = remove_outliers(maskStack)
                                self.currentMaskStack[maskType] = maskStack
                                self.axialImageScene.createMask(maskType)
                                self.updateImages()
                                self.axialImageScene.maskShown = True
                                self.statusbar.showMessage("Loading complete")
                                self.progressBar.hide()
            else:
                self.statusbar.showMessage("Add labels!")
        else:
            self.statusbar.showMessage("Select DICOMs!")
        QApplication.restoreOverrideCursor()

    def saveLabels(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        if self.saveDirectory is None:
            self.statusbar.showMessage("Select save folder before saving!")
        else:
            if len(self.currentMaskStack) == 0:
                self.statusbar.showMessage("No labels to save!")
            else:
                nameLabelsDialog = NameLabelsDialog(parent=self)
                if nameLabelsDialog.exec():
                    csvName = nameLabelsDialog.setCSVName.text() + ".csv"
                    filename = Path(self.saveDirectory) / csvName
                    if os.path.isfile(filename):
                        self.statusbar.showMessage("This file already exists!")
                    else:
                        labelInfo = []
                        i = 0
                        for k, v in self.currentMaskStack.items():
                            labelName = k
                            labelRed = self.maskColors[labelName][0]
                            labelGreen = self.maskColors[labelName][1]
                            labelBlue = self.maskColors[labelName][2]
                            try:
                                labelClass = self.modelClasses[labelName]
                            except KeyError:
                                labelClass = i
                            labelInfo.append([labelName, labelRed, labelGreen, labelBlue, labelClass])
                            i += 1
                        with open(filename, 'w') as f:
                            csvWriter = csv.writer(f, delimiter=',')
                            csvWriter.writerows(labelInfo)

        QApplication.restoreOverrideCursor()

    def loadLabels(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        try:
            labelFilePath = QFileDialog.getOpenFileName(self, 'Choose label file (csv)', directory=self.defaultDirectory)
        except ValueError:
            pass
        else:
            labelFilePath = Path(labelFilePath[0])
            if ".csv" in labelFilePath.name:
                labelFile = open(labelFilePath)
                reader = csv.reader(labelFile, delimiter=',')
                self.maskColors = {}
                self.modelClasses = {}
                self.currentMaskStack = {}
                self.labelTable.setRowCount(0)
                rowPos = -1
                for row in reader:
                    if len(row) != 5:
                        continue
                    else:
                        rowPos += 1
                        labelName = row[0]
                        labelRed = int(row[1])
                        labelGreen = int(row[2])
                        labelBlue = int(row[3])
                        labelClass = int(row[4])
                        self.maskColors[labelName] = [labelRed, labelGreen, labelBlue]
                        self.modelClasses[labelName] = labelClass
                        self.currentMaskStack[labelName] = None
                        self.labelTable.insertRow(rowPos)
                        self.labelTable.setItem(rowPos, 0, QTableWidgetItem(labelName))
                        self.labelTable.setItem(rowPos, 1, QTableWidgetItem(str(labelClass)))
                        self.labelTable.setItem(rowPos, 2, QTableWidgetItem(""))
                        self.labelTable.item(rowPos, 2).setBackground(QColor(labelRed, labelGreen, labelBlue))
                if self.currentDICOMStack is not None:
                    for maskType in self.currentMaskStack:
                        self.currentMaskStack[maskType] = np.zeros(self.currentDICOMStack.shape)
                        self.axialImageScene.createMask(maskType)
                    self.updateImages()
            else:
                self.statusbar.showMessage("Select a csv file!")
        QApplication.restoreOverrideCursor()

    def saveAnnotations(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        if not any(value is None for value in self.currentMaskStack.values()) and self.currentStudyID is not None and self.saveDirectory is not None:
            self.progressBar.show()
            study_id = Path(self.DICOMFolderPath).name
            save_dir = Path(self.saveDirectory)
            os.makedirs(save_dir / "images", exist_ok=True)
            progress_value = 0
            max_progress_value = len(list(self.currentMaskStack)) * self.currentDICOMStack.shape[0]
            image_stack = self.currentDICOMStack.copy()
            if any(value.isChecked() is True for value in self.agFlip.actions()) and self.saveImages and self.saveFlipped:
                for slice_num, image in enumerate(image_stack):
                    filename = study_id + "_" + str(slice_num) + ".png"
                    image_dir_flip = save_dir / "images_flipped"
                    image_save_path = image_dir_flip / filename
                    os.makedirs(image_dir_flip, exist_ok=True)
                    image_slice = image_stack[slice_num, :, :]
                    cv2.imwrite(str(image_save_path), image_slice)
            if self.agFlip.actions()[0].isChecked():
                image_stack = np.flip(image_stack, 0)
            if self.agFlip.actions()[1].isChecked():
                image_stack = np.flip(image_stack, 1)
            if self.agFlip.actions()[2].isChecked():
                image_stack = np.flip(image_stack, 2)
            if self.saveImages:
                for slice_num, image in enumerate(image_stack):
                    filename = study_id + "_" + str(slice_num) + ".png"
                    image_save_path = save_dir / "images" / filename
                    image_slice = image_stack[slice_num, :, :]
                    cv2.imwrite(str(image_save_path), image_slice)
            for i, maskType in enumerate(list(self.currentMaskStack)):
                mask_dir = maskType.lower() + "_masks"
                os.makedirs(save_dir / mask_dir, exist_ok=True)
                current_mask_stack = self.currentMaskStack[maskType].copy()
                if self.removeOutliers:
                    current_mask_stack = remove_outliers(current_mask_stack)
                elif current_mask_stack.max() == 1:
                    current_mask_stack = current_mask_stack.astype("uint8")
                    current_mask_stack = current_mask_stack * 255
                if any(value.isChecked() is True for value in self.agFlip.actions()) and self.saveFlipped:
                    for slice_num, current_mask_slice in enumerate(current_mask_stack):
                        mask_dir_flip = mask_dir + "_flipped"
                        os.makedirs(save_dir / mask_dir_flip, exist_ok=True)
                        filename = study_id + "_" + str(slice_num) + ".png"
                        current_mask_save_path = save_dir / mask_dir_flip / filename
                        cv2.imwrite(str(current_mask_save_path), current_mask_slice)
                if self.agFlip.actions()[0].isChecked():
                    current_mask_stack = np.flip(current_mask_stack, 0)
                if self.agFlip.actions()[1].isChecked():
                    current_mask_stack = np.flip(current_mask_stack, 1)
                if self.agFlip.actions()[2].isChecked():
                    current_mask_stack = np.flip(current_mask_stack, 2)
                for slice_num, current_mask_slice in enumerate(current_mask_stack):
                    filename = study_id + "_" + str(slice_num) + ".png"
                    current_mask_save_path = save_dir / mask_dir / filename
                    cv2.imwrite(str(current_mask_save_path), current_mask_slice)
                    progress_value += 1
                    self.progressBar.setValue(int(progress_value * (100 / max_progress_value)))
            self.statusbar.showMessage("Saving complete")
        elif self.currentStudyID is None:
            self.statusbar.showMessage("Select DICOMs before saving!")
        elif self.currentMaskStack is None:
            self.statusbar.showMessage("Do segmentation before saving!")
        elif self.saveDirectory is None:
            self.statusbar.showMessage("Select save folder before saving!")
        else:
            pass
        self.progressBar.hide()
        QApplication.restoreOverrideCursor()

    def loadAnnotations(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        if self.currentStudyID is not None and self.saveDirectory is not None:
            for maskType in self.currentMaskStack:
                self.progressBar.show()
                studyID = Path(self.DICOMFolderPath).name
                saveDirectory = Path(self.saveDirectory)
                currentMasks = maskType.lower() + "_masks"
                loadDirectory = saveDirectory / currentMasks
                if os.path.isdir(loadDirectory):
                    mask_list_orig = list((Path(loadDirectory).rglob("*.png")))
                    mask_list = []
                    for mask in mask_list_orig:
                        if studyID in str(mask):
                            mask_list.append(mask)
                    masks = sorted(mask_list, key=lambda i: int(os.path.splitext(os.path.basename(i).split("_")[-1])[0]))
                    if len(masks) != len(self.dicoms):
                        pass
                    else:
                        self.progressBar.show()
                        mask_stack = np.zeros(self.currentDICOMStack.shape)
                        for i, mask_path in enumerate(masks):
                            mask = cv2.imread(str(mask_path), 0)
                            mask_stack[i, :, :] = mask
                            self.progressBar.setValue(int(i * (100 / len(mask_stack))))
                        if self.agFlip.actions()[0].isChecked():
                            mask_stack = np.flip(mask_stack, 0)
                        if self.agFlip.actions()[1].isChecked():
                            mask_stack = np.flip(mask_stack, 1)
                        if self.agFlip.actions()[2].isChecked():
                            mask_stack = np.flip(mask_stack, 2)
                        self.progressBar.setValue(100)
                        if self.removeOutliers:
                            mask_stack = remove_outliers(mask_stack)
                        self.currentMaskStack[maskType] = mask_stack
                        self.axialImageScene.createMask(maskType)
                        self.updateImages()
                        self.axialImageScene.maskShown = True
                        if self.setOpacitySlider.isHidden():
                            self.setOpacitySlider.show()
            self.statusbar.showMessage("Loading complete")
            self.progressBar.hide()
        elif self.saveDirectory is None:
            self.statusbar.showMessage("Select save folder before loading!")
        else:
            pass
        self.progressBar.hide()
        QApplication.restoreOverrideCursor()

    def showOrHide(self, act):
        if act.text() == "Axial":
            if self.axialImageLabel.isHidden():
                self.axialImageLabel.show()
                self.axialSlider.show()
                self.axialIndexLabel.show()
            else:
                self.axialImageLabel.hide()
                self.axialSlider.hide()
                self.axialIndexLabel.hide()

        elif act.text() == "Coronal":
            if self.coronalImageLabel.isHidden():
                self.coronalImageLabel.show()
                self.coronalSlider.show()
                self.coronalIndexLabel.show()
                if self.currentDICOMStack is not None:
                    self.coronalImageLabel.setMinimumWidth(540)
            else:
                self.coronalImageLabel.hide()
                self.coronalSlider.hide()
                self.coronalIndexLabel.hide()
                self.coronalImageLabel.setMinimumWidth(1)

        elif act.text() == "Sagittal":
            if self.sagittalImageLabel.isHidden():
                self.sagittalImageLabel.show()
                self.sagittalSlider.show()
                self.sagittalIndexLabel.show()
                if self.currentDICOMStack is not None:
                    self.sagittalImageLabel.setMinimumWidth(540)
            else:
                self.sagittalImageLabel.hide()
                self.sagittalSlider.hide()
                self.sagittalIndexLabel.hide()
                self.sagittalImageLabel.setMinimumWidth(1)

        elif act.text() == "Masks" and self.showMasks:
            self.showMasks = False
            self.setOpacitySlider.hide()
            self.updateImages()

        elif act.text() == "Masks" and not self.showMasks:
            self.showMasks = True
            self.setOpacitySlider.show()
            self.updateImages()

    def showImages(self, imagesChanged=True):

        if self.dicoms and self.currentDICOMStack is None:
            self.progressBar.show()
            try:
                for i, dicomPath in enumerate(self.dicoms):
                    try:
                        ds = dcmread(dicomPath)
                    except pydicom.errors.InvalidDicomError:
                        self.statusbar.showMessage("No DICOMS or invalid DICOMs in folder!")
                        self.progressBar.hide()
                        self.currentDICOMStack = None
                        return 0
                    except IsADirectoryError:
                        self.statusbar.showMessage("Folder contains another folder!")
                        self.progressBar.hide()
                        self.currentDICOMStack = None
                        return 0
                    except PermissionError:
                        self.statusbar.showMessage("Invalid DICOMs in folder or folder contains another folder!")
                        self.progressBar.hide()
                        self.currentDICOMStack = None
                        return 0
                    try:
                        self.currentStudyID = ds.StudyID
                    except AttributeError:
                        self.currentStudyID = 0
                    out = adjust_image(ds, self.dicomWindowCenter, self.dicomWindowWidth)
                    if i == 0:
                        self.currentDICOMStack = np.zeros((len(self.dicoms), out.shape[0], out.shape[1]))
                    self.currentDICOMStack[i, :, :] = out.astype(np.uint16)
                    self.progressBar.setValue(int(i * (100 / len(self.dicoms))))
            except ValueError:
                self.statusbar.showMessage("Invalid DICOMs (wrong shape)!")
                self.progressBar.hide()
                return 0
            self.axialImageLabel.setMinimumWidth(540)
            self.coronalImageLabel.setMinimumWidth(540)
            self.sagittalImageLabel.setMinimumWidth(540)
            self.axialImageLabel.setMinimumHeight(540)
            if imagesChanged:
                self.axialDICOMIndex = 0
                self.coronalDICOMIndex = 0
                self.sagittalDICOMIndex = 0
                self.axialSlider.setValue(0)
                self.coronalSlider.setValue(0)
                self.sagittalSlider.setValue(0)
            self.currentDICOMStack = self.currentDICOMStack.astype(np.uint16)
            if self.agFlip.actions()[0].isChecked():
                self.currentDICOMStack = np.flip(self.currentDICOMStack, 0)
            if self.agFlip.actions()[1].isChecked():
                self.currentDICOMStack = np.flip(self.currentDICOMStack, 1)
            if self.agFlip.actions()[2].isChecked():
                self.currentDICOMStack = np.flip(self.currentDICOMStack, 2)
            axialImage = self.currentDICOMStack[self.axialDICOMIndex, :, :].copy()
            coronalImage = self.currentDICOMStack[:, self.coronalDICOMIndex, :].copy()
            sagittalImage = self.currentDICOMStack[:, :, self.sagittalDICOMIndex].copy()

            h, w = axialImage.shape
            self.axialImageQt = QImage(axialImage, w, h, w * 2, QImage.Format.Format_Grayscale16)
            self.axialImageQt = QPixmap.fromImage(self.axialImageQt)
            self.axialImageScene.clear()
            self.axialImageScene.addPixmap(self.axialImageQt)

            h, w = coronalImage.shape
            coronalImageQt = QImage(coronalImage, w, h, w * 2, QImage.Format.Format_Grayscale16)
            coronalImageQt = QPixmap.fromImage(coronalImageQt)
            self.coronalImageScene.clear()
            self.coronalImageScene.addPixmap(coronalImageQt)

            h, w = sagittalImage.shape
            sagittalImageQt = QImage(sagittalImage, w, h, w * 2, QImage.Format.Format_Grayscale16)
            sagittalImageQt = QPixmap.fromImage(sagittalImageQt)
            self.sagittalImageScene.clear()
            self.sagittalImageScene.addPixmap(sagittalImageQt)

            try:
                self.currentPatientIDLabel.setText(f"Patient ID: {ds.PatientID}")
            except AttributeError:
                self.currentPatientIDLabel.setText(f"Patient ID: None")

            self.axialIndexLabel.setText(f"{self.axialDICOMIndex} / {len(self.dicoms) - 1}")
            self.coronalIndexLabel.setText(f"{self.coronalDICOMIndex} / {axialImage.shape[0] - 1}")
            self.sagittalIndexLabel.setText(f"{self.sagittalDICOMIndex} / {axialImage.shape[1] - 1}")
            self.coronalSlider.setRange(0, axialImage.shape[0] - 1)
            self.sagittalSlider.setRange(0, axialImage.shape[1] - 1)
            for maskType in self.currentMaskStack:
                if self.currentMaskStack[maskType] is None:
                    self.currentMaskStack[maskType] = np.zeros(self.currentDICOMStack.shape)
                    self.axialImageScene.createMask(maskType)

            if self.axialImageLabel.isVisible():
                self.axialSlider.show()
            if self.coronalImageLabel.isVisible():
                self.coronalSlider.show()
            if self.sagittalImageLabel.isVisible():
                self.sagittalSlider.show()
            if self.showMasks:
                self.setOpacitySlider.show()

            self.setMinSegmentationSlider.setRange(0, len(self.dicoms) - 1)
            self.setMaxSegmentationSlider.setRange(0, len(self.dicoms) - 1)
            self.setMinSegmentationSlider.setValue(0)
            self.setMaxSegmentationSlider.setValue(len(self.dicoms) - 1)
            if self.scaleChanged:
                self.axialImageLabel.resetTransform()
                self.coronalImageLabel.resetTransform()
                self.sagittalImageLabel.resetTransform()
                self.axialImageLabel.scale(self.imageScale, self.imageScale)
                self.coronalImageLabel.scale(self.imageScale, self.imageScale)
                self.sagittalImageLabel.scale(self.imageScale, self.imageScale)
            self.removeOutliersButton.show()
            self.fillContoursButton.show()
            self.progressBar.setValue(100)

        self.progressBar.hide()
        return 1

    def updateImages(self):

        if self.dicoms and self.currentDICOMStack is not None:
            if any(self.flip.values()):
                if self.flip["Axial"]:
                    self.currentDICOMStack = np.flip(self.currentDICOMStack, 0)
                if self.flip["Coronal"]:
                    self.currentDICOMStack = np.flip(self.currentDICOMStack, 1)
                if self.flip["Sagittal"]:
                    self.currentDICOMStack = np.flip(self.currentDICOMStack, 2)
                for maskType, mask in self.currentMaskStack.items():
                    if self.currentMaskStack[maskType] is not None:
                        if self.flip["Axial"]:
                            self.currentMaskStack[maskType] = np.flip(self.currentMaskStack[maskType], 0)
                        if self.flip["Coronal"]:
                            self.currentMaskStack[maskType] = np.flip(self.currentMaskStack[maskType], 1)
                        if self.flip["Sagittal"]:
                            self.currentMaskStack[maskType] = np.flip(self.currentMaskStack[maskType], 2)

            self.updateSingleImage("axial")
            self.updateSingleImage("coronal")
            self.updateSingleImage("sagittal")

            if self.scaleChanged:
                self.axialImageLabel.resetTransform()
                self.coronalImageLabel.resetTransform()
                self.sagittalImageLabel.resetTransform()
                self.axialImageLabel.scale(self.imageScale, self.imageScale)
                self.coronalImageLabel.scale(self.imageScale, self.imageScale)
                self.sagittalImageLabel.scale(self.imageScale, self.imageScale)

        self.statusbar.showMessage("")

    def updateSingleImage(self, imageType):

        if self.dicoms and self.currentDICOMStack is not None:
            if imageType == "axial":
                try:
                    image = self.currentDICOMStack[self.axialDICOMIndex, :, :].copy()
                except (ValueError, IndexError):
                    self.axialDICOMIndex = 0
                    image = self.currentDICOMStack[self.axialDICOMIndex, :, :].copy()
                h, w = image.shape
                self.axialImageQt = QImage(image, w, h, w * 2, QImage.Format.Format_Grayscale16)
                self.axialImageQt = QPixmap.fromImage(self.axialImageQt)
                self.axialImageScene.clear()
                self.axialImageScene.addPixmap(self.axialImageQt)
                self.axialIndexLabel.setText(f"{self.axialDICOMIndex} / {len(self.dicoms) - 1}")
                combination = QPixmap(w, h)
                combination.fill(Qt.GlobalColor.transparent)
                p = QPainter(combination)
                p.drawPixmap(0, 0, w, h, self.axialImageQt)
            elif imageType == "coronal":
                try:
                    image = self.currentDICOMStack[:, self.coronalDICOMIndex, :].copy()
                except (ValueError, IndexError):
                    self.coronalDICOMIndex = 0
                    image = self.currentDICOMStack[:, self.coronalDICOMIndex, :].copy()
                h, w = image.shape
                imageQt = QImage(image, w, h, w * 2, QImage.Format.Format_Grayscale16)
                imageQt = QPixmap.fromImage(imageQt)
                self.coronalImageScene.clear()
                self.coronalImageScene.addPixmap(imageQt)
                self.coronalIndexLabel.setText(f"{self.coronalDICOMIndex} / {self.currentDICOMStack.shape[1] - 1}")
                combination = QPixmap(w, h)
                combination.fill(Qt.GlobalColor.transparent)
                p = QPainter(combination)
                p.drawPixmap(0, 0, w, h, imageQt)
            elif imageType == "sagittal":
                try:
                    image = self.currentDICOMStack[:, :, self.sagittalDICOMIndex].copy()
                except (ValueError, IndexError):
                    self.sagittalDICOMIndex = 0
                    image = self.currentDICOMStack[:, :, self.sagittalDICOMIndex].copy()
                h, w = image.shape
                imageQt = QImage(image, w, h, w * 2, QImage.Format.Format_Grayscale16)
                imageQt = QPixmap.fromImage(imageQt)
                self.sagittalImageScene.clear()
                self.sagittalImageScene.addPixmap(imageQt)
                self.sagittalIndexLabel.setText(f"{self.sagittalDICOMIndex} / {self.currentDICOMStack.shape[2] - 1}")
                combination = QPixmap(w, h)
                combination.fill(Qt.GlobalColor.transparent)
                p = QPainter(combination)
                p.drawPixmap(0, 0, w, h, imageQt)
            for maskType in self.currentMaskStack:
                if self.currentMaskStack[maskType] is not None and self.showMasks:
                    try:
                        if imageType == "axial":
                            mask = self.currentMaskStack[maskType][self.axialDICOMIndex, :, :].copy()
                        elif imageType == "coronal":
                            mask = self.currentMaskStack[maskType][:, self.coronalDICOMIndex, :].copy()
                        elif imageType == "sagittal":
                            mask = self.currentMaskStack[maskType][:, :, self.sagittalDICOMIndex].copy()
                    except (ValueError, IndexError):
                        pass
                    else:
                        mask = (np.stack((mask,) * 4, axis=-1) * 255).astype(np.uint8)
                        mask = self.setMaskValues(mask, maskType)
                        h, w, c = mask.shape
                        maskQt = QImage(mask, w, h, c * w, QImage.Format.Format_RGBA8888)
                        maskQt = QPixmap.fromImage(maskQt)
                        p.drawPixmap(0, 0, w, h, maskQt)
            p.end()
            if imageType == "axial":
                self.axialImageScene.clear()
                self.axialImageScene.addPixmap(combination)
            elif imageType == "coronal":
                self.coronalImageScene.clear()
                self.coronalImageScene.addPixmap(combination)
            elif imageType == "sagittal":
                self.sagittalImageScene.clear()
                self.sagittalImageScene.addPixmap(combination)
        self.statusbar.showMessage("")

    def drawMask(self):

        self.axialImageScene.clear()
        self.axialImageScene.addPixmap(self.axialImageQt)
        h, w = self.axialImageQt.height(), self.axialImageQt.width()
        drawnMaskType = self.drawnMaskType
        tempArray = self.currentMaskStack[drawnMaskType][self.axialDICOMIndex, :, :] + (self.axialImageScene.mask[drawnMaskType][self.axialDICOMIndex, :, :] * 255 * self.erasingOrDrawing)
        tempArray[tempArray < 0] = 0
        tempArray[tempArray > 255] = 255
        self.currentMaskStack[drawnMaskType][self.axialDICOMIndex, :, :] = tempArray
        self.axialImageScene.mask[drawnMaskType] = np.zeros(self.axialImageScene.mask[drawnMaskType].shape)
        combinationAxial = QPixmap(w, h)
        combinationAxial.fill(Qt.GlobalColor.transparent)
        p = QPainter(combinationAxial)
        p.drawPixmap(0, 0, w, h, self.axialImageQt)
        for maskType in self.currentMaskStack:
            try:
                axialMask = self.currentMaskStack[maskType][self.axialDICOMIndex, :, :].copy()
            except (ValueError, IndexError):
                pass
            else:
                axialMask = (np.stack((axialMask,) * 4, axis=-1) * 255).astype(np.uint8)
                axialMask = self.setMaskValues(axialMask, maskType)
                h, w, c = axialMask.shape
                axialMaskQt = QImage(axialMask, w, h, c * w, QImage.Format.Format_RGBA8888)
                axialMaskQt = QPixmap.fromImage(axialMaskQt)
                p.drawPixmap(0, 0, w, h, axialMaskQt)
        p.end()
        self.axialImageScene.clear()
        self.axialImageScene.addPixmap(combinationAxial)
        self.statusbar.showMessage("")

    def setMaskValues(self, mask, maskType):

        x = mask[:, :, 0] > 0
        mask[x, 0] = self.maskColors[maskType][0]
        x = mask[:, :, 1] > 0
        mask[x, 1] = self.maskColors[maskType][1]
        x = mask[:, :, 2] > 0
        mask[x, 2] = self.maskColors[maskType][2]
        x = mask[:, :, 3] > 0
        mask[x, 3] = self.maskOpacity

        return mask

    def doSegmentation(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        modelType = self.segmentationModelType
        if modelType is None:
            self.statusbar.showMessage("Select what to segment!")
        elif modelType not in self.currentMaskStack and modelType != "multiple":
            self.statusbar.showMessage("Invalid model type!")
        else:
            models = self.segmentationModelPath
            stack = self.currentDICOMStack
            device = self.device
            indexes = self.indexesToSegment
            if stack is None:
                self.statusbar.showMessage("Select DICOMs")
            elif self.segmentationModelPath is None:
                self.statusbar.showMessage("Select model")
            elif modelType == "multiple":
                classAmount = len(self.modelClasses)
                if len(self.currentMaskStack) != classAmount or classAmount == 0:
                    self.statusbar.showMessage("Wrong number of classes!")
                else:
                    self.progressBar.show()
                    self.statusbar.showMessage(" ")
                    for maskType in self.currentMaskStack:
                        self.axialImageScene.createMask(maskType)
                    try:
                        maskStack = segmentation(models, stack, device, indexes, classAmount, self)
                    except AssertionError:
                        self.statusbar.showMessage("CUDA not found, change device to CPU")
                    except RuntimeError:
                        self.statusbar.showMessage("Wrong model type!")
                    else:
                        if self.removeOutliers:
                            for maskType in self.currentMaskStack:
                                index = self.modelClasses[maskType]
                                maskStack[:, index, :, :] = remove_outliers(maskStack[:, index, :, :])
                        self.progressBar.setValue(100)
                        for maskType in self.currentMaskStack:
                            index = self.modelClasses[maskType]
                            self.currentMaskStack[maskType] = maskStack[:, index, :, :]
                        self.updateImages()
                        self.axialImageScene.maskShown = True

                        self.statusbar.showMessage("Segmentation done")
            else:
                self.progressBar.show()
                self.statusbar.showMessage(" ")
                self.axialImageScene.createMask(modelType)
                try:
                    maskStack = segmentation(models, stack, device, indexes, 1, self)
                except AssertionError:
                    self.statusbar.showMessage("CUDA not found, change device to CPU")
                except RuntimeError:
                    self.statusbar.showMessage("Wrong model type!")
                else:
                    if self.removeOutliers:
                        maskStack = remove_outliers(maskStack)
                    self.progressBar.setValue(100)
                    self.currentMaskStack[modelType] = maskStack
                    self.updateImages()
                    self.axialImageScene.maskShown = True

                    self.statusbar.showMessage("Segmentation done")
            self.progressBar.hide()
        QApplication.restoreOverrideCursor()

    def removeOutliersFunc(self):

        QApplication.setOverrideCursor(Qt.CursorShape.WaitCursor)
        maskType = self.drawnMaskType
        if maskType is not None:
            maskStack = self.currentMaskStack[maskType]
            if maskStack is not None:
                maskStack = remove_outliers(maskStack)
                self.currentMaskStack[maskType] = maskStack
                self.updateImages()
                self.statusbar.showMessage("Outliers removed")
            else:
                self.statusbar.showMessage("No mask to remove outliers from!")
        else:
            self.statusbar.showMessage("Select which label to remove outliers from!")
        QApplication.restoreOverrideCursor()

    def fillContoursFunc(self):

        maskType = self.drawnMaskType
        if maskType is not None:
            maskStack = self.currentMaskStack[maskType]
            if maskStack is not None:
                sliceNum = self.axialDICOMIndex
                mask = maskStack[sliceNum, :, :]
                mask = mask.astype(int)
                seed = np.copy(mask)
                seed[1:-1, 1:-1] = mask.max()
                filled = reconstruction(seed, mask, method='erosion')
                maskStack[sliceNum, :, :] = filled.astype(float)
                self.currentMaskStack[maskType] = maskStack
                self.updateImages()
            else:
                self.statusbar.showMessage("No mask to fill!")
        else:
            self.statusbar.showMessage("Select which label to fill!")


def main():

    app = QApplication(sys.argv)
    dlLabelsCT = DLLabelsCT()
    dlLabelsCT.show()
    sys.exit(app.exec())


if __name__ == '__main__':
    main()
