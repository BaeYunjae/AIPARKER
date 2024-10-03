# contorl_test.py
from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
import board
import busio
import time
from perception import ultra_distance, initialize_gpio
import Jetson.GPIO as GPIO
import queue

# I2C 버스 설정
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 60  # PCA9685 주파수 설정

class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 60  # 주파수 설정

    def set_throttle(self, throttle):
        pulse = int(0xFFFF * abs(throttle))
        if throttle > 0:
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0xFFFF
        elif throttle < 0:
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0xFFFF
            self.pwm.channels[self.channel + 3].duty_cycle = 0
        else:
            self.pwm.channels[self.channel + 5].duty_cycle = 0
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0

# PWMThrottleHat 인스턴스 생성
motor_hat = PWMThrottleHat(pca, channel=0)


detect_cnt = 3
right_cnt = 5

arr = []

def control_dc_motor(command, num, q):
    global detect_cnt
    try:
        if command == "F":
            cnt = 0
            temp = 0

            # 오리 감지 여부 추적
            duck_detected = False
            while True:

                dist = ultra_distance()

                # 오리 신호 확인
                try:
                    signal = q.get_nowait()
                    if signal == "duck":
                        duck_detected = True
                        print("Duck detected inside control_dc_motor.")

                except queue.Empty:
                    pass


                if dist is not None:
                    if duck_detected:
                        if int(dist) <= 30:
                            motor_hat.set_throttle(0)
                            while True:
                                duck_signal = q.get()
                                if duck_signal == "clear":
                                    print("Duck disappeared. Resuming the car.")
                                    duck_detected = False
                                    break
                        else:
                            # 30cm보다 크면 계속 전진
                            print(f"Duck detected but distance > 30cm ({dist:.2f} cm). Continuing...")
                            motor_hat.set_throttle(0.3)
                    else:
                        if num - 4 <= int(dist) <= num + 2:
                            temp = int(dist)
                            arr.append(f'temp: {temp}')
                        if temp - 5 <= int(dist) <= temp + 5:
                            cnt += 1
                            arr.append(f'cnt_dist: {dist}')

                        print(f"Distance: {dist:.2f} cm")
                        if  dist <= num and cnt >= detect_cnt:
                            print("Target distance reached! Stopping the car.")
                            motor_hat.set_throttle(0)  # 정지
                            print(arr)

                            break
                        else:
                            print("Moving forward")
                            motor_hat.set_throttle(0.3)  # 전진 30% 속도
                else:
                    print("Failed to get distance")
                time.sleep(0.1)
        elif command == "R":
            print("R hello")
            motor_hat.set_throttle(0.5)
            time.sleep(num)
            motor_hat.set_throttle(0)
        elif command == "B":
            motor_hat.set_throttle(-0.5)
            time.sleep(num)
            motor_hat.set_throttle(0)
        elif command == "S":
            motor_hat.set_throttle(0)
            print("Detected Duck. Motor Stopped.")
    except KeyboardInterrupt:
        motor_hat.set_throttle(0)

    finally:
        motor_hat.set_throttle(0)  # 모터 정지
        print("Program stopped and motor stopped.")

def i2c_scan(i2c):
    while not i2c.try_lock():
        pass
    try:
        devices = i2c.scan()
        return devices
    finally:
        i2c.unlock()

def reset_servo():
    try:
        print("Scanning I2C bus...")
        devices = i2c_scan(i2c)
        print(f"I2C devices found: {[hex(device) for device in devices]}")
        if not devices:
            raise ValueError("No I2C devices found on the bus.")
        kit = ServoKit(channels=16, i2c=i2c, address=0x60)
        print("PCA9685 initialized at address 0x60.")
        kit.servo[0].angle = 90
        time.sleep(1)
        print("Servo reset completed.")
    except Exception as e:
        print(f"An error occurred while resetting servo: {e}")

def control_servo_motor(command):
    try:
        print("Scanning I2C bus...")
        devices = i2c_scan(i2c)
        print(f"I2C devices found: {[hex(device) for device in devices]}")
        if not devices:
            raise ValueError("No I2C devices found on the bus.")
        kit = ServoKit(channels=16, i2c=i2c, address=0x60)
        print("PCA9685 initialized at address 0x60.")
        reset_servo()
        if command == "R":
            kit.servo[0].angle = 135
            print("Steering right to 135 degrees")
        elif command == "L":
            kit.servo[0].angle = 45
            print("Steering left to 45 degrees")
        else:
            raise ValueError("Invalid command for servo motor. Use 'R' or 'L'.")
        print("Servo control completed.")
    except Exception as e:
        print(f"An error occurred: {e}")


