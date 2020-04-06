# NIIP-Labo 4
> **Bram Kelchtermans, William Thenaers**

## Part 1: 

##### Install OpenCV

First download the OpenCV binaries from [SourceForge](https://sourceforge.net/projects/opencvlibrary/files/4.3.0/), and extract somewhere.

Add the directory `opencv\build\x64\vc15\bin` to your `PATH` variable (Windows) and copy `opencv\build\python\cv2\python-*\cv2.cp*-win_amd64` with your Python version to `<Python install dir>\Lib\site-packages`. Also make sure NumPy is installed.

The following script should now display the OpenCV version (Python 3 example):

```python
import numpy
import cv2
print(f"{cv2.__version__}")  # Prints e.g. 4.3.0
```

[OpenCV ReadTheDocs](https://opencv-python-tutroals.readthedocs.io/en/latest/py_tutorials/py_tutorials.html)