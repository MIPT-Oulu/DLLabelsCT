# DLLabelsCT

DLLabelsCT (Deep Learning Labels Computed Tomography) is an annotation tool for abdomen CT scans. It can use Pytorch segmentation models to assist in annotating.

## Dependencies

- Python 3.10+
- PyQt6
- Pytorch
- Pydicom
- OpenCV-Python
- Scikit-image

## Using DLLabelsCT

The GUI is divided into three parts: the top left part with the three views of the CT scan (axial, coronal, sagittal), the bottom left part with sliders, buttons and which folders are currently selected. On the right is a "label table", where information about the current labels is shown.
The topmost sliders are used to change between different slices in the scan. The second topmost slider on the right changes masks' opacity. The bottommost sliders on the right determine which slices are segmented by the model. The three buttons can be clicked to remove outliers, fill holes in the masks and to do segmentation with the selected model.

### Using the label table

Labels can be added and removed by right-clicking the table. Labels can be set as the drawn label, shown/hidden, removed (this removes any mask drawn with this label) and the label's color reset. The last right click option, "Set label classes", sets which label is which output class in a multiclass segmentation model.  

### Selecting a segmentation model

DLLabelsCT supports ResNetUNet and ResNetFPN encoder-decoder models for segmentation. The selected model must be in a folder containing the segmented label's name and the model's name (".models/label_name/model_name"). If the model can segment multiple different labels, the folder structure must be ".models/multiple/model_name". The "Label class" value in the label table is used by these models.

### Usage example

1. Select a folder in which the annotation data is saved ("Select save folder...")
2. Create or load the labels used in annotating ("Add label..." / "Load labels...")
3. (When using a segmentation model) Select the model to use for segmentation ("Select segmentation model folder...")
4. (When using a multiclass segmentation model) Set which label corresponds to which class in the models output (if using models with multiple outputs)
5. Select either a single scan (Select DICOM folder...) or a folder containing multiple scans ("Select folder to annotate...")
6. (When using a segmentation model) Press the "Do segmentation" button to use the model to generate masks
7. Annotate the scans by left-clicking and dragging the mouse over the axial view with the "Drawing" option enabled. Brightness and contrast can be adjusted by right-clicking and dragging, dragging left or right to adjust brightness, dragging up or down to adjust contrast. Brightness and contrast are reset when changing slides/exams and images are saved without the brightness/contrast adjustments
8. (Optional) Use the "Remove outliers from masks" button to remove any unwanted objects in the currently selected label (Note: leaves only the largest object in the mask, if the mask is meant to contain multiple objects, do not use this button)
9. If labeling a single exam, use the "File/Save masks" option. If labeling a folder, the annotations are saved when changing exams. The annotations can also be manually saved with "File/Save annotations"

## Options

Menubar options:

- File: Contains file/folder selecting and saving and loading actions
- Show: Show or hide the different views
- Windowing: Change the grayscale values in the scans (HU)
  - Tissue 1 (default): 400 width, 50 center
  - Tissue 2: 250 width, 50 center
  - Tissue 3: 150 width, 30 center
  - Lungs: 1500 width, -600 center
  - Bone: 1800 width, 400 center 
  - Custom: Choose any width and center
- Device: Select which device to use when segmenting with a model
- Options: Change various options
  - Remove outliers after segmentation/when saving: Removes all objects (in 3D) that are not connected to the largest object in the mask when segmenting with a model and when saving (Note: leaves only the largest object in the mask, if the mask is meant to contain multiple objects, do not use this option)
  - Automatically fill holes in masks: Fills holes when drawing
  - Save images when annotating: When annotating a folder, saves the scans axial slices as PNG images
  - Save flipped images when annotating: Saves flipped versions of the images in a separate folder
  - Show DICOMs by filename order: Whether to show DICOMs by filename order (if checked) or by DICOMs' InstanceNumber order (if unchecked)
- Drawing options: Change mouse left click function and shape and size of when drawing labels
  - Selecting: Shows the clicked slice in the other views
  - Drawing: Clicking and dragging draws the currently selected label on the mask
  - Erasing: Clicking and dragging erases the currently selected label from the mask
  - Dragging: Clicking and dragging moves the view
  - NxN: Selects the drawing size
  - Circle/Square: Selects the drawing shape
- Zoom: Zoom in/out of the images
- Flip: Flip the scans along the selected axis
- Change exam...: Select which exam to annotate when annotating folders

## Mouse and keyboard shortcuts

- Z - Hide axial image
- X - Hide coronal image
- C - Hide sagittal image
- V - Hide masks
- Q - Go down one slice
- W - Go up one slice
- E - Mouse left click to "erase" mode
- S - Mouse left click to "select" mode
- D - Mouse left click to "draw" mode
- F - Mouse left click to "drag" mode
- 1 - Draw 1x1 size shapes
- 2 - Draw 3x3 size shapes
- 3 - Draw 5x5 size shapes
- 4 - Draw 7x7 size shapes
- Left arrow - Go to previous scan (when annotating folders)
- Right arrow - Go to next scan (when annotating folders)
- Ctrl + mouse wheel up | numpad plus - Zoom in
- Ctrl + mouse wheel down | numpad minus - Zoom out
- Right-clicking + dragging - Adjust brightness/contrast

## DLLabelsCT with PyInstaller 

DLLabelsCT can be made into an executable with [PyInstaller](https://pyinstaller.org/en/stable/), by using the following code:

```
pyinstaller DLLabelsCT.py --collect-submodules pydicom -w
```

## Licence

This software is published under the GNU General Public License version 3 (GPLv3)

Licenses for third party components are listed in the NOTICE file.

The software has not been certified as a medical device and, therefore, must not be used for diagnostic purposes.

## How to cite

If you found this work useful, consider citing the repository
