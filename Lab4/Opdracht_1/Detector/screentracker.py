from webcam import Webcam

from imutils.video import FPS
import cv2
import numpy as np
import time

class ScreenTracker:
    OPENCV_OBJECT_TRACKERS = {
        "csrt"      : cv2.TrackerCSRT_create,
        "kcf"       : cv2.TrackerKCF_create,
        "boosting"  : cv2.TrackerBoosting_create,
        "mil"       : cv2.TrackerMIL_create,
        "tld"       : cv2.TrackerTLD_create,
        "medianflow": cv2.TrackerMedianFlow_create,
        "mosse"     : cv2.TrackerMOSSE_create
    }

    def __init__(self, input_callback=None, tracker="kcf", select_key='s', exit_key='q'):
        super().__init__()

        self.cam          = Webcam(exit_key=exit_key)
        self.tracker      = None
        self.tracker_name = tracker

        self.width, self.height = 0, 0
        self.box = None
        self.fps = FPS()
        self.cropped = None

        self.tracker_init = False

        self._select_key    = select_key
        self.input_callback = input_callback

    def start(self):
        try:
            self.cam.capture_start()
            self.width, self.height = self.cam.width, self.cam.height

            while(True):
                # Capture frame-by-frame
                frame = self.cam.capture_new()

                if frame is not None:
                    self._handle_frame(frame)
                else:
                    break

                self._use_cropped()

                key = cv2.waitKey(1) & 0xFF

                if key == ord(self.cam._exit_key):
                    break
                elif key == ord(self._select_key):
                    self.tracker_init = False
                    self._define_region(frame)
        except KeyboardInterrupt:
            del self.cam

    def _init_tracker(self):
        self.tracker = ScreenTracker.OPENCV_OBJECT_TRACKERS[self.tracker_name]()

    def _define_region(self, frame, title="Select the screen"):
        # Select Region of Interest and start tracker
        initBB = cv2.selectROI(title, frame, fromCenter=False, showCrosshair=True)
        cv2.destroyWindow(title)

        if any(initBB):
            self._init_tracker()
            self.tracker.init(frame, initBB)

            self.fps = FPS().start()
            self.tracker_init = True
            time.sleep(0.1)

    def _handle_frame(self, frame):
        if self.tracker_init:
            # Get and draw track box
            success, self.box = self.tracker.update(frame)
            if success:
                x, y, w, h = (int(v) for v in self.box)
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)
                self.cropped = frame[y:y+h, x:x+w].copy()

            # Update fps
            self.fps.update()
            self.fps.stop()

            # Draw info
            info = [
                ("Success", "Yes" if success else "No"),
                ("FPS", "{:.2f}".format(self.fps.fps())),
            ]

            for i, (k, v) in enumerate(info):
                cv2.putText(frame, "{0}: {1}".format(k, v), (10, (i * 20) + 20),
                            cv2.FONT_HERSHEY_COMPLEX, 0.5, (0, 0, 255), 1)

        cv2.putText(frame, f"(Hit {self._select_key} for select, {self.cam._exit_key} for exit)",
                    (10, self.height - 10), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 0, 255), 1)

        # Display the image
        cv2.imshow("Track screen", frame)

    def _use_cropped(self):
        # self.cropped is a np array
        top, bottom, left, right = 0, 0, 0, 0
        target_w, target_h = 500, 500
        line_height, lines = 15, 10

        if self.cropped is not None and self.cropped.size > 0:
            # Show new window with cropped image and data
            right, bottom = max(0, target_w - self.cropped.shape[1]), \
                            max(0, target_h - self.cropped.shape[0])

            larger = cv2.copyMakeBorder(self.cropped, top, bottom, left, right, cv2.BORDER_CONSTANT, None, (0, 0, 0))

            offset = target_h - ((lines + 1) * line_height)
            cv2.putText(larger, "Input",
                        (10, offset + 0 * line_height), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            if self.input_callback:
                # Look at brightness etc
                data = self.input_callback(self.cropped)

                cv2.putText(larger, f"Data: {data}",
                            (10, offset + 1 * line_height), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            cv2.imshow("Data input", larger)


if __name__ == "__main__":
    """
        Possible trackers:
            csrt, kcf, boosting, mil, tld, medianflow, mosse
    """
    tracker = ScreenTracker(tracker="csrt")
    tracker.start()
