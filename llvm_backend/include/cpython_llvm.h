#pragma once

#if defined(_WIN32) && defined(CPYTHON_LLVM_EXPORTS)
#  define CP_LLVM_API __declspec(dllexport)
#else
#  define CP_LLVM_API
#endif

#ifdef __cplusplus
extern "C" {
#endif

typedef void* CPJitEngine;

CP_LLVM_API CPJitEngine cp_jit_create(void);
CP_LLVM_API void        cp_jit_destroy(CPJitEngine eng);

CP_LLVM_API int cp_jit_compile_func(CPJitEngine eng,
                                    const char* name,
                                    const char* simple_ir,
                                    char* err,
                                    int errlen);

CP_LLVM_API long long cp_jit_call_i64(CPJitEngine eng,
                                      const char* name,
                                      const long long* args,
                                      int n);

CP_LLVM_API double cp_jit_call_f64(CPJitEngine eng,
                                   const char* name,
                                   const double* args,
                                   int n);

CP_LLVM_API int cp_jit_is_llvm(void);

#ifdef __cplusplus
}
#endif
