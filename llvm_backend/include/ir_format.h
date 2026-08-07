#pragma once

#include <cstdint>
#include <string>
#include <unordered_map>
#include <vector>

namespace cpython_llvm {

enum class Ty { I64, F64, Bool };

struct Operand {
  enum Kind { ImmI, ImmF, ImmB, Name } kind = Name;
  int64_t i = 0;
  double f = 0.0;
  bool b = false;
  std::string name;
};

struct Instr {
  enum Op {
    Mov,
    Add,
    Sub,
    Mul,
    Div,
    Mod,
    Neg,
    Not,
    Eq,
    Ne,
    Lt,
    Le,
    Gt,
    Ge,
    And,
    Or,
    Jump,
    JumpIf,
    JumpIfNot,
    Label,
    Ret,
    PhiPlaceholder
  } op = Mov;
  std::string dest;
  Operand a, b;
  std::string target; // jump label
};

struct FuncIR {
  std::string name;
  Ty ret = Ty::I64;
  std::vector<std::pair<std::string, Ty>> params;
  std::vector<Instr> code;
};

// Parse simple three-address IR (see docs in ir_builder.cpp).
bool parse_simple_ir(const std::string& text, FuncIR& out, std::string& err);

Ty parse_ty(const std::string& s, std::string& err);

} // namespace cpython_llvm
