import cv2

cap = cv2.VideoCapture(0, cv2.CAP_DSHOW)

if not cap.isOpened():
    print("Could not open webcam.")
    exit()

while True:
    success, frame = cap.read()
    if not success:
        print("Frame grab failed, retrying...")
        continue

    cv2.imshow("Webcam", frame)
    if cv2.waitKey(1) == ord('q'):
        break

cap.release()
cv2.destroyAllWindows()