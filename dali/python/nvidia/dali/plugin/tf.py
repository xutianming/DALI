# Copyright (c) 2017-2018, NVIDIA CORPORATION. All rights reserved.
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

import tensorflow as tf
import os
import glob
from collections import Iterable
import re

_tf_plugins = glob.glob(os.path.join(os.path.dirname(os.path.realpath(__file__)), 'libdali_tf*.so'))
_dali_tf_module = None
# Order: 'current', prebuilt for current TF version, prebuilt for other TF versions
_tf_version = re.search("(\d+.\d+).\d+", tf.__version__).group(1)
_tf_version_underscore = _tf_version.replace('.', '_')
_dali_tf_current = list(filter(lambda x: 'current' in x, _tf_plugins))
_dali_tf_prebuilt_tf_ver = list(filter(lambda x: _tf_version_underscore in x, _tf_plugins))
_dali_tf_prebuilt_others = list(filter(lambda x: 'current' not in x and _tf_version_underscore not in x, _tf_plugins))
_processed_tf_plugins = _dali_tf_current + _dali_tf_prebuilt_tf_ver + _dali_tf_prebuilt_others

first_error = None
for _libdali_tf in _processed_tf_plugins:
  try:
    _dali_tf_module = tf.load_op_library(_libdali_tf)
    break
  # if plugin is not compatible skip it
  except tf.errors.NotFoundError as error:
    if first_error == None:
      first_error = error
else:
  raise first_error or Exception('No matching DALI plugin found for installed TensorFlow version')

_dali_tf = _dali_tf_module.dali

def DALIIteratorWrapper(pipeline = None, serialized_pipeline = None, sparse = [],
                        shapes = [], dtypes = [], batch_size = -1, prefetch_queue_depth = 2, **kwargs):
  """
TF Plugin Wrapper

This operator works in the same way as DALI TensorFlow plugin, with the exception that is also accepts Pipeline objects as the input and serializes it internally. For more information, please look **TensorFlow Plugin API reference** in the documentation.
  """
  if type(prefetch_queue_depth) is dict:
      exec_separated = True
      cpu_prefetch_queue_depth = prefetch_queue_depth["cpu_size"]
      gpu_prefetch_queue_depth = prefetch_queue_depth["gpu_size"]
  elif type(prefetch_queue_depth) is int:
      exec_separated = False
      cpu_prefetch_queue_depth = -1 # dummy: wont' be used
      gpu_prefetch_queue_depth = prefetch_queue_depth

  if serialized_pipeline is None:
    serialized_pipeline = pipeline.serialize()

  # if batch_size is not provided we need to extract if from the shape arg
  if (not isinstance(shapes, Iterable) or len(shapes) == 0) and batch_size == -1:
    raise Exception('shapes and batch_size arguments cannot be empty, '
                    'please provide at leas one shape argument element with the BATCH size or set batch_size')

  if len(sparse) > 0 and sparse[0] and batch_size == -1:
    if isinstance(shapes[0], Iterable) and len(shapes[0]) == 1:
      shapes[0] = (shapes[0][0], 1)
    else:
      shapes[0] = (shapes[0], 1)

  # shapes and dtypes need to take into account that sparse tensor will produce 3 output tensors
  new_dtypes = []
  new_shapes = []
  for i in range(len(dtypes)):
    if i < len(sparse) and sparse[i]:
      # indices type of sparse tensor is tf.int64
      new_dtypes.append(tf.int64)
      new_dtypes.append(dtypes[i])
      # dense shape type of sparse tensor is tf.int64
      new_dtypes.append(tf.int64)
      if len(shapes) > i and len(shapes[i]) > 0:
        new_shapes.append((shapes[i][0], 1))
        new_shapes.append((shapes[i][0]))
      else:
        new_shapes.append(())
        new_shapes.append(())
      new_shapes.append(())
    else:
      new_dtypes.append(dtypes[i])
      if len(shapes) > i:
        new_shapes.append(shapes[i])

  # gpu_prefetch_queue_depth correspond to the global queue depth in the uniform case
  out = _dali_tf(serialized_pipeline=serialized_pipeline, shapes=new_shapes, dtypes=new_dtypes, sparse=sparse, batch_size=batch_size,
                 exec_separated=exec_separated, gpu_prefetch_queue_depth=gpu_prefetch_queue_depth, cpu_prefetch_queue_depth=cpu_prefetch_queue_depth, **kwargs)
  new_out = []
  j = 0
  for i in range(len(dtypes)):
    if i < len(sparse) and sparse[i]:
      new_out.append(tf.SparseTensor(indices=out[j], values=out[j + 1], dense_shape=out[j + 2]))
      j += 3
    else:
      new_out.append(out[j])
      j += 1
  return new_out

def DALIIterator():
    return DALIIteratorWrapper

# Vanilla raw operator legacy
def DALIRawIterator():
    return _dali_tf


DALIIterator.__doc__ = DALIIteratorWrapper.__doc__
DALIRawIterator.__doc__ = _dali_tf.__doc__
