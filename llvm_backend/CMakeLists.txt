cmake_minimum_required(VERSION 3.16)
project(cpython_llvm LANGUAGES CXX)

set(CMAKE_CXX_STANDARD 17)
set(CMAKE_CXX_STANDARD_REQUIRED ON)

option(CPYTHON_FORCE_STUB "Forza stub IR interpreter senza LLVM" OFF)

set(CPYTHON_LLVM_SOURCES
  src/ir_parser.cpp
  src/c_api.cpp
)

find_package(LLVM CONFIG QUIET)
if(LLVM_FOUND AND NOT CPYTHON_FORCE_STUB)
  message(STATUS "LLVM trovato: ${LLVM_PACKAGE_VERSION} — ORC JIT abilitato")
  list(APPEND CPYTHON_LLVM_SOURCES src/llvm_engine.cpp)
  add_definitions(-DCPYTHON_HAS_LLVM)
  include_directories(${LLVM_INCLUDE_DIRS})
  llvm_map_components_to_libnames(LLVM_LIBS core orcjit native support irreader)
else()
  message(STATUS "LLVM non trovato (o FORCE_STUB): build stub C++ IR interpreter")
  set(LLVM_LIBS "")
endif()

add_library(cpython_llvm SHARED ${CPYTHON_LLVM_SOURCES})
target_compile_definitions(cpython_llvm PRIVATE CPYTHON_LLVM_EXPORTS)
target_include_directories(cpython_llvm
  PUBLIC ${CMAKE_CURRENT_SOURCE_DIR}/include
  PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/src
)
if(LLVM_FOUND AND NOT CPYTHON_FORCE_STUB)
  target_link_libraries(cpython_llvm PRIVATE ${LLVM_LIBS})
endif()

# Su MinGW collega runtime C++ staticamente così ctypes trova la DLL
if(MINGW)
  target_link_options(cpython_llvm PRIVATE -static-libgcc -static-libstdc++ -static)
endif()

# Copia DLL/so nella root llvm_backend/build per il bridge Python
set_target_properties(cpython_llvm PROPERTIES
  RUNTIME_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
  LIBRARY_OUTPUT_DIRECTORY ${CMAKE_BINARY_DIR}
  PREFIX ""
)

add_executable(cp_jit_smoke src/smoke_main.cpp)
target_link_libraries(cp_jit_smoke PRIVATE cpython_llvm)
target_include_directories(cp_jit_smoke PRIVATE ${CMAKE_CURRENT_SOURCE_DIR}/include)
