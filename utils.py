import cv2
import numpy as np
import tensorflow as tf
import os
import glob
import h5py



# Get the Image
def imread(path):
    img = cv2.imread(path)
    return img

def imsave(image, path, config):
    # Check the result dir, if not, create one
    if not os.path.isdir(os.path.join(os.getcwd(),config.result_dir)):
        os.makedirs(os.path.join(os.getcwd(),config.result_dir))
    print(os.path.join(os.getcwd(), path))
    # NOTE: because normial, we need mutlify 255 back
    cv2.imwrite(os.path.join(os.getcwd(),path),image * 255.)

def checkimage(image):
    cv2.imshow("test",image)
    cv2.waitKey(0)

def modcrop(img, scale =3):
    """
        To scale down and up the original image, first thing to do is to have no remainder while scaling operation.
    """
    # Check the image is grayscale
    if len(img.shape) ==3:
        h, w, _ = img.shape
        h = int((h / scale) * scale)
        w = int((w / scale) * scale)
        img = img[0:h, 0:w, :]
    else:
        h, w = img.shape
        h = (h / scale) * scale
        w = (w / scale) * scale
        img = img[0:h, 0:w]
    return img

def checkpoint_dir(config):
    if config.is_train:
        return os.path.join('./{}'.format(config.checkpoint_dir), "train.h5")
    else:
        return os.path.join('/content/{}'.format(config.checkpoint_dir), "test.h5")

def preprocess(is_train,path ,scale = 3):
    """
        Args:
            path: the image directory path
            scale: the image need to scale
    """
    if(is_train):
        img = imread(path)


        label_ = modcrop(img, scale)


        input_ = cv2.resize(label_, None, fx = 1.0/scale, fy = 1.0/scale, interpolation = cv2.INTER_AREA) # Resize by scaling factor

    else:
        img=imread(path)
        input_=modcrop(img, scale)
        label_ = cv2.resize(input_, None, fx = 1.0*scale, fy = 1.0*scale, interpolation = cv2.INTER_CUBIC)


    return input_, label_

def prepare_data(dataset="Train",Input_img=""):
    """
        Args:
            dataset: choose train dataset or test dataset
            For train dataset, output data would be ['.../t1.bmp', '.../t2.bmp',..., 't99.bmp']
    """
    if dataset == "Train":
        data_dir = os.path.join(os.getcwd(), dataset) # Join the Train dir to current directory
        data = glob.glob(os.path.join(data_dir, "*.png")) # make set of all dataset file path
    else:
        if Input_img !="":
            data = [os.path.join(os.getcwd(),Input_img)]
        else:
            data_dir = os.path.join(os.path.join(os.getcwd(), dataset), "Set5")
            data = glob.glob(os.path.join(data_dir, "*.png")) # make set of all dataset file path
    print(data,"---->prepare_data")
    return data

def load_data(is_train, test_img):
    if is_train:
        data = prepare_data(dataset="Train")
    else:
        if test_img != "":
            return prepare_data(dataset="Test",Input_img=test_img)
        data = prepare_data(dataset="Test")
    return data

def make_sub_data(data, config):
    """
        Make the sub_data set
        Args:
            data : the set of all file path
            config : the all flags
    """
    sub_input_sequence = []
    sub_label_sequence = []
    for i in range(len(data)):
        input_, label_, = preprocess(config.is_train,data[i], config.scale)

        if len(input_.shape) == 3: # is color
            h, w, c = input_.shape
        else:
            h, w = input_.shape # is grayscale

        # NOTE: make subimage of LR and HR

        # Input
        nx, ny = 0, 0
        for x in range(0, h - config.image_size + 1, config.stride):
            nx += 1; ny = 0
            for y in range(0, w - config.image_size + 1, config.stride):
                ny += 1
                sub_input = input_[x: x + config.image_size, y: y + config.image_size] # 17 * 17
                #checkimage(sub_input)


                # Reshape the subinput and sublabel
                sub_input = sub_input.reshape([config.image_size, config.image_size, config.c_dim])
                lr=sub_input


                # Normialize
                sub_input =  (sub_input / 255.0) * 2 - 1

                # Add to sequence
                sub_input_sequence.append(sub_input)

        # Label (the time of scale)
        for x in range(0, h * config.scale - config.image_size * config.scale + 1, config.stride * config.scale):
            for y in range(0, w * config.scale - config.image_size * config.scale + 1, config.stride * config.scale):
                sub_label = label_[x: x + config.image_size * config.scale, y: y + config.image_size * config.scale] # 17r * 17r
                #checkimage(sub_label)
                # Reshape the subinput and sublabel
                sub_label = sub_label.reshape([config.image_size * config.scale , config.image_size * config.scale, config.c_dim])

                # Normialize
                sub_label =  (sub_label / 255.0) * 2 - 1
                # Add to sequence
                sub_label_sequence.append(sub_label)

    return sub_input_sequence, sub_label_sequence , nx, ny,lr


def read_data(path):
    print(path,"-->path")
    """
        Read h5 format data file

        Args:
            path: file path of desired file
            data: '.h5' file format that contains  input values
            label: '.h5' file format that contains label values
    """
    with h5py.File(path, 'r') as hf:
        input_ = np.array(hf.get('input'))
        label_ = np.array(hf.get('label'))
        return input_, label_

def make_data_hf(input_, label_, config):
    """
        Make input data as h5 file format
        Depending on "is_train" (flag value), savepath would be change.
    """
    # Check the check dir, if not, create one
    if not os.path.isdir(os.path.join(os.getcwd(),config.checkpoint_dir)):
        os.makedirs(os.path.join(os.getcwd(),config.checkpoint_dir))

    if config.is_train:
        savepath = os.path.join(os.getcwd(), config.checkpoint_dir + '/train.h5')
    else:
        savepath = os.path.join(os.getcwd(), config.checkpoint_dir + '/test.h5')
    print(savepath,"---->savepath")
    with h5py.File(savepath, 'w') as hf:
        hf.create_dataset('input', data=input_)
        hf.create_dataset('label', data=label_)

def input_setup(config):
    """
        Read image files and make their sub-images and saved them as a h5 file format
    """

    # Load data path, if is_train False, get test data

    data = load_data(config.is_train, config.test_img)




    # Make sub_input and sub_label, if is_train false more return nx, ny
    sub_input_sequence, sub_label_sequence, nx, ny,lr = make_sub_data(data, config)


    # Make list to numpy array. With this transform
    arrinput = np.asarray(sub_input_sequence)
    arrlabel = np.asarray(sub_label_sequence)
    make_data_hf(arrinput, arrlabel, config)
    return nx, ny,lr


def merge(images, size, c_dim):
    """
        images is the sub image set, merge it
    """
    print(images.shape)
    h, w = images.shape[1], images.shape[2]

    img = np.zeros((h*size[0], w*size[1], c_dim))
    for idx, image in enumerate(images):
        i = idx % size[1]
        j = idx // size[1]
        print("h = ",h," w = ",w," i = ",i," j = ",j," idx = ",idx)
        img[j * h : j * h + h,i * w : i * w + w, :] = image

    return img
