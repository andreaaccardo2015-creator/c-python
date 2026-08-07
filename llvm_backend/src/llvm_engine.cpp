#if defined(CPYTHON_HAS_LLVM)

#include "llvm_engine.h"

#include "llvm/ExecutionEngine/Orc/LLJIT.h"
#include "llvm/IR/IRBuilder.h"
#include "llvm/IR/LLVMContext.h"
#include "llvm/IR/Module.h"
#include "llvm/IR/Verifier.h"
#include "llvm/Support/TargetSelect.h"

#include <unordered_map>
#include <unordered_set>

using namespace llvm;
using namespace llvm::orc;

namespace cpython_llvm {
namespace {

Type* llvm_ty(LLVMContext& ctx, Ty t) {
  switch (t) {
    case Ty::F64: return Type::getDoubleTy(ctx);
    case Ty::Bool: return Type::getInt1Ty(ctx);
    case Ty::I64:
    default: return Type::getInt64Ty(ctx);
  }
}

class LlvmEngineImpl : public LlvmEngine {
public:
  static std::unique_ptr<LlvmEngineImpl> try_create() {
    InitializeNativeTarget();
    InitializeNativeTargetAsmPrinter();
    InitializeNativeTargetAsmParser();
    auto jit = LLJITBuilder().create();
    if (!jit) return nullptr;
    auto eng = std::unique_ptr<LlvmEngineImpl>(new LlvmEngineImpl());
    eng->jit_ = std::move(*jit);
    return eng;
  }

  bool compile(const FuncIR& fn, std::string& err) override {
    auto ctx = std::make_unique<LLVMContext>();
    auto mod = std::make_unique<Module>("cpython_jit", *ctx);
    IRBuilder<> builder(*ctx);

    std::vector<Type*> param_tys;
    for (auto& p : fn.params) param_tys.push_back(llvm_ty(*ctx, p.second));
    FunctionType* ft = FunctionType::get(llvm_ty(*ctx, fn.ret), param_tys, false);
    Function* f = Function::Create(ft, Function::ExternalLinkage, fn.name, *mod);

    size_t idx = 0;
    std::unordered_map<std::string, Value*> named;
    for (auto& arg : f->args()) {
      arg.setName(fn.params[idx].first);
      named[fn.params[idx].first] = &arg;
      ++idx;
    }

    BasicBlock* entry = BasicBlock::Create(*ctx, "entry", f);
    builder.SetInsertPoint(entry);

    std::unordered_map<std::string, BasicBlock*> blocks;
    // Pre-create blocks for labels
    for (auto& ins : fn.code) {
      if (ins.op == Instr::Label) {
        blocks[ins.target] = BasicBlock::Create(*ctx, ins.target, f);
      }
    }

    auto get_op = [&](const Operand& op) -> Value* {
      switch (op.kind) {
        case Operand::ImmI: return ConstantInt::get(Type::getInt64Ty(*ctx), op.i, true);
        case Operand::ImmF: return ConstantFP::get(Type::getDoubleTy(*ctx), op.f);
        case Operand::ImmB: return ConstantInt::get(Type::getInt1Ty(*ctx), op.b);
        case Operand::Name: {
          auto it = named.find(op.name);
          if (it == named.end()) return nullptr;
          return it->second;
        }
      }
      return nullptr;
    };

    bool terminated = false;
    for (auto& ins : fn.code) {
      if (ins.op == Instr::Label) {
        auto* bb = blocks[ins.target];
        if (!terminated) builder.CreateBr(bb);
        builder.SetInsertPoint(bb);
        terminated = false;
        continue;
      }
      if (terminated) continue;

      if (ins.op == Instr::Jump) {
        builder.CreateBr(blocks[ins.target]);
        terminated = true;
        continue;
      }
      if (ins.op == Instr::JumpIf || ins.op == Instr::JumpIfNot) {
        Value* c = get_op(ins.a);
        if (!c) { err = "cond mancante"; return false; }
        if (c->getType()->isIntegerTy(64))
          c = builder.CreateICmpNE(c, ConstantInt::get(c->getType(), 0));
        else if (c->getType()->isDoubleTy())
          c = builder.CreateFCmpONE(c, ConstantFP::get(c->getType(), 0.0));
        BasicBlock* then_bb = blocks[ins.target];
        BasicBlock* else_bb = BasicBlock::Create(*ctx, "fallthrough", f);
        if (ins.op == Instr::JumpIfNot) c = builder.CreateNot(c);
        builder.CreateCondBr(c, then_bb, else_bb);
        builder.SetInsertPoint(else_bb);
        continue;
      }
      if (ins.op == Instr::Ret) {
        Value* v = get_op(ins.a);
        if (!v) v = ConstantInt::get(llvm_ty(*ctx, fn.ret), 0);
        // cast to ret type if needed
        Type* rt = llvm_ty(*ctx, fn.ret);
        if (v->getType() != rt) {
          if (rt->isDoubleTy()) v = builder.CreateSIToFP(v, rt);
          else if (rt->isIntegerTy(64) && v->getType()->isDoubleTy())
            v = builder.CreateFPToSI(v, rt);
          else if (rt->isIntegerTy(1))
            v = builder.CreateICmpNE(v, Constant::getNullValue(v->getType()));
        }
        builder.CreateRet(v);
        terminated = true;
        continue;
      }

      Value* result = nullptr;
      Value* a = get_op(ins.a);
      Value* b = (ins.op == Instr::Neg || ins.op == Instr::Not || ins.op == Instr::Mov)
                     ? nullptr
                     : get_op(ins.b);

      switch (ins.op) {
        case Instr::Mov: result = a; break;
        case Instr::Neg:
          result = a->getType()->isDoubleTy() ? builder.CreateFNeg(a) : builder.CreateNeg(a);
          break;
        case Instr::Not:
          if (a->getType()->isIntegerTy(1)) result = builder.CreateNot(a);
          else result = builder.CreateICmpEQ(a, Constant::getNullValue(a->getType()));
          break;
        case Instr::Add:
          result = a->getType()->isDoubleTy() || (b && b->getType()->isDoubleTy())
                       ? builder.CreateFAdd(builder.CreateSIToFP(a, Type::getDoubleTy(*ctx)),
                                            builder.CreateSIToFP(b, Type::getDoubleTy(*ctx)))
                       : builder.CreateAdd(a, b);
          break;
        case Instr::Sub:
          result = a->getType()->isDoubleTy() || (b && b->getType()->isDoubleTy())
                       ? builder.CreateFSub(
                             a->getType()->isDoubleTy() ? a : builder.CreateSIToFP(a, Type::getDoubleTy(*ctx)),
                             b->getType()->isDoubleTy() ? b : builder.CreateSIToFP(b, Type::getDoubleTy(*ctx)))
                       : builder.CreateSub(a, b);
          break;
        case Instr::Mul:
          result = a->getType()->isDoubleTy() || (b && b->getType()->isDoubleTy())
                       ? builder.CreateFMul(
                             a->getType()->isDoubleTy() ? a : builder.CreateSIToFP(a, Type::getDoubleTy(*ctx)),
                             b->getType()->isDoubleTy() ? b : builder.CreateSIToFP(b, Type::getDoubleTy(*ctx)))
                       : builder.CreateMul(a, b);
          break;
        case Instr::Div:
          result = a->getType()->isDoubleTy() || (b && b->getType()->isDoubleTy())
                       ? builder.CreateFDiv(
                             a->getType()->isDoubleTy() ? a : builder.CreateSIToFP(a, Type::getDoubleTy(*ctx)),
                             b->getType()->isDoubleTy() ? b : builder.CreateSIToFP(b, Type::getDoubleTy(*ctx)))
                       : builder.CreateSDiv(a, b);
          break;
        case Instr::Mod:
          result = builder.CreateSRem(a, b);
          break;
        case Instr::Eq:
          result = a->getType()->isDoubleTy() ? builder.CreateFCmpOEQ(a, b) : builder.CreateICmpEQ(a, b);
          break;
        case Instr::Ne:
          result = a->getType()->isDoubleTy() ? builder.CreateFCmpONE(a, b) : builder.CreateICmpNE(a, b);
          break;
        case Instr::Lt:
          result = a->getType()->isDoubleTy() ? builder.CreateFCmpOLT(a, b) : builder.CreateICmpSLT(a, b);
          break;
        case Instr::Le:
          result = a->getType()->isDoubleTy() ? builder.CreateFCmpOLE(a, b) : builder.CreateICmpSLE(a, b);
          break;
        case Instr::Gt:
          result = a->getType()->isDoubleTy() ? builder.CreateFCmpOGT(a, b) : builder.CreateICmpSGT(a, b);
          break;
        case Instr::Ge:
          result = a->getType()->isDoubleTy() ? builder.CreateFCmpOGE(a, b) : builder.CreateICmpSGE(a, b);
          break;
        case Instr::And: result = builder.CreateAnd(a, b); break;
        case Instr::Or: result = builder.CreateOr(a, b); break;
        default: err = "op LLVM non supportato"; return false;
      }
      if (!result) { err = "operandi invalidi"; return false; }
      named[ins.dest] = result;
    }

    if (!terminated) {
      builder.CreateRet(Constant::getNullValue(llvm_ty(*ctx, fn.ret)));
    }

    std::string verr;
    raw_string_ostream os(verr);
    if (verifyModule(*mod, &os)) {
      err = "LLVM verify: " + verr;
      return false;
    }

    ThreadSafeModule tsm(std::move(mod), std::move(ctx));
    if (auto e = jit_->addIRModule(std::move(tsm))) {
      err = "addIRModule failed";
      return false;
    }
    compiled_.insert(fn.name);
    ret_tys_[fn.name] = fn.ret;
    return true;
  }

  bool has(const std::string& name) const override { return compiled_.count(name) != 0; }

  int64_t call_i64(const std::string& name, const int64_t* args, int n, std::string& err) override {
    auto sym = jit_->lookup(name);
    if (!sym) { err = "symbol not found"; return 0; }
    using Fn = int64_t (*)(int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t, int64_t);
    auto* fp = sym->toPtr<Fn>();
    int64_t a[8] = {};
    for (int i = 0; i < n && i < 8; ++i) a[i] = args[i];
    return fp(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7]);
  }

  double call_f64(const std::string& name, const double* args, int n, std::string& err) override {
    auto sym = jit_->lookup(name);
    if (!sym) { err = "symbol not found"; return 0; }
    using Fn = double (*)(double, double, double, double, double, double, double, double);
    auto* fp = sym->toPtr<Fn>();
    double a[8] = {};
    for (int i = 0; i < n && i < 8; ++i) a[i] = args[i];
    return fp(a[0], a[1], a[2], a[3], a[4], a[5], a[6], a[7]);
  }

private:
  LlvmEngineImpl() = default;
  std::unique_ptr<LLJIT> jit_;
  std::unordered_set<std::string> compiled_;
  std::unordered_map<std::string, Ty> ret_tys_;
};

} // namespace

std::unique_ptr<LlvmEngine> LlvmEngine::create() {
  return LlvmEngineImpl::try_create();
}

} // namespace cpython_llvm

#endif // CPYTHON_HAS_LLVM
