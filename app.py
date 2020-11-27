import flask
import os
import pickle
import pandas as pd
import numpy as np
import skimage
from skimage import io, color
from skimage.transform import rescale, resize, downscale_local_mean
from werkzeug.utils import secure_filename
from face_detection import Face, find_faces
from create_model import create_gender_model


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static', 'uploads')  # stores uploaded images
FACES_FOLDER = os.path.join(APP_ROOT, 'static', 'faces')  # stores faces found in image
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app = flask.Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER


gender_classifier_path = 'models/gender_model.pkl'

# load models here with pickle from models folder, if there is an error, then generate models
try:
    model_file = open(gender_classifier_path, 'rb')
    gender_classifier = pickle.load(model_file)
except IOError:
    print("Error finding gender classifier model, recreating")
    gender_classifier = create_gender_model()  # returns model for gender and saves it to models folder

# load age model here


@app.route('/', methods=['GET', 'POST'])
def main():
    if flask.request.method == 'GET':
        # clear faces and uploads folder here
        face_not_found = False
        return flask.render_template('main.html')

    if flask.request.method == 'POST':
        # Get file object from user input.
        file = flask.request.files['file']

        if file:
            filename = secure_filename(file.filename)
            original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(original_image_path)  # saving original image before we resize, to display later
            newpath = ""
            for char in original_image_path:
                if char == '\\':
                    newpath += '/'
                else:
                    newpath += char
            original_image_path = 'static' + newpath.split('static')[1]  # only keep path after 'static'

            faces = find_faces(original_image_path, FACES_FOLDER)  # returns a list of Faces from image
            gender_prediction = None
            mod_image_path = None

            if len(faces) > 0:
                for face in faces:
                    img = skimage.io.imread(face.image_path)  # face that has been cropped from original image
                    img = skimage.color.rgb2gray(img)  # convert to grayscale
                    img = skimage.transform.resize(image=img, output_shape=(48, 48))  # downsize to size of our dataset
                    mod_image_path = (os.path.splitext(original_image_path)[0] + '_downscaled'
                                      + os.path.splitext(original_image_path)[1])
                    skimage.io.imsave(mod_image_path, img)  # save our modified file that we use with our model
                    img = img.ravel()  # flatten 48*48 array to 1x(48*48)
                    img = img * 255  # our model expects int value for each pixel 0 - 255
                    img = img.astype(int)

                    gender_prediction = gender_classifier.predict([img])
                    if gender_prediction[0] == 0:
                        face.gender = 'Male'
                    elif gender_prediction[0] == 1:
                        face.gender = 'Female'
                    else:
                        face.gender = None  # error


                    # age =

                    newpath = ""
                    for char in face.image_path:
                        if char == '\\':
                            newpath += '/'
                        else:
                            newpath += char
                    face_found = 'static' + newpath.split('static')[1]  # only keep path after 'static'
                    face.image_path = face_found  # easier format to print in our html page

                return flask.render_template('classify_image.html', faces=faces, original_image=original_image_path)

            else:
                # file uploaded, but no face found in image
                return flask.render_template('main.html', face_not_found=True)

    return flask.render_template('main.html')


@app.route('/classify_image/', methods=['GET', 'POST'])
def classify_image():
    # results page
    # add a return to main page button
    return flask.render_template('classify_image.html')


if __name__ == '__main__':
    app.run(debug=True)
