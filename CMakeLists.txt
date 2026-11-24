cmake_minimum_required(VERSION 3.24)

file(REAL_PATH "${CMAKE_SOURCE_DIR}" dictum_source_dir)
file(REAL_PATH "${CMAKE_BINARY_DIR}" dictum_binary_dir)
if(dictum_source_dir STREQUAL dictum_binary_dir)
    message(FATAL_ERROR "Gunakan direktori build terpisah, misalnya cmake -S . -B build/debug.")
endif()

project(Dictum VERSION 0.1.0 LANGUAGES C)

if(NOT CMAKE_C_COMPILER_ID MATCHES "^(GNU|Clang)$"
   OR CMAKE_C_COMPILER_FRONTEND_VARIANT STREQUAL "MSVC")
    message(FATAL_ERROR "Gunakan GCC atau Clang dengan driver bergaya GCC.")
endif()

option(DICTUM_ENABLE_ASAN "Aktifkan AddressSanitizer" OFF)
option(DICTUM_ENABLE_UBSAN "Aktifkan UndefinedBehaviorSanitizer" OFF)
set(DICTUM_VERSION "${PROJECT_VERSION}-dev")

find_package(Python3 REQUIRED COMPONENTS Interpreter)
find_package(OpenSSL 3.0 REQUIRED COMPONENTS Crypto)
file(GLOB ir_schemas CONFIGURE_DEPENDS "${CMAKE_CURRENT_SOURCE_DIR}/spec/ir/*.schema.json")
set(ir_generated "${CMAKE_CURRENT_BINARY_DIR}/ir_generated.inc")
add_custom_command(OUTPUT "${ir_generated}"
    COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_ir.py" "${ir_generated}"
    DEPENDS ${ir_schemas} tools/generate_ir.py tests/ir/schema_profile.py tests/ir/wire.py tests/ir/run.py tests/ir/semantics.py
    VERBATIM)
add_library(dictum_ir STATIC runtime/native/ir_wire.c runtime/native/ir_schema.c runtime/native/ir_digest.c "${ir_generated}")
target_include_directories(dictum_ir PUBLIC runtime/native PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(dictum_ir PUBLIC OpenSSL::Crypto)
set_target_properties(dictum_ir PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_compile_options(dictum_ir PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)

set(pipeline_generated "${CMAKE_CURRENT_BINARY_DIR}/pipeline_generated.inc")
add_custom_command(OUTPUT "${pipeline_generated}"
    COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_pipeline.py" "${pipeline_generated}"
    DEPENDS tools/generate_pipeline.py spec/pipeline/f0-c-fixture-v1.json
        catalog/core/intents-v1.json catalog/debian-13/v1.json tests/spikes/s2/development-v1.json
    VERBATIM)
set(renderer_unicode "${CMAKE_CURRENT_BINARY_DIR}/renderer_unicode.inc")
add_custom_command(OUTPUT "${renderer_unicode}"
    COMMAND "${Python3_EXECUTABLE}" -B "${CMAKE_CURRENT_SOURCE_DIR}/tools/generate_unicode.py" "${renderer_unicode}"
    DEPENDS tools/generate_unicode.py VERBATIM)
add_library(dictum_pipeline STATIC runtime/native/pipeline.c runtime/native/renderer.c
    "${pipeline_generated}" "${renderer_unicode}")
set_target_properties(dictum_pipeline PROPERTIES C_STANDARD 17 C_STANDARD_REQUIRED YES C_EXTENSIONS NO)
target_include_directories(dictum_pipeline PUBLIC runtime/native PRIVATE "${CMAKE_CURRENT_BINARY_DIR}")
target_link_libraries(dictum_pipeline PUBLIC dictum_ir)
target_compile_options(dictum_pipeline PRIVATE -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla)

add_executable(dictum cli/main.c)
set_target_properties(dictum PROPERTIES
    C_STANDARD 17
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS NO
)
target_include_directories(dictum PRIVATE runtime/native)
target_link_libraries(dictum PRIVATE dictum_pipeline)
target_compile_definitions(dictum PRIVATE DICTUM_VERSION="${DICTUM_VERSION}")
target_compile_options(dictum PRIVATE
    -Wall -Wextra -Wpedantic -Wconversion -Wshadow -Wformat=2
    -Wstrict-prototypes -Wmissing-prototypes -Wundef -Wvla
)

if(DICTUM_ENABLE_ASAN)
    list(APPEND dictum_sanitizers address)
endif()
if(DICTUM_ENABLE_UBSAN)
    list(APPEND dictum_sanitizers undefined)
    target_compile_options(dictum PRIVATE -fno-sanitize-recover=undefined)
endif()
if(dictum_sanitizers)
    list(JOIN dictum_sanitizers "," dictum_sanitizers)
    set(dictum_sanitizer_flag "-fsanitize=${dictum_sanitizers}")
    target_compile_options(dictum PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    target_compile_options(dictum_ir PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    target_compile_options(dictum_pipeline PRIVATE "${dictum_sanitizer_flag}" -fno-omit-frame-pointer)
    target_link_options(dictum_ir INTERFACE "${dictum_sanitizer_flag}")
    if(DICTUM_ENABLE_UBSAN)
        target_compile_options(dictum_ir PRIVATE -fno-sanitize-recover=undefined)
        target_compile_options(dictum_pipeline PRIVATE -fno-sanitize-recover=undefined)
    endif()
    target_link_options(dictum PRIVATE "${dictum_sanitizer_flag}")
endif()

include(CTest)
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()
