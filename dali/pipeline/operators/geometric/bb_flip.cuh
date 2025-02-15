// Copyright (c) 2017-2018, NVIDIA CORPORATION. All rights reserved.
//
// Licensed under the Apache License, Version 2.0 (the "License");
// you may not use this file except in compliance with the License.
// You may obtain a copy of the License at
//
//     http://www.apache.org/licenses/LICENSE-2.0
//
// Unless required by applicable law or agreed to in writing, software
// distributed under the License is distributed on an "AS IS" BASIS,
// WITHOUT WARRANTIES OR CONDITIONS OF ANY KIND, either express or implied.
// See the License for the specific language governing permissions and
// limitations under the License.

#ifndef DALI_PIPELINE_OPERATORS_GEOMETRIC_BB_FLIP_CUH_
#define DALI_PIPELINE_OPERATORS_GEOMETRIC_BB_FLIP_CUH_

#include <vector>

#include "dali/pipeline/operators/geometric/bb_flip.h"

namespace dali {

template <>
class BbFlip<GPUBackend> : public Operator<GPUBackend> {
 public:
  explicit BbFlip(const OpSpec &spec) : Operator<GPUBackend>(spec) {}

  bool SetupImpl(std::vector<OutputDesc> &output_desc, const DeviceWorkspace &ws) override {
    return false;
  }

  void RunImpl(Workspace<GPUBackend> &ws) override;
 private:
};

}  // namespace dali

#endif  // DALI_PIPELINE_OPERATORS_GEOMETRIC_BB_FLIP_CUH_
