import flask
import os
import pickle
import pandas as pd
import numpy as np
import tensorflow as tf
import skimage
from skimage import io, color
from skimage.transform import rescale, resize, downscale_local_mean
from werkzeug.utils import secure_filename
from werkzeug.datastructures import FileStorage
from face_detection import Face, find_faces
import create_model
from create_model import create_gender_model, create_age_model_sk


APP_ROOT = os.path.dirname(os.path.abspath(__file__))
UPLOAD_FOLDER = os.path.join(APP_ROOT, 'static', 'uploads')  # stores uploaded images
FACES_FOLDER = os.path.join(APP_ROOT, 'static', 'faces')  # stores faces found in image
ALLOWED_EXTENSIONS = {'png', 'jpg', 'jpeg', 'gif'}
app = flask.Flask(__name__, template_folder='templates')
app.config['UPLOAD_FOLDER'] = UPLOAD_FOLDER

gender_classifier_path = 'models/gender_model.pkl'
age_predictor_path = 'models/age_model.pkl'

# load models using pickle from models folder, if there is an error, then generate models
try:
    model_file = open(gender_classifier_path, 'rb')
    gender_classifier = pickle.load(model_file)
except IOError:
    print("Error finding gender classifier model, recreating")
    gender_classifier = create_gender_model()  # returns model for gender and saves it to models folder

try:
    #age_predictor = tf.keras.models.load_model(age_predictor_path)
    model_file = open(age_predictor_path, 'rb')
    age_predictor = pickle.load(model_file)
except IOError:
    print("Error finding age prediction model, recreating")
    age_predictor = create_age_model_sk()


@app.route('/', methods=['GET', 'POST'])
def main():
    if flask.request.method == 'GET':
        # clear faces and uploads folder here
        face_not_found = False
        return flask.render_template('main.html')

    if flask.request.method == 'POST':
        sample_image = flask.request.args.get('sample_image')
        filename = None
        if sample_image:
            file = open(os.path.join(APP_ROOT, 'static', sample_image), "rb")
            # wrap file in werkzeug filestorage class to be compatible with our code below
            file = FileStorage(file, content_type=('image/' + str(sample_image.split('.')[1])))
            filename = secure_filename(file.filename)
            filename = filename.split('static_')[1]
        else:
            file = flask.request.files['file']
            filename = secure_filename(file.filename)

        if file:
            original_image_path = os.path.join(app.config['UPLOAD_FOLDER'], filename)
            file.save(original_image_path)  # saving original image before we resize, to display later

            if os.name == 'nt':
                original_image_path = original_image_path.replace("\\", "/")

            original_image_path = 'static' + original_image_path.split('static')[1]  # only keep path after 'static'

            faces = find_faces(original_image_path, FACES_FOLDER)  # returns a list of Faces from image
            gender_prediction = None

            if len(faces) > 0:
                for face in faces:
                    img = skimage.io.imread(face.image_path)  # face that has been cropped from original image
                    img = skimage.color.rgb2gray(img)  # convert to grayscale
                    img = skimage.transform.resize(image=img, output_shape=(48, 48))  # downsize to size of our dataset
                    mod_image_path = (os.path.splitext(original_image_path)[0] + '_downscaled'
                                      + os.path.splitext(original_image_path)[1])
                    skimage.io.imsave(mod_image_path, img)  # save our modified file that we use with our model
                    
                    #tf_img = img.reshape(1, 48, 48, -1)

                    img = img.ravel()  # flatten 48*48 array to 1x(48*48)
                    img = img * 255  # our sk-learn model expects int value for each pixel 0 - 255
                    img = img.astype(int)

                    gender_prediction = gender_classifier.predict([img])
                    if gender_prediction[0] == 0:
                        face.gender = 'Male'
                    elif gender_prediction[0] == 1:
                        face.gender = 'Female'
                    else:
                        face.gender = None  # error

                    age_pred = age_predictor.predict([img])
                    #age_pred = tf.argmax(age_pred, axis=-1)
                    face.age = create_model.get_age_range(age_pred)

                    if os.name == 'nt':
                        face.image_path = face.image_path.replace("\\", "/")

                    face_found = 'static' + newpath.split('static')[1]  # only keep path after 'static'
                    face.image_path = face_found  # easier format to print in our html page

                return flask.render_template('classify_image.html', faces=faces, original_image=original_image_path)

            else:
                # file uploaded, but no face found in image
                return flask.render_template('main.html', face_not_found=True)

    return flask.render_template('main.html')


@app.route('/classify_image', methods=['GET', 'POST'])
def classify_image():

    return flask.render_template('classify_image.html')


if __name__ == '__main__':
    app.run(debug=True, host='0.0.0.0')
