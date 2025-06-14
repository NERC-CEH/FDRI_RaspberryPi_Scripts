import cv2

def blur_faces_and_bodies(input_path, output_path=None, blur_level=51,
                          face_cascade_path=None, body_cascade_path=None):
    """
    Detects faces and full bodies in an image and blurs them.
    """
    image = cv2.imread(str(input_path))
    if image is None:
        raise ValueError(f"Could not read image from {input_path}")

    # Default to OpenCV's built-in haarcascades if not provided
    if not face_cascade_path:
        face_cascade_path = cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    if not body_cascade_path:
        body_cascade_path = "classifiers/haarcascade_fullbody.xml"  # <--- Set your path

    face_cascade = cv2.CascadeClassifier(face_cascade_path)
    body_cascade = cv2.CascadeClassifier(body_cascade_path)

    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)
    bodies = body_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=3)

    # Blur faces
    for (x, y, w, h) in faces:
        roi = image[y:y+h, x:x+w]
        roi = cv2.GaussianBlur(roi, (blur_level, blur_level), 0)
        image[y:y+h, x:x+w] = roi

    # Blur bodies
    for (x, y, w, h) in bodies:
        roi = image[y:y+h, x:x+w]
        roi = cv2.GaussianBlur(roi, (blur_level, blur_level), 0)
        image[y:y+h, x:x+w] = roi

    out_path = output_path if output_path is not None else input_path
    cv2.imwrite(str(out_path), image)