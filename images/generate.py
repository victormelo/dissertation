import matplotlib
# matplotlib.use('Agg')
# %% imports
import matplotlib.pyplot as plt
plt.rcParams['figure.figsize'] = (10.0, 8.0) # set default size of plots
plt.rcParams['image.interpolation'] = 'none'
plt.rcParams['image.cmap'] = 'gray'
import tensorflow as tf
import os
import random
from tensorflow.python.framework import ops
from tensorflow.python.framework import dtypes
import numpy as np
import math
import time
import scipy
import shutil
import scipy.misc
from scipy.misc import imsave
import os.path as P
from tqdm import tqdm

model_path = "/home/vkslm/playground/weights-first-try"

h = 150
w = 383


def lrelu(x, leak=0.2, name="lrelu"):
    """Leaky rectifier.

    Parameters
    ----------
    x : Tensor
        The tensor to apply the nonlinearity to.
    leak : float, optional
        Leakage parameter.
    name : str, optional
        Variable scope to use.

    Returns
    -------
    x : Tensor
        Output of the nonlinearity.
    """
    with tf.variable_scope(name):
        f1 = 0.5 * (1 + leak)
        f2 = 0.5 * (1 - leak)
        return f1 * x + f2 * abs(x)


def load_dataset(batch_size, num_epochs):
    def read_labeled_image_list():
        """Reads a .txt file containing pathes and labeles
        Args:
           image_list_file: a .txt file with one /path/to/image per line
           label: optionally, if set label will be pasted after each line
        Returns:
           List with all filenames in file image_list_file
        """
        off_fns = []
        on_fns = []
        for i in range(23003):
            off_fns.append('%010d-off.png' % i)
            on_fns.append('%010d-on.png' % i)

        label_fns = [os.path.join('out/', f) for f in off_fns]
        data_fns = [os.path.join('out/', f) for f in on_fns]

        return data_fns, label_fns

    def read_images_from_disk(input_queue):
        """Consumes a single filename and label as a ' '-delimited string.
        Args:
          filename_and_label_tensor: A scalar string tensor.
        Returns:
          Two tensors: the decoded image, and the string label.
        """

        data_content = tf.read_file(input_queue[0])
        label_content = tf.read_file(input_queue[1])

        data = tf.image.decode_png(data_content, channels=1)
        label = tf.image.decode_png(label_content, channels=1)

        data.set_shape([h, w, 1])
        data = tf.cast(data, tf.float32)/255.0

        label.set_shape([h, w, 1])
        label = tf.cast(label, tf.float32)/255.0

        return data, label


    # Reads pfathes of images together with their labels
    image_list, label_list = read_labeled_image_list()

    images = ops.convert_to_tensor(image_list, dtype=dtypes.string)
    labels = ops.convert_to_tensor(label_list, dtype=dtypes.string)

    # Makes an input queue
    input_queue = tf.train.slice_input_producer([images, labels],
                                                num_epochs=num_epochs,
                                                shuffle=True)

    image, label = read_images_from_disk(input_queue)

    # Optional Image and Label Batching
    image_batch, label_batch = tf.train.batch([image, label],
                                              batch_size=batch_size, num_threads=4,
                                              capacity = 4*batch_size,
                                              name='input')

    return image_batch, label_batch

input_shape=[None, h*w]

x = tf.placeholder(
    tf.float32, input_shape, name='x')
y_true = tf.placeholder(
    tf.float32, input_shape, name='y')
x_tensor = tf.reshape(x, [-1, h, w, 1])
y_true_tensor = tf.reshape(y_true, [-1, h, w, 1])

encoder = []
shapes = []

w1 = tf.Variable(
        tf.random_uniform([
        3, 3, 1, 16],
        -1.0 / math.sqrt(1),
        1.0 / math.sqrt(1)))
b1 = tf.Variable(tf.zeros([16]))

w2 = tf.Variable(
        tf.random_uniform([
        3, 3, 16, 32],
        -1.0 / math.sqrt(16),
        1.0 / math.sqrt(16)))
b2 = tf.Variable(tf.zeros([32]))

w3 = tf.Variable(
        tf.random_uniform([
        3, 3, 32, 32],
        -1.0 / math.sqrt(32),
        1.0 / math.sqrt(32)))
b3 = tf.Variable(tf.zeros([32]))

w4 = tf.Variable(
        tf.random_uniform([
        3, 3, 32, 64],
        -1.0 / math.sqrt(32),
        1.0 / math.sqrt(32)))
b4 = tf.Variable(tf.zeros([64]))

encoder.append(w1)
encoder.append(w2)
encoder.append(w3)
encoder.append(w4)

h_conv1 = lrelu(tf.add(tf.nn.conv2d(x_tensor, w1, strides=[1, 2, 2, 1], padding='SAME'), b1))
h_conv2 = lrelu(tf.add(tf.nn.conv2d(h_conv1, w2, strides=[1, 2, 2, 1], padding='SAME'), b2))
h_conv3 = lrelu(tf.add(tf.nn.conv2d(h_conv2, w3, strides=[1, 2, 2, 1], padding='SAME'), b3))
h_conv4 = lrelu(tf.add(tf.nn.conv2d(h_conv3, w4, strides=[1, 2, 2, 1], padding='SAME'), b4))


shapes.append(x_tensor.get_shape().as_list())
shapes.append(h_conv1.get_shape().as_list())
shapes.append(h_conv2.get_shape().as_list())
shapes.append(h_conv3.get_shape().as_list())

current_input = h_conv4

# store the latent representation
z = current_input
encoder.reverse()
shapes.reverse()

# %%
# Build the decoder using the same weights
for layer_i, shape in enumerate(shapes):
    W = encoder[layer_i]
    b = tf.Variable(tf.zeros([W.get_shape().as_list()[2]]))
    output = lrelu(tf.add(
        tf.nn.conv2d_transpose(
            current_input, W,
            tf.stack([tf.shape(x)[0], shape[1], shape[2], shape[3]]),
            strides=[1, 2, 2, 1], padding='SAME'), b))
    current_input = output

# %%
# now have the reconstruction through the network
y = current_input
# cost function measures pixel-wise difference
cost = tf.reduce_sum(tf.square(y - y_true_tensor))
# %%
learning_rate = 0.001

optimizer = tf.train.AdamOptimizer(learning_rate).minimize(cost)
# %%
# We create a session to use the graph
sess = tf.Session()


ckpt = tf.train.get_checkpoint_state('/home/vkslm/playground/WEIGHTS-FIRST_TRY')
saver = tf.train.Saver()

# saver.restore(sess, ckpt.model_checkpoint_path)
# new_saver = tf.train.import_meta_graph('/home/vkslm/playground/weights-first-try/model.ckpt-99.meta')
saver.restore(sess, ckpt.model_checkpoint_path)
from PIL import Image
fn = '/home/vkslm/playground/icdar-2017/imagens/0000009194-on.png'
fnoff = '/home/vkslm/playground/icdar-2017/imagens/0000009194-off.png'
predict = Image.open(fn)
off = Image.open(fnoff)
predict = np.array(predict)
off = np.array(off)
on = predict.copy()
predict = predict.flatten().reshape(1, predict.shape[0]*predict.shape[1])
predict = (np.array(predict, dtype='float')/255)
result = sess.run(y, feed_dict={x: predict})
result = result.reshape(result.shape[1:3])
imsave('/home/vkslm/playground/icdar-2017/imagens/output/%s' % '0000009194-out.png', 255-result)
imsave('/home/vkslm/playground/icdar-2017/imagens/output/%s' % '0000009194-on.png', 255-on)
imsave('/home/vkslm/playground/icdar-2017/imagens/output/%s' % '0000009194-off.png', 255-off)


# predict = Image.open('/home/vkslm/playground/datasets/IRONOFF-Subset/out/0000000000-on.png')

# # %%
# # Fit all training data
# batch_size = 64
# n_epochs = 100
# n_samples = 20000

# batch_data, batch_label = load_dataset(batch_size, n_epochs)

# sess.run(tf.global_variables_initializer())
# sess.run(tf.local_variables_initializer())
# tf.train.start_queue_runners(sess=sess)
# saver = tf.train.Saver()

# exp_folder = 'results_'+time.strftime('%d_%b_%H-%M-%S')
# os.mkdir(exp_folder)
# checkpoint_path = os.path.join(exp_folder, 'model.ckpt')
# for epoch_i in range(n_epochs):
#     nsteps = n_samples // batch_size
#     pbar = tqdm(total = n_samples, desc='Epoch %d' % epoch_i)
#     for batch_i in range(nsteps):
#         batch_data_flatten = tf.reshape(batch_data, [batch_size, h*w])
#         batch_label_flatten = tf.reshape(batch_label, [batch_size, h*w])

#         batch_xs, batch_ys = sess.run([batch_data_flatten, batch_label_flatten])
#         _, loss = sess.run([optimizer, cost], feed_dict={x: batch_xs, y_true: batch_ys})
#         pbar.set_postfix(loss=loss)
#         pbar.update(batch_size)

#     saver.save(sess, checkpoint_path, global_step=epoch_i)

#     folder = exp_folder+'/%05d' % epoch_i

#     os.mkdir(folder)
#     # shutil.copy2('/home/vkslm/playground/index-vae.html', folder+'/index.html')
#     recon = sess.run(y, feed_dict={x: batch_xs, y_true: batch_ys})
#     for i in range(recon.shape[0]):
#         plt.subplot(311)
#         plt.imshow(recon[i].reshape((h,w)))
#         plt.subplot(312)
#         plt.imshow(batch_ys[i].reshape(h,w))
#         plt.subplot(313)
#         plt.imshow(batch_xs[i].reshape(h,w))

#         filename = '%d.png' % (i)

#         filename = os.path.join(folder, filename)
#         plt.savefig(filename)

