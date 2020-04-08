from webcam import Webcam

import numpy as np
import cv2
import time

# import the necessary packages
import datetime

class FPS:
    def __init__(self):
        self._start  = None
        self._end    = None
        self._frames = 0

    def start(self):
        self._start = datetime.datetime.now()
        return self

    def stop(self):
        self._end = datetime.datetime.now()

    def update(self):
        self._frames += 1

    def remove(self, last=1):
        self._frames -= last

    def elapsed(self):
        return (self._end - self._start).total_seconds()

    def fps(self):
        return self._frames / self.elapsed()

    def frames(self):
        self.update()
        self.stop()
        return self.fps()


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

    def __init__(self, input_callback=None, tracker="kcf", fps_limit=16, select_key='s', exit_key='q'):
        super().__init__()

        self.cam          = Webcam(exit_key=exit_key)
        self.tracker      = None
        self.tracker_name = tracker

        self.width, self.height = 0, 0
        self.box       = None
        self.fps       = FPS()
        self.fps_limit = fps_limit
        self.cropped   = None

        self.tracker_init = False

        self._select_key    = select_key
        self.input_callback = input_callback

    def start(self):
        try:
            self.cam.capture_start()
            self.width, self.height = self.cam.width, self.cam.height
            self.cam.fps = self.fps_limit

            while(True):
                # Capture frame-by-frame
                frame = self.cam.capture_new()

                if frame is not None:
                    self._handle_frame(frame)
                    self._use_cropped()
                else:
                    break

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
                self.cropped = frame[y:y+h, x:x+w].copy()
                cv2.rectangle(frame, (x, y), (x + w, y + h), (0, 255, 0), 2)

            # Update fps
            frames = self.fps.frames()

            # Drop frame on fps limit
            if frames > self.fps_limit:
                self.fps.remove()
                self.cropped = None

            # Draw info
            info = [
                ("Success", "Yes" if success else "No"),
                ("FPS", "{:.2f}".format(frames)),
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
            # Apply filters
            gray = cv2.cvtColor(self.cropped, cv2.COLOR_BGR2GRAY)
            blur = cv2.GaussianBlur(gray, (5,5), 0)
            ret, filtered = cv2.threshold(blur, 0, 255, cv2.THRESH_BINARY + cv2.THRESH_OTSU)

            if ret:
                self.cropped = filtered

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

                for line in data:
                    cv2.putText(larger, line,
                                (10, offset + 1 * line_height), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (255, 255, 255), 1)

            cv2.imshow("Data input", larger)


if __name__ == "__main__":
    """
        Possible trackers:
            csrt, kcf, boosting, mil, tld, medianflow, mosse
    """
    tracker = ScreenTracker(tracker="csrt")
    tracker.start()
