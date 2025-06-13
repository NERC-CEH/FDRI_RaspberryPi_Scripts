import cv2

def blur_faces(input_path, output_path=None, blur_level=51):
    """
    Detects faces in an image and blurs them.
    
    Args:
        input_path: Path to the input image.
        output_path: Path to save the output image. If None, overwrites input.
        blur_level: Size of Gaussian blur kernel (must be odd).
    """
    image = cv2.imread(str(input_path))
    if image is None:
        raise ValueError(f"Could not read image from {input_path}")

    face_cascade = cv2.CascadeClassifier(
        cv2.data.haarcascades + "haarcascade_frontalface_default.xml"
    )
    gray = cv2.cvtColor(image, cv2.COLOR_BGR2GRAY)
    faces = face_cascade.detectMultiScale(gray, scaleFactor=1.1, minNeighbors=5)

    for (x, y, w, h) in faces:
        face = image[y:y+h, x:x+w]
        face = cv2.GaussianBlur(face, (blur_level, blur_level), 0)
        image[y:y+h, x:x+w] = face

    out_path = output_path if output_path is not None else input_path
    cv2.imwrite(str(out_path), image)
