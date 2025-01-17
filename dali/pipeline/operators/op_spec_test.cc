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

#include <gtest/gtest.h>

#include "dali/core/common.h"
#include "dali/pipeline/data/backend.h"
#include "dali/pipeline/data/buffer.h"
#include "dali/pipeline/data/tensor.h"
#include "dali/pipeline/operators/operator.h"
#include "dali/pipeline/pipeline.h"
#include "dali/pipeline/workspace/workspace.h"
#include "dali/test/dali_test.h"

namespace dali {

class TestArgumentInput_Producer : public Operator<SupportBackend> {
 public:
  explicit TestArgumentInput_Producer(const OpSpec &spec) : Operator<SupportBackend>(spec) {}

  bool CanInferOutputs() const override {
    return true;
  }

  bool SetupImpl(std::vector<OutputDesc> &output_desc, const SupportWorkspace &ws) override {
    output_desc.resize(4);
    output_desc[0] = {kernels::uniform_list_shape(batch_size_, {1}), TypeInfo::Create<int>()};
    output_desc[1] = {kernels::TensorListShape<>{{10}}, TypeInfo::Create<float>()};
    // Non-matching shapes
    output_desc[2] = {kernels::uniform_list_shape(batch_size_ + 5, {1}), TypeInfo::Create<int>()};
    output_desc[3] = {kernels::uniform_list_shape(batch_size_, {1, 2}), TypeInfo::Create<int>()};
    return true;
  }

  void RunImpl(SupportWorkspace &ws) override {
    // Initialize all the data with a 0, 1, 2 .... sequence
    auto &out0 = ws.OutputRef<CPUBackend>(0);
    for (int i = 0; i < out0.shape().num_samples(); i++) {
      *out0.mutable_tensor<int>(i) = i;
    }

    auto &out1 = ws.OutputRef<CPUBackend>(1);
    for (int i = 0; i < out1.shape()[0][0]; i++) {
      out1.mutable_data<float>()[i] = i;
    }

    auto &out2 = ws.OutputRef<CPUBackend>(2);
    for (int i = 0; i < out2.shape().num_samples(); i++) {
      *out2.mutable_tensor<int>(i) = i;
    }

    auto &out3 = ws.OutputRef<CPUBackend>(3);
    for (int i = 0; i < out3.shape().num_samples(); i++) {
      for (int j = 0; j < 2; j++) {
        out3.mutable_tensor<int>(i)[j] = i;
      }
    }
  }
};

DALI_REGISTER_OPERATOR(TestArgumentInput_Producer, TestArgumentInput_Producer, Support);

DALI_SCHEMA(TestArgumentInput_Producer)
    .DocStr("TestArgumentInput_Producer")
    .NumInput(0)
    .NumOutput(4);

class TestArgumentInput_Consumer : public Operator<CPUBackend> {
 public:
  explicit TestArgumentInput_Consumer(const OpSpec &spec) : Operator<CPUBackend>(spec) {}

  bool CanInferOutputs() const override {
    return true;
  }

  bool SetupImpl(std::vector<OutputDesc> &output_desc, const HostWorkspace &ws) override {
    output_desc.resize(1);
    output_desc[0] = {kernels::uniform_list_shape(batch_size_, {1}), TypeInfo::Create<int>()};
    return true;
  }

  void RunImpl(HostWorkspace &ws) override {
    for (int i = 0; i < batch_size_; i++) {
      EXPECT_EQ(spec_.GetArgument<int>("arg0", &ws, i), i);
      EXPECT_EQ(spec_.GetArgument<float>("arg1", &ws, i), i);
    }
    // Non-matching shapes (differnet than 1 scalar value per sample) should not work with
    // OpSpec::GetArgument()
    ASSERT_THROW(auto z = spec_.GetArgument<float>("arg2", &ws, 0), std::runtime_error);
    ASSERT_THROW(auto z = spec_.GetArgument<float>("arg3", &ws, 0), std::runtime_error);

    // They can be accessed as proper ArgumentInputs
    auto &ref_2 = ws.ArgumentInput("arg2");
    ASSERT_EQ(ref_2.shape().num_samples(), batch_size_ + 5);
    ASSERT_TRUE(kernels::is_uniform(ref_2.shape()));
    ASSERT_EQ(ref_2.shape()[0], kernels::TensorShape<>(1));
    for (int i = 0; i < ref_2.shape().num_samples(); i++) {
      EXPECT_EQ(ref_2.tensor<int>(i)[0], i);
    }

    auto &ref_3 = ws.ArgumentInput("arg3");
    ASSERT_EQ(ref_3.shape().num_samples(), batch_size_);
    ASSERT_TRUE(kernels::is_uniform(ref_3.shape()));
    ASSERT_EQ(ref_3.shape()[0], kernels::TensorShape<>(1, 2));
    for (int i = 0; i < ref_3.shape().num_samples(); i++) {
      for (int j = 0; j < 2; j++) {
        EXPECT_EQ(ref_3.tensor<int>(i)[j], i);
      }
    }
  }
};

DALI_REGISTER_OPERATOR(TestArgumentInput_Consumer, TestArgumentInput_Consumer, CPU);

DALI_SCHEMA(TestArgumentInput_Consumer)
    .DocStr("TestArgumentInput_Consumer")
    .NumInput(0)
    .NumOutput(1)
    .AddOptionalArg("arg0", "no-doc", 42, true)
    .AddOptionalArg("arg1", "no-doc", 42.f, true)
    .AddOptionalArg("arg2", "no-doc", 42, true)
    .AddOptionalArg("arg3", "no-doc", 42, true);

/*
 * This test is based on test operators implemented specifically for the purpose of testing
 * the access to argument inputs.
 *
 * The EXPECT_* and ASSERT_* macros are actually placed in the RunImpl of operator
 * accessing the data (TestArgumentInput_Consumer), and the different (valid and invalid)
 * arguments inputs are provided by a SupportOp: TestArgumentInput_Producer.
 */
TEST(ArgumentInputTest, OpSpecAccess) {
  Pipeline pipe(10, 4, 0);
  pipe.AddOperator(OpSpec("TestArgumentInput_Producer")
                       .AddArg("device", "support")
                       .AddOutput("support_arg0", "cpu")
                       .AddOutput("support_arg1", "cpu")
                       .AddOutput("support_arg2", "cpu")
                       .AddOutput("support_arg3", "cpu"));

  pipe.AddOperator(OpSpec("TestArgumentInput_Consumer")
                       .AddArg("device", "cpu")
                       .AddArgumentInput("arg0", "support_arg0")
                       .AddArgumentInput("arg1", "support_arg1")
                       .AddArgumentInput("arg2", "support_arg2")
                       .AddArgumentInput("arg3", "support_arg3")
                       .AddOutput("I need to specify something", "cpu")
                       .AddArg("preserve", true));

  vector<std::pair<string, string>> outputs = {{"I need to specify something", "cpu"}};
  pipe.Build(outputs);

  pipe.RunCPU();
  pipe.RunGPU();

  DeviceWorkspace ws;
  pipe.Outputs(&ws);
}

}  // namespace dali
