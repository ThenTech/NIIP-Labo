# NIIP-Labo 4
> **Bram Kelchtermans, William Thenaers**

## Part 1:

##### Install OpenCV

Make sure the following packages are installed:

```
pip install numpy
pip install opencv-contrib-python
pip install bitarray
```

The following script should now display the OpenCV version (Python 3 example):

```python
import numpy
import cv2
print(f"{cv2.__version__}")  # Prints e.g. 4.3.0
```

[OpenCV ReadTheDocs](https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_tutorials.html)

##### Reading frames from webcam

This uses `cv2.VideoCapture(0)` to get the capture stream.

```python
from webcam import Webcam
cam = Webcam()
cam.capture_start()
cam.capture_loop(Webcam.show_frame)
```

##### Tracking the phone screen

We use the [MOSSE](https://www.cs.colostate.edu/~vision/publications/bolme_cvpr10.pdf) tracker (created with `cv2.TrackerMOSSE_create()`) to track the screen. After pressing `s` a Region of Interest (ROI) can be selected by clicking and dragging and pressing RETURN. This region will now be followed as indicated by the green square.

```python
tracker = cv2.TrackerMOSSE_create()

while True:
	frame = cam.capture_new()
	success, box = tracker.update(frame)
	if success:
		# Use bounding box to crop frame
		# ...
		
		# Process cropped frame
		handle_frame(cropped)
		
def handle_frame(frame):
	# Make grayscale
	# Apply Gaussian blur
	# Apply Binary thresholding with OTSU threshold
	# Send result to callback function in detector
```

##### Detecting bits

A callback function is defined that gets called with the pre-processed cropped frame from the tracker above. The resulting string is displayed on screen and in the console.

```python
def callback(frame):
	# Check white to black ratio in pixels
	# If more withes, append True to buffer else False
	# When certain start bits are received (configurable),
	# slice the buffer to that index and append each following byte
	# to an output stream.
	
	# When an endbyte(s) is received, return the resulting string.
```