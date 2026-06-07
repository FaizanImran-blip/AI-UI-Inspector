import json
import cv2

with open("assets/xml/inspector_output.json", "r") as f:
    data = json.load(f)

# Load image
img = cv2.imread("assets/ui.png")

if img is None:
    print("Image not found")
    exit()

# Debug info
print("Image shape:", img.shape)

if len(data) > 0:
    print("First node bounds:", data[0]["bounds"])

# Draw full image border in RED
cv2.rectangle(
    img,
    (0, 0),
    (img.shape[1] - 1, img.shape[0] - 1),
    (0, 0, 255),
    5,
)

for item in data:
    bounds = item.get("bounds")
    desc = item.get("content_desc", "")

    if not desc:
        continue

    if bounds == [0, 0, 1080, 2400]:
        continue

    scale_x = img.shape[1] / 1080
    scale_y = img.shape[0] / 2400
    y_offset = -25

    x1 = int(bounds[0] * scale_x)
    y1 = int(bounds[1] * scale_y) + y_offset
    x2 = int(bounds[2] * scale_x)
    y2 = int(bounds[3] * scale_y) + y_offset

    cv2.rectangle(img, (x1, y1), (x2, y2), (0, 255, 0), 2)
    cv2.putText(img, desc[:10], (x1, y1), cv2.FONT_HERSHEY_SIMPLEX, 0.4, (0, 255, 0), 1)

cv2.imwrite("assets/image_detection.png", img)

print("Detection image saved")
