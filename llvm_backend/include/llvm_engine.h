#pragma once
/*
 * Motore LLVM ORC JIT reale.
 * Compilato solo se CPYTHON_HAS_LLVM è definito (find_package LLVM riuscito).
 */

#include "ir_format.h"

#include <memory>
#include <string>

namespace cpython_llvm {

class LlvmEngine {
public:
  static std::unique_ptr<LlvmEngine> create();
  virtual ~LlvmEngine() = default;

  virtual bool compile(const FuncIR& fn, std::string& err) = 0;
  virtual bool has(const std::string& name) const = 0;
  virtual int64_t call_i64(const std::string& name, const int64_t* args, int n,
                           std::string& err) = 0;
  virtual double call_f64(const std::string& name, const double* args, int n,
                          std::string& err) = 0;
};

} // namespace cpython_llvm
