# find_dist.py
import cv2
import torch
import sys
import subprocess
from pathlib import Path
import pathlib
from calc_dist import getDistance1, getDistance2, getDistance3

temp = pathlib.WindowsPath
pathlib.WindowsPath = pathlib.PosixPath

# YOLOv5 소스 코드 경로를 Python 경로에 추가
yolov5_path = str(Path('/home/orin/yolov5').resolve())  # YOLOv5 소스 코드 경로로 변경
sys.path.insert(0, yolov5_path)

try:
    from models.common import DetectMultiBackend  # YOLOv5의 모델 클래스 직접 임포트
    from utils.general import non_max_suppression, scale_boxes, xyxy2xywh
    from utils.torch_utils import select_device
except ImportError as e:
    print("모듈 임포트 오류:", e)
    print("확인할 경로:", yolov5_path)
    sys.exit(1)

def plot_one_box(x, img, color=(255, 0, 0), label=None, line_thickness=3):
    # Add one bounding box to the image
    tl = line_thickness or round(0.002 * (img.shape[0] + img.shape[1]) / 2) + 1  # line/font thickness
    color = [int(c) for c in color]
    c1, c2 = (int(x[0]), int(x[1])), (int(x[2]), int(x[3]))
    #print(f"x : {(x[2] + x[0]) / 2}, y: {(x[3] + x[1]) / 2}")
    cv2.rectangle(img, c1, c2, color, thickness=tl, lineType=cv2.LINE_AA)
    if label:
        tf = max(tl - 1, 1)  # font thickness
        t_size = cv2.getTextSize(label, 0, fontScale=tl / 3, thickness=tf)[0]
        c2 = c1[0] + t_size[0], c1[1] - t_size[1] - 3
        cv2.rectangle(img, c1, c2, color, -1, cv2.LINE_AA)  # filled
        cv2.putText(img, label, (c1[0], c1[1] - 2), 0, tl / 3, [225, 255, 255], thickness=tf, lineType=cv2.LINE_AA)

def gstreamer_pipeline(
    sensor_id=0,
    capture_width=1280,
    capture_height=720,
    display_width=960,
    display_height=540,
    framerate=20,
    flip_method=0,
):
    return (
        "nvarguscamerasrc sensor-id=%d ! "
        "video/x-raw(memory:NVMM), width=(int)%d, height=(int)%d, framerate=(fraction)%d/1 ! "
        "nvvidconv flip-method=%d ! "
        "video/x-raw, width=(int)%d, height=(int)%d, format=(string)BGRx ! "
        "videoconvert ! "
        "video/x-raw, format=(string)BGR ! appsink drop=true max-buffers=1"
        %(
            sensor_id,
            capture_width,
            capture_height,
            framerate,
            flip_method,
            display_width,
            display_height,
          )
        )

def display_dist(xyxy, distance, frame):
    text = f'Distance: {distance:.2f} cm'
    (w, h), _ = cv2.getTextSize(text, cv2.FONT_HERSHEY_SIMPLEX, 0.9, 2)

    # Draw background rectangle
    cv2.rectangle(frame, (int(xyxy[0]), int(xyxy[1]) - 30 - h), (int(xyxy[0]) + w, (int(xyxy[1]) - 30)), (255, 0, 0), -1)

    # Draw text
    cv2.putText(frame, text, (int(xyxy[0]), int(xyxy[1]) - 30), cv2.FONT_HERSHEY_SIMPLEX, 0.5, (255, 255, 255), 2)


def show_camera(queue=None):
    window_title = "CSI Camera with YOLOv5"

    # Load custom YOLOv5 model
    model_path = '/home/orin/models_yolo/rm_bar_s30.pt'  # 사용자 모델 경로로 변경

    # 디바이스 설정
    device = torch.device('cuda' if torch.cuda.is_available() else 'cpu')
    if device.type == 'cuda':
        torch.cuda.init() # CUDA initialize

    model = DetectMultiBackend(model_path, device=device)

    # To flip the image, modify the flip_method parameter (0 and 2 are the most common)
    video_capture = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)

    while True:
        if not video_capture.isOpened():
            # restart_nvargus_daemon()
            video_capture = cv2.VideoCapture(gstreamer_pipeline(), cv2.CAP_GSTREAMER)
            print("Error: Unable to open camera")
            return []
        else:
            break
        
        
    start = False  # 주행 시작 여부 
    sign1_detection_count = 0 # sign1이 감지된 횟수 추적 변수
    duck_detection_count = 0  # duck이 연속으로 감지된 횟수 추적 변수
    duck_absence_count = 0    # duck이 감지되지 않는 횟수 추적 변수
    detection_threshold = 3   # 감지되었다고 간주할 연속 감지 횟수
    duck_signal_sent = False
        
    try:
        window_handle = cv2.namedWindow(window_title, cv2.WINDOW_AUTOSIZE)
        while True:
            ret_val, frame = video_capture.read()

            if not ret_val:
                print("Error: Unable to read frame")
                # restart_nvargus_daemon()
                break

            # Object detection
            img = torch.from_numpy(frame).to(device)
            img = img.permute(2, 0, 1).float() / 255.0  # Convert to torch format
            if img.ndimension() == 3:
                img = img.unsqueeze(0)
            pred = model(img, augment=False)
            pred = non_max_suppression(pred, 0.25, 0.45, classes=None, agnostic=False)

            duck_detected_in_frame = False

            # 프레임에서 감지되는 labels 정보들 저장하는 list
            detection_results = []

            # Process detections          
            for det in pred:
                if len(det):
                    # Rescale boxes from img_size to frame size
                    det[:, :4] = scale_boxes(img.shape[2:], det[:, :4], frame.shape).round()

                    # Render boxes on frame
                    for *xyxy, conf, cls in reversed(det):
                        c = int(cls)  # integer class
                        label = f'{model.names[c]} {conf:.2f}'

                        bbox_height = (xyxy[3] - xyxy[1]).cpu().numpy()
                        x = (xyxy[0] + xyxy[2]) / 2
                        y = (xyxy[1] + xyxy[3]) / 2 

                        print(f"name: {model.names[c]}, height: {bbox_height}")
                        if model.names[c] == "sign1":
                            distance = getDistance1(bbox_height)
                            display_dist(xyxy, distance, frame)
                            
                            # start == False일 때 sign1이 detect되면 차단기 올라간 것 = 차량 출발
		                    # start == True면 pass
                            if not start:
                                sign1_detection_count += 1
                                if sign1_detection_count >= detection_threshold:
                                    start = True
                                    if queue:
                                        queue.put("Start")
                            
                        elif model.names[c] == "sign2":
                            distance = getDistance2(bbox_height)
                            display_dist(xyxy, distance, frame)
                        elif model.names[c] == "sign3":
                            distance = getDistance3(bbox_height)
                            display_dist(xyxy, distance, frame)

                        elif model.names[c] == "duck":
                            duck_detected_in_frame = True
                            duck_detection_count += 1
                            duck_absence_count = 0

                            if duck_detection_count >= detection_threshold:
                                if not duck_signal_sent:
                                    # print("Duck detected. Stopping the car.")
                                    queue.put("duck")
                                    duck_signal_sent = True
                                
                        # label, bbox_height 정보 저장
                        detection_results.append({
                        'label': model.names[c],
                        'bbox_height': bbox_height,
                        ## 중앙 좌표 전달 ## 
                        'center_x': x,
                        'center_y': y
                        })

                        
                        plot_one_box(xyxy, frame, label=label, color=(255, 0, 0), line_thickness=2)
        
                if not duck_detected_in_frame and duck_signal_sent:
                    duck_absence_count += 1
                    print(f"-------오리 없음----------: {duck_absence_count}")
                    if duck_absence_count >= detection_threshold:
                        queue.put("clear")
                        print("Duck cleared.")
                        duck_signal_sent = False

                duck_detected = duck_detected_in_frame

            # Check to see if the user closed the window
            if cv2.getWindowProperty(window_title, cv2.WND_PROP_AUTOSIZE) >= 0:
                cv2.imshow(window_title, frame)
            else:
                break

            keyCode = cv2.waitKey(10) & 0xFF
            # Stop the program on the ESC key or 'q'
            if keyCode == 27 or keyCode == ord('q'):
                break

    except Exception as e:
        print(f"An error occurred in show_camera: {e}")

    finally:
        video_capture.release()
        cv2.destroyAllWindows()

