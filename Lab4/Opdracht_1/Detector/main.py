from webcam import Webcam



if __name__ == "__main__":
    cam = Webcam()
    cam.capture_start()
    cam.capture_loop(Webcam.show_frame)
