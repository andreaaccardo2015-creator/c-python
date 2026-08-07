#include "ir_format.h"

#include <cctype>
#include <sstream>

namespace cpython_llvm {
namespace {

std::string trim(const std::string& s) {
  size_t a = 0, b = s.size();
  while (a < b && std::isspace(static_cast<unsigned char>(s[a]))) ++a;
  while (b > a && std::isspace(static_cast<unsigned char>(s[b - 1]))) --b;
  return s.substr(a, b - a);
}

std::vector<std::string> split_ws(const std::string& line) {
  std::vector<std::string> out;
  std::istringstream iss(line);
  std::string tok;
  while (iss >> tok) out.push_back(tok);
  return out;
}

bool parse_operand(const std::string& tok, Operand& op, std::string& err) {
  if (tok == "true") {
    op.kind = Operand::ImmB;
    op.b = true;
    return true;
  }
  if (tok == "false") {
    op.kind = Operand::ImmB;
    op.b = false;
    return true;
  }
  // float?
  bool is_num = !tok.empty() && (std::isdigit(static_cast<unsigned char>(tok[0])) ||
                                 tok[0] == '-' || tok[0] == '+');
  if (is_num) {
    if (tok.find('.') != std::string::npos) {
      op.kind = Operand::ImmF;
      op.f = std::stod(tok);
    } else {
      op.kind = Operand::ImmI;
      op.i = std::stoll(tok);
    }
    return true;
  }
  op.kind = Operand::Name;
  op.name = tok;
  return true;
}

Instr::Op bin_op(const std::string& s) {
  if (s == "add") return Instr::Add;
  if (s == "sub") return Instr::Sub;
  if (s == "mul") return Instr::Mul;
  if (s == "div") return Instr::Div;
  if (s == "mod") return Instr::Mod;
  if (s == "eq") return Instr::Eq;
  if (s == "ne") return Instr::Ne;
  if (s == "lt") return Instr::Lt;
  if (s == "le") return Instr::Le;
  if (s == "gt") return Instr::Gt;
  if (s == "ge") return Instr::Ge;
  if (s == "and") return Instr::And;
  if (s == "or") return Instr::Or;
  return Instr::Mov;
}

} // namespace

Ty parse_ty(const std::string& s, std::string& err) {
  if (s == "i64" || s == "int") return Ty::I64;
  if (s == "f64" || s == "float") return Ty::F64;
  if (s == "bool" || s == "i1") return Ty::Bool;
  err = "tipo sconosciuto: " + s;
  return Ty::I64;
}

bool parse_simple_ir(const std::string& text, FuncIR& out, std::string& err) {
  out = FuncIR{};
  std::istringstream in(text);
  std::string line;
  bool in_block = false;
  while (std::getline(in, line)) {
    line = trim(line);
    if (line.empty() || line[0] == '#' || line[0] == ';') continue;
    auto parts = split_ws(line);
    if (parts.empty()) continue;

    if (parts[0] == "fun") {
      if (parts.size() < 2) {
        err = "fun richiede un nome";
        return false;
      }
      out.name = parts[1];
      continue;
    }
    if (parts[0] == "rettype" || (parts[0] == "ret" && !in_block)) {
      if (parts.size() < 2) {
        err = "rettype richiede un tipo";
        return false;
      }
      err.clear();
      out.ret = parse_ty(parts[1], err);
      if (!err.empty()) return false;
      continue;
    }
    if (parts[0] == "param") {
      if (parts.size() < 3) {
        err = "param nome tipo";
        return false;
      }
      err.clear();
      Ty t = parse_ty(parts[2], err);
      if (!err.empty()) return false;
      out.params.emplace_back(parts[1], t);
      continue;
    }
    if (parts[0] == "block") {
      in_block = true;
      continue;
    }
    if (parts[0] == "end") {
      in_block = false;
      continue;
    }
    if (!in_block) {
      err = "istruzione fuori da block: " + line;
      return false;
    }

    // label:
    if (parts[0].back() == ':' && parts.size() == 1) {
      Instr ins;
      ins.op = Instr::Label;
      ins.target = parts[0].substr(0, parts[0].size() - 1);
      out.code.push_back(ins);
      continue;
    }

    if (parts[0] == "jmp") {
      Instr ins;
      ins.op = Instr::Jump;
      if (parts.size() < 2) {
        err = "jmp label";
        return false;
      }
      ins.target = parts[1];
      out.code.push_back(ins);
      continue;
    }
    if (parts[0] == "jz" || parts[0] == "jnz") {
      Instr ins;
      ins.op = parts[0] == "jz" ? Instr::JumpIfNot : Instr::JumpIf;
      if (parts.size() < 3) {
        err = "jz/jnz cond label";
        return false;
      }
      if (!parse_operand(parts[1], ins.a, err)) return false;
      ins.target = parts[2];
      out.code.push_back(ins);
      continue;
    }
    if (parts[0] == "ret") {
      Instr ins;
      ins.op = Instr::Ret;
      if (parts.size() >= 2) {
        if (!parse_operand(parts[1], ins.a, err)) return false;
      } else {
        ins.a.kind = Operand::ImmI;
        ins.a.i = 0;
      }
      out.code.push_back(ins);
      continue;
    }
    if (parts[0] == "neg" || parts[0] == "not") {
      // dest = neg a
      if (parts.size() < 4 || parts[2] != "=") {
        err = "dest = neg/not src";
        return false;
      }
      Instr ins;
      ins.op = parts[0] == "neg" ? Instr::Neg : Instr::Not;
      // Actually format: t0 = neg a  → parts: t0 = neg a — wait our format is "t0 = neg a"
    }

    // Three-address: dest = op a [b]
    // or: dest = a  (mov)
    if (parts.size() >= 3 && parts[1] == "=") {
      Instr ins;
      ins.dest = parts[0];
      if (parts.size() == 3) {
        ins.op = Instr::Mov;
        if (!parse_operand(parts[2], ins.a, err)) return false;
      } else if (parts.size() == 4) {
        // dest = neg a | dest = not a
        if (parts[2] == "neg") {
          ins.op = Instr::Neg;
          if (!parse_operand(parts[3], ins.a, err)) return false;
        } else if (parts[2] == "not") {
          ins.op = Instr::Not;
          if (!parse_operand(parts[3], ins.a, err)) return false;
        } else {
          err = "unary op sconosciuto: " + parts[2];
          return false;
        }
      } else if (parts.size() == 5) {
        ins.op = bin_op(parts[2]);
        if (parts[2] != "mov" && parts[2] != "add" && parts[2] != "sub" && parts[2] != "mul" &&
            parts[2] != "div" && parts[2] != "mod" && parts[2] != "eq" && parts[2] != "ne" &&
            parts[2] != "lt" && parts[2] != "le" && parts[2] != "gt" && parts[2] != "ge" &&
            parts[2] != "and" && parts[2] != "or") {
          err = "op sconosciuto: " + parts[2];
          return false;
        }
        if (parts[2] == "mov") ins.op = Instr::Mov;
        if (!parse_operand(parts[3], ins.a, err)) return false;
        if (!parse_operand(parts[4], ins.b, err)) return false;
      } else {
        err = "formato istruzione non valido: " + line;
        return false;
      }
      out.code.push_back(ins);
      continue;
    }

    err = "riga IR non riconosciuta: " + line;
    return false;
  }

  if (out.name.empty()) {
    err = "manca direttiva fun";
    return false;
  }
  return true;
}

} // namespace cpython_llvm
