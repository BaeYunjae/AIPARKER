# perception.py
import Jetson.GPIO as GPIO
import time
import threading
from find_dist import show_camera

# GPIO 핀 번호 설정
TRIG_PIN = 23  # 사용할 GPIO 핀 번호
ECHO_PIN = 24  # 사용할 GPIO 핀 번호


def initialize_gpio():
    """
    GPIO를 초기화하는 함수. 이미 초기화되어 있으면 설정하지 않음.
    """

    # GPIO 리소스 정리 후 다시 설정
    GPIO.cleanup()
    GPIO.setmode(GPIO.BCM)
    GPIO.setup(TRIG_PIN, GPIO.OUT, initial=GPIO.LOW)
    GPIO.setup(ECHO_PIN, GPIO.IN)

def ultra_distance():
    """
    초음파 센서를 사용하여 거리를 측정하는 함수.
    """
    initialize_gpio()
    time.sleep(0.1)  # wait for a moment

    GPIO.output(TRIG_PIN, True)
    time.sleep(0.00006)
    GPIO.output(TRIG_PIN, False)

    start_time = time.time()
    timeout = start_time + 0.1  # 100ms 타임아웃

    pulse_start = None
    pulse_end = None

    while GPIO.input(ECHO_PIN) == 0 and time.time() < timeout:
        pulse_start = time.time()

    if pulse_start is None or time.time() >= timeout:
        print("Echo start signal timeout")
        return None

    while GPIO.input(ECHO_PIN) == 1 and time.time() < timeout:
        pulse_end = time.time()

    if pulse_end is None or time.time() >= timeout:
        print("Echo end signal timeout")
        return None

    pulse_duration = pulse_end - pulse_start
    distance = pulse_duration * 34300 / 2
    return distance

def detecting_distance(queue):
    """
    카메라 기반 거리 정보
    """
    try:
        show_camera(queue)
    except KeyboardInterrupt:
        print("Detecting distance interrupted")


