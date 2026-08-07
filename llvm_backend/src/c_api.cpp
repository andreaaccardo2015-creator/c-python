#include "cpython_llvm.h"
#include "ir_format.h"
#include "stub_engine.h"

#include <cstdio>
#include <cstring>
#include <memory>
#include <string>
#include <unordered_map>

#if defined(CPYTHON_HAS_LLVM)
#  include "llvm_engine.h"
#endif

struct EngineBox {
  cpython_llvm::StubEngine stub;
#if defined(CPYTHON_HAS_LLVM)
  std::unique_ptr<cpython_llvm::LlvmEngine> llvm;
  bool use_llvm = false;
#endif
  std::unordered_map<std::string, cpython_llvm::Ty> ret_types;
};

static void set_err(char* err, int errlen, const std::string& msg) {
  if (!err || errlen <= 0) return;
  std::snprintf(err, static_cast<size_t>(errlen), "%s", msg.c_str());
}

extern "C" {

CP_LLVM_API CPJitEngine cp_jit_create(void) {
  auto* box = new EngineBox();
#if defined(CPYTHON_HAS_LLVM)
  box->llvm = cpython_llvm::LlvmEngine::create();
  box->use_llvm = static_cast<bool>(box->llvm);
#endif
  return box;
}

CP_LLVM_API void cp_jit_destroy(CPJitEngine eng) {
  delete static_cast<EngineBox*>(eng);
}

CP_LLVM_API int cp_jit_is_llvm(void) {
#if defined(CPYTHON_HAS_LLVM)
  return 1;
#else
  return 0;
#endif
}

CP_LLVM_API int cp_jit_compile_func(CPJitEngine eng, const char* name, const char* simple_ir,
                                    char* err, int errlen) {
  if (!eng || !simple_ir) {
    set_err(err, errlen, "argomenti null");
    return 1;
  }
  auto* box = static_cast<EngineBox*>(eng);
  cpython_llvm::FuncIR fn;
  std::string perr;
  if (!cpython_llvm::parse_simple_ir(simple_ir, fn, perr)) {
    set_err(err, errlen, perr);
    return 2;
  }
  if (name && *name) fn.name = name;

#if defined(CPYTHON_HAS_LLVM)
  if (box->use_llvm && box->llvm) {
    if (box->llvm->compile(fn, perr)) {
      box->ret_types[fn.name] = fn.ret;
      set_err(err, errlen, "");
      return 0;
    }
  }
#endif
  if (!box->stub.compile(fn, perr)) {
    set_err(err, errlen, perr.empty() ? "compile stub failed" : perr);
    return 3;
  }
  box->ret_types[fn.name] = fn.ret;
  set_err(err, errlen, "");
  return 0;
}

CP_LLVM_API long long cp_jit_call_i64(CPJitEngine eng, const char* name, const long long* args,
                                      int n) {
  auto* box = static_cast<EngineBox*>(eng);
  std::string err;
#if defined(CPYTHON_HAS_LLVM)
  if (box->use_llvm && box->llvm && box->llvm->has(name)) {
    return box->llvm->call_i64(name, args, n, err);
  }
#endif
  return box->stub.call_i64(name, args, n, err);
}

CP_LLVM_API double cp_jit_call_f64(CPJitEngine eng, const char* name, const double* args, int n) {
  auto* box = static_cast<EngineBox*>(eng);
  std::string err;
#if defined(CPYTHON_HAS_LLVM)
  if (box->use_llvm && box->llvm && box->llvm->has(name)) {
    return box->llvm->call_f64(name, args, n, err);
  }
#endif
  return box->stub.call_f64(name, args, n, err);
}

} // extern "C"
