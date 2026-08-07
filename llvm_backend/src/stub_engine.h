#include "ir_format.h"

#include <cmath>
#include <stdexcept>
#include <string>
#include <unordered_map>
#include <variant>
#include <vector>

namespace cpython_llvm {

using Value = std::variant<int64_t, double, bool>;

class StubEngine {
public:
  bool compile(const FuncIR& fn, std::string& err) {
    funcs_[fn.name] = fn;
    return true;
  }

  bool has(const std::string& name) const { return funcs_.count(name) != 0; }

  const FuncIR* get(const std::string& name) const {
    auto it = funcs_.find(name);
    return it == funcs_.end() ? nullptr : &it->second;
  }

  int64_t call_i64(const std::string& name, const int64_t* args, int n, std::string& err) {
    Value v = call(name, args, nullptr, n, /*prefer_f64*/ false, err);
    if (!err.empty()) return 0;
    if (std::holds_alternative<int64_t>(v)) return std::get<int64_t>(v);
    if (std::holds_alternative<bool>(v)) return std::get<bool>(v) ? 1 : 0;
    if (std::holds_alternative<double>(v)) return static_cast<int64_t>(std::get<double>(v));
    return 0;
  }

  double call_f64(const std::string& name, const double* args, int n, std::string& err) {
    Value v = call(name, nullptr, args, n, /*prefer_f64*/ true, err);
    if (!err.empty()) return 0.0;
    if (std::holds_alternative<double>(v)) return std::get<double>(v);
    if (std::holds_alternative<int64_t>(v)) return static_cast<double>(std::get<int64_t>(v));
    if (std::holds_alternative<bool>(v)) return std::get<bool>(v) ? 1.0 : 0.0;
    return 0.0;
  }

private:
  std::unordered_map<std::string, FuncIR> funcs_;

  static double as_f(const Value& v) {
    if (std::holds_alternative<double>(v)) return std::get<double>(v);
    if (std::holds_alternative<int64_t>(v)) return static_cast<double>(std::get<int64_t>(v));
    if (std::holds_alternative<bool>(v)) return std::get<bool>(v) ? 1.0 : 0.0;
    return 0.0;
  }

  static int64_t as_i(const Value& v) {
    if (std::holds_alternative<int64_t>(v)) return std::get<int64_t>(v);
    if (std::holds_alternative<double>(v)) return static_cast<int64_t>(std::get<double>(v));
    if (std::holds_alternative<bool>(v)) return std::get<bool>(v) ? 1 : 0;
    return 0;
  }

  static bool as_b(const Value& v) {
    if (std::holds_alternative<bool>(v)) return std::get<bool>(v);
    if (std::holds_alternative<int64_t>(v)) return std::get<int64_t>(v) != 0;
    if (std::holds_alternative<double>(v)) return std::get<double>(v) != 0.0;
    return false;
  }

  Value load_op(const Operand& op, std::unordered_map<std::string, Value>& env, std::string& err) {
    switch (op.kind) {
      case Operand::ImmI: return op.i;
      case Operand::ImmF: return op.f;
      case Operand::ImmB: return op.b;
      case Operand::Name: {
        auto it = env.find(op.name);
        if (it == env.end()) {
          err = "variabile IR sconosciuta: " + op.name;
          return int64_t{0};
        }
        return it->second;
      }
    }
    return int64_t{0};
  }

  Value call(const std::string& name, const int64_t* iargs, const double* fargs, int n,
             bool prefer_f64, std::string& err) {
    auto it = funcs_.find(name);
    if (it == funcs_.end()) {
      err = "funzione non compilata: " + name;
      return int64_t{0};
    }
    const FuncIR& fn = it->second;
    if (n != static_cast<int>(fn.params.size())) {
      err = "numero argomenti errato";
      return int64_t{0};
    }

    std::unordered_map<std::string, Value> env;
    for (int i = 0; i < n; ++i) {
      Ty t = fn.params[i].second;
      if (t == Ty::F64) {
        double v = fargs ? fargs[i] : static_cast<double>(iargs[i]);
        env[fn.params[i].first] = v;
      } else if (t == Ty::Bool) {
        int64_t v = iargs ? iargs[i] : static_cast<int64_t>(fargs[i]);
        env[fn.params[i].first] = (v != 0);
      } else {
        int64_t v = iargs ? iargs[i] : static_cast<int64_t>(fargs[i]);
        env[fn.params[i].first] = v;
      }
    }

    // Build label map
    std::unordered_map<std::string, size_t> labels;
    for (size_t i = 0; i < fn.code.size(); ++i) {
      if (fn.code[i].op == Instr::Label) labels[fn.code[i].target] = i;
    }

    size_t pc = 0;
    while (pc < fn.code.size()) {
      const Instr& ins = fn.code[pc];
      switch (ins.op) {
        case Instr::Label:
          ++pc;
          break;
        case Instr::Jump: {
          auto lit = labels.find(ins.target);
          if (lit == labels.end()) {
            err = "label mancante: " + ins.target;
            return int64_t{0};
          }
          pc = lit->second;
          break;
        }
        case Instr::JumpIf:
        case Instr::JumpIfNot: {
          Value c = load_op(ins.a, env, err);
          if (!err.empty()) return int64_t{0};
          bool truth = as_b(c);
          if ((ins.op == Instr::JumpIf && truth) || (ins.op == Instr::JumpIfNot && !truth)) {
            auto lit = labels.find(ins.target);
            if (lit == labels.end()) {
              err = "label mancante: " + ins.target;
              return int64_t{0};
            }
            pc = lit->second;
          } else {
            ++pc;
          }
          break;
        }
        case Instr::Ret: {
          return load_op(ins.a, env, err);
        }
        case Instr::Mov: {
          env[ins.dest] = load_op(ins.a, env, err);
          ++pc;
          break;
        }
        case Instr::Neg: {
          Value a = load_op(ins.a, env, err);
          if (std::holds_alternative<double>(a)) env[ins.dest] = -as_f(a);
          else env[ins.dest] = -as_i(a);
          ++pc;
          break;
        }
        case Instr::Not: {
          env[ins.dest] = !as_b(load_op(ins.a, env, err));
          ++pc;
          break;
        }
        case Instr::Add:
        case Instr::Sub:
        case Instr::Mul:
        case Instr::Div:
        case Instr::Mod: {
          Value va = load_op(ins.a, env, err);
          Value vb = load_op(ins.b, env, err);
          bool use_f = prefer_f64 || std::holds_alternative<double>(va) ||
                       std::holds_alternative<double>(vb);
          if (use_f) {
            double a = as_f(va), b = as_f(vb);
            double r = 0;
            if (ins.op == Instr::Add) r = a + b;
            else if (ins.op == Instr::Sub) r = a - b;
            else if (ins.op == Instr::Mul) r = a * b;
            else if (ins.op == Instr::Div) r = a / b;
            else r = std::fmod(a, b);
            env[ins.dest] = r;
          } else {
            int64_t a = as_i(va), b = as_i(vb);
            int64_t r = 0;
            if (ins.op == Instr::Add) r = a + b;
            else if (ins.op == Instr::Sub) r = a - b;
            else if (ins.op == Instr::Mul) r = a * b;
            else if (ins.op == Instr::Div) r = b ? a / b : 0;
            else r = b ? a % b : 0;
            env[ins.dest] = r;
          }
          ++pc;
          break;
        }
        case Instr::Eq:
        case Instr::Ne:
        case Instr::Lt:
        case Instr::Le:
        case Instr::Gt:
        case Instr::Ge: {
          Value va = load_op(ins.a, env, err);
          Value vb = load_op(ins.b, env, err);
          bool use_f = std::holds_alternative<double>(va) || std::holds_alternative<double>(vb);
          bool r = false;
          if (use_f) {
            double a = as_f(va), b = as_f(vb);
            if (ins.op == Instr::Eq) r = a == b;
            else if (ins.op == Instr::Ne) r = a != b;
            else if (ins.op == Instr::Lt) r = a < b;
            else if (ins.op == Instr::Le) r = a <= b;
            else if (ins.op == Instr::Gt) r = a > b;
            else r = a >= b;
          } else {
            int64_t a = as_i(va), b = as_i(vb);
            if (ins.op == Instr::Eq) r = a == b;
            else if (ins.op == Instr::Ne) r = a != b;
            else if (ins.op == Instr::Lt) r = a < b;
            else if (ins.op == Instr::Le) r = a <= b;
            else if (ins.op == Instr::Gt) r = a > b;
            else r = a >= b;
          }
          env[ins.dest] = r;
          ++pc;
          break;
        }
        case Instr::And:
        case Instr::Or: {
          bool a = as_b(load_op(ins.a, env, err));
          bool b = as_b(load_op(ins.b, env, err));
          env[ins.dest] = (ins.op == Instr::And) ? (a && b) : (a || b);
          ++pc;
          break;
        }
        default:
          err = "istruzione stub non supportata";
          return int64_t{0};
      }
      if (!err.empty()) return int64_t{0};
    }
    err = "funzione terminata senza return";
    return int64_t{0};
  }
};

} // namespace cpython_llvm
