#include "cpython_llvm.h"

#include <cstdio>
#include <cstring>

int main() {
  CPJitEngine eng = cp_jit_create();
  const char* ir =
      "fun add\n"
      "rettype i64\n"
      "param a i64\n"
      "param b i64\n"
      "block\n"
      "t0 = add a b\n"
      "ret t0\n"
      "end\n";
  char err[256];
  int rc = cp_jit_compile_func(eng, "add", ir, err, 256);
  if (rc != 0) {
    std::printf("compile failed: %s\n", err);
    cp_jit_destroy(eng);
    return 1;
  }
  long long args[2] = {2, 5};
  long long r = cp_jit_call_i64(eng, "add", args, 2);
  std::printf("add(2,5)=%lld llvm=%d\n", r, cp_jit_is_llvm());
  cp_jit_destroy(eng);
  return r == 7 ? 0 : 2;
}
