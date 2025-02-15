// Copyright (c) 2019, NVIDIA CORPORATION. All rights reserved.
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

#ifndef DALI_PIPELINE_OPERATORS_DECODER_NVJPEG_DECOUPLED_API_FUSED_NVJPEG_DECODER_CPU_SLICE_H_
#define DALI_PIPELINE_OPERATORS_DECODER_NVJPEG_DECOUPLED_API_FUSED_NVJPEG_DECODER_CPU_SLICE_H_

#include <vector>
#include "dali/pipeline/operators/decoder/nvjpeg/decoupled_api/nvjpeg_decoder_cpu.h"
#include "dali/pipeline/operators/crop/slice_attr.h"

namespace dali {

class nvJPEGDecoderCPUStageSlice : public nvJPEGDecoderCPUStage, public SliceAttr {
 public:
  explicit nvJPEGDecoderCPUStageSlice(const OpSpec& spec)
    : nvJPEGDecoderCPUStage(spec)
    , SliceAttr(spec)
  {}

  DISABLE_COPY_MOVE_ASSIGN(nvJPEGDecoderCPUStageSlice);

 protected:
  using Operator<CPUBackend>::RunImpl;
  void RunImpl(SampleWorkspace &ws) override {
    SliceAttr::ProcessArguments(ws);
    nvJPEGDecoderCPUStage::RunImpl(ws);
  }

  CropWindowGenerator GetCropWindowGenerator(int data_idx) const override {
    return SliceAttr::GetCropWindowGenerator(data_idx);
  }
};

}  // namespace dali

#endif  // DALI_PIPELINE_OPERATORS_DECODER_NVJPEG_DECOUPLED_API_FUSED_NVJPEG_DECODER_CPU_SLICE_H_
