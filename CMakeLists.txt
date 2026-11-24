cmake_minimum_required(VERSION 3.24)

if(CMAKE_SOURCE_DIR STREQUAL CMAKE_BINARY_DIR)
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

add_executable(dictum
    cli/main.c
    runtime/native/proposal.c
)
set_target_properties(dictum PROPERTIES
    C_STANDARD 17
    C_STANDARD_REQUIRED YES
    C_EXTENSIONS NO
)
target_include_directories(dictum PRIVATE runtime/native)
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
    target_link_options(dictum PRIVATE "${dictum_sanitizer_flag}")
endif()

include(CTest)
if(BUILD_TESTING)
    add_subdirectory(tests)
endif()
