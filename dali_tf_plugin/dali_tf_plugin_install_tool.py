# Copyright (c) 2019, NVIDIA CORPORATION. All rights reserved.
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

import platform
from shutil import copyfile
from dali_tf_plugin_utils import *
import os

class InstallerHelper:
    def __init__(self):
        self.dali_lib_path = get_module_path('nvidia/dali')
        self.tf_path = get_module_path('tensorflow')
        self.plugin_dest_dir = self.dali_lib_path + '/plugin' if self.dali_lib_path else ''
        self.is_conda = is_conda_env()
        self.tf_version = get_tf_version()
        self.tf_compiler = get_tf_compiler_version()
        self.cpp_compiler = get_cpp_compiler()
        self.default_cpp_version = get_cpp_compiler_version()
        self.is_tf_built_with_cpp_4_8 = self.tf_compiler == '4.8'
        self.alt_compiler = 'g++-{}'.format(self.tf_compiler)
        self.has_alt_compiler = which(self.alt_compiler) is not None
        self.platform_system = platform.system()
        self.platform_machine = platform.machine()
        self.is_compatible_with_prebuilt_bin = self.platform_system == 'Linux' and self.platform_machine == 'x86_64'
        self.can_install_prebuilt = self.is_tf_built_with_cpp_4_8 and self.is_compatible_with_prebuilt_bin
        self.can_compile = self.default_cpp_version == self.tf_compiler
        self.src_path = os.path.dirname(os.path.realpath(__file__))

    def debug_str(self):
        s = "\n Environment:"
        s += "\n ---------------------------------------------------------------------------------------------------------"
        s += "\n Platform system:                      {}".format(self.platform_system)
        s += "\n Platform machine:                     {}".format(self.platform_machine)
        s += "\n DALI lib path:                        {}".format(self.dali_lib_path or "Not Installed")
        s += "\n TF path:                              {}".format(self.tf_path or "Not Installed")
        s += "\n DALI TF plugin destination directory: {}".format(self.plugin_dest_dir if self.dali_lib_path else "Not installed")
        s += "\n Is Conda environment?                 {}".format("Yes" if self.is_conda else "No")
        s += "\n TF version installed:                 {}".format(self.tf_version or "Empty")
        s += "\n g++ version used to compile TF:       {}".format(self.tf_compiler or "Empty")
        s += "\n Using compiler:                       \"{}\", version {}".format(self.cpp_compiler, self.default_cpp_version or "Empty")
        s += "\n Is TF compiled with g++ 4.8?          {}".format("Yes" if self.is_tf_built_with_cpp_4_8 else "No")
        s += "\n Is {} present in the system?     {}".format(self.alt_compiler, "Yes" if self.has_alt_compiler else "No")
        s += "\n Can install prebuilt plugin?          {}".format("Yes" if self.can_install_prebuilt else "No")
        s += "\n Can compile with default compiler?    {}".format("Yes" if self.can_compile else "No")
        s += "\n Can compile with alt compiler?        {}".format("Yes" if self.has_alt_compiler else "No")
        s += "\n---------------------------------------------------------------------------------------------------------"
        return s

    def install_prebuilt(self):
        assert(self.is_tf_built_with_cpp_4_8)
        assert(self.is_compatible_with_prebuilt_bin)
        tf_version_underscore = self.tf_version.replace('.', '_')
        plugin_name = 'libdali_tf_' + tf_version_underscore + '.so'
        prebuilt_plugin = self.src_path + '/' + plugin_name
        print("Tensorflow was built with g++ 4.8, providing prebuilt plugin")
        if not os.path.isfile(prebuilt_plugin):
            available_files = find('libdali_tf_*.so', self.src_path)
            best_version = find_available_prebuilt_tf(self.tf_version, available_files)
            if best_version is None:
                error_msg = "Installation error:"
                error_msg += '\n Prebuilt DALI TF plugin version {} is not present. Available files: {}'.format(prebuilt_plugin, ', '.join(available_files))
                error_msg += '\n' + self.debug_str()
                raise ImportError(error_msg)
            print("Prebuilt DALI TF plugin version {} is not present. Best match is {}".format(self.tf_version, best_version))
            tf_version_underscore = best_version.replace('.', '_')
            plugin_name = 'libdali_tf_' + tf_version_underscore + '.so'
            prebuilt_plugin = self.src_path + '/' + plugin_name
        plugin_dest = self.plugin_dest_dir + '/' + plugin_name
        print("Copy {} to {}".format(prebuilt_plugin, self.plugin_dest_dir))
        copyfile(prebuilt_plugin, plugin_dest)

    def install(self):
        print("Checking build environment for DALI TF plugin ...")
        print(self.debug_str())

        if self.tf_version == "":
            error_msg = "Installation error:"
            error_msg += "\n Tensorflow installation not found. Install `tensorflow-gpu` and try again"
            error_msg += '\n' + self.debug_str()
            raise ImportError(error_msg)

        if self.dali_lib_path == "":
            error_msg = "Installation error:"
            error_msg += "\n DALI installation not found. Install `nvidia-dali` and try again"
            error_msg += '\n' + self.debug_str()
            raise ImportError(error_msg)

        compiler = self.cpp_compiler

        # From tensorflow team (https://github.com/tensorflow/tensorflow/issues/29643):
        # Our pip packages are still built with gcc 4.8."
        # To make anything that uses C++ APIs work, all custom ops need to be built
        # with the same compiler (and the version) we use to build the pip packages.
        # Anything not built with that may break due to compilers generating ABIs differently."
        if self.is_tf_built_with_cpp_4_8 and self.is_compatible_with_prebuilt_bin:
            self.install_prebuilt()
            return

        if self.default_cpp_version != self.tf_compiler:
            if self.is_conda:
                error_msg = "Installation error:"
                error_msg += "\n Conda C++ compiler version should be the same as the compiler used to build tensorflow ({} != {}).".format(self.default_cpp_version, self.tf_compiler)
                error_msg += "\n Try to run `conda install gxx_linux-64=={}` or install an alternative compiler `g++-{}` and install again".format(self.tf_compiler, self.tf_compiler)
                error_msg += '\n' + self.debug_str()
                raise ImportError(error_msg)

            if self.has_alt_compiler:
                print("Will use alternative compiler {}".format(alt_compiler))
                compiler = self.alt_compiler

            else:
                error_msg = "Installation error:"
                error_msg += "\n Tensorflow was built with a different compiler than the currently installed ({} != {})".format(self.default_cpp_version, self.tf_compiler)
                error_msg += "\n Try to install `g++-{}` or use CXX environment variable to point to the right compiler and install again".format(self.tf_compiler)
                error_msg += '\n' + self.debug_str()
                raise ImportError(error_msg)

        print("Proceed with build...")
        dali_cflags, dali_lflags = get_dali_build_flags()
        tf_cflags, tf_lflags = get_tf_build_flags()
        cuda_cflags, cuda_lflags = get_cuda_build_flags()
        plugin_src = self.src_path + '/daliop.cc'
        lib_path = self.plugin_dest_dir + '/libdali_tf_current.so'
        cmd = compiler + ' -Wl,-R,\'$ORIGIN/..\' -std=c++11 -shared ' \
            + plugin_src + ' -o ' + lib_path + ' -fPIC ' + dali_cflags + ' ' \
            + tf_cflags + ' ' + cuda_cflags + ' ' + dali_lflags + ' ' + tf_lflags + ' ' \
            + cuda_lflags + ' -O2'
        print("Build command:\n\n " + cmd + '\n\n')
        subprocess.check_call(cmd, cwd=self.src_path, shell=True)


def main():
    env = InstallerHelper()
    env.install()

if __name__ == "__main__":
    main()
