###############################################################################
# SETUP - EXECUTE THIS FIRST                                                  #
###############################################################################
# 1. Go into "Runtime" -> "Change runtime type" and Select "GPU" for hardward accelerator
# 2. Click the "Connect" button, at the right to start the instance.
# This will get the dataset into this instance
# 3. Note that the dataset RGB.zip, PSRI.zip, NDVI45.zip, NDVI.zip or GNDVI.zip must be in the root of your google drive
# 4. Name the dataset below before you start!
###############################################################################
# Variables                                                                   #
###############################################################################
import os
from datetime import datetime 
dataset="RGB"  #Name the dataset here 
timestamp = datetime.now().strftime("%d%b%Y%Hh%Mm%S")

dataset_zip=dataset+".zip"
past_model="DenseNet_" + dataset + "_" + timestamp + "_*.hdf5"
final_model="DenseNet_"+ dataset + "_" + timestamp + "_final.h5"

number_of_classes=10 
img_width, img_height = 64, 64  
epochs_pre = 10      # Pre-training epoch 
epochs_last = 20     # Complete model epoch
batch_size = 128     # Batch size
###############################################################################


###############################################################################
# HELPER FUNCTIONS
###############################################################################
def number_of_files(dirname):
	cpt = sum([len(files) for r, d, files in os.walk(dirname)])
	return cpt

################################################################################ 
# DÉFINITION DES DONNÉES D'ENTRÉE                                              #
################################################################################
train_data_dir = dataset+'/training'
validation_data_dir = dataset+'/validation'
test_data_dir = dataset+'/test'
nb_train_samples=number_of_files(train_data_dir)
nb_validation_samples=number_of_files(validation_data_dir)
nb_test_samples=number_of_files(test_data_dir)

#/content/drive/'My Drive'/
#!unzip EuroSatRGB_very_small.zip

# ==============================================================================
# Etienne Lord, Amanda Boatswain Jacques - 2021
#
# Licensed under the Apache License, Version 2.0 (the "License");
# you may not use this file except in compliance with the License.
# You may obtain a copy of the License at
#
#     http://www.apache.org/licenses/LICENSE-2.0
#
# Unless required by applicable law or agreed to in writing, software
# distributed under the License is distributed on an "AS IS" BASIS,
# WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
# See the License for the specific language governing permissions and
# limitations under the License.
# ==============================================================================
# %tensorflow_version 1.x\

from tensorflow.keras.applications import DenseNet121
from tensorflow.keras.preprocessing import image
from tensorflow.keras.applications.densenet import preprocess_input, decode_predictions
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential, load_model
from tensorflow.keras.layers import Conv2D, MaxPooling2D, LeakyReLU
from tensorflow.keras.layers import Activation, Dropout, Flatten, Dense,GlobalAveragePooling2D
from tensorflow.keras.optimizers import Adam  # Adam optimiser is preferred during transfer learning with EfficientNet
from tensorflow.keras.callbacks import *
from tensorflow.keras.models import Model
from tensorflow.keras import backend as K
import tensorflow as tf
from pathlib import Path
import os

num_threads=16
tf.config.threading.set_inter_op_parallelism_threads(num_threads)
tf.config.threading.set_intra_op_parallelism_threads(num_threads)
tf.config.set_soft_device_placement(True)
tf.random.set_seed(20210926)

################################################################################ 
# MODEL DEFINITION                                                             #
################################################################################
base_model = DenseNet121(weights='imagenet', include_top=False) # Load the DenseNet model 

x = base_model.output
x = GlobalAveragePooling2D()(x)
x = Dense(1024, activation='relu')(x)
x = Dropout(0.25)(x)
# and a logistic layer with number_of_classes classes (in our dataset)
predictions = Dense(number_of_classes, activation='softmax')(x)

# first: train only the top layers (which were randomly initialized)
for layer in base_model.layers:
    layer.trainable = False

# Model definitions
model = Model(inputs=base_model.input, outputs=predictions)
model.summary()


# Compile the model (should be done *after* setting layers to non-trainable)
model.compile(optimizer=Adam(learning_rate=1e-4), loss='categorical_crossentropy', metrics=['accuracy'])

################################################################################ 
# IMAGES LOADING                                                               #
################################################################################

# Note, we could use data augmentation
train_datagen = ImageDataGenerator(rotation_range=90)
test_datagen = ImageDataGenerator() 

train_generator = train_datagen.flow_from_directory(
    train_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size,
	  shuffle = True,
    class_mode='categorical') # Note: the class_mode is categorical

validation_generator = test_datagen.flow_from_directory(
    validation_data_dir,
    target_size=(img_width, img_height),
	shuffle = True,
    batch_size=batch_size,
    class_mode='categorical')

test_generator = test_datagen.flow_from_directory(
    test_data_dir,
    target_size=(img_width, img_height),
    batch_size=batch_size,
    class_mode='categorical')

reduce_lr = ReduceLROnPlateau(monitor='val_loss', factor=0.2,patience=5, min_lr=0.001)

tensor=TensorBoard(log_dir='.',histogram_freq=1,embeddings_freq=1,)
csv_logger = CSVLogger("DenseNet_"+dataset+"_"+ timestamp+ "_pre_log.csv", append=True, separator=';')

################################################################################ 
# RUN MODEL  (Part 1)                                                          #
################################################################################

# Start the pretraining 
original_hist=model.fit(
    train_generator,
    steps_per_epoch=nb_train_samples // batch_size,
    epochs=epochs_pre,
    verbose=1,
    callbacks=[csv_logger],
    validation_data=validation_generator,
    validation_steps= (nb_validation_samples // batch_size))

# At this point, the top layers are well trained and we can start fine-tuning
# convolutional layers. We will freeze the bottom N layers
# and train the remaining top layers.

################################################################################ 
# RUN MODEL (Part 2)                                                           #
################################################################################

for layer in model.layers:
   layer.trainable = True

model.compile(optimizer=Adam(lr=1e-2), loss='categorical_crossentropy', metrics=['accuracy'])

csv_logger = CSVLogger("DenseNet_" + dataset + "_" + timestamp + "_log.csv", append=True, separator=';')
checkpointer = ModelCheckpoint(filepath="DenseNet_" + dataset + "_" + timestamp + "_weights.{epoch:02d}-{val_accuracy:.2f}.h5", verbose=1, save_best_only=False)
original_hist2=model.fit(
    train_generator,
    steps_per_epoch=nb_train_samples // batch_size,
    epochs=epochs_last,
    verbose=1,
    callbacks=[csv_logger],
    validation_data=validation_generator,
    validation_steps= (nb_validation_samples // batch_size))

################################################################################ 
# SAVE MODEL                                                                   #
################################################################################
model.save(final_model)

#%tensorflow_version 1.x
#from tensorflow.keras.applications import EfficientNetB0

from tensorflow.keras.preprocessing import image
#from tensorflow.keras.applications.efficientnet import preprocess_input, decode_predictions
import numpy as np
from tensorflow.keras.preprocessing.image import ImageDataGenerator
from tensorflow.keras.models import Sequential
from tensorflow.keras.layers import Conv2D, MaxPooling2D, LeakyReLU
from tensorflow.keras.layers import Activation, Dropout, Flatten, Dense,GlobalAveragePooling2D
from tensorflow.keras.optimizers import Adam
from tensorflow.keras.callbacks import *
from tensorflow.keras.models import Model, load_model
from tensorflow.keras import backend as K
from pathlib import Path
import os
from sklearn.metrics import classification_report, confusion_matrix
import matplotlib.pyplot as plt
from sklearn.utils.multiclass import unique_labels
import itertools
import pandas as pd

# dimensions des images d'entraînement
img_width, img_height = 64, 64
batch_size = 128
################################################################################
# HELPER FUNCTIONS                                                             #
################################################################################ 

def number_of_files(dirname):
	cpt = sum([len(files) for r, d, files in os.walk(dirname)])
	return cpt

def plot_confusion_matrix(cm, classes,
                          normalize=False,
                          title='Confusion matrix',
                          cmap=plt.cm.Blues):
    """
    This function prints and plots the confusion matrix.
    Normalization can be applied by setting `normalize=True`.
    """
    if normalize:
        cm = cm.astype('float') / cm.sum(axis=1)[:, np.newaxis]
        print("Normalized confusion matrix")
    else:
        print('Confusion matrix, without normalization')

    print(cm)

    plt.imshow(cm, interpolation='nearest', cmap=cmap)
    plt.title(title)
    plt.colorbar()
    tick_marks = np.arange(len(classes))
    plt.xticks(tick_marks, classes, rotation=45)
    plt.yticks(tick_marks, classes)

    fmt = '.2f' if normalize else 'd'
    thresh = cm.max() / 2.
    for i, j in itertools.product(range(cm.shape[0]), range(cm.shape[1])):
        plt.text(j, i, format(cm[i, j], fmt),
                 horizontalalignment="center",
                 color="white" if cm[i, j] > thresh else "black")

    plt.tight_layout()
    plt.ylabel('True label')
    plt.xlabel('Predicted label')

	
	
################################################################################ 
# DÉFINITION DES DONNÉES D'ENTRÉE                                              #
################################################################################
#test_data_dir="EuroSatRGBmini"
nb_test_samples=number_of_files(test_data_dir)

################################################################################ 
# TEST MODEL	                                                               #
################################################################################
model=load_model(final_model)

# predict_class
test_datagen = ImageDataGenerator()

test_generator = test_datagen.flow_from_directory(
        test_data_dir,
        target_size=(64, 64),
		    shuffle=False,
        class_mode='categorical',
        batch_size=batch_size)

filenames = test_generator.filenames
nb_samples = len(filenames)
y_true_labels = test_generator.classes
#y_true_labels=y_true_labels.astype(int)
y_indices=test_generator.class_indices
print(test_generator.class_indices)

target_names=test_generator.class_indices.keys()
evalu = model.evaluate_generator(test_generator,steps = nb_samples // batch_size)       
print("Total samples:"+str(nb_test_samples))
print(model.metrics_names)
print(evalu)
test_generator.reset()
predicted = model.predict_generator(test_generator,steps = nb_samples / batch_size, verbose=1)
y_pred = np.rint(predicted)
predicted_class_indices=np.argmax(predicted,axis=1)

#Next step is I want the name of the classes:

labels = (test_generator.class_indices)
labels = dict((v,k) for k,v in labels.items())
predictions = [labels[k] for k in predicted_class_indices]
#Where by class numbers will be replaced by the class names. One final step if you want to save it to a csv file, arrange it in a dataframe with the image names appended with the class predicted.
print("=======================================================================")
print("Confusion matrix test set")
print(confusion_matrix(test_generator.classes, predicted_class_indices))
print("=======================================================================")
print("Report for test set")

#For the EuroSat network only
#target_names=['AnnualCrop','Forest','HerbaceousVegetation','Highway','Industrial','Pasture','PermanentCrop','Residential','River','SeaLake']
print(classification_report(test_generator.classes, predicted_class_indices, target_names=target_names))
#cm=confusion_matrix(test_generator.class_indices, y_pred)
#print(classification_report(test_generator.class_indices, predicted_class_indices, target_names=labels))
filenames=test_generator.filenames
results=pd.DataFrame({"Filename":filenames,
                      "Predictions":predictions})
filename="prediction_"+dataset+".csv"
results.to_csv(filename)
#!cp $filename /content/drive/'My Drive'/
print(results)
