#main.py
from perception import *
from control_test import *
import threading
import asyncio
import websockets
import queue
import json
from passive import control_motor

parking_mode = {
    "A1": [['F', 31], ['R', 0], ['B', 3]],
    "A2": [['F', 25], ['R', 0], ['B', 5]],
}

async def connect():
    uri = ""
    websocket = await websockets.connect(uri)
    try:
        # Send the vehicle type
        await websocket.send('{"licensePlate": "차량번호"}')
        # Receive and print the path
        response = await websocket.recv()

        # JSON 문자열을 Python 리스트로 변환
        path_arr = json.loads(response)

        return path_arr, websocket
    except websockets.exceptions.ConnectionClosedError as e:
        print(f"Connection error: {e}")
        return None, websocket


def run_detecting_distance(q):
    detecting_distance(q)

def run_motor_control(path_arr, q):
    for ele in path_arr:
        if ele == "parking":
            for p in parking_mode[path_arr[0]]:
                path_arr.append(p)
            continue

        completed = False
        while not completed:
            print(f"Now command : {ele[0]}")
            if ele[0] == "F":
                reset_servo()
                control_dc_motor("F", ele[1], q)  # 114cm 주행을 초음파 센서로 감지
                time.sleep(0.1)
                completed = True  # F 명령이 완료된 후 루프 종료
            elif ele[0] == "R":
                control_servo_motor("R")
                if ele[1] != 0:
                    control_dc_motor("R", ele[1], q)
                print("exit")
                completed = True  # R 명령이 완료된 후 루프 종료
            elif ele[0] == "L":
                control_servo_motor("L")
                control_dc_motor("L", ele[1], q)
                completed = True  # L 명령이 완료된 후 루프 종료
            elif ele[0] == "B":
                control_dc_motor("B", ele[1], q)
                reset_servo()
                control_dc_motor("B", 0.5, q)
                time.sleep(0.1)
                completed = True  # B 명령이 완료된 후 루프 종료
            else:
                break


            if completed:
                break  # 명령이 정상적으로 완료된 경우에만 루프 탈출

async def main():
    reset_servo()
    
    # 차단기 앞까지 수동 제어
    control_motor()

    path_arr, websocket = await connect()
    if path_arr is None:
        print("Failed to establish WebSocket connection.")
        return 

    print(path_arr)
    
    q = queue.Queue()

    # Start the distance detection thread
    distance_thread = threading.Thread(target=run_detecting_distance, args=(q,))
    distance_thread.start()
    
    # 큐에서 "Start"라는 값을 받을 때까지 대기
    start = False
    
    while not start:
        start_signal = q.get()
        if start_signal == "Start":
            start = True
            print("Starting the car...")

    # "Start" 신호를 받은 후 모터 제어와 감지 동시에 실행   
    motor_control_thread = threading.Thread(target=run_motor_control, args=(path_arr, q))
    motor_control_thread.start()     
    
    # Ensure the distance detection thread is cleaned up properly
    motor_control_thread.join()
    distance_thread.join()

    # await websocket.close()
    # print("WebSocket connection closed.")

    # GPIO.cleanup()  # GPIO 리소스 정리

if __name__ == "__main__": 
    # Run the main logic
    asyncio.run(main())
    # main()

