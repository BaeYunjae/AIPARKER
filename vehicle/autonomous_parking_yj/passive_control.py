# passive.py
from adafruit_pca9685 import PCA9685
from adafruit_servokit import ServoKit
import board
import busio
import time

class PWMThrottleHat:
    def __init__(self, pwm, channel):
        self.pwm = pwm
        self.channel = channel
        self.pwm.frequency = 60

    def set_throttle(self, throttle):
        pulse = int(0xFFFF * abs(throttle))
        if throttle > 0:
            # 전진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0xFFFF
        elif throttle < 0:
            # 후진
            self.pwm.channels[self.channel + 5].duty_cycle = pulse
            self.pwm.channels[self.channel + 4].duty_cycle = 0xFFFF
            self.pwm.channels[self.channel + 3].duty_cycle = 0
        else:
            # 정지
            self.pwm.channels[self.channel + 5].duty_cycle = 0
            self.pwm.channels[self.channel + 4].duty_cycle = 0
            self.pwm.channels[self.channel + 3].duty_cycle = 0

# I2C 설정 및 모터/서보 초기화
i2c = busio.I2C(board.SCL, board.SDA)
pca = PCA9685(i2c)
pca.frequency = 60

motor_hat = PWMThrottleHat(pca, channel=0)
kit = ServoKit(channels=16, i2c=i2c, address=0x60)
pan = 90
kit.servo[0].angle = pan

def control_motor():
    global pan

    while True:
        print("\nControls: w = forward, s = backward, a = servo left, d = servo right, q = quit")
        key = input("Enter command: ")

        if key == 'w':
            print("Motor forward")
            motor_hat.set_throttle(0.3)  # 전진 80% 속도
            time.sleep(0.3)
            motor_hat.set_throttle(0)
        elif key == 's':
            print("Motor backward")
            motor_hat.set_throttle(-0.3)  # 후진 50% 속도
            time.sleep(0.3)
            motor_hat.set_throttle(0)
        elif key == 'a':
            print("Servo left")
            pan -= 5
            if pan < 0:
                pan = 0
            kit.servo[0].angle = pan
            print(f"Servo angle set to: {pan}")
        elif key == 'd':
            print("Servo right")
            pan += 5
            if pan > 180:
                pan = 180
            kit.servo[0].angle = pan
            print(f"Servo angle set to: {pan}")
        elif key == 'q':
            print("Exiting control...")
            break
        else:
            motor_hat.set_throttle(0)  # 잘못된 키 입력 시 모터 정지

def main():
    try:
        control_motor()
    except KeyboardInterrupt:
        pass
    finally:
        motor_hat.set_throttle(0)
        kit.servo[0].angle = 90
        pca.deinit()
        print("Program stopped and motor stopped.")

if __name__ == "__main__":
    main()

